import 'dart:convert';
import 'dart:io';

import 'package:data_collector/core/package/package_paths.dart';
import 'package:data_collector/core/storage/database.dart';
import 'package:data_collector/features/collection/logic/package_server_manifest.dart';
import 'package:dio/dio.dart';
import 'package:drift/drift.dart' show Value;
import 'package:flutter/foundation.dart';
import 'package:path/path.dart' as p;

/// Загрузка одного пакета на Django API (спека 08).
///
/// [allowedProjectIds] — `project_id`, к которым у текущего пользователя есть доступ
/// по актуальному каталогу с сервера; иначе загрузка не начинается.
Future<void> uploadDriftPackageToServer({
  required Dio dio,
  required AppDatabase db,
  required Package pkg,
  required Set<String> allowedProjectIds,
}) async {
  if (kIsWeb) {
    throw UnsupportedError('Upload is not supported on web.');
  }

  final projectId = pkg.projectId;
  final packageId = pkg.id;

  Future<void> setState(String state, String? err) async {
    await (db.update(db.packages)..where((t) => t.id.equals(packageId))).write(
      PackagesCompanion(
        serverDeliveryState: Value(state),
        serverDeliveryError: Value(err),
      ),
    );
  }

  if (pkg.status == 'draft') {
    throw StateError('Нельзя отправить незавершённый черновик — завершите сбор на устройстве.');
  }

  if (!allowedProjectIds.contains(projectId)) {
    const msg = 'Нет доступа к этому проекту у текущего пользователя (проверьте каталог на сервере).';
    await setState('failed', msg);
    throw StateError(msg);
  }

  await setState('uploading', null);

  try {
    final sessionRes = await dio.post<dynamic>(
      '/v1/projects/$projectId/packages',
      data: {'package_id': packageId},
      options: Options(validateStatus: (s) => s == 200 || s == 201 || s == 409),
    );
    if (sessionRes.statusCode == 409) {
      final st = await dio.get<Map<String, dynamic>>('/v1/projects/$projectId/packages/$packageId');
      final status = st.data?['status']?.toString();
      if (status == 'completed') {
        await setState('completed', null);
        return;
      }
    }

    final root = PackagePaths.packageRootFor(packageId);
    final blobsDir = Directory(p.join(root, 'blobs'));
    if (await blobsDir.exists()) {
      await for (final entity in blobsDir.list(followLinks: false)) {
        if (entity is! File) continue;
        final name = p.basename(entity.path);
        final logical = 'blobs/$name';
        final bytes = await entity.readAsBytes();
        final pathSuffix = logical.split('/').map(Uri.encodeComponent).join('/');
        await dio.put(
          '/v1/projects/$projectId/packages/$packageId/blobs/$pathSuffix',
          data: bytes,
          options: Options(
            headers: {Headers.contentTypeHeader: 'application/octet-stream'},
            // Ответ — JSON (Map), не байты; generic List<int> у put давал неверный cast.
            responseType: ResponseType.json,
          ),
        );
      }
    }

    final manifestMap = await loadPackagePayloadMap(pkg);
    injectSubmittedByIntoServerManifest(manifestMap);

    final manifestBody = const JsonEncoder.withIndent('  ').convert(manifestMap);

    await dio.put<dynamic>(
      '/v1/projects/$projectId/packages/$packageId/manifest',
      data: manifestBody,
      options: Options(
        headers: {Headers.contentTypeHeader: 'application/json; charset=utf-8'},
      ),
    );

    await dio.post<dynamic>('/v1/projects/$projectId/packages/$packageId/commit');

    await setState('completed', null);
  } catch (e, st) {
    debugPrint('uploadDriftPackageToServer: $e\n$st');
    await setState('failed', e.toString());
    rethrow;
  }
}
