import 'package:flutter/material.dart';

import 'kalmgu_theme.dart';
import 'kalmgu_brand.dart';
import 'theme_controller.dart';

/// Брендированный лоадер: логотип в кольце спиннера. Используется как замена
/// «голому» CircularProgressIndicator в местах загрузки данных приложения.
class KalmguLoader extends StatelessWidget {
  const KalmguLoader({super.key, this.size = 56});

  final double size;

  /// Удобный конструктор: лоадер по центру (для `loading:` веток AsyncValue).
  static Widget center({double size = 56, String? label}) =>
      _KalmguLoaderCentered(size: size, label: label);

  @override
  Widget build(BuildContext context) {
    final ringSize = size + 18;
    return ValueListenableBuilder<Brightness>(
      valueListenable: appBrightnessNotifier,
      builder: (context, _, _) => SizedBox(
        width: ringSize,
        height: ringSize,
        child: Stack(
          alignment: Alignment.center,
          children: [
            SizedBox(
              width: ringSize,
              height: ringSize,
              child: CircularProgressIndicator(
                strokeWidth: 2.4,
                color: KalmguTheme.accent,
                backgroundColor: KalmguTheme.border.withValues(alpha: 0.35),
              ),
            ),
            Image.asset(
              KalmguBrand.mark,
              width: size,
              height: size,
              fit: BoxFit.contain,
            ),
          ],
        ),
      ),
    );
  }
}

class _KalmguLoaderCentered extends StatelessWidget {
  const _KalmguLoaderCentered({required this.size, required this.label});

  final double size;
  final String? label;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          KalmguLoader(size: size),
          if (label != null) ...[
            const SizedBox(height: 14),
            Text(
              label!,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: KalmguTheme.textMuted),
            ),
          ],
        ],
      ),
    );
  }
}
