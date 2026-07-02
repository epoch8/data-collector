import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Постоянное хранилище пользовательских настроек приложения
/// (язык, тема). Инициализируется один раз в `main()`.
class AppPreferences {
  AppPreferences._(this._prefs);

  final SharedPreferences _prefs;

  static const String _kLocale = 'app.locale';
  static const String _kThemeMode = 'app.themeMode';

  static AppPreferences? _instance;

  static Future<AppPreferences> ensureInitialized() async {
    if (_instance != null) return _instance!;
    final prefs = await SharedPreferences.getInstance();
    _instance = AppPreferences._(prefs);
    return _instance!;
  }

  /// Доступно только после [ensureInitialized].
  static AppPreferences get instance {
    final i = _instance;
    assert(
      i != null,
      'AppPreferences.ensureInitialized() must be called first',
    );
    return i!;
  }

  Locale? readLocale() {
    final code = _prefs.getString(_kLocale);
    if (code == null || code.isEmpty) return null;
    return Locale(code);
  }

  Future<void> writeLocale(Locale locale) async {
    await _prefs.setString(_kLocale, locale.languageCode);
  }

  ThemeMode? readThemeMode() {
    final raw = _prefs.getString(_kThemeMode);
    switch (raw) {
      case 'light':
        return ThemeMode.light;
      case 'dark':
        return ThemeMode.dark;
      case 'system':
        return ThemeMode.system;
    }
    return null;
  }

  Future<void> writeThemeMode(ThemeMode mode) async {
    final raw = switch (mode) {
      ThemeMode.light => 'light',
      ThemeMode.dark => 'dark',
      ThemeMode.system => 'system',
    };
    await _prefs.setString(_kThemeMode, raw);
  }
}
