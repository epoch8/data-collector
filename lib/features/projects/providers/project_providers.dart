import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../../../models/project_config.dart';

part 'project_providers.g.dart';

@riverpod
List<Project> mockProjects(Ref ref) {
  return [
    Project(
      id: 'korovas-2026',
      name: 'Korovas',
      version: '1.0',
      config: ProjectConfig(fields: []),
    ),
  ];
}
