import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'dart:convert';
import 'features/projects/providers/project_providers.dart';
import 'features/collection/presentation/wizard_screen.dart';
import 'core/storage/database_provider.dart';

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
      builder: (context, state) => CollectionWizardScreen(projectId: state.pathParameters['id']!),
    ),
  ],
);

class DataCollectorApp extends StatelessWidget {
  const DataCollectorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Data Collector',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blueAccent),
        useMaterial3: true,
      ),
      routerConfig: _router,
    );
  }
}

class LoginScreen extends StatelessWidget {
  const LoginScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.collections, size: 80, color: Colors.blueAccent),
            const SizedBox(height: 16),
            const Text('Data Collector', style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
            const SizedBox(height: 48),
            ElevatedButton(
              onPressed: () => context.go('/dashboard'),
              child: const Text('Enter Application'),
            ),
          ],
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
        appBar: AppBar(
          title: const Text("Data Collector Workspace"),
          bottom: const TabBar(
            tabs: [
              Tab(icon: Icon(Icons.folder), text: "Projects"),
              Tab(icon: Icon(Icons.history), text: "History"),
            ],
          ),
          actions: [
            IconButton(
              icon: const Icon(Icons.logout),
              onPressed: () => context.go('/login'),
            )
          ],
        ),
        body: TabBarView(
          children: [
            projects.isEmpty
                ? const Center(child: Text('No projects mapped yet.'))
                : ListView.builder(
                    itemCount: projects.length,
                    itemBuilder: (context, index) {
                      final project = projects[index];
                      return Card(
                        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                        child: ListTile(
                          leading: const CircleAvatar(child: Icon(Icons.folder_special)),
                          title: Text(project.name, style: const TextStyle(fontWeight: FontWeight.bold)),
                          subtitle: Text('Version: ${project.version} • ${project.config.fields.length} steps required'),
                          trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                          onTap: () {
                            context.go('/project/${project.id}/wizard');
                          },
                        ),
                      );
                    },
                  ),
            packagesAsync.when(
              data: (packages) => packages.isEmpty
                  ? const Center(child: Text('No offline history yet.'))
                  : ListView.builder(
                      itemCount: packages.length,
                      itemBuilder: (context, index) {
                        final pkg = packages[index];
                        final rawMap = jsonDecode(pkg.dataJson) as Map<String, dynamic>;
                        return Card(
                          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                          child: ListTile(
                            leading: const Icon(Icons.cloud_done, color: Colors.green),
                            title: Text('Project: ${pkg.projectId}'),
                            subtitle: Text('Fields recorded: ${rawMap.length}\nRecorded on: ${pkg.createdAt.toString().split('.')[0]}'),
                            isThreeLine: true,
                          ),
                        );
                      },
                    ),
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, st) => Center(child: Text('Error: $e')),
            ),
          ],
        ),
      ),
    );
  }
}
