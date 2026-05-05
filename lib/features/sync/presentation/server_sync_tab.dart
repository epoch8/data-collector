import 'package:data_collector/core/api/api_environment.dart';
import 'package:data_collector/core/api/dio_provider.dart';
import 'package:data_collector/core/storage/database.dart';
import 'package:data_collector/core/storage/database_provider.dart';
import 'package:data_collector/features/collection/logic/package_server_upload.dart';
import 'package:data_collector/features/projects/providers/project_providers.dart';
import 'package:data_collector/features/projects/server_project_catalog.dart';
import 'package:data_collector/l10n/app_localizations.dart';
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
        final loc = AppLocalizations.of(context);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(loc.projectsUpdated)),
        );
      }
    } catch (e) {
      if (mounted) {
        final loc = AppLocalizations.of(context);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('${loc.syncError}: $e')),
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
      final projects = await ref.read(projectsProvider.future);
      final allowed = projects.map((p) => p.id).toSet();
      final db = ref.read(databaseProvider);
      await uploadDriftPackageToServer(
        dio: dio,
        db: db,
        pkg: pkg,
        allowedProjectIds: allowed,
      );
      if (mounted) {
        final loc = AppLocalizations.of(context);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(loc.packageSent(pkg.id))),
        );
      }
    } catch (e) {
      if (mounted) {
        final loc = AppLocalizations.of(context);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('${loc.errorPrefix}: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _busyPackageId = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context);
    if (!ApiEnvironment.isConfigured) {
      return Epoch8ScreenBody(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(
              loc.serverSetupHint,
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
            loc.baseUrlLabel(ApiEnvironment.normalizedBaseUrl()),
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
            label: Text(_syncing ? loc.syncingConfigs : loc.syncProjects),
          ),
          const SizedBox(height: 24),
          Text(
            loc.serverQueue,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 8),
          packagesAsync.when(
            data: (packages) {
              final queue = packages
                  .where((p) => p.serverDeliveryState != 'completed' && p.status != 'draft')
                  .toList()
                ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
              if (queue.isEmpty) {
                return Padding(
                  padding: EdgeInsets.only(top: 16),
                  child: Epoch8EmptyState(
                    icon: Icons.cloud_done_outlined,
                    title: loc.noQueuePackages,
                    subtitle: loc.noQueuePackagesSubtitle,
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
                            '${loc.serverStateLabel(pkg.serverDeliveryState)}'
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
                                  tooltip: loc.send,
                                  onPressed: () => _uploadOne(pkg),
                                ),
                        ),
                      ),
                    ),
                ],
              );
            },
            loading: () => const Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator())),
            error: (e, _) => Text('${loc.dbError}: $e', style: TextStyle(color: Epoch8Theme.danger)),
          ),
        ],
      ),
    );
  }
}
