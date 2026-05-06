import 'dart:convert';

import 'package:data_collector/features/projects/project_asset_cache.dart';
import 'package:data_collector/models/project_config.dart';
import 'package:dio/dio.dart';

/// Загрузка каталога и конфигов проектов строго с сервера.
final class ServerProjectCatalog {
  ServerProjectCatalog(this._dio);

  final Dio _dio;

  /// Возвращает актуальный каталог с Django.
  /// Ошибки сети/сервера не маскируются локальным кэшем.
  Future<List<Project>> loadProjectsWithFallback() async {
    return syncFromServer();
  }

  Future<List<Project>> syncFromServer() async {
    final catRes = await _dio.get<dynamic>(
      '/v1/projects',
      options: Options(
        validateStatus: (s) => s == 200,
      ),
    );

    final data = catRes.data;
    late final Map<String, dynamic> catalogMap;
    if (data is Map<String, dynamic>) {
      catalogMap = data;
    } else if (data is String) {
      catalogMap = jsonDecode(data) as Map<String, dynamic>;
    } else {
      throw StateError('Unexpected catalog response');
    }

    return _projectsFromCatalog(catalogMap);
  }

  Future<List<Project>> _projectsFromCatalog(Map<String, dynamic> catalog) async {
    final items = catalog['projects'] as List<dynamic>? ?? [];
    final out = <Project>[];
    for (final raw in items) {
      if (raw is! Map) continue;
      final pid = raw['project_id'] as String?;
      if (pid == null) continue;
      final r = await _dio.get<dynamic>(
        '/v1/projects/$pid/config',
        options: Options(validateStatus: (s) => s == 200),
      );
      final data = r.data;
      if (data is Map<String, dynamic>) {
        out.add(Project.fromJson(data));
      } else if (data is String) {
        out.add(Project.fromJson(jsonDecode(data) as Map<String, dynamic>));
      } else {
        throw StateError('Unexpected project config response for $pid');
      }
      await deleteCachedAssetsForProject(pid);
    }
    return out;
  }
}
