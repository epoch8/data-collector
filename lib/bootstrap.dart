/// Устанавливается в `main()` после попытки [Firebase.initializeApp].
bool firebaseInitialized = false;

/// Стартовый маршрут после восстановления сессии Firebase Auth с устройства.
String appRouterInitialLocation = '/login';
