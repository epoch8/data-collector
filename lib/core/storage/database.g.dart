// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'database.dart';

// ignore_for_file: type=lint
class $PackagesTable extends Packages with TableInfo<$PackagesTable, Package> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $PackagesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _projectIdMeta = const VerificationMeta(
    'projectId',
  );
  @override
  late final GeneratedColumn<String> projectId = GeneratedColumn<String>(
    'project_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _statusMeta = const VerificationMeta('status');
  @override
  late final GeneratedColumn<String> status = GeneratedColumn<String>(
    'status',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta(
    'createdAt',
  );
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _dataJsonMeta = const VerificationMeta(
    'dataJson',
  );
  @override
  late final GeneratedColumn<String> dataJson = GeneratedColumn<String>(
    'data_json',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _serverDeliveryStateMeta =
      const VerificationMeta('serverDeliveryState');
  @override
  late final GeneratedColumn<String> serverDeliveryState =
      GeneratedColumn<String>(
        'server_delivery_state',
        aliasedName,
        false,
        type: DriftSqlType.string,
        requiredDuringInsert: false,
        defaultValue: const Constant<String>('pending'),
      );
  static const VerificationMeta _serverDeliveryErrorMeta =
      const VerificationMeta('serverDeliveryError');
  @override
  late final GeneratedColumn<String> serverDeliveryError =
      GeneratedColumn<String>(
        'server_delivery_error',
        aliasedName,
        true,
        type: DriftSqlType.string,
        requiredDuringInsert: false,
      );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    projectId,
    status,
    createdAt,
    dataJson,
    serverDeliveryState,
    serverDeliveryError,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'packages';
  @override
  VerificationContext validateIntegrity(
    Insertable<Package> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('project_id')) {
      context.handle(
        _projectIdMeta,
        projectId.isAcceptableOrUnknown(data['project_id']!, _projectIdMeta),
      );
    } else if (isInserting) {
      context.missing(_projectIdMeta);
    }
    if (data.containsKey('status')) {
      context.handle(
        _statusMeta,
        status.isAcceptableOrUnknown(data['status']!, _statusMeta),
      );
    } else if (isInserting) {
      context.missing(_statusMeta);
    }
    if (data.containsKey('created_at')) {
      context.handle(
        _createdAtMeta,
        createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta),
      );
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('data_json')) {
      context.handle(
        _dataJsonMeta,
        dataJson.isAcceptableOrUnknown(data['data_json']!, _dataJsonMeta),
      );
    } else if (isInserting) {
      context.missing(_dataJsonMeta);
    }
    if (data.containsKey('server_delivery_state')) {
      context.handle(
        _serverDeliveryStateMeta,
        serverDeliveryState.isAcceptableOrUnknown(
          data['server_delivery_state']!,
          _serverDeliveryStateMeta,
        ),
      );
    }
    if (data.containsKey('server_delivery_error')) {
      context.handle(
        _serverDeliveryErrorMeta,
        serverDeliveryError.isAcceptableOrUnknown(
          data['server_delivery_error']!,
          _serverDeliveryErrorMeta,
        ),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  Package map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return Package(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}id'],
      )!,
      projectId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}project_id'],
      )!,
      status: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}status'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at'],
      )!,
      dataJson: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}data_json'],
      )!,
      serverDeliveryState: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}server_delivery_state'],
      )!,
      serverDeliveryError: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}server_delivery_error'],
      ),
    );
  }

  @override
  $PackagesTable createAlias(String alias) {
    return $PackagesTable(attachedDatabase, alias);
  }
}

