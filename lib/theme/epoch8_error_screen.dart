import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';
import 'epoch8_theme.dart';
import 'epoch8_ui.dart';

/// Замена дефолтному «красному квадрату» Flutter'а: дружелюбный экран ошибки
/// с логотипом и сворачиваемыми техническими деталями.
class Epoch8ErrorScreen extends StatelessWidget {
  const Epoch8ErrorScreen({super.key, required this.details});

  final FlutterErrorDetails details;

  @override
  Widget build(BuildContext context) {
    final loc = _safeLoc(context);
    return Material(
      color: Epoch8Theme.bgDeep,
      child: Epoch8ScreenBody(
        padding: const EdgeInsets.symmetric(horizontal: Epoch8Layout.pagePadding, vertical: 24),
        child: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 520),
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 96,
                      height: 96,
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(24),
                        color: Epoch8Theme.danger.withValues(alpha: 0.12),
                        border: Border.all(color: Epoch8Theme.danger.withValues(alpha: 0.35)),
                      ),
                      alignment: Alignment.center,
                      child: Icon(
                        Icons.error_outline,
                        size: 48,
                        color: Epoch8Theme.danger,
                      ),
                    ),
                    const SizedBox(height: 22),
                    Text(
                      loc?.errorScreenTitle ?? 'Something went wrong',
                      style: Theme.of(context).textTheme.titleLarge,
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 10),
                    Text(
                      loc?.errorScreenSubtitle ??
                          'An unexpected error occurred. Try going back or restarting the app.',
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: Epoch8Theme.textMuted,
                            height: 1.45,
                          ),
                    ),
                    const SizedBox(height: 18),
                    Epoch8Card(
                      child: Theme(
                        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
                        child: ExpansionTile(
                          tilePadding: EdgeInsets.zero,
                          childrenPadding: EdgeInsets.zero,
                          title: Text(
                            loc?.errorScreenDetailsLabel ?? 'Details (for developers)',
                            style: Theme.of(context).textTheme.titleSmall,
                          ),
                          children: [
                            SelectableText(
                              details.exceptionAsString(),
                              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                    fontFamily: 'monospace',
                                    height: 1.35,
                                  ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  /// Локализация может быть недоступна (например, ошибка случилась до построения
  /// `Localizations`). В этом случае молча падаем на английский фолбэк.
  AppLocalizations? _safeLoc(BuildContext context) {
    try {
      return AppLocalizations.of(context);
    } catch (_) {
      return null;
    }
  }
}
