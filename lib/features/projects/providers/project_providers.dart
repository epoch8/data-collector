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

/// Без `API_BASE_URL` — только bundled JSON.
/// При `API_BASE_URL` каталог и конфиги грузятся только с сервера.
final projectsProvider = FutureProvider<List<Project>>((ref) async {
  if (!ApiEnvironment.isConfigured) {
    return ProjectCatalog.loadAll();
  }

  // Дождаться первого снимка сессии перед `/v1/projects`, иначе часто два запроса подряд (loading → user).
  await ref.watch(firebaseAuthUserProvider.future);
  final dio = ref.watch(dioProvider);
  if (dio == null) {
    throw StateError('API configured but Dio is not initialized');
  }
  return ServerProjectCatalog(dio).loadProjectsWithFallback();
});
