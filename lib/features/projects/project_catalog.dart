import 'dart:convert';

import 'package:data_collector/features/projects/catalog_project.dart';
import 'package:data_collector/models/project_config.dart';
import 'package:flutter/services.dart';

/// Loads [Project] definitions from bundled JSON (see `assets/config/`).
abstract final class ProjectCatalog {
  static const _manifestAsset = 'assets/config/projects.json';
  static const simplePhotoNotesAsset = 'assets/config/simple-photo-notes.json';

  static Future<Project> loadSimplePhotoNotes() =>
      loadOne(simplePhotoNotesAsset);

  static Future<Project> loadOne(String assetPath) async {
    final raw = await rootBundle.loadString(assetPath);
    return Project.fromJson(jsonDecode(raw) as Map<String, dynamic>);
  }

  static Future<List<CatalogProject>> loadAll() async {
    final manifestRaw = await rootBundle.loadString(_manifestAsset);
    final manifest = jsonDecode(manifestRaw) as Map<String, dynamic>;
    final paths = (manifest['projects'] as List<dynamic>)
        .map((e) => e.toString())
        .toList();
    final out = <CatalogProject>[];
    for (final path in paths) {
      final project = await loadOne(path);
      out.add(
        CatalogProject(
          id: project.id,
          name: project.name,
          forms: [ProjectFormEntry(formId: 'default', project: project)],
        ),
      );
    }
    return out;
  }
}
