import 'package:data_collector/core/quality/image_quality_types.dart';

ImageQualityResult analyzeCaptureQualityInIsolate(String imagePath) =>
    ImageQualityResult.ok(skipped: true);
