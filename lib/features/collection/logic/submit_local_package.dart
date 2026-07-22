import 'dart:convert';

import 'package:data_collector/bootstrap.dart';
import 'package:data_collector/core/storage/database.dart';
import 'package:data_collector/core/storage/database_provider.dart';
import 'package:data_collector/features/collection/logic/collection_draft_store.dart';
import 'package:data_collector/features/collection/logic/local_package_materializer.dart';
import 'package:data_collector/features/collection/providers/wizard_state_provider.dart';
import 'package:data_collector/features/collection/logic/package_payload_codec.dart';
import 'package:data_collector/l10n/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:drift/drift.dart' show Value;

/// Persists one completed package: on-disk layout per spec 07 + SQLite index row.
///
/// [existingDraftPackageId] — завершить сессию черновика с тем же [id] (и [draftCreatedAt]).
Future<void> submitLocalPackage({
  required WidgetRef ref,
  required BuildContext context,
  required String projectId,
  required Map<String, dynamic> answers,
  String? existingDraftPackageId,
  DateTime? draftCreatedAt,
}) async {
  final db = ref.read(databaseProvider);
  final String packageId =
      existingDraftPackageId ?? 'pkg_${DateTime.now().millisecondsSinceEpoch}';
  final createdAt = draftCreatedAt ?? DateTime.now();

  final answersForSave = Map<String, dynamic>.from(answers);
  stripCollectionDraftKeys(answersForSave);

  final materialized = await materializeLocalPackage(
    packageId: packageId,
    projectId: projectId,
    createdAt: createdAt,
    answers: answersForSave,
  );

  final payloadJson = jsonEncode(materialized.payload);
  if (existingDraftPackageId != null) {
    final rowsUpdated =
        await (db.update(
          db.packages,
        )..where((t) => t.id.equals(packageId))).write(
          PackagesCompanion(
            status: const Value('completed'),
            dataJson: Value(payloadJson),
            serverDeliveryState: const Value('pending'),
            serverDeliveryError: const Value.absent(),
          ),
        );
    if (rowsUpdated == 0) {
      await db
          .into(db.packages)
          .insert(
            PackagesCompanion.insert(
              id: packageId,
              projectId: projectId,
              status: 'completed',
              createdAt: createdAt,
              dataJson: payloadJson,
            ),
          );
    }
  } else {
    await db
        .into(db.packages)
        .insert(
          PackagesCompanion.insert(
            id: packageId,
            projectId: projectId,
            status: 'completed',
            createdAt: createdAt,
            dataJson: payloadJson,
          ),
        );
  }

  await deleteAllDraftPackagesForProject(db, projectId);

  if (!context.mounted) return;

  // Текст берём до go(); SnackBar — через корневой messenger, иначе после
  // ухода с review бывает "Looking up a deactivated widget's ancestor".
  final savedMsg = AppLocalizations.of(context).packageSavedLocal;
  context.go('/dashboard');
  // Сброс после ухода с экрана — иначе review перерисовывается с пустым wizard state.
  ref.read(wizardStateProvider(projectId).notifier).reset();

  rootScaffoldMessengerKey.currentState?.showSnackBar(
    SnackBar(
      content: Text(savedMsg),
      behavior: SnackBarBehavior.floating,
    ),
  );
}
