import 'package:flutter/material.dart';

final ValueNotifier<Locale> appLocaleNotifier = ValueNotifier(const Locale('ru'));

void toggleAppLocale() {
  appLocaleNotifier.value =
      appLocaleNotifier.value.languageCode == 'ru' ? const Locale('en') : const Locale('ru');
}
