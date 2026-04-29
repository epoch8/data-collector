import 'dart:io';

import 'package:dio/dio.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

/// Относительный ключ файла в хранилище проекта (как в `GET …/assets/{key}`), без процент-кодирования.
/// `null` для абсолютных URL и прочих путей, которые не мапятся на этот API.
String? projectAssetStorageRelativePath(String rawPath) {
  var p0 = rawPath.trim().replaceAll(r'\', '/');
  if (p0.isEmpty) return null;
  if (p0.startsWith('./')) {
    p0 = p0.substring(2);
  }
  if (p0.startsWith('http://') || p0.startsWith('https://')) {
    return null;
  }
  if (p0.startsWith('/v1/')) {
    return null;
  }
  final String rel;
  if (p0.startsWith('assets/')) {
    rel = p0.substring('assets/'.length);
  } else if (!p0.contains('://') && !p0.startsWith('/')) {
    rel = p0;
  } else {
    return null;
  }
  if (rel.isEmpty || rel.split('/').contains('..')) {
    return null;
  }
  return rel;
}

Future<Directory> _projectAssetsCacheRoot() async {
  final d = await getApplicationSupportDirectory();
  final dir = Directory(p.join(d.path, 'server_project_cache', 'project_assets'));
  await dir.create(recursive: true);
  return dir;
}

/// Локальная копия `GET /v1/projects/{id}/assets/…` после первой загрузки.
Future<File> cachedProjectAssetFile(String projectId, String relativePath) async {
  final root = await _projectAssetsCacheRoot();
  return File(p.join(root.path, projectId, relativePath));
}

/// Сброс медиа проекта при обновлении JSON-конфига (ссылки в инструкциях могут смениться).
Future<void> deleteCachedAssetsForProject(String projectId) async {
  final dir = Directory(p.join((await _projectAssetsCacheRoot()).path, projectId));
  if (await dir.exists()) {
    await dir.delete(recursive: true);
  }
}

final Map<String, Future<void>> _assetDownloadInflight = {};

/// Скачивает файл в [cachedProjectAssetFile], если его ещё нет. Параллельные запросы того же ключа ждут один download.
Future<void> ensureProjectAssetCached({
  required Dio dio,
  required String projectId,
  required String relativePath,
  required Uri downloadUri,
}) async {
  final file = await cachedProjectAssetFile(projectId, relativePath);
  if (await file.exists()) {
    return;
  }
  await file.parent.create(recursive: true);
  final key = '$projectId|$relativePath';
  final inflight = _assetDownloadInflight[key];
  if (inflight != null) {
    try {
      await inflight;
    } catch (_) {
      rethrow;
    }
    if (await file.exists()) {
      return;
    }
  }
  final run = () async {
    if (await file.exists()) {
      return;
    }
    try {
      await dio.download(downloadUri.toString(), file.path);
    } catch (_) {
      if (await file.exists()) {
        try {
          await file.delete();
        } catch (_) {}
      }
      rethrow;
    }
  }();
  _assetDownloadInflight[key] = run;
  try {
    await run;
  } finally {
    _assetDownloadInflight.remove(key);
  }
}
