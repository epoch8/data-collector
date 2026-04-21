import 'package:data_collector/core/api/api_environment.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// `null`, если [ApiEnvironment.isConfigured] == false.
final dioProvider = Provider<Dio?>((ref) {
  final base = ApiEnvironment.normalizedBaseUrl();
  if (base.isEmpty) return null;

  final dio = Dio(
    BaseOptions(
      baseUrl: base,
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(minutes: 2),
      headers: {Headers.acceptHeader: 'application/json'},
    ),
  );

  final token = ApiEnvironment.bearerToken.trim();
  if (token.isNotEmpty) {
    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          options.headers['Authorization'] = 'Bearer $token';
          return handler.next(options);
        },
      ),
    );
  }

  return dio;
});
