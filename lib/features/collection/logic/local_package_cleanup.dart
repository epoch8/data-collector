import 'package:data_collector/core/storage/database.dart';
import 'package:flutter/foundation.dart';

import 'local_package_cleanup_io.dart'
    if (dart.library.html) 'local_package_cleanup_web.dart'
    as cleanup_fs;

/// Удаляет запись пакета в Drift и каталог `packages/<id>/` на диске (не web).
Future<void> deleteLocalPackageStorage(AppDatabase db, String packageId) async {
  await (db.delete(db.packages)..where((t) => t.id.equals(packageId))).go();
  if (kIsWeb) return;
  await cleanup_fs.deletePackageDirectoryIfExists(packageId);
}

/// Удаляет все пакеты со статусом «загружен на сервер» — запись и локальные файлы.
Future<int> deleteCompletedPackagesLocalCache(AppDatabase db) async {
  final rows = await (db.select(
    db.packages,
  )..where((t) => t.serverDeliveryState.equals('completed'))).get();
  for (final p in rows) {
    await deleteLocalPackageStorage(db, p.id);
  }
  return rows.length;
}
