import 'dart:io';

import 'package:data_collector/core/package/package_paths.dart';
import 'package:data_collector/core/storage/database.dart';
import 'package:flutter/foundation.dart';

/// Удаляет запись пакета в Drift и каталог `packages/<id>/` на диске (не web).
Future<void> deleteLocalPackageStorage(AppDatabase db, String packageId) async {
  await (db.delete(db.packages)..where((t) => t.id.equals(packageId))).go();
  if (kIsWeb) return;
  final root = PackagePaths.packageRootFor(packageId);
  if (root.isEmpty) return;
  try {
    final dir = Directory(root);
    if (await dir.exists()) await dir.delete(recursive: true);
  } catch (_) {}
}

/// Удаляет все пакеты со статусом «загружен на сервер» — запись и локальные файлы.
Future<int> deleteCompletedPackagesLocalCache(AppDatabase db) async {
  final rows =
      await (db.select(db.packages)..where((t) => t.serverDeliveryState.equals('completed'))).get();
  for (final p in rows) {
    await deleteLocalPackageStorage(db, p.id);
  }
  return rows.length;
}
