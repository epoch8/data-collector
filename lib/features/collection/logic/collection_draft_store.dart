import 'dart:convert';

import 'package:data_collector/core/storage/database.dart';
import 'package:data_collector/features/collection/logic/local_package_cleanup.dart';
import 'package:data_collector/features/collection/presentation/flow/package_payload_keys.dart';
import 'package:drift/drift.dart' show OrderingTerm, Value;

/// Локальный незавершённый пакет (спека: Draft).
const String kPackageStatusDraft = 'draft';

/// Последний черновик по проекту (если несколько — по дате создания).
Future<Package?> selectLatestDraftForProject(AppDatabase db, String projectId) async {
  final rows = await (db.select(db.packages)
        ..where((t) => t.projectId.equals(projectId))
        ..where((t) => t.status.equals(kPackageStatusDraft))
        ..orderBy([(t) => OrderingTerm.desc(t.createdAt)])
        ..limit(1))
      .get();
  return rows.isEmpty ? null : rows.first;
}

/// Удаляет все локальные черновики по [projectId] (запись + каталог на диске при наличии).
/// После завершённого пакета не должны оставаться «висячие» сессии, из‑за которых снова
/// показывается диалог продолжения или подтягиваются старые данные.
Future<int> deleteAllDraftPackagesForProject(AppDatabase db, String projectId) async {
  final drafts = await (db.select(db.packages)
        ..where((t) => t.projectId.equals(projectId))
        ..where((t) => t.status.equals(kPackageStatusDraft)))
      .get();
  var n = 0;
  for (final d in drafts) {
    await deleteLocalPackageStorage(db, d.id);
    n++;
  }
  return n;
}

int draftFlowStepFromUnpackedData(Map<String, dynamic> data) {
  final raw = data[PackagePayloadKeys.collectionDraftFlowStep];
  if (raw is int) return raw;
  if (raw is num) return raw.toInt();
  return 0;
}

/// Сохраняет или обновляет строку черновика с полным envelope JSON (как у завершённого пакета).
Future<void> upsertCollectionDraft({
  required AppDatabase db,
  required String packageId,
  required String projectId,
  required Map<String, dynamic> answers,
  required int flowStep,
  required DateTime createdAt,
}) async {
  final data = Map<String, dynamic>.from(answers);
  data[PackagePayloadKeys.collectionDraftFlowStep] = flowStep;
  final env = <String, dynamic>{
    'package_id': packageId,
    'project_id': projectId,
    'created_at': createdAt.toUtc().toIso8601String(),
    'data': data,
  };
  final json = jsonEncode(env);

  final existing =
      await (db.select(db.packages)..where((t) => t.id.equals(packageId))).get();
  if (existing.isNotEmpty && existing.first.status != kPackageStatusDraft) {
    // Не откатывать завершённый пакет в черновик (гонка debounce после submit на web/mobile).
    return;
  }
  if (existing.isEmpty) {
    await db.into(db.packages).insert(
          PackagesCompanion.insert(
            id: packageId,
            projectId: projectId,
            status: kPackageStatusDraft,
            createdAt: createdAt,
            dataJson: json,
          ),
        );
  } else {
    await (db.update(db.packages)..where((t) => t.id.equals(packageId))).write(
          PackagesCompanion(
            dataJson: Value(json),
            status: const Value(kPackageStatusDraft),
          ),
        );
  }
}
