import 'package:flutter/material.dart';

import '../core/preferences/app_preferences.dart';

/// Выбранный пользователем режим темы (только светлая/тёмная).
final ValueNotifier<ThemeMode> appThemeModeNotifier = ValueNotifier(ThemeMode.dark);

/// Реальная яркость, применяемая к UI прямо сейчас.
/// В бинарном режиме полностью зависит от [appThemeModeNotifier].
final ValueNotifier<Brightness> appBrightnessNotifier = ValueNotifier(Brightness.dark);

bool get isLightThemeEnabled => appBrightnessNotifier.value == Brightness.light;

void initAppThemeMode() {
  final stored = AppPreferences.instance.readThemeMode();
  switch (stored) {
    case ThemeMode.light:
    case ThemeMode.dark:
      appThemeModeNotifier.value = stored!;
      break;
    case ThemeMode.system:
      // Мягкая миграция со старой 3-режимной версии.
      appThemeModeNotifier.value = ThemeMode.dark;
      AppPreferences.instance.writeThemeMode(ThemeMode.dark);
      break;
    case null:
      break;
  }
}

/// Переключает только между двумя режимами: light <-> dark.
void toggleAppThemeMode() {
  final next =
      appThemeModeNotifier.value == ThemeMode.light ? ThemeMode.dark : ThemeMode.light;
  appThemeModeNotifier.value = next;
  AppPreferences.instance.writeThemeMode(next);
}

IconData iconForThemeMode(ThemeMode mode) {
  return mode == ThemeMode.light ? Icons.light_mode_outlined : Icons.dark_mode_outlined;
}
