import 'package:flutter/material.dart';

final ValueNotifier<ThemeMode> appThemeModeNotifier = ValueNotifier(ThemeMode.dark);

bool get isLightThemeEnabled => appThemeModeNotifier.value == ThemeMode.light;

void toggleAppThemeMode() {
  appThemeModeNotifier.value = isLightThemeEnabled ? ThemeMode.dark : ThemeMode.light;
}
