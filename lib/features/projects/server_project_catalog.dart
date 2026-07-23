import 'dart:convert';

import 'project_asset_cache_delete_io.dart'
    if (dart.library.html) 'project_asset_cache_delete_web.dart'
    as cache_del;
import 'package:data_collector/features/projects/catalog_project.dart';
import 'package:data_collector/models/project_config.dart';
import 'package:dio/dio.dart';

/// Загрузка каталога и форм проектов строго с сервера.
final class ServerProjectCatalog {
  ServerProjectCatalog(this._dio);

  final Dio _dio;

  /// Возвращает актуальный каталог с Django.
  /// Ошибки сети/сервера не маскируются локальным кэшем.
  Future<List<CatalogProject>> loadProjectsWithFallback() async {
    return syncFromServer();
  }

  Future<List<CatalogProject>> syncFromServer() async {
    final catRes = await _dio.get<dynamic>(
      '/v1/projects',
      options: Options(validateStatus: (s) => s == 200),
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

  Future<List<CatalogProject>> _projectsFromCatalog(
    Map<String, dynamic> catalog,
  ) async {
    final items = catalog['projects'] as List<dynamic>? ?? [];
    final out = <CatalogProject>[];
    for (final raw in items) {
      if (raw is! Map) continue;
      final pid = raw['project_id'] as String?;
      if (pid == null) continue;
      final catalogName = (raw['name'] as String?)?.trim();
      final forms = await _loadForms(pid);
      if (forms.isEmpty) continue;
      out.add(
        CatalogProject(
          id: pid,
          name: (catalogName != null && catalogName.isNotEmpty)
              ? catalogName
              : forms.first.formName,
          forms: forms,
        ),
      );
      await cache_del.deleteCachedAssetsForProject(pid);
    }
    return out;
  }

  Future<List<ProjectFormEntry>> _loadForms(String projectId) async {
    final r = await _dio.get<dynamic>(
      '/v1/projects/$projectId/forms',
      options: Options(validateStatus: (s) => s == 200 || s == 404),
    );
    if (r.statusCode == 200) {
      final data = r.data;
      final map = _asMap(data);
      final list = map['forms'] as List<dynamic>? ?? [];
      final out = <ProjectFormEntry>[];
      for (final item in list) {
        if (item is! Map) continue;
        final formId = item['form_id'] as String? ?? 'default';
        final configRaw = item['config'];
        if (configRaw is! Map) continue;
        final project = Project.fromJson(Map<String, dynamic>.from(configRaw));
        out.add(ProjectFormEntry(formId: formId, project: project));
      }
      if (out.isNotEmpty) return out;
    }

    // Legacy fallback: GET /config → одна форма default.
    final cfg = await _dio.get<dynamic>(
      '/v1/projects/$projectId/config',
      options: Options(validateStatus: (s) => s == 200),
    );
    final project = Project.fromJson(_asMap(cfg.data));
    return [ProjectFormEntry(formId: 'default', project: project)];
  }

  Map<String, dynamic> _asMap(dynamic data) {
    if (data is Map<String, dynamic>) return data;
    if (data is Map) {
      return Map<String, dynamic>.from(data);
    }
    if (data is String) {
      return jsonDecode(data) as Map<String, dynamic>;
    }
    throw StateError('Unexpected JSON response');
  }
}
