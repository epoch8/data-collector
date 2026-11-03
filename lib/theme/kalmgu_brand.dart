import 'package:flutter/material.dart';

import 'theme_controller.dart';

/// Знаки КалмГУ: герб для иконки и мелких мест, горизонтальный логотип для входа.
abstract final class KalmguBrand {
  static const mark = 'assets/brand/kalmgu-gerb.png';
  static const logo = 'assets/brand/kalmgu-logo.png';
  static const logoInverse = 'assets/brand/kalmgu-logo-inverse.png';
}

/// Горизонтальный логотип: цветной на светлой теме, белый на тёмной.
class KalmguWordmark extends StatelessWidget {
  const KalmguWordmark({super.key, this.maxWidth = 340});

  final double maxWidth;

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<Brightness>(
      valueListenable: appBrightnessNotifier,
      builder: (context, brightness, _) {
        final dark = brightness == Brightness.dark;
        return ConstrainedBox(
          constraints: BoxConstraints(maxWidth: maxWidth),
          child: Image.asset(
            dark ? KalmguBrand.logoInverse : KalmguBrand.logo,
            fit: BoxFit.contain,
            semanticLabel: 'Калмыцкий государственный университет',
          ),
        );
      },
    );
  }
}
