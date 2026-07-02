// Конфиг Firebase для Firebase.initializeApp.
// Обновить можно: (1) dart run flutterfire_cli:flutterfire configure
// (2) Firebase MCP в Cursor: firebase_login → firebase_get_sdk_config (android/ios/web).

import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;
import 'package:flutter/foundation.dart'
    show TargetPlatform, defaultTargetPlatform, kIsWeb;

class DefaultFirebaseOptions {
  static FirebaseOptions get currentPlatform {
    if (kIsWeb) {
      return web;
    }
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return android;
      case TargetPlatform.iOS:
        return ios;
      case TargetPlatform.macOS:
        return macos;
      default:
        return android;
    }
  }

  /// Добавьте веб-приложение в Firebase и подставьте appId с суффиксом :web:…
  static const FirebaseOptions web = FirebaseOptions(
    apiKey: 'AIzaSyA4FEzQHpt0Jces728UrbAIa6EwMGuvvLQ',
    appId: '1:59903871663:android:83c40cfe504ef60952225a',
    messagingSenderId: '59903871663',
    projectId: 'e8-gke',
    authDomain: 'e8-gke.firebaseapp.com',
    storageBucket: 'e8-gke.firebasestorage.app',
  );

  /// Данные из android/app/google-services.json
  static const FirebaseOptions android = FirebaseOptions(
    apiKey: 'AIzaSyA4FEzQHpt0Jces728UrbAIa6EwMGuvvLQ',
    appId: '1:59903871663:android:83c40cfe504ef60952225a',
    messagingSenderId: '59903871663',
    projectId: 'e8-gke',
    authDomain: 'e8-gke.firebaseapp.com',
    storageBucket: 'e8-gke.firebasestorage.app',
  );

  /// Для реального iOS: зарегистрируйте приложение в Firebase, скачайте GoogleService-Info.plist и обновите ключи / GOOGLE_APP_ID.
  static const FirebaseOptions ios = FirebaseOptions(
    apiKey: 'AIzaSyCGtNxCn-rs7Gd3LEbG754GimCxz1yOi7c',
    appId: '1:181572319604:ios:0000000000000000000000',
    messagingSenderId: '181572319604',
    projectId: 'data-collector-dev-e8',
    storageBucket: 'data-collector-dev-e8.firebasestorage.app',
    iosBundleId: 'com.example.dataCollector',
  );

  static const FirebaseOptions macos = FirebaseOptions(
    apiKey: 'AIzaSyCGtNxCn-rs7Gd3LEbG754GimCxz1yOi7c',
    appId: '1:181572319604:ios:0000000000000000000001',
    messagingSenderId: '181572319604',
    projectId: 'data-collector-dev-e8',
    storageBucket: 'data-collector-dev-e8.firebasestorage.app',
    iosBundleId: 'com.example.dataCollector',
  );
}

// apiKey: 'AIzaSyA4FEzQHpt0Jces728UrbAIa6EwMGuvvLQ',
// appId: '1:59903871663:android:83c40cfe504ef60952225a',
// messagingSenderId: '59903871663',
// projectId: 'e8-gke',
// authDomain: 'e8-gke.firebaseapp.com',
// storageBucket: 'e8-gke.firebasestorage.app',
