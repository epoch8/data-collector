import 'package:data_collector/core/storage/database.dart';
import 'package:data_collector/core/storage/database_provider.dart';
import 'package:data_collector/features/collection/logic/local_package_cleanup.dart';
import 'package:data_collector/l10n/app_localizations.dart';
import 'package:data_collector/theme/epoch8_theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

Future<void> confirmAndDeleteLocalPackage(
  BuildContext context,
  WidgetRef ref,
  Package pkg,
) async {
  final loc = AppLocalizations.of(context);
  final ok =
      await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text(loc.confirmDeletePackageTitle),
          content: Text(
            loc.confirmDeletePackageBody(pkg.id),
            style: TextStyle(color: Epoch8Theme.textMuted, height: 1.4),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: Text(loc.cancel),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: Text(loc.delete),
            ),
          ],
        ),
      ) ??
      false;
  if (!ok || !context.mounted) return;
  await deleteLocalPackageStorage(ref.read(databaseProvider), pkg.id);
  if (!context.mounted) return;
  ScaffoldMessenger.of(
    context,
  ).showSnackBar(SnackBar(content: Text(loc.deletedFromDevice(pkg.id))));
}

Future<int?> confirmAndClearUploadedPackagesCache(
  BuildContext context,
  WidgetRef ref,
) async {
  final loc = AppLocalizations.of(context);
  final ok =
      await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text(loc.clearUploadedCacheConfirmTitle),
          content: Text(
            loc.clearUploadedCacheConfirmBody,
            style: TextStyle(color: Epoch8Theme.textMuted, height: 1.4),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: Text(loc.cancel),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: Text(loc.clear),
            ),
          ],
        ),
      ) ??
      false;
  if (!ok || !context.mounted) return null;
  final n = await deleteCompletedPackagesLocalCache(ref.read(databaseProvider));
  if (!context.mounted) return n;
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(
      content: Text(n == 0 ? loc.nothingToDelete : loc.clearedPackagesCount(n)),
    ),
  );
  return n;
}
