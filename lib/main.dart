import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'dart:convert';
import 'dart:io';
import 'features/projects/providers/project_providers.dart';
import 'models/project_config.dart';
import 'features/collection/presentation/korovas/korovas_collection_screen.dart';
import 'features/collection/presentation/korovas/korovas_keys.dart';
import 'features/collection/presentation/wizard_screen.dart';
import 'core/storage/database.dart';
import 'core/storage/database_provider.dart';
import 'core/package/package_paths.dart';
import 'features/collection/logic/package_payload_codec.dart';
import 'features/collection/logic/project_config_korovas.dart';
import 'theme/epoch8_theme.dart';
import 'theme/epoch8_ui.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await PackagePaths.init();
  runApp(const ProviderScope(child: DataCollectorApp()));
}

final _router = GoRouter(
  initialLocation: '/login',
  routes: [
    GoRoute(
      path: '/login',
      builder: (context, state) => const LoginScreen(),
    ),
    GoRoute(
      path: '/dashboard',
      builder: (context, state) => const DashboardScreen(),
    ),
    GoRoute(
      path: '/project/:id/wizard',
      builder: (context, state) {
        final id = state.pathParameters['id']!;
        return Consumer(
          builder: (context, ref, _) {
            final async = ref.watch(projectsProvider);
            return async.when(
              data: (projects) {
                final Project project;
                try {
                  project = projects.firstWhere((p) => p.id == id);
                } catch (_) {
                  return Scaffold(
                    backgroundColor: Epoch8Theme.bgDeep,
                    appBar: AppBar(title: const Text('Проект')),
                    body: const Center(child: Text('Проект не найден в конфигурации.')),
                  );
                }
                if (project.config.collectionFlow == 'korovas') {
                  return KorovasCollectionScreen(projectId: id);
                }
                return CollectionWizardScreen(projectId: id);
              },
              loading: () => const Scaffold(
                backgroundColor: Epoch8Theme.bgDeep,
                body: Center(child: CircularProgressIndicator()),
              ),
              error: (e, _) => Scaffold(
                backgroundColor: Epoch8Theme.bgDeep,
                body: Center(child: Text('Ошибка: $e')),
              ),
            );
          },
        );
      },
    ),
    GoRoute(
      path: '/history/project/:projectId/cow/:cowId',
      builder: (context, state) => CowHistoryScreen(
        projectId: state.pathParameters['projectId']!,
        cowId: Uri.decodeComponent(state.pathParameters['cowId']!),
      ),
    ),
    GoRoute(
      path: '/history/package/:packageId',
      builder: (context, state) => PackageHistoryScreen(packageId: state.pathParameters['packageId']!),
    ),
  ],
);

class DataCollectorApp extends StatelessWidget {
  const DataCollectorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Data Collector',
      theme: Epoch8Theme.dark,
      darkTheme: Epoch8Theme.dark,
      themeMode: ThemeMode.dark,
      routerConfig: _router,
      debugShowCheckedModeBanner: false,
    );
  }
}

