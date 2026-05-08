import 'dart:io';

import 'package:data_collector/core/device/device_camera_channel.dart';
import 'package:data_collector/core/device/device_sensor_fallback.dart';
import 'package:data_collector/features/collection/presentation/flow/package_payload_keys.dart';
import 'package:data_collector/features/collection/providers/wizard_state_provider.dart';
import 'package:device_info_plus/device_info_plus.dart';
import 'package:exif/exif.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Collects phone model, native camera intrinsics, per-image EXIF, and derived focal estimates.
class CameraMetadataCollector {
  CameraMetadataCollector._();

  static final DeviceInfoPlugin _deviceInfo = DeviceInfoPlugin();

  /// Call after each successful camera capture: fills [PackagePayloadKeys.cameraCaptureContext]
  /// with device + native intrinsics, and stores per-frame EXIF / derived data under [poseFieldId]
  /// as `{ "<abs-or-blob-path>": { exif, derived, collected_at } }`.
  static Future<void> attachPoseMetadata({
    required WidgetRef ref,
    required String projectId,
    required String poseFieldId,
    required String imagePath,
  }) async {
    if (kIsWeb) return;

    final notifier = ref.read(wizardStateProvider(projectId).notifier);
    final state = ref.read(wizardStateProvider(projectId));
    final ctx = _cloneContext(state[PackagePayloadKeys.cameraCaptureContext]);
    ctx.remove('poses');

    await _ensureDevice(ctx);
    await _ensureNativeCamera(ctx);

    final exifMap = await _readExifSubset(imagePath);
    final derived = _deriveIntrinsics(
      native: ctx['native_back_camera'] as Map<String, dynamic>?,
      exif: exifMap,
    );

    final dev = ctx['device'];
    final deviceModel = dev is Map ? dev['model']?.toString() : null;
    final frameCamera = buildFrameCamera(
      native: ctx['native_back_camera'] as Map<String, dynamic>?,
      exif: exifMap,
      derived: derived,
      deviceModel: deviceModel,
    );

    final shotMeta = <String, dynamic>{
      'exif': exifMap,
      'derived': derived,
      PackagePayloadKeys.frameCamera: frameCamera,
      'collected_at': DateTime.now().toUtc().toIso8601String(),
    };

    final pathMap = CapturedPhotoPaths.coerceToPathMetadataMap(state[poseFieldId]);
    pathMap[imagePath] = shotMeta;

    notifier.updateField(poseFieldId, pathMap);
    notifier.updateField(PackagePayloadKeys.cameraCaptureContext, ctx);
  }

  /// Удалить один кадр из поля ракурса (map path → meta) и убрать устаревший блок `poses` из контекста, если был.
  static void removePoseShotByPath({
    required WidgetRef ref,
    required String projectId,
    required String poseFieldId,
    required String imagePath,
  }) {
    final notifier = ref.read(wizardStateProvider(projectId).notifier);
    final state = ref.read(wizardStateProvider(projectId));
    final pathMap = CapturedPhotoPaths.coerceToPathMetadataMap(state[poseFieldId]);
    pathMap.remove(imagePath);
    notifier.updateField(poseFieldId, pathMap.isEmpty ? null : pathMap);

    final ctx = _cloneContext(state[PackagePayloadKeys.cameraCaptureContext]);
    if (ctx.remove('poses') != null) {
      notifier.updateField(PackagePayloadKeys.cameraCaptureContext, ctx);
    }
  }

  /// Удалить устаревший `camera_capture_context.poses` (раньше дублировали кадры).
  static void stripLegacyContextPoses({
    required WidgetRef ref,
    required String projectId,
  }) {
    final notifier = ref.read(wizardStateProvider(projectId).notifier);
    final state = ref.read(wizardStateProvider(projectId));
    final ctx = _cloneContext(state[PackagePayloadKeys.cameraCaptureContext]);
    if (ctx.remove('poses') == null) return;
    notifier.updateField(PackagePayloadKeys.cameraCaptureContext, ctx);
  }

