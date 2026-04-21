import 'package:data_collector/core/api/api_environment.dart';
import 'package:data_collector/core/api/dio_provider.dart';
import 'package:data_collector/core/storage/database.dart';
import 'package:data_collector/core/storage/database_provider.dart';
import 'package:data_collector/features/collection/logic/package_server_upload.dart';
import 'package:data_collector/features/projects/providers/project_providers.dart';
import 'package:data_collector/features/projects/server_project_catalog.dart';
import 'package:data_collector/theme/epoch8_theme.dart';
import 'package:data_collector/theme/epoch8_ui.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Вкладка «Сервер»: синхронизация проектов и отправка пакетов на Django.
class ServerSyncTab extends ConsumerStatefulWidget {
  const ServerSyncTab({super.key});

  @override
  ConsumerState<ServerSyncTab> createState() => _ServerSyncTabState();
}

class _ServerSyncTabState extends ConsumerState<ServerSyncTab> {
  bool _syncing = false;
  String? _busyPackageId;

  Future<void> _syncProjects() async {
    final dio = ref.read(dioProvider);
    if (dio == null) return;
    setState(() => _syncing = true);
    try {
      await ServerProjectCatalog(dio).syncFromServer();
      ref.invalidate(projectsProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Проекты обновлены с сервера')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Ошибка синхронизации: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _syncing = false);
    }
  }

  Future<void> _uploadOne(Package pkg) async {
    final dio = ref.read(dioProvider);
    if (dio == null) return;
    setState(() => _busyPackageId = pkg.id);
    try {
      final db = ref.read(databaseProvider);
      await uploadDriftPackageToServer(dio: dio, db: db, pkg: pkg);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Пакет ${pkg.id} отправлен')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Ошибка: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _busyPackageId = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!ApiEnvironment.isConfigured) {
      return Epoch8ScreenBody(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(
              'Чтобы ходить на Django с эмулятора, запустите приложение с:\n\n'
              'flutter run '
              '--dart-define=API_BASE_URL=http://10.0.2.2:8000\n\n'
              '(порт как у runserver). При токене на сервере добавьте:\n'
              '--dart-define=API_BEARER_TOKEN=...',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
          ),
        ),
      );
    }

    final dio = ref.watch(dioProvider);
    final packagesAsync = ref.watch(packagesStreamProvider);

    return Epoch8ScreenBody(
      child: ListView(
        padding: const EdgeInsets.fromLTRB(Epoch8Layout.pagePadding, 12, Epoch8Layout.pagePadding, 24),
        children: [
          Text(
            'База: ${ApiEnvironment.normalizedBaseUrl()}',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Epoch8Theme.textMuted),
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: (_syncing || dio == null) ? null : _syncProjects,
            icon: _syncing
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.cloud_download_outlined),
            label: Text(_syncing ? 'Качаем конфиги…' : 'Синхронизировать проекты'),
          ),
          const SizedBox(height: 24),
          Text(
            'Очередь на сервер',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 8),
          packagesAsync.when(
            data: (packages) {
              final queue = packages
                  .where((p) => p.serverDeliveryState != 'completed')
                  .toList()
                ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
              if (queue.isEmpty) {
                return const Padding(
                  padding: EdgeInsets.only(top: 16),
                  child: Epoch8EmptyState(
                    icon: Icons.cloud_done_outlined,
                    title: 'Нет пакетов в очереди',
                    subtitle: 'Все сохранённые пакеты уже на сервере или нет локальных данных.',
                  ),
                );
              }
              return Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  for (final pkg in queue)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: Epoch8Card(
                        child: ListTile(
                          title: Text(
                            pkg.id,
                            style: const TextStyle(fontWeight: FontWeight.w600),
                          ),
                          subtitle: Text(
                            '${pkg.projectId}\n'
                            'Сервер: ${pkg.serverDeliveryState}'
                            '${pkg.serverDeliveryError != null ? '\n${pkg.serverDeliveryError}' : ''}',
                          ),
                          isThreeLine: true,
                          trailing: _busyPackageId == pkg.id
                              ? const SizedBox(
                                  width: 28,
                                  height: 28,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : IconButton(
                                  icon: const Icon(Icons.cloud_upload_outlined),
                                  tooltip: 'Отправить',
                                  onPressed: () => _uploadOne(pkg),
                                ),
                        ),
                      ),
                    ),
                ],
              );
            },
            loading: () => const Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator())),
            error: (e, _) => Text('Ошибка БД: $e', style: const TextStyle(color: Epoch8Theme.danger)),
          ),
        ],
      ),
    );
  }
}
