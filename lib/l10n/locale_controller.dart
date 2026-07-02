import 'package:flutter/material.dart';

import '../core/preferences/app_preferences.dart';

final ValueNotifier<Locale> appLocaleNotifier = ValueNotifier(
  const Locale('ru'),
);

void initAppLocale() {
  final stored = AppPreferences.instance.readLocale();
  if (stored != null) {
    appLocaleNotifier.value = stored;
  }
}

void toggleAppLocale() {
  final next = appLocaleNotifier.value.languageCode == 'ru'
      ? const Locale('en')
      : const Locale('ru');
  appLocaleNotifier.value = next;
  AppPreferences.instance.writeLocale(next);
}
