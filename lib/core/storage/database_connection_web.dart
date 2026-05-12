import 'package:drift/drift.dart';
import 'package:drift/wasm.dart';

LazyDatabase openDriftConnection() {
  return LazyDatabase(() async {
    final result = await WasmDatabase.open(
      databaseName: 'data_collector',
      sqlite3Uri: Uri.base.resolve('sqlite3.wasm'),
      driftWorkerUri: Uri.base.resolve('drift_worker.js'),
    );
    return result.resolvedExecutor;
  });
}