class Package extends DataClass implements Insertable<Package> {
  final String id;
  final String projectId;
  final String status;
  final DateTime createdAt;
  final String dataJson;
  final String serverDeliveryState;
  final String? serverDeliveryError;
  const Package({
    required this.id,
    required this.projectId,
    required this.status,
    required this.createdAt,
    required this.dataJson,
    required this.serverDeliveryState,
    this.serverDeliveryError,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['project_id'] = Variable<String>(projectId);
    map['status'] = Variable<String>(status);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['data_json'] = Variable<String>(dataJson);
    map['server_delivery_state'] = Variable<String>(serverDeliveryState);
    if (!nullToAbsent || serverDeliveryError != null) {
      map['server_delivery_error'] = Variable<String>(serverDeliveryError);
    }
    return map;
  }

  PackagesCompanion toCompanion(bool nullToAbsent) {
    return PackagesCompanion(
      id: Value(id),
      projectId: Value(projectId),
      status: Value(status),
      createdAt: Value(createdAt),
      dataJson: Value(dataJson),
      serverDeliveryState: Value(serverDeliveryState),
      serverDeliveryError: serverDeliveryError == null && nullToAbsent
          ? const Value.absent()
          : Value(serverDeliveryError),
    );
  }

  factory Package.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return Package(
      id: serializer.fromJson<String>(json['id']),
      projectId: serializer.fromJson<String>(json['projectId']),
      status: serializer.fromJson<String>(json['status']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      dataJson: serializer.fromJson<String>(json['dataJson']),
      serverDeliveryState: serializer.fromJson<String>(
        json['serverDeliveryState'],
      ),
      serverDeliveryError: serializer.fromJson<String?>(
        json['serverDeliveryError'],
      ),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'projectId': serializer.toJson<String>(projectId),
      'status': serializer.toJson<String>(status),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'dataJson': serializer.toJson<String>(dataJson),
      'serverDeliveryState': serializer.toJson<String>(serverDeliveryState),
      'serverDeliveryError': serializer.toJson<String?>(serverDeliveryError),
    };
  }

  Package copyWith({
    String? id,
    String? projectId,
    String? status,
    DateTime? createdAt,
    String? dataJson,
    String? serverDeliveryState,
    Value<String?> serverDeliveryError = const Value.absent(),
  }) => Package(
    id: id ?? this.id,
    projectId: projectId ?? this.projectId,
    status: status ?? this.status,
    createdAt: createdAt ?? this.createdAt,
    dataJson: dataJson ?? this.dataJson,
    serverDeliveryState: serverDeliveryState ?? this.serverDeliveryState,
    serverDeliveryError: serverDeliveryError.present
        ? serverDeliveryError.value
        : this.serverDeliveryError,
  );
  Package copyWithCompanion(PackagesCompanion data) {
    return Package(
      id: data.id.present ? data.id.value : this.id,
      projectId: data.projectId.present ? data.projectId.value : this.projectId,
      status: data.status.present ? data.status.value : this.status,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      dataJson: data.dataJson.present ? data.dataJson.value : this.dataJson,
      serverDeliveryState: data.serverDeliveryState.present
          ? data.serverDeliveryState.value
          : this.serverDeliveryState,
      serverDeliveryError: data.serverDeliveryError.present
          ? data.serverDeliveryError.value
          : this.serverDeliveryError,
    );
  }

  @override
  String toString() {
    return (StringBuffer('Package(')
          ..write('id: $id, ')
          ..write('projectId: $projectId, ')
          ..write('status: $status, ')
          ..write('createdAt: $createdAt, ')
          ..write('dataJson: $dataJson, ')
          ..write('serverDeliveryState: $serverDeliveryState, ')
          ..write('serverDeliveryError: $serverDeliveryError')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    projectId,
    status,
    createdAt,
    dataJson,
    serverDeliveryState,
    serverDeliveryError,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is Package &&
          other.id == this.id &&
          other.projectId == this.projectId &&
          other.status == this.status &&
          other.createdAt == this.createdAt &&
          other.dataJson == this.dataJson &&
          other.serverDeliveryState == this.serverDeliveryState &&
          other.serverDeliveryError == this.serverDeliveryError);
}

class PackagesCompanion extends UpdateCompanion<Package> {
  final Value<String> id;
  final Value<String> projectId;
  final Value<String> status;
  final Value<DateTime> createdAt;
  final Value<String> dataJson;
  final Value<String> serverDeliveryState;
  final Value<String?> serverDeliveryError;
  final Value<int> rowid;
  const PackagesCompanion({
    this.id = const Value.absent(),
    this.projectId = const Value.absent(),
    this.status = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.dataJson = const Value.absent(),
    this.serverDeliveryState = const Value.absent(),
    this.serverDeliveryError = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  PackagesCompanion.insert({
    required String id,
    required String projectId,
    required String status,
    required DateTime createdAt,
    required String dataJson,
    this.serverDeliveryState = const Value.absent(),
    this.serverDeliveryError = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       projectId = Value(projectId),
       status = Value(status),
       createdAt = Value(createdAt),
       dataJson = Value(dataJson);
  static Insertable<Package> custom({
    Expression<String>? id,
    Expression<String>? projectId,
    Expression<String>? status,
    Expression<DateTime>? createdAt,
    Expression<String>? dataJson,
    Expression<String>? serverDeliveryState,
    Expression<String>? serverDeliveryError,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (projectId != null) 'project_id': projectId,
      if (status != null) 'status': status,
      if (createdAt != null) 'created_at': createdAt,
      if (dataJson != null) 'data_json': dataJson,
      if (serverDeliveryState != null)
        'server_delivery_state': serverDeliveryState,
      if (serverDeliveryError != null)
        'server_delivery_error': serverDeliveryError,
      if (rowid != null) 'rowid': rowid,
    });
  }

  PackagesCompanion copyWith({
    Value<String>? id,
    Value<String>? projectId,
    Value<String>? status,
    Value<DateTime>? createdAt,
    Value<String>? dataJson,
    Value<String>? serverDeliveryState,
    Value<String?>? serverDeliveryError,
    Value<int>? rowid,
  }) {
    return PackagesCompanion(
      id: id ?? this.id,
      projectId: projectId ?? this.projectId,
      status: status ?? this.status,
      createdAt: createdAt ?? this.createdAt,
      dataJson: dataJson ?? this.dataJson,
      serverDeliveryState: serverDeliveryState ?? this.serverDeliveryState,
      serverDeliveryError: serverDeliveryError ?? this.serverDeliveryError,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (projectId.present) {
      map['project_id'] = Variable<String>(projectId.value);
    }
    if (status.present) {
      map['status'] = Variable<String>(status.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (dataJson.present) {
      map['data_json'] = Variable<String>(dataJson.value);
    }
    if (serverDeliveryState.present) {
      map['server_delivery_state'] = Variable<String>(
        serverDeliveryState.value,
      );
    }
    if (serverDeliveryError.present) {
      map['server_delivery_error'] = Variable<String>(
        serverDeliveryError.value,
      );
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('PackagesCompanion(')
          ..write('id: $id, ')
          ..write('projectId: $projectId, ')
          ..write('status: $status, ')
          ..write('createdAt: $createdAt, ')
          ..write('dataJson: $dataJson, ')
          ..write('serverDeliveryState: $serverDeliveryState, ')
          ..write('serverDeliveryError: $serverDeliveryError, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

abstract class _$AppDatabase extends GeneratedDatabase {
  _$AppDatabase(QueryExecutor e) : super(e);
  $AppDatabaseManager get managers => $AppDatabaseManager(this);
  late final $PackagesTable packages = $PackagesTable(this);
  @override
  Iterable<TableInfo<Table, Object?>> get allTables =>
      allSchemaEntities.whereType<TableInfo<Table, Object?>>();
  @override
  List<DatabaseSchemaEntity> get allSchemaEntities => [packages];
}

typedef $$PackagesTableCreateCompanionBuilder =
    PackagesCompanion Function({
      required String id,
      required String projectId,
      required String status,
      required DateTime createdAt,
      required String dataJson,
      Value<String> serverDeliveryState,
      Value<String?> serverDeliveryError,
      Value<int> rowid,
    });
typedef $$PackagesTableUpdateCompanionBuilder =
    PackagesCompanion Function({
      Value<String> id,
      Value<String> projectId,
      Value<String> status,
      Value<DateTime> createdAt,
      Value<String> dataJson,
      Value<String> serverDeliveryState,
      Value<String?> serverDeliveryError,
      Value<int> rowid,
    });

class $$PackagesTableFilterComposer
    extends Composer<_$AppDatabase, $PackagesTable> {
  $$PackagesTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get projectId => $composableBuilder(
    column: $table.projectId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get status => $composableBuilder(
    column: $table.status,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get dataJson => $composableBuilder(
    column: $table.dataJson,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get serverDeliveryState => $composableBuilder(
    column: $table.serverDeliveryState,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get serverDeliveryError => $composableBuilder(
    column: $table.serverDeliveryError,
    builder: (column) => ColumnFilters(column),
  );
}

class $$PackagesTableOrderingComposer
    extends Composer<_$AppDatabase, $PackagesTable> {
  $$PackagesTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get projectId => $composableBuilder(
    column: $table.projectId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get status => $composableBuilder(
    column: $table.status,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get dataJson => $composableBuilder(
    column: $table.dataJson,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get serverDeliveryState => $composableBuilder(
    column: $table.serverDeliveryState,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get serverDeliveryError => $composableBuilder(
    column: $table.serverDeliveryError,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$PackagesTableAnnotationComposer
    extends Composer<_$AppDatabase, $PackagesTable> {
  $$PackagesTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get projectId =>
      $composableBuilder(column: $table.projectId, builder: (column) => column);

  GeneratedColumn<String> get status =>
      $composableBuilder(column: $table.status, builder: (column) => column);

  GeneratedColumn<DateTime> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);

  GeneratedColumn<String> get dataJson =>
      $composableBuilder(column: $table.dataJson, builder: (column) => column);

  GeneratedColumn<String> get serverDeliveryState => $composableBuilder(
    column: $table.serverDeliveryState,
    builder: (column) => column,
  );

  GeneratedColumn<String> get serverDeliveryError => $composableBuilder(
    column: $table.serverDeliveryError,
    builder: (column) => column,
  );
}

class $$PackagesTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $PackagesTable,
          Package,
          $$PackagesTableFilterComposer,
          $$PackagesTableOrderingComposer,
          $$PackagesTableAnnotationComposer,
          $$PackagesTableCreateCompanionBuilder,
          $$PackagesTableUpdateCompanionBuilder,
          (Package, BaseReferences<_$AppDatabase, $PackagesTable, Package>),
          Package,
          PrefetchHooks Function()
        > {
  $$PackagesTableTableManager(_$AppDatabase db, $PackagesTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$PackagesTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$PackagesTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$PackagesTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<String> id = const Value.absent(),
                Value<String> projectId = const Value.absent(),
                Value<String> status = const Value.absent(),
                Value<DateTime> createdAt = const Value.absent(),
                Value<String> dataJson = const Value.absent(),
                Value<String> serverDeliveryState = const Value.absent(),
                Value<String?> serverDeliveryError = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => PackagesCompanion(
                id: id,
                projectId: projectId,
                status: status,
                createdAt: createdAt,
                dataJson: dataJson,
                serverDeliveryState: serverDeliveryState,
                serverDeliveryError: serverDeliveryError,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String id,
                required String projectId,
                required String status,
                required DateTime createdAt,
                required String dataJson,
                Value<String> serverDeliveryState = const Value.absent(),
                Value<String?> serverDeliveryError = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => PackagesCompanion.insert(
                id: id,
                projectId: projectId,
                status: status,
                createdAt: createdAt,
                dataJson: dataJson,
                serverDeliveryState: serverDeliveryState,
                serverDeliveryError: serverDeliveryError,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$PackagesTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $PackagesTable,
      Package,
      $$PackagesTableFilterComposer,
      $$PackagesTableOrderingComposer,
      $$PackagesTableAnnotationComposer,
      $$PackagesTableCreateCompanionBuilder,
      $$PackagesTableUpdateCompanionBuilder,
      (Package, BaseReferences<_$AppDatabase, $PackagesTable, Package>),
      Package,
      PrefetchHooks Function()
    >;

class $AppDatabaseManager {
  final _$AppDatabase _db;
  $AppDatabaseManager(this._db);
  $$PackagesTableTableManager get packages =>
      $$PackagesTableTableManager(_db, _db.packages);
}
