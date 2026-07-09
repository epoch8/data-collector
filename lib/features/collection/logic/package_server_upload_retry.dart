import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

/// Логические пути `blobs/…`, уже принятые сервером (для resume после обрыва).
Future<Set<String>> fetchUploadedBlobPaths(
  Dio dio,
  String projectId,
  String packageId,
) async {
  try {
    final res = await dio.get<Map<String, dynamic>>(
      '/v1/projects/$projectId/packages/$packageId',
    );
    final blobs = res.data?['blobs'];
    if (blobs is List) {
      return blobs.map((e) => e.toString()).toSet();
    }
  } catch (e, st) {
    debugPrint('fetchUploadedBlobPaths: $e\n$st');
  }
  return {};
}

/// Ошибка сети/таймаута, которую имеет смысл повторить.
bool isTransientUploadError(DioException e) {
  switch (e.type) {
    case DioExceptionType.sendTimeout:
    case DioExceptionType.receiveTimeout:
    case DioExceptionType.connectionTimeout:
    case DioExceptionType.connectionError:
      return true;
    case DioExceptionType.unknown:
      final msg = '${e.error ?? e.message}'.toLowerCase();
      return msg.contains('connection abort') ||
          msg.contains('connection reset') ||
          msg.contains('broken pipe') ||
          msg.contains('network is unreachable') ||
          msg.contains('failed host lookup') ||
          msg.contains('connection closed') ||
          msg.contains('software caused connection abort');
    default:
      return false;
  }
}

/// Выполняет запрос с повтором при временных сетевых ошибках.
///
/// Все шаги upload (PUT blob / PUT manifest / POST commit) идемпотентны на
/// сервере, поэтому повтор безопасен.
Future<Response<T>> sendWithRetry<T>(
  Future<Response<T>> Function() send, {
  String label = 'request',
  int maxAttempts = 4,
}) async {
  var delay = const Duration(seconds: 2);
  for (var attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await send();
    } on DioException catch (e) {
      if (attempt >= maxAttempts || !isTransientUploadError(e)) rethrow;
      debugPrint(
        'sendWithRetry[$label]: attempt $attempt/$maxAttempts failed: $e; '
        'retry in ${delay.inSeconds}s',
      );
      await Future<void>.delayed(delay);
      delay *= 2;
    }
  }
  throw StateError('sendWithRetry: unreachable');
}
