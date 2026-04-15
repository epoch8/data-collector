import 'package:data_collector/features/projects/project_catalog.dart';
import 'package:data_collector/models/project_config.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Все проекты из `assets/config/projects.json` и связанных файлов.
final projectsProvider = FutureProvider<List<Project>>((ref) async {
  return ProjectCatalog.loadAll();
});
