/// Keys written into package `data` for camera metadata and multi-shot paths.
abstract final class PackagePayloadKeys {
  /// Nested map: device, native_back_camera, poses[1..n] with exif + derived intrinsics.
  static const cameraCaptureContext = 'camera_capture_context';

  /// Compact camera session at package save (no Camera2 dump).
  static const cameraSession = 'camera_session';

  /// Full capture context + heavy blobs for debugging.
  static const cameraDebug = 'camera_debug';

  /// Per-shot primary intrinsics for the saved image file (JPEG coordinates).
  static const frameCamera = 'frame_camera';

  /// Per-shot EXIF + derived alternatives (after materialize).
  static const cameraSupplement = 'camera_supplement';

  /// Индекс шага сценария сбора в незавершённом пакете (черновик); не уходит на сервер.
  static const collectionDraftFlowStep = '_collection_draft_flow_step';
}

/// Normalizes stored values for `camera_photo` fields:
/// a list of paths, a single path string, or a map `{ pathOrBlobUri: { exif, derived, … } }`.
abstract final class CapturedPhotoPaths {
  static List<String> list(dynamic v) {
    if (v == null) return [];
    if (v is Map) {
      return v.keys.map((e) => e.toString()).where((s) => s.isNotEmpty).toList();
    }
    if (v is List) return v.map((e) => e.toString()).where((s) => s.isNotEmpty).toList();
    if (v is String) return v.isEmpty ? [] : [v];
    return [];
  }

  static bool hasPhotos(dynamic v) => list(v).isNotEmpty;

  /// For subject-grouped flow: merge list/legacy values into a path → metadata map (metadata may be empty).
  static Map<String, dynamic> coerceToPathMetadataMap(dynamic v) {
    if (v == null) return {};
    if (v is Map) {
      final out = <String, dynamic>{};
      for (final e in v.entries) {
        final ks = e.key.toString();
        if (ks.isEmpty) continue;
        final val = e.value;
        if (val is Map<String, dynamic>) {
          out[ks] = Map<String, dynamic>.from(val);
        } else if (val is Map) {
          out[ks] = Map<String, dynamic>.from(val.map((k, x) => MapEntry(k.toString(), x)));
        } else {
          out[ks] = <String, dynamic>{};
        }
      }
      return out;
    }
    if (v is List) {
      final out = <String, dynamic>{};
      for (final p in v) {
        final s = p?.toString() ?? '';
        if (s.isNotEmpty) out[s] = <String, dynamic>{};
      }
      return out;
    }
    if (v is String && v.isNotEmpty) {
      return {v: <String, dynamic>{}};
    }
    return {};
  }
}