class LoginScreen extends StatelessWidget {
  const LoginScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Scaffold(
      backgroundColor: Epoch8Theme.bgDeep,
      body: Epoch8ScreenBody(
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) {
              return SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: Epoch8Layout.pagePadding),
                child: ConstrainedBox(
                  constraints: BoxConstraints(minHeight: constraints.maxHeight),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const SizedBox(height: 24),
                      Container(
                        width: 190,
                        height: 190,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(32),
                          color: Epoch8Theme.card.withValues(alpha: 0.9),
                          border: Border.all(color: Epoch8Theme.border),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withValues(alpha: 0.45),
                              blurRadius: 32,
                              offset: const Offset(0, 16),
                            ),
                          ],
                        ),
                        clipBehavior: Clip.antiAlias,
                        padding: const EdgeInsets.all(16),
                        child: Image.asset(
                          'e8_logo.png',
                          fit: BoxFit.contain,
                        ),
                      ),
                      const SizedBox(height: 28),
                      Text(
                        'EPOCH8',
                        style: t.labelLarge?.copyWith(
                          color: Epoch8Theme.accent,
                          letterSpacing: 5,
                          fontWeight: FontWeight.w800,
                          fontSize: 12,
                        ),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        'Data Collector',
                        style: t.headlineSmall,
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 12),
                      Text(
                        'Сбор полевых данных и фото с офлайн-историей на устройстве',
                        style: t.bodyMedium?.copyWith(fontSize: 15),
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 40),
                      SizedBox(
                        width: double.infinity,
                        child: FilledButton(
                          onPressed: () => context.go('/dashboard'),
                          child: const Text('Перейти в рабочее пространство'),
                        ),
                      ),
                      const SizedBox(height: 32),
                    ],
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final projectsAsync = ref.watch(projectsProvider);
    final packagesAsync = ref.watch(packagesStreamProvider);

    return DefaultTabController(
      length: 2,
      child: Scaffold(
        backgroundColor: Epoch8Theme.bgDeep,
        appBar: AppBar(
          title: const Text('Рабочее пространство'),
          bottom: PreferredSize(
            preferredSize: const Size.fromHeight(58),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 0),
              child: Material(
                color: Epoch8Theme.card.withValues(alpha: 0.55),
                borderRadius: BorderRadius.circular(Epoch8Layout.radiusMd),
                child: TabBar(
                  padding: const EdgeInsets.all(4),
                  indicator: BoxDecoration(
                    borderRadius: BorderRadius.circular(Epoch8Layout.radiusSm + 2),
                    color: Epoch8Theme.accent.withValues(alpha: 0.18),
                    border: Border.all(color: Epoch8Theme.accent.withValues(alpha: 0.35)),
                  ),
                  indicatorSize: TabBarIndicatorSize.tab,
                  dividerHeight: 0,
                  tabs: const [
                    Tab(icon: Icon(Icons.folder_outlined, size: 20), text: 'Проекты'),
                    Tab(icon: Icon(Icons.history_outlined, size: 20), text: 'История'),
                  ],
                ),
              ),
            ),
          ),
          actions: [
            IconButton(
              icon: const Icon(Icons.logout_outlined),
              tooltip: 'Выйти',
              onPressed: () => context.go('/login'),
            ),
          ],
        ),
        body: Epoch8ScreenBody(
          child: TabBarView(
            children: [
              projectsAsync.when(
                data: (projects) => projects.isEmpty
                    ? const Epoch8EmptyState(
                        icon: Icons.folder_open_outlined,
                        title: 'Пока нет проектов',
                        subtitle: 'Добавьте проекты в assets/config/projects.json.',
                      )
                    : ListView.separated(
                        padding: const EdgeInsets.fromLTRB(
                          Epoch8Layout.pagePadding,
                          12,
                          Epoch8Layout.pagePadding,
                          24,
                        ),
                        itemCount: projects.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 12),
                        itemBuilder: (context, index) {
                          final project = projects[index];
                          return Epoch8Card(
                            accentBorder: project.id == 'korovas-2026',
                            child: ListTile(
                              contentPadding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
                              leading: Container(
                                width: 52,
                                height: 52,
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(14),
                                  color: Epoch8Theme.accent.withValues(alpha: 0.12),
                                  border: Border.all(color: Epoch8Theme.accent.withValues(alpha: 0.25)),
                                ),
                                child: const Icon(Icons.folder_special_outlined, color: Epoch8Theme.accent, size: 26),
                              ),
                              title: Text(
                                project.name,
                                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
                              ),
                              subtitle: Padding(
                                padding: const EdgeInsets.only(top: 6),
                                child: Text(
                                  project.config.collectionFlow == 'korovas'
                                      ? 'Версия ${project.version} • анкета → справка → ${project.korovasCameraFields.length} ракурса → проверка'
                                      : 'Версия ${project.version} • полей: ${project.config.fields.length}',
                                  style: Theme.of(context).textTheme.bodySmall?.copyWith(height: 1.4),
                                ),
                              ),
                              trailing: Container(
                                padding: const EdgeInsets.all(8),
                                decoration: BoxDecoration(
                                  color: Epoch8Theme.bgElevated,
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: const Icon(Icons.arrow_forward_ios_rounded, size: 16, color: Epoch8Theme.textMuted),
                              ),
                              onTap: () => context.go('/project/${project.id}/wizard'),
                            ),
                          );
                        },
                      ),
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (e, _) => Center(child: Text('Ошибка конфига: $e')),
              ),
              _historyTabBody(context, ref, projectsAsync, packagesAsync),
            ],
          ),
        ),
      ),
    );
  }
}

