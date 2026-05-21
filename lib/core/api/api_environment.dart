/// Базовый URL Django без завершающего `/`.
/// Android emulator → хост ПК: `http://10.0.2.2:8000`
///
/// Запуск:
/// `flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000`
/// Опционально: `--dart-define=API_BEARER_TOKEN=...` если на Django не включён Firebase Auth.
abstract final class ApiEnvironment {
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: '',
  );
  static const String bearerToken = String.fromEnvironment(
    'API_BEARER_TOKEN',
    defaultValue: '',
  );

  static bool get isConfigured => baseUrl.trim().isNotEmpty;

  static String normalizedBaseUrl() {
    final b = baseUrl.trim();
    if (b.isEmpty) return '';
    return b.endsWith('/') ? b.substring(0, b.length - 1) : b;
  }
}
