import 'package:flutter/material.dart';
import 'kalmgu_theme.dart';
import 'theme_controller.dart';

/// Отступы и радиусы единообразно по всему приложению.
abstract final class KalmguLayout {
  static const double pagePadding = 20;
  static const double sectionGap = 20;
  static const double cardPadding = 18;
  static const double radiusSm = 12;
  static const double radiusMd = 16;
  static const double radiusLg = 22;
}

/// Обёртка экрана: градиент + опциональный безопасный отступ.
/// Подписан на смену темы — пересоздаёт фон при переключении light/dark.
class KalmguScreenBody extends StatelessWidget {
  const KalmguScreenBody({super.key, required this.child, this.padding});

  final Widget child;
  final EdgeInsetsGeometry? padding;

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<Brightness>(
      valueListenable: appBrightnessNotifier,
      builder: (context, _, _) => Container(
        width: double.infinity,
        height: double.infinity,
        decoration: KalmguTheme.screenGradient(),
        child: padding != null
            ? Padding(padding: padding!, child: child)
            : child,
      ),
    );
  }
}

/// Карточка с мягкой «подсветкой» границы и скруглением.
class KalmguCard extends StatelessWidget {
  const KalmguCard({
    super.key,
    required this.child,
    this.padding,
    this.onTap,
    this.accentBorder = false,

    /// Явный цвет границы (например статус доставки на сервер). Имеет приоритет над [accentBorder].
    this.highlightBorderColor,
    this.highlightBorderWidth = 1.5,
  });

  final Widget child;
  final EdgeInsetsGeometry? padding;
  final VoidCallback? onTap;
  final bool accentBorder;
  final Color? highlightBorderColor;
  final double highlightBorderWidth;

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<Brightness>(
      valueListenable: appBrightnessNotifier,
      builder: (context, _, _) {
        final content = Padding(
          padding: padding ?? const EdgeInsets.all(KalmguLayout.cardPadding),
          child: child,
        );

        final Color borderColor;
        final double borderW;
        if (highlightBorderColor != null) {
          borderColor = highlightBorderColor!;
          borderW = highlightBorderWidth;
        } else if (accentBorder) {
          borderColor = KalmguTheme.accent.withValues(alpha: 0.35);
          borderW = 1.25;
        } else {
          borderColor = KalmguTheme.border.withValues(alpha: 0.85);
          borderW = 1;
        }

        final deco = BoxDecoration(
          borderRadius: BorderRadius.circular(KalmguLayout.radiusMd),
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              KalmguTheme.card.withValues(alpha: 0.92),
              KalmguTheme.card.withValues(alpha: 0.65),
            ],
          ),
          border: Border.all(color: borderColor, width: borderW),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.35),
              blurRadius: 20,
              offset: const Offset(0, 10),
            ),
          ],
        );

        final box = DecoratedBox(decoration: deco, child: content);
        if (onTap != null) {
          return GestureDetector(
            onTap: onTap,
            child: MouseRegion(cursor: SystemMouseCursors.click, child: box),
          );
        }
        return box;
      },
    );
  }
}

/// Заголовок секции: мелкий лейбл + крупный заголовок.
class KalmguSectionHeader extends StatelessWidget {
  const KalmguSectionHeader({
    super.key,
    required this.title,
    this.overline,
    this.subtitle,
  });

  final String title;
  final String? overline;
  final String? subtitle;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (overline != null) ...[
          Text(
            overline!.toUpperCase(),
            style: t.labelSmall?.copyWith(
              color: KalmguTheme.accent.withValues(alpha: 0.9),
              letterSpacing: 1.4,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 6),
        ],
        Text(
          title,
          style: t.titleLarge?.copyWith(
            fontWeight: FontWeight.w700,
            letterSpacing: -0.4,
            height: 1.2,
          ),
        ),
        if (subtitle != null) ...[
          const SizedBox(height: 8),
          Text(
            subtitle!,
            style: t.bodyMedium?.copyWith(
              color: KalmguTheme.textMuted,
              height: 1.45,
            ),
          ),
        ],
      ],
    );
  }
}

/// Пустое состояние для списков.
class KalmguEmptyState extends StatelessWidget {
  const KalmguEmptyState({
    super.key,
    required this.icon,
    required this.title,
    this.subtitle,
  });

  final IconData icon;
  final String title;
  final String? subtitle;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(22),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: KalmguTheme.accent.withValues(alpha: 0.08),
                border: Border.all(color: KalmguTheme.border),
              ),
              child: Icon(
                icon,
                size: 40,
                color: KalmguTheme.accent.withValues(alpha: 0.85),
              ),
            ),
            const SizedBox(height: 20),
            Text(
              title,
              textAlign: TextAlign.center,
              style: Theme.of(
                context,
              ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
            ),
            if (subtitle != null) ...[
              const SizedBox(height: 8),
              Text(
                subtitle!,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Индикатор шага для мастера (точки).
class KalmguStepDots extends StatelessWidget {
  const KalmguStepDots({super.key, required this.current, required this.total});

  final int current;
  final int total;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: List.generate(total, (i) {
        final active = i == current;
        return AnimatedContainer(
          duration: const Duration(milliseconds: 220),
          curve: Curves.easeOutCubic,
          margin: const EdgeInsets.symmetric(horizontal: 4),
          width: active ? 22 : 8,
          height: 8,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(4),
            color: active
                ? KalmguTheme.accent
                : KalmguTheme.border.withValues(alpha: 0.7),
          ),
        );
      }),
    );
  }
}
