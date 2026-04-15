/// JSON keys for Korovas scan payload (korova_data + timestamp + pictures paths).
abstract final class KorovasKeys {
  static const scanTime = 'scan_time';
  /// Spec 02: `cow_identifier`; старые пакеты могут содержать `cow_id` (см. разбор в истории).
  static const cowId = 'cow_identifier';
  static const cowAge = 'cow_age';
  static const cowWeight = 'cow_weight';
  static const cowBreed = 'cow_breed';

  static String pose(int index1Based) => 'pose_$index1Based';

  /// Nested map: device, native_back_camera, poses[1..3] with exif + derived intrinsics.
  static const cameraContext = 'korovas_camera_context';
}

/// Значение [KorovasKeys.pose] — список путей к файлам (несколько кадров на ракурс) или один путь (устар.).
abstract final class KorovasPosePaths {
  static List<String> list(dynamic v) {
    if (v == null) return [];
    if (v is List) return v.map((e) => e.toString()).where((s) => s.isNotEmpty).toList();
    if (v is String) return v.isEmpty ? [] : [v];
    return [];
  }

  static bool hasPhotos(dynamic v) => list(v).isNotEmpty;
}
