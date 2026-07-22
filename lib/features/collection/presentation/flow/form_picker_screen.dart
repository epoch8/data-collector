import 'package:data_collector/features/projects/catalog_project.dart';
import 'package:data_collector/features/projects/providers/project_providers.dart';
import 'package:data_collector/l10n/app_localizations.dart';
import 'package:data_collector/theme/epoch8_loader.dart';
import 'package:data_collector/theme/epoch8_theme.dart';
import 'package:data_collector/theme/epoch8_ui.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// Выбор формы внутри проекта (specs/10).
class FormPickerScreen extends ConsumerWidget {
  const FormPickerScreen({super.key, required this.projectId});

  final String projectId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final loc = AppLocalizations.of(context);
    final async = ref.watch(projectsProvider);
    return async.when(
      skipLoadingOnReload: true,
      loading: () => Scaffold(body: Epoch8Loader.center()),
      error: (e, _) => Scaffold(
        appBar: AppBar(title: Text(loc.project)),
        body: Center(child: Text('${loc.errorPrefix}: $e')),
      ),
      data: (projects) {
        final catalog = projects.byId(projectId);
        if (catalog == null) {
          return Scaffold(
            appBar: AppBar(title: Text(loc.project)),
            body: Center(child: Text(loc.projectNotFound)),
          );
        }
        if (catalog.forms.length == 1) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (!context.mounted) return;
            context.go(
              '/project/$projectId/form/${catalog.forms.first.formId}/wizard',
            );
          });
          return Scaffold(body: Epoch8Loader.center());
        }
        return Scaffold(
          appBar: AppBar(
            title: Text(catalog.name),
            leading: IconButton(
              icon: const Icon(Icons.arrow_back),
              onPressed: () => context.go('/dashboard'),
            ),
          ),
          body: Epoch8ScreenBody(
            child: ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
              itemCount: catalog.forms.length,
              separatorBuilder: (context, index) => const SizedBox(height: 10),
              itemBuilder: (context, i) {
                final form = catalog.forms[i];
                return Material(
                  color: Epoch8Theme.bgElevated,
                  borderRadius: BorderRadius.circular(14),
                  child: ListTile(
                    contentPadding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 8,
                    ),
                    title: Text(
                      form.formName,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    trailing: Icon(
                      Icons.arrow_forward_ios_rounded,
                      size: 16,
                      color: Epoch8Theme.textMuted,
                    ),
                    onTap: () => context.go(
                      '/project/$projectId/form/${form.formId}/wizard',
                    ),
                  ),
                );
              },
            ),
          ),
        );
      },
    );
  }
}