class CowHistoryScreen extends ConsumerWidget {
  const CowHistoryScreen({super.key, required this.projectId, required this.cowId});

  final String projectId;
  final String cowId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final packagesAsync = ref.watch(packagesStreamProvider);
    return Scaffold(
      backgroundColor: Epoch8Theme.bgDeep,
      appBar: AppBar(title: Text('Корова $cowId')),
      body: packagesAsync.when(
        data: (packages) {
          final filtered = packages
              .where((p) => p.projectId == projectId && _extractCowIdFromPackage(p) == cowId)
              .toList()
            ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
          if (filtered.isEmpty) {
            return const Epoch8EmptyState(
              icon: Icons.cloud_off_outlined,
              title: 'Пакеты не найдены',
              subtitle: 'Для этой коровы пока нет сохранённых пакетов.',
            );
          }
          return ListView.separated(
            padding: const EdgeInsets.fromLTRB(Epoch8Layout.pagePadding, 12, Epoch8Layout.pagePadding, 24),
            itemCount: filtered.length,
            separatorBuilder: (_, __) => const SizedBox(height: 12),
            itemBuilder: (context, index) {
              final pkg = filtered[index];
              final photoCount = _extractImagePaths(pkg).length;
              return Epoch8Card(
                child: ListTile(
                  title: Text(
                    'Пакет ${pkg.id}',
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                  subtitle: Text(
                    '${pkg.createdAt.toString().split('.').first}\nФото: $photoCount • Проект: ${pkg.projectId}',
                  ),
                  isThreeLine: true,
                  trailing: const Icon(Icons.arrow_forward_ios_rounded, size: 16, color: Epoch8Theme.textMuted),
                  onTap: () => context.push('/history/package/${pkg.id}'),
                ),
              );
            },
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, st) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text('Ошибка: $e', style: const TextStyle(color: Epoch8Theme.danger)),
          ),
        ),
      ),
    );
  }
}

class PackageHistoryScreen extends ConsumerWidget {
  const PackageHistoryScreen({super.key, required this.packageId});

