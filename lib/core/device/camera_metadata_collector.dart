import 'dart:io';

import 'package:data_collector/core/device/device_camera_channel.dart';
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

    final shotMeta = <String, dynamic>{
      'exif': exifMap,
      'derived': derived,
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