  static Map<String, dynamic> _cloneContext(dynamic raw) {
    if (raw is Map<String, dynamic>) {
      return Map<String, dynamic>.from(raw);
    }
    return <String, dynamic>{};
  }

  static Future<void> _ensureDevice(Map<String, dynamic> ctx) async {
    if (ctx.containsKey('device')) return;
    if (kIsWeb) {
      ctx['device'] = <String, dynamic>{'platform': 'web'};
      return;
    }
    if (Platform.isAndroid) {
      final a = await _deviceInfo.androidInfo;
      ctx['device'] = <String, dynamic>{
        'platform': 'android',
        'model': a.model,
        'brand': a.brand,
        'manufacturer': a.manufacturer,
        'device': a.device,
        'product': a.product,
        'hardware': a.hardware,
        'sdk_int': a.version.sdkInt,
        'release': a.version.release,
      };
      return;
    }
    if (Platform.isIOS) {
      final i = await _deviceInfo.iosInfo;
      ctx['device'] = <String, dynamic>{
        'platform': 'ios',
        'model': i.model,
        'machine': i.utsname.machine,
        'name': i.name,
        'system_version': i.systemVersion,
      };
    }
  }

  static Future<void> _ensureNativeCamera(Map<String, dynamic> ctx) async {
    if (ctx.containsKey('native_back_camera')) return;
    final native = await DeviceCameraChannel.getBackCameraIntrinsics();
    ctx['native_back_camera'] = native;
  }

  static const int _maxExifValueChars = 8000;

  static Future<Map<String, dynamic>> _readExifSubset(String path) async {
    final out = <String, dynamic>{};
    try {
      final bytes = await File(path).readAsBytes();
      final data = await readExifFromBytes(bytes);
      if (data.isEmpty) return out;

      for (final e in data.entries) {
        final key = e.key.toString();
        final tag = e.value;
        try {
          var s = tag.printable;
          if (s.length > _maxExifValueChars) {
            s = '${s.substring(0, _maxExifValueChars)}…(truncated, ${_maxExifValueChars} chars max)';
            out['${key}__value_truncated'] = true;
          }
          out[key] = s;
        } catch (_) {
          out[key] = tag.toString();
        }
      }
    } catch (_) {
      // ignore corrupt / missing exif
    }
    return out;
  }