  final String packageId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final packagesAsync = ref.watch(packagesStreamProvider);
    return Scaffold(
      backgroundColor: Epoch8Theme.bgDeep,
      appBar: AppBar(title: Text('Пакет $packageId')),
      body: packagesAsync.when(
        data: (packages) {
          Package? pkg;
          for (final item in packages) {
            if (item.id == packageId) {
              pkg = item;
              break;
            }
          }
          if (pkg == null) {
            return const Epoch8EmptyState(
              icon: Icons.error_outline,
              title: 'Пакет не найден',
              subtitle: 'Возможно, он был удалён или база обновилась.',
            );
          }
          final raw = _decodePackageData(pkg);
          final photos = _extractImagePaths(pkg);
          final metadataByPath = _extractPoseMetadataByPath(raw, pkg.id);
          final projectsList = ref.watch(projectsProvider).maybeWhen(
                data: (v) => v,
                orElse: () => null,
              );
          final projMeta = _projectById(projectsList, pkg.projectId);
          final isKorovas = projMeta?.config.collectionFlow == 'korovas';
          return ListView(
            padding: const EdgeInsets.fromLTRB(Epoch8Layout.pagePadding, 12, Epoch8Layout.pagePadding, 24),
            children: [
              Epoch8Card(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      projMeta != null ? 'Проект: ${projMeta.name}' : 'Проект: ${pkg.projectId}',
                      style: Theme.of(context).textTheme.titleSmall,
                    ),
                    if (isKorovas) ...[
                      const SizedBox(height: 8),
                      Text('Корова: ${_extractCowId(raw)}', style: Theme.of(context).textTheme.titleSmall),
                    ],
                    const SizedBox(height: 8),
                    Text('Идентификатор: ${pkg.projectId}', style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Epoch8Theme.textMuted)),
                    Text('Создан: ${pkg.createdAt.toString().split('.').first}', style: Theme.of(context).textTheme.bodyMedium),
                    Text('Фото: ${photos.length}', style: Theme.of(context).textTheme.bodyMedium),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              Epoch8Card(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Данные анкеты',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 12),
                    ..._packageFormSummaryRows(context, ref, pkg, raw),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              if (photos.isEmpty)
                const Epoch8EmptyState(
                  icon: Icons.photo_library_outlined,
                  title: 'В пакете нет фото',
                  subtitle: 'Сохранены только поля формы.',
                )
              else
                ...photos.map((path) {
                  final meta = metadataByPath[path];
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Epoch8Card(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          ClipRRect(
                            borderRadius: BorderRadius.circular(12),
                            child: File(path).existsSync()
                                ? InkWell(
                                    onTap: () => _showFullPhoto(context, path),
                                    child: Stack(
                                      children: [
                                        Image.file(File(path), height: 180, width: double.infinity, fit: BoxFit.cover),
                                        Positioned(
                                          right: 8,
                                          bottom: 8,
                                          child: Container(
                                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                            decoration: BoxDecoration(
                                              color: Colors.black.withValues(alpha: 0.55),
                                              borderRadius: BorderRadius.circular(8),
                                            ),
                                            child: const Text(
                                              'Открыть',
                                              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                  )
                                : Container(
                                    height: 120,
                                    color: Epoch8Theme.bgElevated,
                                    alignment: Alignment.center,
                                    child: const Text('Файл не найден на устройстве'),
                                  ),
                          ),
                          const SizedBox(height: 10),
                          Text(path.split(RegExp(r'[\\/]')).last, style: Theme.of(context).textTheme.titleSmall),
                          const SizedBox(height: 6),
                          Text(
                            'Путь: $path',
                            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Epoch8Theme.textMuted),
                          ),
                          if (meta != null) ...[
                            const SizedBox(height: 8),
                            Theme(
                              data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
                              child: ExpansionTile(
                                tilePadding: EdgeInsets.zero,
                                childrenPadding: EdgeInsets.zero,
                                iconColor: Epoch8Theme.textMuted,
                                collapsedIconColor: Epoch8Theme.textMuted,
                                title: Text(
                                  'Параметры кадра и камеры',
                                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w600),
                                ),
                                children: [
                                  SelectableText(
                                    const JsonEncoder.withIndent('  ').convert(meta),
                                    style: Theme.of(context).textTheme.bodySmall?.copyWith(height: 1.35),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  );
                }),
            ],
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, st) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text('Ошибка: $e', style: const TextStyle(color: Epoch8Theme.danger)),
          ),
        ),
      ),
    );
  }
}

Widget _historyTabBody(
  BuildContext context,
  WidgetRef ref,
  AsyncValue<List<Project>> projectsAsync,
  AsyncValue<List<Package>> packagesAsync,
) {
  return projectsAsync.when(
    data: (projects) {
      return packagesAsync.when(
        data: (packages) {
          if (packages.isEmpty) {
            return const Epoch8EmptyState(
              icon: Icons.cloud_outlined,
              title: 'История пуста',
              subtitle: 'Отправленные пакеты появятся здесь.',
            );
          }
          final byProject = <String, List<Package>>{};
          for (final p in packages) {
            byProject.putIfAbsent(p.projectId, () => []).add(p);
          }
          final knownIds = projects.map((p) => p.id).toSet();
          final sections = <Widget>[];
          for (final proj in projects) {
            final pkgs = byProject[proj.id];
            if (pkgs == null || pkgs.isEmpty) continue;
            sections.add(_historyProjectSection(context, proj, pkgs));
          }
          for (final entry in byProject.entries) {
            if (knownIds.contains(entry.key)) continue;
            sections.add(_historyOrphanProjectSection(context, entry.key, entry.value));
          }
          return ListView(
            padding: const EdgeInsets.fromLTRB(Epoch8Layout.pagePadding, 12, Epoch8Layout.pagePadding, 24),
            children: sections,
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Ошибка: $e')),
      );
    },
    loading: () => const Center(child: CircularProgressIndicator()),
    error: (e, _) => Center(child: Text('Ошибка конфига: $e')),
  );
}

Widget _historyProjectSection(BuildContext context, Project proj, List<Package> packages) {
  final isKorovas = proj.config.collectionFlow == 'korovas';
  return Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Padding(
        padding: const EdgeInsets.only(bottom: 8, top: 4),
        child: Row(
          children: [
            Icon(isKorovas ? Icons.pets_outlined : Icons.folder_outlined, size: 20, color: Epoch8Theme.accent),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                proj.name,
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                      color: Epoch8Theme.accent,
                    ),
              ),
            ),
            Text(
              '${packages.length} пак.',
              style: Theme.of(context).textTheme.labelSmall?.copyWith(color: Epoch8Theme.textMuted),
            ),
          ],
        ),
      ),
      if (isKorovas) ...[
        for (final g in _groupPackagesByCow(packages)) ...[
          Epoch8Card(
            child: ListTile(
              contentPadding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
              leading: Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(12),
                  color: Epoch8Theme.accent.withValues(alpha: 0.12),
                  border: Border.all(color: Epoch8Theme.accent.withValues(alpha: 0.25)),
                ),
                child: const Icon(Icons.pets_outlined, color: Epoch8Theme.accent, size: 24),
              ),
              title: Text('Корова ${g.cowId}', style: const TextStyle(fontWeight: FontWeight.w600)),
              subtitle: Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Text(
                  'Пакетов: ${g.packages.length} • Фото: ${g.totalPhotos}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
              trailing: const Icon(Icons.arrow_forward_ios_rounded, size: 16, color: Epoch8Theme.textMuted),
              onTap: () => context.push('/history/project/${proj.id}/cow/${Uri.encodeComponent(g.cowId)}'),
            ),
          ),
          const SizedBox(height: 12),
        ],
      ] else ...[
        for (final pkg in (packages.toList()..sort((a, b) => b.createdAt.compareTo(a.createdAt)))) ...[
          Epoch8Card(
            child: ListTile(
              contentPadding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
              leading: Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(12),
                  color: Epoch8Theme.card,
                  border: Border.all(color: Epoch8Theme.border),
                ),
                child: const Icon(Icons.photo_library_outlined, color: Epoch8Theme.textMuted, size: 24),
              ),
              title: Text(
                pkg.id,
                style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              subtitle: Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Text(
                  '${pkg.createdAt.toString().split('.').first} • фото: ${_extractImagePaths(pkg).length}\n${_historyPackageSubtitle(pkg)}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
              isThreeLine: true,
              trailing: const Icon(Icons.arrow_forward_ios_rounded, size: 16, color: Epoch8Theme.textMuted),
              onTap: () => context.push('/history/package/${pkg.id}'),
            ),
          ),
          const SizedBox(height: 12),
        ],
      ],
      const SizedBox(height: 8),
    ],
  );
}

String _historyPackageSubtitle(Package pkg) {
  final raw = unpackPackageFormData(pkg.dataJson);
  final n = raw['session_note']?.toString().trim() ?? '';
  if (n.isEmpty) return '';
  return n.length > 80 ? '${n.substring(0, 80)}…' : n;
}

Widget _historyOrphanProjectSection(BuildContext context, String projectId, List<Package> packages) {
  final sorted = packages.toList()..sort((a, b) => b.createdAt.compareTo(a.createdAt));
  return Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Padding(
        padding: const EdgeInsets.only(bottom: 8, top: 4),
        child: Text(
          'Проект $projectId (нет в конфиге)',
          style: Theme.of(context).textTheme.titleSmall?.copyWith(color: Epoch8Theme.textMuted, fontWeight: FontWeight.w600),
        ),
      ),
      for (final pkg in sorted) ...[
        Epoch8Card(
          child: ListTile(
            title: Text(pkg.id, style: const TextStyle(fontWeight: FontWeight.w600)),
            subtitle: Text(pkg.createdAt.toString().split('.').first),
            trailing: const Icon(Icons.arrow_forward_ios_rounded, size: 16, color: Epoch8Theme.textMuted),
            onTap: () => context.push('/history/package/${pkg.id}'),
          ),
        ),
        const SizedBox(height: 12),
      ],
    ],
  );
}

