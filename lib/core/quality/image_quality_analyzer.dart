import 'image_quality_analyze_io.dart' if (dart.library.html) 'image_quality_analyze_web.dart';
import 'package:data_collector/core/quality/image_quality_types.dart';
import 'package:flutter/foundation.dart';

export 'image_quality_types.dart' show ImageQualityResult, ImageQualityThresholds;

/// Анализ в isolate, чтобы не блокировать UI.
Future<ImageQualityResult> analyzeCaptureQuality(String imagePath) async {
  if (kIsWeb) return ImageQualityResult.ok(skipped: true);
  try {
    return await compute(analyzeCaptureQualityInIsolate, imagePath);
  } catch (_) {
    return ImageQualityResult.ok(skipped: true);
  }
}
