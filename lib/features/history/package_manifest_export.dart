import 'dart:convert';
import 'dart:io';

import 'package:data_collector/core/storage/database.dart';
import 'package:data_collector/features/collection/logic/package_server_manifest.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

/// Делится тем же JSON, что уходит в [PUT …/manifest]: payload + [injectSubmittedByIntoServerManifest].
Future<void> sharePackageServerManifest(BuildContext context, Package pkg) async {
  if (kIsWeb) {
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Экспорт JSON на веб пока не поддерживается.')),
      );
    }
    return;
  }

  final map = await loadPackagePayloadMap(pkg);
  injectSubmittedByIntoServerManifest(map);
  final body = const JsonEncoder.withIndent('  ').convert(map);
  final dir = await getTemporaryDirectory();
  final name = '${pkg.id}_server_manifest.json';
  final file = File('${dir.path}/$name');
  await file.writeAsString(body);

  await Share.shareXFiles(
    [XFile(file.path, mimeType: 'application/json', name: name)],
    subject: 'Манифест ${pkg.id}',
    text: 'JSON манифеста пакета (как на сервер)',
  );
}

/// Обёртка с [SnackBar] при ошибке.
Future<void> sharePackageServerManifestWithSnackBar(BuildContext context, Package pkg) async {
  try {
    await sharePackageServerManifest(context, pkg);
  } catch (e, st) {
    debugPrint('sharePackageServerManifest: $e\n$st');
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Не удалось экспортировать JSON: $e')),
      );
    }
  }
}
