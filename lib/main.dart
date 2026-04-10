import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'dart:convert';
import 'features/projects/providers/project_providers.dart';
import 'features/collection/presentation/korovas/korovas_collection_screen.dart';
import 'features/collection/presentation/wizard_screen.dart';
import 'core/storage/database_provider.dart';
import 'theme/epoch8_theme.dart';
import 'theme/epoch8_ui.dart';

void main() {
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
        if (id == 'korovas-2026') {
          return KorovasCollectionScreen(projectId: id);
        }
        return CollectionWizardScreen(projectId: id);
      },
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
                      Stack(
                        alignment: Alignment.center,
                        children: [
                          Container(
                            width: 160,
                            height: 160,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              gradient: RadialGradient(
                                colors: [
                                  Epoch8Theme.accent.withValues(alpha: 0.22),
                                  Epoch8Theme.accent.withValues(alpha: 0.0),
                                ],
                              ),
                            ),
                          ),
                          Container(
                            padding: const EdgeInsets.all(28),
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: Epoch8Theme.card.withValues(alpha: 0.85),
                              border: Border.all(color: Epoch8Theme.border),
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black.withValues(alpha: 0.45),
                                  blurRadius: 32,
                                  offset: const Offset(0, 16),
                                ),
                              ],
                            ),
                            child: Icon(
                              Icons.hub_outlined,
                              size: 56,
                              color: Epoch8Theme.accent.withValues(alpha: 0.95),
                            ),
                          ),
                        ],
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
    final projects = ref.watch(mockProjectsProvider);
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
              projects.isEmpty
                  ? const Epoch8EmptyState(
                      icon: Icons.folder_open_outlined,
                      title: 'Пока нет проектов',
                      subtitle: 'Когда проекты появятся в конфигурации, они отобразятся здесь.',
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
                                project.config.fields.isEmpty
                                    ? 'Версия ${project.version} • анкета → справка → 3 ракурса → проверка'
                                    : 'Версия ${project.version} • шагов: ${project.config.fields.length}',
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
              packagesAsync.when(
                data: (packages) => packages.isEmpty
                    ? const Epoch8EmptyState(
                        icon: Icons.cloud_outlined,
                        title: 'История пуста',
                        subtitle: 'Отправленные пакеты появятся здесь.',
                      )
                    : ListView.separated(
                        padding: const EdgeInsets.fromLTRB(
                          Epoch8Layout.pagePadding,
                          12,
                          Epoch8Layout.pagePadding,
                          24,
                        ),
                        itemCount: packages.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 12),
                        itemBuilder: (context, index) {
                          final pkg = packages[index];
                          final rawMap = jsonDecode(pkg.dataJson) as Map<String, dynamic>;
                          return Epoch8Card(
                            child: ListTile(
                              contentPadding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
                              leading: Container(
                                width: 48,
                                height: 48,
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(12),
                                  color: Epoch8Theme.success.withValues(alpha: 0.12),
                                  border: Border.all(color: Epoch8Theme.success.withValues(alpha: 0.25)),
                                ),
                                child: const Icon(Icons.cloud_done_rounded, color: Epoch8Theme.success, size: 24),
                              ),
                              title: Text(
                                'Проект ${pkg.projectId}',
                                style: const TextStyle(fontWeight: FontWeight.w600),
                              ),
                              subtitle: Padding(
                                padding: const EdgeInsets.only(top: 6),
                                child: Text(
                                  'Полей в пакете: ${rawMap.length}\n${pkg.createdAt.toString().split('.')[0]}',
                                  style: Theme.of(context).textTheme.bodySmall,
                                ),
                              ),
                              isThreeLine: true,
                            ),
                          );
                        },
                      ),
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (e, st) => Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Text('Ошибка: $e', style: const TextStyle(color: Epoch8Theme.danger)),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
