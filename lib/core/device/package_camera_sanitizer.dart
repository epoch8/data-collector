import 'package:data_collector/features/collection/presentation/flow/package_payload_keys.dart';

/// Rewrites package `data` for persistence: compact [PackagePayloadKeys.cameraSession],
/// heavy capture dump under [PackagePayloadKeys.cameraDebug], hoists per-shot
/// `exif` / `derived` into [PackagePayloadKeys.cameraSupplement].
void sanitizePackageCameraPayload(Map<String, dynamic> data) {
  _splitCaptureContext(data);
  _hoistShotSupplementsDeep(data);
}

void _splitCaptureContext(Map<String, dynamic> data) {
  Map<String, dynamic>? ctx;
  if (data.containsKey(PackagePayloadKeys.cameraCaptureContext)) {
    final raw = data.remove(PackagePayloadKeys.cameraCaptureContext);
    if (raw is Map<String, dynamic>) {
      ctx = Map<String, dynamic>.from(raw);
    } else if (raw is Map) {
      ctx = Map<String, dynamic>.from(raw.map((k, v) => MapEntry(k.toString(), v)));
    }
  } else if (data.containsKey('korovas_camera_context')) {
    final raw = data.remove('korovas_camera_context');
    if (raw is Map<String, dynamic>) {
      ctx = Map<String, dynamic>.from(raw);
    } else if (raw is Map) {
      ctx = Map<String, dynamic>.from(raw.map((k, v) => MapEntry(k.toString(), v)));
    }
  }
  if (ctx == null || ctx.isEmpty) return;

  final session = <String, dynamic>{};
  final device = ctx['device'];
  if (device != null) session['device'] = device;

  final native = ctx['native_back_camera'];
  if (native is Map<String, dynamic>) {
    session['native_back_camera'] = _nativeSummaryWithoutCamera2(native);
  } else if (native is Map) {
    session['native_back_camera'] = _nativeSummaryWithoutCamera2(
      Map<String, dynamic>.from(native.map((k, v) => MapEntry(k.toString(), v))),
    );
  }

  data[PackagePayloadKeys.cameraSession] = session;

  final debug = <String, dynamic>{
    PackagePayloadKeys.cameraCaptureContext: ctx,
  };
  final existing = data[PackagePayloadKeys.cameraDebug];
  if (existing is Map<String, dynamic>) {
    existing.addAll(debug);
    data[PackagePayloadKeys.cameraDebug] = existing;
  } else if (existing is Map) {
    final m = Map<String, dynamic>.from(existing.map((k, v) => MapEntry(k.toString(), v)));
    m.addAll(debug);
    data[PackagePayloadKeys.cameraDebug] = m;
  } else {
    data[PackagePayloadKeys.cameraDebug] = debug;
  }
}

Map<String, dynamic> _nativeSummaryWithoutCamera2(Map<String, dynamic> native) {
  final out = Map<String, dynamic>.from(native);
  out.remove('camera2_characteristics');
  return out;
}

void _hoistShotSupplementsDeep(dynamic node) {
  if (node is Map<String, dynamic>) {
    _maybeHoistShotSupplement(node);
    for (final k in node.keys.toList()) {
      _hoistShotSupplementsDeep(node[k]);
    }
  } else if (node is Map) {
    final m = Map<String, dynamic>.from(node.map((k, v) => MapEntry(k.toString(), v)));
    _maybeHoistShotSupplement(m);
    node
      ..clear()
      ..addAll(m);
    for (final k in node.keys.toList()) {
      _hoistShotSupplementsDeep(node[k]);
    }
  } else if (node is List) {
    for (final item in node) {
      _hoistShotSupplementsDeep(item);
    }
  }
}

void _maybeHoistShotSupplement(Map<String, dynamic> m) {
  if (!m.containsKey('collected_at')) return;
  if (!m.containsKey('exif') && !m.containsKey('derived')) return;
  if (m.containsKey(PackagePayloadKeys.cameraSupplement)) return;

  final sup = <String, dynamic>{};
  final ex = m.remove('exif');
  final der = m.remove('derived');
  if (ex != null) sup['exif'] = ex;
  if (der != null) sup['derived'] = der;
  if (sup.isNotEmpty) {
    m[PackagePayloadKeys.cameraSupplement] = sup;
  }
}
