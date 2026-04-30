import 'package:data_collector/core/api/api_environment.dart';
import 'package:data_collector/core/api/dio_provider.dart';
import 'package:data_collector/features/projects/project_catalog.dart';
import 'package:data_collector/features/projects/server_project_catalog.dart';
import 'package:data_collector/models/project_config.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Сбрасывает кэш каталога при смене сессии Firebase (другой пользователь — другой доступ к проектам).
final firebaseAuthUserProvider = StreamProvider<User?>((ref) {
  return FirebaseAuth.instance.authStateChanges();
});

/// Без `API_BASE_URL` — только bundled JSON. Иначе при сети — актуальный `/v1/projects` + конфиги;
/// офлайн — кэш на диске, затем bundled (см. [ServerProjectCatalog.loadProjectsWithFallback]).
final projectsProvider = FutureProvider<List<Project>>((ref) async {
  List<Project> projects;
  if (!ApiEnvironment.isConfigured) {
    projects = await ProjectCatalog.loadAll();
  } else {
    // Дождаться первого снимка сессии перед `/v1/projects`, иначе часто два запроса подряд (loading → user).
    await ref.watch(firebaseAuthUserProvider.future);
    final dio = ref.watch(dioProvider);
    if (dio == null) {
      projects = await ProjectCatalog.loadAll();
    } else {
      projects = await ServerProjectCatalog(dio).loadProjectsWithFallback();
    }
  }

  // Всегда держим локальный «Заметка + фото» как офлайн-safe базовый проект.
  try {
    final defaultProject = await ProjectCatalog.loadSimplePhotoNotes();
    final idx = projects.indexWhere((p) => p.id == defaultProject.id);
    if (idx >= 0) {
      projects[idx] = defaultProject;
    } else {
      projects.insert(0, defaultProject);
    }
  } catch (_) {
    // Если asset поврежден, не ломаем загрузку остального каталога.
  }

  return projects;
});
