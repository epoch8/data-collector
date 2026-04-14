import 'dart:io';
import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:image/image.dart' as img;

/// Эвристическая оценка кадра без ML. Пороги настроены **строже**, чем в первой версии:
/// средняя яркость сама по себе часто «обманывает» (одно яркое пятно), поэтому добавлены
/// доли тёмных/светлых пикселей и перцентили. Размытие — по **двум** признакам (лапласиан + градиенты).
///
/// Подстройка: см. [ImageQualityThresholds].
abstract final class ImageQualityThresholds {
  /// Длинная сторона превью для анализа (больше — стабильнее метрики, чуть дольше в isolate).
  static const int analysisLongestSide = 480;

  /// Средняя яркость (0–255): ниже — в целом слишком темно (порог мягче — допускаем тени на объекте).
  static const double minMeanLuma = 40;

  /// Средняя яркость: выше — в целом пересвет.
  static const double maxMeanLuma = 232;

  /// 10-й перцентиль: низкий p10 нормален при контровом свете / тени на части кадра — порог ослаблен.
  static const double minP10Luma = 12;

  /// 90-й перцентиль: если высокий — много «вылезших» светлых участков.
  static const double maxP90Luma = 245;

  /// Доля **очень** тёмных пикселей (см. [darkPixelLumaCutoff]): тени допустимы, ругаем только сильный недосвет.
  static const double maxDarkPixelFraction = 0.52;
  /// Считаем «тёмными» только пиксели не ярче этого уровня (ниже порог — строже метрика, выше — мягче).
  static const int darkPixelLumaCutoff = 22;

  /// Тени на части кадра (низкий p10 / много тёмных пикселей) не считаем браком, если средняя яркость выше этого —
  /// типично объект в свете, углы в тени.
  static const double shadowChecksMeanGate = 50;

  /// Доля очень светлых пикселей — вспышка / выбитые блики.
  static const double maxBrightPixelFraction = 0.34;
  static const int brightPixelLumaCutoff = 245;

  /// Стандартное отклонение яркости: низкое — мало деталей / «серое полотно».
  static const double minLumaStdDev = 11;

  /// Дисперсия лапласиана: типично падает при сильном размытии.
  static const double minLaplacianVariance = 58;

  /// Средняя энергия градиента (горизонталь + вертикаль): падает при смазе и сильном блюре.
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

  String get userMessage {
    if (issues.isEmpty) return 'Качество кадра в порядке.';
    return 'Кадр не прошёл проверку:\n${issues.map((e) => '• $e').join('\n')}';
  }
}

/// Анализ в isolate, чтобы не блокировать UI.
Future<ImageQualityResult> analyzeCaptureQuality(String imagePath) async {
  if (kIsWeb) return ImageQualityResult.ok(skipped: true);
  try {
    return await compute(_analyzeInIsolate, imagePath);
  } catch (_) {
    return ImageQualityResult.ok(skipped: true);
  }
}

ImageQualityResult _analyzeInIsolate(String imagePath) {
  try {
    final file = File(imagePath);
    if (!file.existsSync()) return ImageQualityResult.ok(skipped: true);
    final bytes = file.readAsBytesSync();
    final decoded = img.decodeImage(bytes);
    if (decoded == null) return ImageQualityResult.ok(skipped: true);

    final resized = _resizeLongestSide(decoded, ImageQualityThresholds.analysisLongestSide);
    final gray = img.grayscale(resized);

    final lumaStats = _lumaMeanAndStd(gray);
    final hist = _lumaHistogram(gray);
    final p10 = _percentileFromHistogram(hist, gray.width * gray.height, 0.10);
    final p90 = _percentileFromHistogram(hist, gray.width * gray.height, 0.90);
    final darkFrac = _fractionBelow(hist, ImageQualityThresholds.darkPixelLumaCutoff, gray.width * gray.height);
    final brightFrac = _fractionAbove(hist, ImageQualityThresholds.brightPixelLumaCutoff, gray.width * gray.height);

    final lapVar = _laplacianVariance(gray);
    final gradE = _gradientEnergy(gray);

    final issues = <String>[];

    if (lumaStats.mean < ImageQualityThresholds.minMeanLuma) {
      issues.add('слишком тёмно — добавьте света на объект или включите вспышку');
    }
    if (lumaStats.mean > ImageQualityThresholds.maxMeanLuma) {
      issues.add('слишком светло / пересвет — снимайте без прямого света в объектив, при необходимости снизьте экспозицию');
    }
    if (p10 < ImageQualityThresholds.minP10Luma &&
        lumaStats.mean < ImageQualityThresholds.shadowChecksMeanGate) {
      issues.add('большая часть кадра в тени — подсветите сцену равномернее');
    }
    if (p90 > ImageQualityThresholds.maxP90Luma) {
      issues.add('много пересвеченных участков — отойдите от яркого источника или смените ракурс');
    }
    if (darkFrac > ImageQualityThresholds.maxDarkPixelFraction &&
        lumaStats.mean < ImageQualityThresholds.shadowChecksMeanGate) {
      issues.add('слишком много тёмных пикселей — улучшите освещение');
    }
    if (brightFrac > ImageQualityThresholds.maxBrightPixelFraction) {
      issues.add('слишком много «вылезшего» белого — уберите засвет / блики');
    }
    if (lumaStats.stdDev < ImageQualityThresholds.minLumaStdDev) {
      issues.add('мало контраста — кадр выглядит «плоским», добавьте направленный свет');
    }

    // Размытие: любой из показателей ниже порога — кадр считаем недостаточно «чётким» (строже, чем AND).
    final lapLow = lapVar < ImageQualityThresholds.minLaplacianVariance;
    final gradLow = gradE < ImageQualityThresholds.minGradientEnergy;
    if (lapLow || gradLow) {
      final hint = lapLow && gradLow
          ? 'сильное размытие или смаз'
          : lapLow
              ? 'мало высокочастотных деталей (возможен смаз или сильное сжатие)'
              : 'мало чётких границ (возможен смаз или недофокус)';
      issues.add(
        'изображение нечёткое ($hint) — держите телефон устойчивее, дождитесь фокуса, при необходимости отойдите',
      );
    }

    return ImageQualityResult(
      isAcceptable: issues.isEmpty,
      issues: issues,
      meanLuma: lumaStats.mean,
      lumaStdDev: lumaStats.stdDev,
      laplacianVariance: lapVar,
      gradientEnergy: gradE,
    );
  } catch (_) {
    return ImageQualityResult.ok(skipped: true);
  }
}