  /// Combines native sensor + lens data with EXIF when native is incomplete.
  static Map<String, dynamic> _deriveIntrinsics({
    required Map<String, dynamic>? native,
    required Map<String, dynamic> exif,
  }) {
    final d = <String, dynamic>{};

    double? focalMm;
    double? focal35;
    int? imgW;
    int? imgH;
    for (final e in exif.entries) {
      final k = e.key.toString();
      final ku = k.toUpperCase();
      if (focalMm == null && ku.contains('FOCALLENGTH') && !ku.contains('35')) {
        focalMm = _parseRational(e.value);
      }
      if (focal35 == null && ku.contains('FOCALLENGTH') && ku.contains('35')) {
        focal35 = _parseInt(e.value)?.toDouble();
      }
      if (imgW == null && (ku.contains('EXIFIMAGEWIDTH') || ku == 'IMAGE WIDTH')) {
        imgW = _parseInt(e.value);
      }
      if (imgH == null && (ku.contains('EXIFIMAGELENGTH') || ku == 'IMAGE LENGTH')) {
        imgH = _parseInt(e.value);
      }
    }

    final sensorWmm = _asDouble(native?['sensor_physical_width_mm']);
    final sensorHmm = _asDouble(native?['sensor_physical_height_mm']);
    final pxW = _asInt(native?['sensor_pixel_array_width']);
    final pxH = _asInt(native?['sensor_pixel_array_height']);

    final calList = _asDoubleList(native?['lens_intrinsic_calibration_px']) ??
        _calibrationFromCamera2Map(native?['camera2_characteristics'] as Map<String, dynamic>?);
    if (calList != null && calList.length >= 4) {
      d['fx_px_from_lens_intrinsic_calibration'] = calList[0];
      d['fy_px_from_lens_intrinsic_calibration'] = calList[1];
      d['cx_px_from_lens_intrinsic_calibration'] = calList[2];
      d['cy_px_from_lens_intrinsic_calibration'] = calList[3];
      if (calList.length >= 5) {
        d['skew_from_lens_intrinsic_calibration'] = calList[4];
      }
    }

    final nativeFx = _asDouble(native?['estimated_fx_px']);
    final nativeFy = _asDouble(native?['estimated_fy_px']);

    if (nativeFx != null) d['fx_px_from_native_mm'] = nativeFx;
    if (nativeFy != null) d['fy_px_from_native_mm'] = nativeFy;

    // Pinhole: fx_px = f_mm / sensor_width_mm * image_width_px (full sensor; EXIF size may differ)
    if (focalMm != null && sensorWmm != null && sensorWmm > 0 && imgW != null) {
      d['fx_px_from_exif_focal_and_native_sensor'] = (focalMm / sensorWmm) * imgW;
    }

    // Classic 35mm equivalent scaling (when sensor intrinsics missing in EXIF)
    if (focal35 != null && focal35 > 0 && imgW != null) {
      d['fx_px_from_35mm_equiv'] = (imgW / 36.0) * focal35;
    }

    // Prefer OEM intrinsic calibration when present, then EXIF+sensor, then pinhole native, then 35mm equiv.
    if (d.containsKey('fx_px_from_lens_intrinsic_calibration')) {
      d['preferred_fx_px_estimate'] = d['fx_px_from_lens_intrinsic_calibration'];
    } else if (d.containsKey('fx_px_from_exif_focal_and_native_sensor')) {
      d['preferred_fx_px_estimate'] = d['fx_px_from_exif_focal_and_native_sensor'];
    } else if (d.containsKey('fx_px_from_native_mm')) {
      d['preferred_fx_px_estimate'] = d['fx_px_from_native_mm'];
    } else if (d.containsKey('fx_px_from_35mm_equiv')) {
      d['preferred_fx_px_estimate'] = d['fx_px_from_35mm_equiv'];
    }

    d['notes'] = <String, dynamic>{
      'image_width_exif': imgW,
      'image_height_exif': imgH,
      'sensor_width_mm_native': sensorWmm,
      'sensor_height_mm_native': sensorHmm,
      'pixel_array_native': (pxW != null && pxH != null) ? '${pxW}x$pxH' : null,
      'focal_length_mm_exif': focalMm,
      'focal_length_35mm_equiv_exif': focal35,
    };

    return d;
  }

