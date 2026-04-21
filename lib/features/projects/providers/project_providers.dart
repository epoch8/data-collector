import 'package:data_collector/core/api/api_environment.dart';
import 'package:data_collector/core/api/dio_provider.dart';
import 'package:data_collector/features/projects/project_catalog.dart';
import 'package:data_collector/features/projects/server_project_catalog.dart';
import 'package:data_collector/models/project_config.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Без `API_BASE_URL` — только bundled JSON. Иначе — Django + кэш (спека 09).
final projectsProvider = FutureProvider<List<Project>>((ref) async {
  if (!ApiEnvironment.isConfigured) {
    return ProjectCatalog.loadAll();
  }
  final dio = ref.watch(dioProvider);
  if (dio == null) return ProjectCatalog.loadAll();
  return ServerProjectCatalog(dio).loadProjectsWithFallback();
});
