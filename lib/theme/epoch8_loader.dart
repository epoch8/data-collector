import 'package:flutter/material.dart';

import 'epoch8_theme.dart';
import 'theme_controller.dart';

/// Брендированный лоадер: логотип в кольце спиннера. Используется как замена
/// «голому» CircularProgressIndicator в местах загрузки данных приложения.
class Epoch8Loader extends StatelessWidget {
  const Epoch8Loader({super.key, this.size = 56});

  final double size;

  /// Удобный конструктор: лоадер по центру (для `loading:` веток AsyncValue).
  static Widget center({double size = 56, String? label}) =>
      _Epoch8LoaderCentered(size: size, label: label);

  @override
  Widget build(BuildContext context) {
    final ringSize = size + 18;
    return ValueListenableBuilder<Brightness>(
      valueListenable: appBrightnessNotifier,
      builder: (context, _, __) => SizedBox(
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
                color: Epoch8Theme.accent,
                backgroundColor: Epoch8Theme.border.withValues(alpha: 0.35),
              ),
            ),
            ClipRRect(
              borderRadius: BorderRadius.circular(size / 4),
              child: Image.asset(
                'e8-team-logo-1024.png',
                width: size,
                height: size,
                fit: BoxFit.cover,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Epoch8LoaderCentered extends StatelessWidget {
  const _Epoch8LoaderCentered({required this.size, required this.label});

  final double size;
  final String? label;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Epoch8Loader(size: size),
          if (label != null) ...[
            const SizedBox(height: 14),
            Text(
              label!,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: Epoch8Theme.textMuted),
            ),
          ],
        ],
      ),
    );
  }
}
