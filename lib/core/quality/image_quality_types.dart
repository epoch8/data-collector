import 'package:data_collector/l10n/locale_controller.dart';

/// Эвристическая оценка кадра без ML. Пороги настроены **строже**, чем в первой версии:
/// средняя яркость сама по себе часто «обманывает» (одно яркое пятно), поэтому добавлены
/// доли тёмных/светлых пикселей и перцентили. Размытие — по **двум** признакам (лапласиан + градиенты).
///
/// Подстройка: см. [ImageQualityThresholds].
abstract final class ImageQualityThresholds {
  static const int analysisLongestSide = 480;
  static const double minMeanLuma = 40;
  static const double maxMeanLuma = 232;
  static const double minP10Luma = 12;
  static const double maxP90Luma = 245;
  static const double maxDarkPixelFraction = 0.52;
  static const int darkPixelLumaCutoff = 22;
  static const double shadowChecksMeanGate = 50;
  static const double maxBrightPixelFraction = 0.34;
  static const int brightPixelLumaCutoff = 245;
  static const double minLumaStdDev = 11;
  static const double minLaplacianVariance = 58;
  static const double minGradientEnergy = 260;
}

class ImageQualityResult {
  const ImageQualityResult({
    required this.isAcceptable,
    required this.issues,
    this.meanLuma,
    this.lumaStdDev,
    this.laplacianVariance,
    this.gradientEnergy,
    this.skipped = false,
  });

  final bool isAcceptable;
  final List<String> issues;
  final double? meanLuma;
  final double? lumaStdDev;
  final double? laplacianVariance;
  final double? gradientEnergy;
  final bool skipped;

  static ImageQualityResult ok({bool skipped = false}) =>
      ImageQualityResult(isAcceptable: true, issues: const [], skipped: skipped);

  static bool get _isRu => appLocaleNotifier.value.languageCode == 'ru';

  String get userMessage {
    if (issues.isEmpty) {
      return _isRu ? 'Качество кадра в порядке.' : 'Image quality looks good.';
    }
    final title = _isRu ? 'Кадр не прошёл проверку:' : 'Frame did not pass quality check:';
    return '$title\n${issues.map((e) => '• $e').join('\n')}';
  }
}
