/// Fallback sensor physical size (mm) when native Camera2 / EXIF pipeline is incomplete.
/// Values are approximate; extend per popular devices as needed (see OpenMVG sensor DB).
abstract final class DeviceSensorFallback {
  /// Returns `sensor_width_mm`, `sensor_height_mm` if [model] matches a known entry.
  static Map<String, double>? lookupSensorMm(String? model) {
    if (model == null || model.isEmpty) return null;
    final m = model.trim().toUpperCase();

    if (m.contains('SM-A505')) {
      return {'sensor_width_mm': 5.184, 'sensor_height_mm': 3.888};
    }
    if (m.contains('SM-G973') || m.contains('S10')) {
      return {'sensor_width_mm': 5.65, 'sensor_height_mm': 4.23};
    }
    if (m.contains('PIXEL 7')) {
      return {'sensor_width_mm': 9.8, 'sensor_height_mm': 7.36};
    }

    return null;
  }
}
