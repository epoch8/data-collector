import 'package:data_collector/bootstrap.dart';
import 'package:data_collector/core/api/api_environment.dart';
import 'package:dio/dio.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// `null`, если [ApiEnvironment.isConfigured] == false.
final dioProvider = Provider<Dio?>((ref) {
  final base = ApiEnvironment.normalizedBaseUrl();
  if (base.isEmpty) return null;

  final dio = Dio(
    BaseOptions(
      baseUrl: base,
      // Короткое подключение — быстрее уходим на локальный кэш при недоступном API.
      connectTimeout: const Duration(seconds: 12),
      sendTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(minutes: 2),
      headers: {Headers.acceptHeader: 'application/json'},
    ),
  );

  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) async {
        if (firebaseInitialized) {
          final user = FirebaseAuth.instance.currentUser;
          if (user != null) {
            final id = await user.getIdToken();
            if (id != null && id.isNotEmpty) {
              options.headers['Authorization'] = 'Bearer $id';
            }
          }
        }
        if (options.headers['Authorization'] == null) {
          final token = ApiEnvironment.bearerToken.trim();
          if (token.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $token';
          }
        }
        return handler.next(options);
      },
    ),
  );

  return dio;
});