Project? _projectById(List<Project>? projects, String id) {
  if (projects == null) return null;
  for (final p in projects) {
    if (p.id == id) return p;
  }
  return null;
}

List<Widget> _packageFormSummaryRows(BuildContext context, WidgetRef ref, Package pkg, Map<String, dynamic> raw) {
  final projects = ref.watch(projectsProvider).maybeWhen(
        data: (v) => v,
        orElse: () => null,
      );
  final proj = _projectById(projects, pkg.projectId);
  if (proj?.config.collectionFlow == 'korovas') {
    return [
      _packageHistoryFieldRow(context, 'ID коровы', raw[KorovasKeys.cowId]?.toString()),
      _packageHistoryFieldRow(context, 'Время скана', _formatPackageScanTime(raw[KorovasKeys.scanTime])),
      _packageHistoryFieldRow(context, 'Возраст', raw[KorovasKeys.cowAge]?.toString()),
      _packageHistoryFieldRow(context, 'Вес', raw[KorovasKeys.cowWeight]?.toString()),
      _packageHistoryFieldRow(context, 'Порода', raw[KorovasKeys.cowBreed]?.toString()),
    ];
  }
  return _genericPayloadFieldRows(context, raw);
}

List<Widget> _genericPayloadFieldRows(BuildContext context, Map<String, dynamic> raw) {
  const skip = {'korovas_camera_context'};
  final out = <Widget>[];
  final keys = raw.keys.where((k) => !skip.contains(k)).toList()..sort();
  for (final k in keys) {
    final v = raw[k];
    String display;
    if (v == null) {
      display = '—';
    } else if (v is List) {
      if (v.isEmpty) {
        display = '—';
      } else if (v.every((x) => x is String && (x.contains('/') || x.contains('\\') || x.startsWith('blobs/')))) {
        display = '${v.length} файл(ов)';
      } else {
        display = v.map((x) => x.toString()).join(', ');
      }
    } else if (v is Map) {
      display = '{…}';
    } else {
      display = v.toString();
    }
    out.add(_packageHistoryFieldRow(context, k, display));
  }
  return out;
}

