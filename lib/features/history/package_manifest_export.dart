import 'dart:convert';
import 'dart:io';

import 'package:data_collector/core/storage/database.dart';
import 'package:data_collector/features/collection/logic/package_server_manifest.dart';
import 'package:data_collector/l10n/app_localizations.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

/// Делится тем же JSON, что уходит в [PUT …/manifest]: payload + [injectSubmittedByIntoServerManifest].
Future<void> sharePackageServerManifest(BuildContext context, Package pkg) async {
  if (kIsWeb) {
    if (context.mounted) {
      final loc = AppLocalizations.of(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(loc.webExportNotSupported)),
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
    subject: AppLocalizations.of(context).manifestSubject(pkg.id),
    text: AppLocalizations.of(context).manifestShareText,
  );
}

/// Обёртка с [SnackBar] при ошибке.
Future<void> sharePackageServerManifestWithSnackBar(BuildContext context, Package pkg) async {
  try {
    await sharePackageServerManifest(context, pkg);
  } catch (e, st) {
    debugPrint('sharePackageServerManifest: $e\n$st');
    if (context.mounted) {
      final loc = AppLocalizations.of(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(loc.exportJsonFailed('$e'))),
      );
    }
  }
}
