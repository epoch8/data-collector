import 'dart:convert';
import 'dart:typed_data';

import 'package:cross_file/cross_file.dart';
import 'package:data_collector/core/storage/database.dart';
import 'package:data_collector/features/collection/logic/local_package_materializer_payload_utils.dart';
import 'package:data_collector/features/collection/logic/package_server_manifest.dart';
import 'package:dio/dio.dart';
import 'package:drift/drift.dart' show Value;
import 'package:flutter/foundation.dart';
import 'package:path/path.dart' as p;

/// Загрузка пакета на Django API (спека 08) без локальной ФС.
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

    final manifestMap = Map<String, dynamic>.from(
      jsonDecode(jsonEncode(await loadPackagePayloadMap(pkg))) as Map,
    );

    final dataRaw = manifestMap['data'];
    final dynamic pathSubject =
        manifestMap.containsKey('package_id') && dataRaw is Map
        ? dataRaw
        : manifestMap;

    final candidates = collectWebCaptureRefsFromPayloadShallow(pathSubject);
    final absToRel = <String, String>{};
    var blobCounter = 0;

    for (final src in candidates) {
      if (absToRel.containsKey(src)) continue;
      if (src.startsWith('blobs/') || src.startsWith('blobs\\')) continue;

      Uint8List bytes;
      try {
        bytes = await XFile(src).readAsBytes();
      } catch (e, st) {
        debugPrint(
          'uploadDriftPackageToServer web: skip unreadable path $src: $e\n$st',
        );
        continue;
      }
      if (bytes.isEmpty) continue;

      blobCounter++;
      var ext = p.extension(src.split('?').first);
      if (ext.isEmpty || ext == '.' || ext.length > 8) {
        ext = '.jpg';
      }
      final name = 'img_${blobCounter.toString().padLeft(4, '0')}$ext';
      const relPath = 'blobs/';
      final logical = '$relPath$name';
      absToRel[src] = logical;

      final pathSuffix = logical.split('/').map(Uri.encodeComponent).join('/');
      await dio.put(
        '/v1/projects/$projectId/packages/$packageId/blobs/$pathSuffix',
        data: bytes,
        options: Options(
          headers: {Headers.contentTypeHeader: 'application/octet-stream'},
          responseType: ResponseType.json,
        ),
      );
    }

    replacePathsInPayload(pathSubject, absToRel);

    injectSubmittedByIntoServerManifest(manifestMap);

    final manifestBody = const JsonEncoder.withIndent(
      '  ',
    ).convert(manifestMap);

    await dio.put<dynamic>(
      '/v1/projects/$projectId/packages/$packageId/manifest',
      data: manifestBody,
      options: Options(
        headers: {Headers.contentTypeHeader: 'application/json; charset=utf-8'},
      ),
    );

    await dio.post<dynamic>(
      '/v1/projects/$projectId/packages/$packageId/commit',
    );

    await setState('completed', null);
  } catch (e, st) {
    debugPrint('uploadDriftPackageToServer: $e\n$st');
    await setState('failed', e.toString());
    rethrow;
  }
}
