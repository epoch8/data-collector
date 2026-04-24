import 'dart:convert';
import 'dart:io';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:data_collector/models/project_config.dart';
import 'package:dio/dio.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

/// Синхронизация каталога и конфигов с сервера (спека 09): ETag / 304.
final class ServerProjectCatalog {
  ServerProjectCatalog(this._dio);

  final Dio _dio;

  Future<Directory> _cacheRoot() async {
    final d = await getApplicationSupportDirectory();
    final root = Directory(p.join(d.path, 'server_project_cache'));
    await root.create(recursive: true);
    await Directory(p.join(root.path, 'configs')).create(recursive: true);
    return root;
  }

  /// При наличии сети — актуальный каталог с Django (в т.ч. пустой список при отсутствии доступа).
  /// Офлайн или ошибка запроса — только кэш с диска. Bundled из assets здесь не подмешиваются
  /// (они только если в приложении не задан `API_BASE_URL`).
  Future<List<Project>> loadProjectsWithFallback() async {
    final online = await _likelyHasNetwork();
    if (!online) {
      return _loadProjectsFromDiskCache();
    }
    try {
      return await syncFromServer();
    } catch (_) {
      return _loadProjectsFromDiskCache();
    }
  }

  static Future<bool> _likelyHasNetwork() async {
    try {
      final r = await Connectivity().checkConnectivity();
      if (r.isEmpty) return true;
      return !r.every((e) => e == ConnectivityResult.none);
    } catch (_) {
      return true;
    }
  }

  Future<List<Project>> _loadProjectsFromDiskCache() async {
    final root = await _cacheRoot();
    final catalogFile = File(p.join(root.path, 'catalog.json'));
    if (!await catalogFile.exists()) return [];
    final catalog = jsonDecode(await catalogFile.readAsString()) as Map<String, dynamic>;
    final items = catalog['projects'] as List<dynamic>? ?? [];
    final out = <Project>[];
    for (final item in items) {
      if (item is! Map) continue;
      final pid = item['project_id'] as String?;
      if (pid == null) continue;
      final f = File(p.join(root.path, 'configs', '$pid.json'));
      if (!await f.exists()) continue;
      try {
        final m = jsonDecode(await f.readAsString()) as Map<String, dynamic>;
        out.add(Project.fromJson(m));
      } catch (_) {}
    }
    return out;
  }

  Future<List<Project>> syncFromServer() async {
    final root = await _cacheRoot();
    final catalogEtagPath = p.join(root.path, 'catalog.etag');
    final catalogJsonPath = p.join(root.path, 'catalog.json');

    final reqHeaders = <String, String>{};
    final etagFile = File(catalogEtagPath);
    if (await etagFile.exists()) {
      final e = (await etagFile.readAsString()).trim();
      if (e.isNotEmpty) reqHeaders['If-None-Match'] = e;
    }

    final catRes = await _dio.get<dynamic>(
      '/v1/projects',
      options: Options(
        headers: reqHeaders,
        validateStatus: (s) => s == 200 || s == 304,
      ),
    );

    late final Map<String, dynamic> catalogMap;
    if (catRes.statusCode == 304) {
      final body = File(catalogJsonPath);
      if (!await body.exists()) {
        throw StateError('304 Not Modified but no catalog.json cache');
      }
      catalogMap = jsonDecode(await body.readAsString()) as Map<String, dynamic>;
    } else {
      final data = catRes.data;
      if (data is Map<String, dynamic>) {
        catalogMap = data;
      } else if (data is String) {
        catalogMap = jsonDecode(data) as Map<String, dynamic>;
      } else {
        throw StateError('Unexpected catalog response');
      }
      await File(catalogJsonPath).writeAsString(jsonEncode(catalogMap));
      final newEtag = catRes.headers.value('etag');
      if (newEtag != null && newEtag.isNotEmpty) {
        await etagFile.writeAsString(newEtag);
      }
    }

    final items = catalogMap['projects'] as List<dynamic>? ?? [];
    for (final raw in items) {
      if (raw is! Map) continue;
      final pid = raw['project_id'] as String?;
      if (pid == null) continue;
      final ver = raw['config_version']?.toString() ?? '';
      await _ensureProjectConfig(
        projectId: pid,
        configVersion: ver,
        cacheRoot: root,
      );
    }

    return _projectsFromCatalogFile(catalogMap, root);
  }

  Future<void> _ensureProjectConfig({
    required String projectId,
    required String configVersion,
    required Directory cacheRoot,
  }) async {
    final jsonPath = p.join(cacheRoot.path, 'configs', '$projectId.json');
    final metaPath = p.join(cacheRoot.path, 'configs', '$projectId.meta.json');
    Map<String, dynamic> meta = {};
    if (await File(metaPath).exists()) {
      try {
        meta = jsonDecode(await File(metaPath).readAsString()) as Map<String, dynamic>;
      } catch (_) {}
    }
    final cachedVer = meta['config_version']?.toString();
    final cachedEtag = meta['etag']?.toString();
    final fileOk = await File(jsonPath).exists();
    final headers = <String, String>{};
    if (fileOk &&
        cachedVer == configVersion &&
        cachedEtag != null &&
        cachedEtag.isNotEmpty) {
      headers['If-None-Match'] = cachedEtag;
    }

    final r = await _dio.get<dynamic>(
      '/v1/projects/$projectId/config',
      options: Options(
        headers: headers,
        validateStatus: (s) => s == 200 || s == 304,
      ),
    );
    if (r.statusCode == 304) return;
    await _writeConfigResponse(projectId, metaPath, jsonPath, configVersion, r);
  }

  Future<void> _writeConfigResponse(
    String projectId,
    String metaPath,
    String jsonPath,
    String configVersion,
    Response<dynamic> r,
  ) async {
    final etag = r.headers.value('etag') ?? '';
    final bodyStr =
        r.data is String ? r.data as String : jsonEncode(r.data);
    await File(jsonPath).writeAsString(bodyStr, flush: true);
    await File(metaPath).writeAsString(
      jsonEncode({
        'project_id': projectId,
        'config_version': configVersion,
        'etag': etag,
      }),
      flush: true,
    );
  }

  List<Project> _projectsFromCatalogFile(Map<String, dynamic> catalog, Directory root) {
    final items = catalog['projects'] as List<dynamic>? ?? [];
    final out = <Project>[];
    for (final raw in items) {
      if (raw is! Map) continue;
      final pid = raw['project_id'] as String?;
      if (pid == null) continue;
      final f = File(p.join(root.path, 'configs', '$pid.json'));
      if (!f.existsSync()) continue;
      final m = jsonDecode(f.readAsStringSync()) as Map<String, dynamic>;
      out.add(Project.fromJson(m));
    }
    return out;
  }
}
