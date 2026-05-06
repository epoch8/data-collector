import 'package:flutter/material.dart';

import '../core/preferences/app_preferences.dart';

/// Выбранный пользователем режим темы (включая «как в системе»).
final ValueNotifier<ThemeMode> appThemeModeNotifier = ValueNotifier(ThemeMode.dark);

/// Реальная яркость, применяемая к UI прямо сейчас (рассчитывается из
/// [appThemeModeNotifier] и системной яркости). Используется токенами
/// [Epoch8Theme] для возврата правильной палитры в [ThemeMode.system].
final ValueNotifier<Brightness> appBrightnessNotifier = ValueNotifier(Brightness.dark);

bool get isLightThemeEnabled => appBrightnessNotifier.value == Brightness.light;

void initAppThemeMode() {
  final stored = AppPreferences.instance.readThemeMode();
  if (stored != null) {
    appThemeModeNotifier.value = stored;
  }
}

/// Циклически переключает: system -> light -> dark -> system.
void toggleAppThemeMode() {
  final next = switch (appThemeModeNotifier.value) {
    ThemeMode.system => ThemeMode.light,
    ThemeMode.light => ThemeMode.dark,
    ThemeMode.dark => ThemeMode.system,
  };
  appThemeModeNotifier.value = next;
  AppPreferences.instance.writeThemeMode(next);
}

IconData iconForThemeMode(ThemeMode mode) {
  return switch (mode) {
    ThemeMode.system => Icons.brightness_auto_outlined,
    ThemeMode.light => Icons.light_mode_outlined,
    ThemeMode.dark => Icons.dark_mode_outlined,
  };
}
