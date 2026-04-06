import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:data_collector/core/storage/database.dart';

final databaseProvider = Provider<AppDatabase>((ref) {
  final db = AppDatabase();
  ref.onDispose(db.close);
  return db;
});

final packagesStreamProvider = StreamProvider<List<Package>>((ref) {
  final db = ref.watch(databaseProvider);
  return db.select(db.packages).watch();
});
