import 'package:data_collector/models/project_config.dart';

/// Форма внутри проекта (один config.json).
class ProjectFormEntry {
  const ProjectFormEntry({required this.formId, required this.project});

  final String formId;

  /// Конфиг формы; [Project.name] — отображаемое имя формы.
  final Project project;

  String get formName => project.name;
  String get formVersion => project.version;
}

/// Элемент каталога: Django-проект + список форм.
class CatalogProject {
  const CatalogProject({
    required this.id,
    required this.name,
    required this.forms,
  });

  final String id;

  /// Имя проекта в каталоге (не имя формы).
  final String name;
  final List<ProjectFormEntry> forms;

  ProjectFormEntry? formById(String formId) {
    for (final f in forms) {
      if (f.formId == formId) return f;
    }
    return null;
  }

  /// Единственная / default форма, если picker не нужен.
  ProjectFormEntry? get primaryForm {
    if (forms.isEmpty) return null;
    for (final f in forms) {
      if (f.formId == 'default') return f;
    }
    return forms.first;
  }
}

extension CatalogProjectListX on List<CatalogProject> {
  CatalogProject? byId(String projectId) {
    for (final p in this) {
      if (p.id == projectId) return p;
    }
    return null;
  }

  Set<String> get projectIds => map((p) => p.id).toSet();
}