class _CowGroup {
  const _CowGroup({required this.cowId, required this.packages, required this.totalPhotos});

  final String cowId;
  final List<Package> packages;
  final int totalPhotos;
}

List<_CowGroup> _groupPackagesByCow(List<Package> packages) {
  final byCow = <String, List<Package>>{};
  for (final pkg in packages) {
    final cowId = _extractCowIdFromPackage(pkg);
    byCow.putIfAbsent(cowId, () => <Package>[]).add(pkg);
  }

  final groups = byCow.entries
      .map(
        (entry) => _CowGroup(
          cowId: entry.key,
          packages: entry.value..sort((a, b) => b.createdAt.compareTo(a.createdAt)),
          totalPhotos: entry.value.fold<int>(0, (sum, pkg) => sum + _extractImagePaths(pkg).length),
        ),
      )
      .toList()
    ..sort((a, b) {
      final aDate = a.packages.isNotEmpty ? a.packages.first.createdAt : DateTime.fromMillisecondsSinceEpoch(0);
      final bDate = b.packages.isNotEmpty ? b.packages.first.createdAt : DateTime.fromMillisecondsSinceEpoch(0);
      return bDate.compareTo(aDate);
    });
  return groups;
}

String _formatPackageScanTime(dynamic v) {
  if (v == null) return '—';
  final s = v.toString().trim();
  if (s.isEmpty) return '—';
  final d = DateTime.tryParse(s)?.toLocal();
  if (d == null) return s;
  String two(int n) => n.toString().padLeft(2, '0');
  return '${d.year}-${two(d.month)}-${two(d.day)} ${two(d.hour)}:${two(d.minute)}';
}