img.Image _resizeLongestSide(img.Image source, int maxSide) {
  final w = source.width;
  final h = source.height;
  if (w <= 0 || h <= 0) return source;
  final longest = math.max(w, h);
  if (longest <= maxSide) return source;
  if (w >= h) {
    return img.copyResize(source, width: maxSide, interpolation: img.Interpolation.linear);
  }
  return img.copyResize(source, height: maxSide, interpolation: img.Interpolation.linear);
}

double _luma(img.Pixel p) => 0.299 * p.r + 0.587 * p.g + 0.114 * p.b;

({double mean, double stdDev}) _lumaMeanAndStd(img.Image gray) {
  final w = gray.width;
  final h = gray.height;
  if (w < 1 || h < 1) return (mean: 128, stdDev: 0);
  var sum = 0.0;
  var sumSq = 0.0;
  final n = w * h;
  for (var y = 0; y < h; y++) {
    for (var x = 0; x < w; x++) {
      final l = _luma(gray.getPixel(x, y));
      sum += l;
      sumSq += l * l;
    }
  }
  final mean = sum / n;
  final variance = (sumSq / n) - mean * mean;
  final stdDev = math.sqrt(math.max(0, variance));
  return (mean: mean, stdDev: stdDev);
}

List<int> _lumaHistogram(img.Image gray) {
  final hist = List<int>.filled(256, 0);
  final w = gray.width;
  final h = gray.height;
  for (var y = 0; y < h; y++) {
    for (var x = 0; x < w; x++) {
      var li = _luma(gray.getPixel(x, y)).round();
      if (li < 0) li = 0;
      if (li > 255) li = 255;
      hist[li]++;
    }
  }
  return hist;
}

/// Наименьший уровень L, для которого накопленная доля >= [quantile] (0..1).
double _percentileFromHistogram(List<int> hist, int totalPixels, double quantile) {
  if (totalPixels <= 0) return 128;
  final target = (totalPixels * quantile).ceil().clamp(1, totalPixels);
  var cum = 0;
  for (var i = 0; i < 256; i++) {
    cum += hist[i];
    if (cum >= target) return i.toDouble();
  }
  return 255;
}

double _fractionBelow(List<int> hist, int cutoffInclusive, int totalPixels) {
  if (totalPixels <= 0) return 0;
  var n = 0;
  final up = cutoffInclusive.clamp(0, 255);
  for (var i = 0; i <= up; i++) {
    n += hist[i];
  }
  return n / totalPixels;
}

double _fractionAbove(List<int> hist, int cutoffInclusive, int totalPixels) {
  if (totalPixels <= 0) return 0;
  var n = 0;
  final lo = cutoffInclusive.clamp(0, 255);
  for (var i = lo; i < 256; i++) {
    n += hist[i];
  }
  return n / totalPixels;
}

/// Дисперсия отклика лапласиана (резкость).
double _laplacianVariance(img.Image gray) {
  final w = gray.width;
  final h = gray.height;
  if (w < 3 || h < 3) return 0;
  var sum = 0.0;
  var sumSq = 0.0;
  var count = 0;
  for (var y = 1; y < h - 1; y++) {
    for (var x = 1; x < w - 1; x++) {
      final c = _luma(gray.getPixel(x, y));
      final lap = 4 * c -
          _luma(gray.getPixel(x - 1, y)) -
          _luma(gray.getPixel(x + 1, y)) -
          _luma(gray.getPixel(x, y - 1)) -
          _luma(gray.getPixel(x, y + 1));
      sum += lap;
      sumSq += lap * lap;
      count++;
    }
  }
  if (count == 0) return 0;
  final mean = sum / count;
  return (sumSq / count) - mean * mean;
}

/// Средняя сумма квадратов горизонтального и вертикального градиента (детали / кромки).
double _gradientEnergy(img.Image gray) {
  final w = gray.width;
  final h = gray.height;
  if (w < 2 || h < 2) return 0;
  var sum = 0.0;
  var count = 0;
  for (var y = 0; y < h - 1; y++) {
    for (var x = 0; x < w - 1; x++) {
      final l00 = _luma(gray.getPixel(x, y));
      final l10 = _luma(gray.getPixel(x + 1, y));
      final l01 = _luma(gray.getPixel(x, y + 1));
      final gx = l10 - l00;
      final gy = l01 - l00;
      sum += gx * gx + gy * gy;
      count++;
    }
  }
  if (count == 0) return 0;
  return sum / count;
}
