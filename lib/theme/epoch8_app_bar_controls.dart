import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';
import '../l10n/locale_controller.dart';
import 'epoch8_theme.dart';
import 'theme_controller.dart';

/// Кнопка-«таблетка» переключения языка для AppBar/Stack-шапок.
/// Имеет собственные внутренние отступы, поэтому метка «RU/EN» всегда
/// центрирована и не упирается в край стандартной IconButton-области.
class Epoch8LanguageSwitcher extends StatelessWidget {
  const Epoch8LanguageSwitcher({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context);
    return ValueListenableBuilder<Brightness>(
      valueListenable: appBrightnessNotifier,
      builder: (context, _, __) => Tooltip(
        message: loc.languageToggleTooltip,
        child: SizedBox(
          width: 62,
          child: Center(
            child: Material(
              color: Epoch8Theme.accent.withValues(alpha: 0.10),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
                side: BorderSide(
                  color: Epoch8Theme.accent.withValues(alpha: 0.30),
                ),
              ),
              child: InkWell(
                borderRadius: BorderRadius.circular(12),
                onTap: toggleAppLocale,
                child: SizedBox(
                  width: 52,
                  height: 36,
                  child: Center(
                    child: Text(
                      loc.languageCodeLabel,
                      style: TextStyle(
                        fontWeight: FontWeight.w800,
                        fontSize: 13,
                        letterSpacing: 0.8,
                        color: Epoch8Theme.accent,
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// IconButton переключения темы (light ↔ dark).
class Epoch8ThemeSwitcher extends StatelessWidget {
  const Epoch8ThemeSwitcher({super.key});

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context);
    return ValueListenableBuilder<ThemeMode>(
      valueListenable: appThemeModeNotifier,
      builder: (context, mode, _) {
        final tooltip = mode == ThemeMode.light ? loc.themeModeLight : loc.themeModeDark;
        return IconButton(
          tooltip: tooltip,
          onPressed: toggleAppThemeMode,
          icon: Icon(iconForThemeMode(mode)),
        );
      },
    );
  }
}