  /// Intrinsics for the **saved image file** (EXIF image width/height), for depth / K consumers.
  static Map<String, dynamic> buildFrameCamera({
    required Map<String, dynamic>? native,
    required Map<String, dynamic> exif,
    required Map<String, dynamic> derived,
    String? deviceModel,
  }) {
    final notes = derived['notes'];
    final notesMap = <String, dynamic>{};
    if (notes is Map) {
      notes.forEach((k, v) => notesMap[k.toString()] = v);
    }

    var imgW = _asInt(notesMap['image_width_exif']);
    var imgH = _asInt(notesMap['image_height_exif']);
    if (imgW == null || imgH == null) {
      final d = _parseExifImageDimensions(exif);
      imgW = imgW ?? d.$1;
      imgH = imgH ?? d.$2;
    }

    final natW = _asInt(native?['sensor_pixel_array_width']);
    final natH = _asInt(native?['sensor_pixel_array_height']);

    var focalMm = _asDouble(notesMap['focal_length_mm_exif']);
    focalMm ??= _asDouble(native?['primary_focal_length_mm']);

    final sensorWmm = _asDouble(notesMap['sensor_width_mm_native']) ?? _asDouble(native?['sensor_physical_width_mm']);
    final sensorHmm = _asDouble(notesMap['sensor_height_mm_native']) ?? _asDouble(native?['sensor_physical_height_mm']);

    final focal35 = _asDouble(notesMap['focal_length_35mm_equiv_exif']);

    var source = _intrinsicsSourceFromDerived(derived);
    double? fx;
    double? fy;
    double? cx;
    double? cy;
    double? skew;
    var principalPointFallback = false;

    final natFx = _asDouble(derived['fx_px_from_native_mm']);
    final natFy = _asDouble(derived['fy_px_from_native_mm']);

    if (imgW != null &&
        imgH != null &&
        natW != null &&
        natH != null &&
        natW > 0 &&
        natH > 0) {
      final sx = imgW / natW;
      final sy = imgH / natH;

      if (derived.containsKey('fx_px_from_lens_intrinsic_calibration')) {
        final fxN = _asDouble(derived['fx_px_from_lens_intrinsic_calibration']);
        final fyN = _asDouble(derived['fy_px_from_lens_intrinsic_calibration']);
        final cxN = _asDouble(derived['cx_px_from_lens_intrinsic_calibration']);
        final cyN = _asDouble(derived['cy_px_from_lens_intrinsic_calibration']);
        skew = _asDouble(derived['skew_from_lens_intrinsic_calibration']);
        if (fxN != null) fx = fxN * sx;
        if (fyN != null) fy = fyN * sy;
        if (cxN != null) cx = cxN * sx;
        if (cyN != null) cy = cyN * sy;
      } else if (derived.containsKey('fx_px_from_exif_focal_and_native_sensor')) {
        fx = _asDouble(derived['fx_px_from_exif_focal_and_native_sensor']);
        if (focalMm != null && sensorHmm != null && sensorHmm > 0) {
          fy = (focalMm / sensorHmm) * imgH;
        } else if (natFy != null) {
          fy = natFy * sy;
        } else {
          fy = fx;
        }
        cx = imgW / 2.0;
        cy = imgH / 2.0;
      } else if (derived.containsKey('fx_px_from_native_mm') && natFx != null) {
        fx = natFx * sx;
        fy = (natFy ?? natFx) * sy;
        cx = imgW / 2.0;
        cy = imgH / 2.0;
      } else if (derived.containsKey('fx_px_from_35mm_equiv')) {
        fx = _asDouble(derived['fx_px_from_35mm_equiv']);
        fy = fx;
        cx = imgW / 2.0;
        cy = imgH / 2.0;
      }
    }

    if (fx != null && imgW != null && imgH != null && _isInvalidPrincipalPoint(cx, cy, imgW, imgH)) {
      // Some Android vendors expose LENS_INTRINSIC_CALIBRATION with cx/cy=0 placeholders.
      final estCxNative = _asDouble(native?['estimated_cx_px']);
      final estCyNative = _asDouble(native?['estimated_cy_px']);
      if (estCxNative != null && estCyNative != null && natW != null && natH != null && natW > 0 && natH > 0) {
        cx = estCxNative * (imgW / natW);
        cy = estCyNative * (imgH / natH);
      }
      if (_isInvalidPrincipalPoint(cx, cy, imgW, imgH)) {
        cx = imgW / 2.0;
        cy = imgH / 2.0;
      }
      principalPointFallback = true;
      if (source == 'lens_intrinsic_calibration') {
        source = 'lens_intrinsic_calibration_with_principal_point_fallback';
      }
    }

    if (fx == null && source == 'incomplete') {
      final fb = DeviceSensorFallback.lookupSensorMm(deviceModel);
      if (fb != null && focalMm != null && imgW != null && imgH != null) {
        final sw = fb['sensor_width_mm']!;
        final sh = fb['sensor_height_mm']!;
        if (sw > 0 && sh > 0) {
          fx = (focalMm / sw) * imgW;
          fy = (focalMm / sh) * imgH;
          cx = imgW / 2.0;
          cy = imgH / 2.0;
          source = 'fallback_device_db';
        }
      }
    }

    if (fx != null && (cx == null || cy == null) && imgW != null && imgH != null) {
      cx = imgW / 2.0;
      cy = imgH / 2.0;
    }

    final orientation = _exifOrientationTag(exif);

    final out = <String, dynamic>{
      if (imgW != null) 'image_width_px': imgW,
      if (imgH != null) 'image_height_px': imgH,
      if (fx != null) 'fx_px': fx,
      if (fy != null) 'fy_px': fy,
      if (cx != null) 'cx_px': cx,
      if (cy != null) 'cy_px': cy,
      if (focalMm != null) 'focal_length_mm': focalMm,
      if (sensorWmm != null) 'sensor_width_mm': sensorWmm,
      if (sensorHmm != null) 'sensor_height_mm': sensorHmm,
      if (focal35 != null) 'focal_length_35mm_equiv': focal35,
      'intrinsics_source': source,
      if (principalPointFallback) 'principal_point_fallback_applied': true,
      if (skew != null) 'skew': skew,
      if (orientation != null) 'image_orientation_exif': orientation,
    };

    final dist = native?['lens_distortion'];
    if (dist is List && dist.isNotEmpty) {
      final nums = <double>[];
      for (final e in dist) {
        final d = _asDouble(e);
        if (d != null) nums.add(d);
      }
      if (nums.isNotEmpty) out['lens_distortion'] = nums;
    }

    return out;
  }

