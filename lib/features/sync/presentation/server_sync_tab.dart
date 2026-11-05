import 'package:data_collector/core/api/api_environment.dart';
import 'package:data_collector/core/api/dio_provider.dart';
import 'package:data_collector/core/storage/database.dart';
import 'package:data_collector/core/storage/database_provider.dart';
import 'package:data_collector/features/collection/logic/package_server_upload.dart';
import 'package:data_collector/features/projects/catalog_project.dart';
import 'package:data_collector/features/projects/providers/project_providers.dart';
import 'package:data_collector/features/projects/server_project_catalog.dart';
import 'package:data_collector/l10n/app_localizations.dart';
import 'package:data_collector/theme/kalmgu_loader.dart';
import 'package:data_collector/theme/kalmgu_theme.dart';
import 'package:data_collector/theme/theme_controller.dart';
import 'package:data_collector/theme/kalmgu_ui.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
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

  @override
  void initState() {
    super.initState();
    appBrightnessNotifier.addListener(_onBrightnessChanged);
  }

  @override
  void dispose() {
    appBrightnessNotifier.removeListener(_onBrightnessChanged);
    super.dispose();
  }

  void _onBrightnessChanged() {
    if (mounted) setState(() {});
  }

  Future<void> _syncProjects() async {
    final dio = ref.read(dioProvider);
    if (dio == null) return;
    setState(() => _syncing = true);
    try {
      await ServerProjectCatalog(dio).syncFromServer();
      ref.invalidate(projectsProvider);
      if (mounted) {
        final loc = AppLocalizations.of(context);
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(loc.projectsUpdated)));
      }
    } catch (e) {
      if (mounted) {
        final loc = AppLocalizations.of(context);
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('${loc.syncError}: $e')));
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
      final allowed = projects.projectIds;
      final db = ref.read(databaseProvider);
      await uploadDriftPackageToServer(
        dio: dio,
        db: db,
        pkg: pkg,
        allowedProjectIds: allowed,
      );
      if (mounted) {
        final loc = AppLocalizations.of(context);
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(loc.packageSent(pkg.id))));
      }
    } catch (e) {
      if (mounted) {
        final loc = AppLocalizations.of(context);
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('${loc.errorPrefix}: $e')));
      }
    } finally {
      if (mounted) setState(() => _busyPackageId = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context);
    if (!ApiEnvironment.isConfigured) {
      return _ServerNotConfiguredView(loc: loc);
    }

    final dio = ref.watch(dioProvider);
    final packagesAsync = ref.watch(packagesStreamProvider);

    return KalmguScreenBody(
      child: ListView(
        padding: const EdgeInsets.fromLTRB(
          KalmguLayout.pagePadding,
          12,
          KalmguLayout.pagePadding,
          24,
        ),
        children: [
          Text(
            loc.baseUrlLabel(ApiEnvironment.normalizedBaseUrl()),
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: KalmguTheme.textMuted),
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
            style: Theme.of(
              context,
            ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 8),
          packagesAsync.when(
            data: (packages) {
              final queue =
                  packages
                      .where(
                        (p) =>
                            p.serverDeliveryState != 'completed' &&
                            p.status != 'draft',
                      )
                      .toList()
                    ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
              if (queue.isEmpty) {
                return Padding(
                  padding: EdgeInsets.only(top: 16),
                  child: KalmguEmptyState(
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
                      child: KalmguCard(
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
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                  ),
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
            loading: () => Padding(
              padding: const EdgeInsets.all(24),
              child: KalmguLoader.center(),
            ),
            error: (e, _) => Text(
              '${loc.dbError}: $e',
              style: TextStyle(color: KalmguTheme.danger),
            ),
          ),
        ],
      ),
    );
  }
}

class _ServerNotConfiguredView extends StatelessWidget {
  const _ServerNotConfiguredView({required this.loc});

  final AppLocalizations loc;

  static const String _command =
      'flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000';

  @override
  Widget build(BuildContext context) {
    return KalmguScreenBody(
      child: ListView(
        padding: const EdgeInsets.fromLTRB(
          KalmguLayout.pagePadding,
          24,
          KalmguLayout.pagePadding,
          24,
        ),
        children: [
          Center(
            child: Container(
              width: 92,
              height: 92,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: KalmguTheme.accent.withValues(alpha: 0.1),
                border: Border.all(color: KalmguTheme.border),
              ),
              alignment: Alignment.center,
              child: Icon(
                Icons.cloud_off_outlined,
                size: 46,
                color: KalmguTheme.accent.withValues(alpha: 0.85),
              ),
            ),
          ),
          const SizedBox(height: 18),
          Text(
            loc.serverSetupTitle,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 10),
          Text(
            loc.serverSetupSubtitle,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: KalmguTheme.textMuted,
              height: 1.45,
            ),
          ),
          const SizedBox(height: 20),
          KalmguCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  loc.serverSetupCommandLabel,
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: KalmguTheme.accent,
                    letterSpacing: 1.2,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 10),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: KalmguTheme.bgElevated,
                    borderRadius: BorderRadius.circular(KalmguLayout.radiusSm),
                    border: Border.all(color: KalmguTheme.border),
                  ),
                  child: SelectableText(
                    _command,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      fontFamily: 'monospace',
                      height: 1.4,
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Align(
                  alignment: Alignment.centerRight,
                  child: TextButton.icon(
                    onPressed: () async {
                      await Clipboard.setData(
                        const ClipboardData(text: _command),
                      );
                      if (!context.mounted) return;
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text(loc.copiedToClipboard)),
                      );
                    },
                    icon: const Icon(Icons.copy_outlined, size: 18),
                    label: Text(loc.copyToClipboard),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          KalmguCard(
            child: Text(
              loc.serverSetupHintNote,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: KalmguTheme.textMuted,
                height: 1.45,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
