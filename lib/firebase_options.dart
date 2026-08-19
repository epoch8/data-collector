// Конфиг Firebase для Firebase.initializeApp.
//
// Два профиля:
//   local — data-collector-dev-e8
//   prod  — e8-gke
//
// Выбор: --dart-define=FIREBASE_PROFILE=local|prod
// По умолчанию: prod (чтобы случайно не утащить local в прод).
// На Android обязательно тот же --flavor local|prod (google-services.json).

import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;
import 'package:flutter/foundation.dart'
    show TargetPlatform, defaultTargetPlatform, kIsWeb;

enum FirebaseProfile {
  local,
  prod;

  static FirebaseProfile fromName(String raw) {
    switch (raw.trim().toLowerCase()) {
      case 'local':
      case 'dev':
        return FirebaseProfile.local;
      case 'prod':
      case 'production':
        return FirebaseProfile.prod;
      default:
        return FirebaseProfile.prod;
    }
  }
}

class DefaultFirebaseOptions {
  /// `local` | `prod`. Default: prod.
  static const String profileName = String.fromEnvironment(
    'FIREBASE_PROFILE',
    defaultValue: 'prod',
  );

  static FirebaseProfile get profile => FirebaseProfile.fromName(profileName);

  static FirebaseOptions get currentPlatform {
    final opts = profile == FirebaseProfile.local
        ? _LocalOptions()
        : _ProdOptions();
    if (kIsWeb) {
      return opts.web;
    }
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return opts.android;
      case TargetPlatform.iOS:
        return opts.ios;
      case TargetPlatform.macOS:
        return opts.macos;
      default:
        return opts.android;
    }
  }
}

abstract class _ProfileOptions {
  FirebaseOptions get web;
  FirebaseOptions get android;
  FirebaseOptions get ios;
  FirebaseOptions get macos;
}

/// Firebase project: data-collector-dev-e8
class _LocalOptions implements _ProfileOptions {
  @override
  FirebaseOptions get web => const FirebaseOptions(
    apiKey: 'AIzaSyDDp9CMDUL-1S7Y-3IcCzb6nx06AF1zY8Q',
    appId: '1:181572319604:web:8ddfbe6ee6462e36c09421',
    messagingSenderId: '181572319604',
    projectId: 'data-collector-dev-e8',
    authDomain: 'data-collector-dev-e8.firebaseapp.com',
    storageBucket: 'data-collector-dev-e8.firebasestorage.app',
    measurementId: 'G-BTV5Z9BXHH',
  );

  @override
  FirebaseOptions get android => const FirebaseOptions(
    apiKey: 'AIzaSyCGtNxCn-rs7Gd3LEbG754GimCxz1yOi7c',
    appId: '1:181572319604:android:0f8051297f8c019bc09421',
    messagingSenderId: '181572319604',
    projectId: 'data-collector-dev-e8',
    authDomain: 'data-collector-dev-e8.firebaseapp.com',
    storageBucket: 'data-collector-dev-e8.firebasestorage.app',
  );

  @override
  FirebaseOptions get ios => const FirebaseOptions(
    apiKey: 'AIzaSyCGtNxCn-rs7Gd3LEbG754GimCxz1yOi7c',
    appId: '1:181572319604:ios:0000000000000000000000',
    messagingSenderId: '181572319604',
    projectId: 'data-collector-dev-e8',
    storageBucket: 'data-collector-dev-e8.firebasestorage.app',
    iosBundleId: 'com.example.dataCollector',
  );

  @override
  FirebaseOptions get macos => const FirebaseOptions(
    apiKey: 'AIzaSyCGtNxCn-rs7Gd3LEbG754GimCxz1yOi7c',
    appId: '1:181572319604:ios:0000000000000000000001',
    messagingSenderId: '181572319604',
    projectId: 'data-collector-dev-e8',
    storageBucket: 'data-collector-dev-e8.firebasestorage.app',
    iosBundleId: 'com.example.dataCollector',
  );
}

/// Firebase project: e8-gke
class _ProdOptions implements _ProfileOptions {
  @override
  FirebaseOptions get web => const FirebaseOptions(
    apiKey: 'AIzaSyA4FEzQHpt0Jces728UrbAIa6EwMGuvvLQ',
    appId: '1:59903871663:android:83c40cfe504ef60952225a',
    messagingSenderId: '59903871663',
    projectId: 'e8-gke',
    authDomain: 'e8-gke.firebaseapp.com',
    storageBucket: 'e8-gke.firebasestorage.app',
  );

  @override
  FirebaseOptions get android => const FirebaseOptions(
    apiKey: 'AIzaSyA4FEzQHpt0Jces728UrbAIa6EwMGuvvLQ',
    appId: '1:59903871663:android:83c40cfe504ef60952225a',
    messagingSenderId: '59903871663',
    projectId: 'e8-gke',
    authDomain: 'e8-gke.firebaseapp.com',
    storageBucket: 'e8-gke.firebasestorage.app',
  );

  @override
  FirebaseOptions get ios => const FirebaseOptions(
    apiKey: 'AIzaSyA4FEzQHpt0Jces728UrbAIa6EwMGuvvLQ',
    appId: '1:59903871663:ios:0000000000000000000000',
    messagingSenderId: '59903871663',
    projectId: 'e8-gke',
    storageBucket: 'e8-gke.firebasestorage.app',
    iosBundleId: 'com.example.dataCollector',
  );

  @override
  FirebaseOptions get macos => const FirebaseOptions(
    apiKey: 'AIzaSyA4FEzQHpt0Jces728UrbAIa6EwMGuvvLQ',
    appId: '1:59903871663:ios:0000000000000000000001',
    messagingSenderId: '59903871663',
    projectId: 'e8-gke',
    storageBucket: 'e8-gke.firebasestorage.app',
    iosBundleId: 'com.example.dataCollector',
  );
}