  static String _intrinsicsSourceFromDerived(Map<String, dynamic> derived) {
    if (derived.containsKey('fx_px_from_lens_intrinsic_calibration')) {
      return 'lens_intrinsic_calibration';
    }
    if (derived.containsKey('fx_px_from_exif_focal_and_native_sensor')) {
      return 'exif_focal_sensor';
    }
    if (derived.containsKey('fx_px_from_native_mm')) {
      return 'native_pinhole';
    }
    if (derived.containsKey('fx_px_from_35mm_equiv')) {
      return '35mm_equiv';
    }
    return 'incomplete';
  }

  static (int?, int?) _parseExifImageDimensions(Map<String, dynamic> exif) {
    int? w;
    int? h;
    for (final e in exif.entries) {
      final k = e.key.toString().toUpperCase();
      if (w == null && (k.contains('EXIFIMAGEWIDTH') || k == 'IMAGE WIDTH')) {
        w = _parseInt(e.value);
      }
      if (h == null && (k.contains('EXIFIMAGELENGTH') || k == 'IMAGE LENGTH')) {
        h = _parseInt(e.value);
      }
    }
    return (w, h);
  }

  static String? _exifOrientationTag(Map<String, dynamic> exif) {
    for (final e in exif.entries) {
      final k = e.key.toString().toUpperCase();
      if (k.contains('ORIENTATION')) {
        return e.value?.toString();
      }
    }
    return null;
  }

  static bool _isInvalidPrincipalPoint(double? cx, double? cy, int imgW, int imgH) {
    if (cx == null || cy == null) return true;
    // Treat near-zero as invalid for smartphone camera calibration.
    if (cx.abs() < 1.0 && cy.abs() < 1.0) return true;
    if (cx < 0 || cx > imgW) return true;
    if (cy < 0 || cy > imgH) return true;
    return false;
  }

  static double? _asDouble(dynamic v) {
    if (v == null) return null;
    if (v is double) return v;
    if (v is int) return v.toDouble();
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString());
  }

  static int? _asInt(dynamic v) {
    if (v == null) return null;
    if (v is int) return v;
    if (v is double) return v.round();
    return int.tryParse(v.toString());
  }

  static double? _parseRational(dynamic v) {
    if (v == null) return null;
    final s = v.toString();
    if (s.contains('/')) {
      final parts = s.split('/');
      if (parts.length == 2) {
        final a = double.tryParse(parts[0].trim());
        final b = double.tryParse(parts[1].trim());
        if (a != null && b != null && b != 0) return a / b;
      }
    }
    return double.tryParse(s);
  }

  static int? _parseInt(dynamic v) => _asInt(v);

  static List<double>? _asDoubleList(dynamic v) {
    if (v is! List || v.isEmpty) return null;
    final out = <double>[];
    for (final e in v) {
      final d = _asDouble(e);
      if (d == null) return null;
      out.add(d);
    }
    return out;
  }

  /// Fallback when only [camera2_characteristics] is present (e.g. hand-built JSON).
  static List<double>? _calibrationFromCamera2Map(Map<String, dynamic>? m) {
    if (m == null) return null;
    final raw = m['android.lens.intrinsicCalibration'];
    return _asDoubleList(raw);
  }
}
