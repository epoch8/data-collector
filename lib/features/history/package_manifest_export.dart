import 'dart:convert';

import 'package:data_collector/core/storage/database.dart';
import 'package:data_collector/features/collection/logic/package_server_manifest.dart';
import 'package_manifest_export_io.dart' if (dart.library.html) 'package_manifest_export_web.dart' as manifest_io;
import 'package:data_collector/l10n/app_localizations.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

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
  final loc = AppLocalizations.of(context);
  final name = '${pkg.id}_server_manifest.json';
  await manifest_io.shareJsonFileWithOsShareSheet(
    context: context,
    body: body,
    fileName: name,
    subject: loc.manifestSubject(pkg.id),
    shareText: loc.manifestShareText,
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
