/// Keys written into package `data` for camera metadata and multi-shot paths.
abstract final class PackagePayloadKeys {
  /// Nested map: device, native_back_camera, poses[1..n] with exif + derived intrinsics.
  static const cameraCaptureContext = 'camera_capture_context';
}

/// Normalizes stored values for `camera_photo` fields (list of paths or single path).
abstract final class CapturedPhotoPaths {
  static List<String> list(dynamic v) {
    if (v == null) return [];
    if (v is List) return v.map((e) => e.toString()).where((s) => s.isNotEmpty).toList();
    if (v is String) return v.isEmpty ? [] : [v];
    return [];
  }

  static bool hasPhotos(dynamic v) => list(v).isNotEmpty;
}
