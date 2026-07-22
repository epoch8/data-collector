// Конфиг Firebase для Firebase.initializeApp.
// Обновить можно: (1) dart run flutterfire_cli:flutterfire configure
// (2) Firebase MCP в Cursor: firebase_login → firebase_get_sdk_config (android/ios/web).
//
// TEMP (локалка): сейчас везде data-collector-dev-e8, чтобы совпадать с
// django_server/firebase-service-account.json.
// TODO: вернуть Android/Web на e8-gke (см. docs/mobile-revisions-2026-07-17/README.md → Firebase).

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

  static const FirebaseOptions web = FirebaseOptions(
    apiKey: 'AIzaSyDDp9CMDUL-1S7Y-3IcCzb6nx06AF1zY8Q',
    appId: '1:181572319604:web:8ddfbe6ee6462e36c09421',
    messagingSenderId: '181572319604',
    projectId: 'data-collector-dev-e8',
    authDomain: 'data-collector-dev-e8.firebaseapp.com',
    storageBucket: 'data-collector-dev-e8.firebasestorage.app',
    measurementId: 'G-BTV5Z9BXHH',
  );

  /// Данные из android/app/google-services.json (data-collector-dev-e8).
  static const FirebaseOptions android = FirebaseOptions(
    apiKey: 'AIzaSyCGtNxCn-rs7Gd3LEbG754GimCxz1yOi7c',
    appId: '1:181572319604:android:0f8051297f8c019bc09421',
    messagingSenderId: '181572319604',
    projectId: 'data-collector-dev-e8',
    authDomain: 'data-collector-dev-e8.firebaseapp.com',
    storageBucket: 'data-collector-dev-e8.firebasestorage.app',
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

// --- PREVIOUS (e8-gke) — вернуть, когда будет SA для e8-gke ---
// android/web:
// apiKey: 'AIzaSyA4FEzQHpt0Jces728UrbAIa6EwMGuvvLQ'
// appId: '1:59903871663:android:83c40cfe504ef60952225a'
// messagingSenderId: '59903871663'
// projectId: 'e8-gke'
// authDomain: 'e8-gke.firebaseapp.com'
// storageBucket: 'e8-gke.firebasestorage.app'
