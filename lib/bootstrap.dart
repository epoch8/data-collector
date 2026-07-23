import 'package:flutter/material.dart';

/// Устанавливается в `main()` после попытки [Firebase.initializeApp].
bool firebaseInitialized = false;

/// Стартовый маршрут после восстановления сессии Firebase Auth с устройства.
String appRouterInitialLocation = '/login';

/// Корневой [ScaffoldMessenger] для SnackBar после навигации (например после submit пакета).
final GlobalKey<ScaffoldMessengerState> rootScaffoldMessengerKey =
    GlobalKey<ScaffoldMessengerState>();
