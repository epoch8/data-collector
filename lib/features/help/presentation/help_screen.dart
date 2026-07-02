import 'package:data_collector/l10n/app_localizations.dart';
import 'package:data_collector/theme/epoch8_app_bar_controls.dart';
import 'package:data_collector/theme/epoch8_theme.dart';
import 'package:data_collector/theme/epoch8_ui.dart';
import 'package:flutter/material.dart';
import 'package:package_info_plus/package_info_plus.dart';

class HelpScreen extends StatelessWidget {
  const HelpScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(loc.helpTitle),
        actions: const [
          Epoch8ThemeSwitcher(),
          Epoch8LanguageSwitcher(),
          SizedBox(width: 4),
        ],
      ),
      body: Epoch8ScreenBody(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(
            Epoch8Layout.pagePadding,
            12,
            Epoch8Layout.pagePadding,
            24,
          ),
          children: [
            Epoch8Card(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    loc.helpQuickStartTitle,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    loc.helpQuickStartBody,
                    style: Theme.of(
                      context,
                    ).textTheme.bodyMedium?.copyWith(height: 1.35),
                  ),
                  const SizedBox(height: 12),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 10,
                    ),
                    decoration: BoxDecoration(
                      color: Epoch8Theme.bgElevated,
                      borderRadius: BorderRadius.circular(
                        Epoch8Layout.radiusSm,
                      ),
                      border: Border.all(color: Epoch8Theme.border),
                    ),
                    child: Text(
                      loc.helpFlowLine,
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(
                        color: Epoch8Theme.accent,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0.3,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            _HelpStepCard(
              number: 1,
              title: loc.helpStep1Title,
              body: loc.helpStep1Body,
              icon: Icons.folder_open_outlined,
            ),
            const SizedBox(height: 12),
            _HelpStepCard(
              number: 2,
              title: loc.helpStep2Title,
              body: loc.helpStep2Body,
              icon: Icons.fact_check_outlined,
            ),
            const SizedBox(height: 12),
            _HelpStepCard(
              number: 3,
              title: loc.helpStep3Title,
              body: loc.helpStep3Body,
              icon: Icons.cloud_upload_outlined,
            ),
            const SizedBox(height: 12),
            _HelpStepCard(
              number: 4,
              title: loc.helpStep4Title,
              body: loc.helpStep4Body,
              icon: Icons.history_outlined,
            ),
            const SizedBox(height: 12),
            Epoch8Card(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    loc.helpHintTitle,
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    loc.helpHintBody,
                    style: Theme.of(
                      context,
                    ).textTheme.bodyMedium?.copyWith(height: 1.35),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
            const _AppVersionFooter(),
          ],
        ),
      ),
    );
  }
}

class _AppVersionFooter extends StatefulWidget {
  const _AppVersionFooter();

  @override
  State<_AppVersionFooter> createState() => _AppVersionFooterState();
}

class _AppVersionFooterState extends State<_AppVersionFooter> {
  PackageInfo? _info;

  @override
  void initState() {
    super.initState();
    PackageInfo.fromPlatform().then((info) {
      if (mounted) setState(() => _info = info);
    });
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context);
    final info = _info;
    final text = info == null
        ? loc.appVersionLabel
        : '${loc.appVersionLabel} ${info.version} (${info.buildNumber})';
    return Center(
      child: Text(
        text,
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
          color: Epoch8Theme.textMuted,
          letterSpacing: 0.4,
        ),
      ),
    );
  }
}

class _HelpStepCard extends StatelessWidget {
  const _HelpStepCard({
    required this.number,
    required this.title,
    required this.body,
    required this.icon,
  });

  final int number;
  final String title;
  final String body;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Epoch8Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                  color: Epoch8Theme.accent.withValues(alpha: 0.16),
                  borderRadius: BorderRadius.circular(10),
                ),
                alignment: Alignment.center,
                child: Icon(icon, size: 18, color: Epoch8Theme.accent),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  '$number. $title',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    color: Epoch8Theme.accent,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            body,
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(height: 1.35),
          ),
        ],
      ),
    );
  }
}
