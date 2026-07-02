import 'package:data_collector/core/storage/database.dart';
import 'package:dio/dio.dart';

import 'package_server_upload_io.dart'
    if (dart.library.html) 'package_server_upload_web.dart'
    as impl;

/// Загрузка одного пакета на Django API (спека 08).
///
/// [allowedProjectIds] — `project_id`, к которым у текущего пользователя есть доступ
/// по актуальному каталогу с сервера; иначе загрузка не начинается.
Future<void> uploadDriftPackageToServer({
  required Dio dio,
  required AppDatabase db,
  required Package pkg,
  required Set<String> allowedProjectIds,
}) => impl.uploadDriftPackageToServer(
  dio: dio,
  db: db,
  pkg: pkg,
  allowedProjectIds: allowedProjectIds,
);
