import 'dart:typed_data';

import 'package:data_collector/core/api/api_environment.dart';
import 'package:dio/dio.dart';

/// Совпадает ли [uri] с хостом/портом/схемой [API_BASE_URL] (без утечки Bearer на чужие домены).
bool projectExampleUriSameApiOrigin(Uri uri) {
  final raw = ApiEnvironment.normalizedBaseUrl();
  final base = Uri.tryParse(raw);
  if (base == null || !base.hasScheme || !uri.hasScheme) return false;
  return uri.scheme == base.scheme && uri.host == base.host && uri.port == base.port;
}

/// Загрузка изображения с того же API, что и [dio] (интерцептор подставит Firebase / static Bearer).
///
/// Не бросает на 4xx — иначе вызывающий код не должен делать второй запрос через [Image.network]
/// без токена (в логах Django это даёт 401).
Future<Uint8List?> fetchProjectExampleImageBytes(Dio dio, Uri uri) async {
  if (!projectExampleUriSameApiOrigin(uri)) return null;
  try {
    final res = await dio.get<List<int>>(
      uri.toString(),
      options: Options(
        responseType: ResponseType.bytes,
        headers: {Headers.acceptHeader: '*/*'},
        validateStatus: (status) => status != null && status < 500,
      ),
    );
    if (res.statusCode != 200) {
      return null;
    }
    final d = res.data;
    if (d == null || d.isEmpty) return null;
    return Uint8List.fromList(d);
  } catch (_) {
    return null;
  }
}
