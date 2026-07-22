import 'dart:convert';

import 'package:data_collector/core/storage/database.dart';
import 'package:data_collector/features/collection/logic/local_package_cleanup.dart';
import 'package:data_collector/features/collection/presentation/flow/package_payload_keys.dart';
import 'package:drift/drift.dart' show OrderingTerm, Value;

/// Локальный незавершённый пакет (спека: Draft).
const String kPackageStatusDraft = 'draft';

String envelopeFormId(Map<String, dynamic> env) {
  final raw = env['form_id'];
  if (raw is String && raw.trim().isNotEmpty) return raw.trim();
  return 'default';
}

bool _draftMatchesForm(Package row, String formId) {
  try {
    final env = jsonDecode(row.dataJson);
    if (env is Map<String, dynamic>) {
      return envelopeFormId(env) == formId;
    }
    if (env is Map) {
      return envelopeFormId(Map<String, dynamic>.from(env)) == formId;
    }
  } catch (_) {}
  return formId == 'default';
}

/// Последний черновик по проекту и форме (если несколько — по дате создания).
Future<Package?> selectLatestDraftForProject(
  AppDatabase db,
  String projectId, {
  String formId = 'default',
}) async {
  final rows =
      await (db.select(db.packages)
            ..where((t) => t.projectId.equals(projectId))
            ..where((t) => t.status.equals(kPackageStatusDraft))
            ..orderBy([(t) => OrderingTerm.desc(t.createdAt)]))
          .get();
  for (final row in rows) {
    if (_draftMatchesForm(row, formId)) return row;
  }
  return null;
}

/// Удаляет локальные черновики project+form (запись + каталог на диске при наличии).
Future<int> deleteAllDraftPackagesForProject(
  AppDatabase db,
  String projectId, {
  String formId = 'default',
}) async {
  final drafts =
      await (db.select(db.packages)
            ..where((t) => t.projectId.equals(projectId))
            ..where((t) => t.status.equals(kPackageStatusDraft)))
          .get();
  var n = 0;
  for (final d in drafts) {
    if (!_draftMatchesForm(d, formId)) continue;
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
  String formId = 'default',
  String? formName,
  String? formVersion,
}) async {
  final data = Map<String, dynamic>.from(answers);
  data[PackagePayloadKeys.collectionDraftFlowStep] = flowStep;
  final env = <String, dynamic>{
    'package_id': packageId,
    'project_id': projectId,
    'form_id': formId,
    if (formName != null && formName.isNotEmpty) 'form_name': formName,
    if (formVersion != null && formVersion.isNotEmpty)
      'form_version': formVersion,
    'created_at': createdAt.toUtc().toIso8601String(),
    'data': data,
  };
  final json = jsonEncode(env);

  final existing = await (db.select(
    db.packages,
  )..where((t) => t.id.equals(packageId))).get();
  if (existing.isNotEmpty && existing.first.status != kPackageStatusDraft) {
    // Не откатывать завершённый пакет в черновик (гонка debounce после submit на web/mobile).
    return;
  }
  if (existing.isEmpty) {
    await db
        .into(db.packages)
        .insert(
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
