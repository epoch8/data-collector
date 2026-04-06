import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;
import 'dart:io';

part 'database.g.dart';

class Packages extends Table {
  TextColumn get id => text()();
  TextColumn get projectId => text()();
  TextColumn get status => text()();
  DateTimeColumn get createdAt => dateTime()();
  TextColumn get dataJson => text()();

  @override
  Set<Column> get primaryKey => {id};
}

@DriftDatabase(tables: [Packages])
class AppDatabase extends _$AppDatabase {
  AppDatabase() : super(_openConnection());

  @override
  int get schemaVersion => 1;
}

LazyDatabase _openConnection() {
  return LazyDatabase(() async {
    final dbFolder = await getApplicationDocumentsDirectory();
    final file = File(p.join(dbFolder.path, 'db.sqlite'));
    return NativeDatabase.createInBackground(file);
  });
}
