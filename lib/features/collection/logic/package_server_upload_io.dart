import 'dart:convert';
import 'dart:io';

import 'package:data_collector/core/package/package_paths.dart';
import 'package:data_collector/core/storage/database.dart';
import 'package:data_collector/features/collection/logic/local_package_materializer_payload_utils.dart';
import 'package:data_collector/features/collection/logic/package_server_manifest.dart';
import 'package:data_collector/features/collection/logic/package_server_upload_retry.dart';
import 'package:dio/dio.dart';
import 'package:drift/drift.dart' show Value;
import 'package:flutter/foundation.dart';
import 'package:path/path.dart' as p;

/// Загрузка одного пакета на Django API (спека 08).
Future<void> uploadDriftPackageToServer({
  required Dio dio,
  required AppDatabase db,
  required Package pkg,
  required Set<String> allowedProjectIds,
}) async {
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
    throw StateError(
      'Cannot upload unfinished draft — complete collection on device first.',
    );
  }

  if (!allowedProjectIds.contains(projectId)) {
    const msg =
        'No access to this project for current user (check server catalog).';
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
      final st = await dio.get<Map<String, dynamic>>(
        '/v1/projects/$projectId/packages/$packageId',
      );
      final status = st.data?['status']?.toString();
      if (status == 'completed') {
        await setState('completed', null);
        return;
      }
    }

    final uploadedBlobs = await fetchUploadedBlobPaths(dio, projectId, packageId);

    final manifestMap = await loadPackagePayloadMap(pkg);
    final requiredBlobs = <String>{};
    collectBlobLogicalPathsFromPayload(manifestMap, requiredBlobs);

    final root = PackagePaths.packageRootFor(packageId);
    final blobsDir = Directory(p.join(root, 'blobs'));
    if (await blobsDir.exists()) {
      await for (final entity in blobsDir.list(followLinks: false)) {
        if (entity is! File) continue;
        final name = p.basename(entity.path);
        final logical = 'blobs/$name';
        if (!requiredBlobs.contains(logical)) {
          continue;
        }
        if (uploadedBlobs.contains(logical)) {
          debugPrint('uploadDriftPackageToServer: skip already uploaded $logical');
          continue;
        }
        final bytes = await entity.readAsBytes();
        final pathSuffix = logical
            .split('/')
            .map(Uri.encodeComponent)
            .join('/');
        final blobUrl =
            '/v1/projects/$projectId/packages/$packageId/blobs/$pathSuffix';
        await sendWithRetry(
          () => dio.put<dynamic>(
            blobUrl,
            data: bytes,
            options: Options(
              headers: {Headers.contentTypeHeader: 'application/octet-stream'},
              responseType: ResponseType.json,
              sendTimeout: const Duration(minutes: 15),
              // Каждый blob — на свежем соединении: избегаем ECONNABORTED (errno 103)
              // при переиспользовании «протухшего» keep-alive сокета после серии загрузок.
              persistentConnection: false,
            ),
          ),
          label: logical,
          maxAttempts: 6,
        );
      }
    }

    injectSubmittedByIntoServerManifest(manifestMap);

    final manifestBody = const JsonEncoder.withIndent(
      '  ',
    ).convert(manifestMap);

    await sendWithRetry(
      () => dio.put<dynamic>(
        '/v1/projects/$projectId/packages/$packageId/manifest',
        data: manifestBody,
        options: Options(
          headers: {
            Headers.contentTypeHeader: 'application/json; charset=utf-8',
          },
        ),
      ),
      label: 'manifest',
    );

    await sendWithRetry(
      () => dio.post<dynamic>(
        '/v1/projects/$projectId/packages/$packageId/commit',
      ),
      label: 'commit',
    );

    await setState('completed', null);
  } catch (e, st) {
    debugPrint('uploadDriftPackageToServer: $e\n$st');
    await setState('failed', e.toString());
    rethrow;
  }
}