Widget _packageHistoryFieldRow(BuildContext context, String label, String? value) {
  final v = (value == null || value.trim().isEmpty) ? '—' : value.trim();
  return Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 120,
          child: Text(label, style: TextStyle(color: Epoch8Theme.textMuted, fontSize: 13)),
        ),
        Expanded(child: Text(v, style: Theme.of(context).textTheme.bodyMedium)),
      ],
    ),
  );
}

String _extractCowIdFromPackage(Package pkg) => _extractCowId(_decodePackageData(pkg));

Map<String, dynamic> _decodePackageData(Package pkg) => unpackPackageFormData(pkg.dataJson);

String _extractCowId(Map<String, dynamic> data) {
  const keys = ['cow_identifier', 'cow_id', 'cowId', 'animal_id', 'animalId', 'cow_tag', 'tag_id'];
  for (final k in keys) {
    final value = data[k]?.toString().trim();
    if (value != null && value.isNotEmpty) return value;
  }
  return 'без-id';
}

List<String> _extractImagePaths(Package pkg) {
  final data = _decodePackageData(pkg);
  final out = <String>{};
  for (final entry in data.entries) {
    final key = entry.key.toLowerCase();
    final value = entry.value;
    if (value is String && value.isNotEmpty && (key.contains('photo') || key.contains('image') || key.contains('pose_'))) {
      out.add(PackagePaths.resolveMediaReference(value, pkg.id));
    }
    if (value is List) {
      for (final item in value) {
        final path = item?.toString() ?? '';
        if (path.isNotEmpty) {
          out.add(PackagePaths.resolveMediaReference(path, pkg.id));
        }
      }
    }
  }
  return out.toList();
}

Map<String, Map<String, dynamic>> _extractPoseMetadataByPath(Map<String, dynamic> data, String packageId) {
  final out = <String, Map<String, dynamic>>{};
  final ctx = data['korovas_camera_context'];
  if (ctx is! Map) return out;
  final poses = ctx['poses'];
  if (poses is! Map) return out;

  for (final poseEntry in poses.entries) {
    final poseValue = poseEntry.value;
    if (poseValue is! Map) continue;
    final shots = poseValue['shots'];
    if (shots is! List) continue;
    for (final shot in shots) {
      if (shot is! Map) continue;
      final imagePath = shot['image_path']?.toString();
      if (imagePath == null || imagePath.isEmpty) continue;
      final resolved = PackagePaths.resolveMediaReference(imagePath, packageId);
      final payload = <String, dynamic>{'pose': poseEntry.key.toString()};
      for (final key in ['collected_at', 'exif', 'derived']) {
        payload[key] = shot[key];
      }
      out[resolved] = payload;
    }
  }
  return out;
}

Future<void> _showFullPhoto(BuildContext context, String path) async {
  await showDialog<void>(
    context: context,
    builder: (context) {
      final file = File(path);
      return Dialog(
        backgroundColor: Colors.black,
        insetPadding: const EdgeInsets.all(10),
        child: Stack(
          children: [
            Positioned.fill(
              child: file.existsSync()
                  ? InteractiveViewer(
                      minScale: 0.8,
                      maxScale: 6,
                      child: Center(child: Image.file(file, fit: BoxFit.contain)),
                    )
                  : const Center(child: Text('Файл не найден', style: TextStyle(color: Colors.white70))),
            ),
            Positioned(
              right: 8,
              top: 8,
              child: IconButton(
                onPressed: () => Navigator.of(context).pop(),
                icon: const Icon(Icons.close, color: Colors.white),
                tooltip: 'Закрыть',
              ),
            ),
          ],
        ),
      );
    },
  );
}
