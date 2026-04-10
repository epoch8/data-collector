import 'package:flutter/material.dart';
import 'epoch8_theme.dart';

/// Отступы и радиусы единообразно по всему приложению.
abstract final class Epoch8Layout {
  static const double pagePadding = 20;
  static const double sectionGap = 20;
  static const double cardPadding = 18;
  static const double radiusSm = 12;
  static const double radiusMd = 16;
  static const double radiusLg = 22;
}

/// Обёртка экрана: градиент + опциональный безопасный отступ.
class Epoch8ScreenBody extends StatelessWidget {
  const Epoch8ScreenBody({super.key, required this.child, this.padding});

  final Widget child;
  final EdgeInsetsGeometry? padding;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      height: double.infinity,
      decoration: Epoch8Theme.screenGradient(),
      child: padding != null
          ? Padding(padding: padding!, child: child)
          : child,
    );
  }
}

/// Карточка с мягкой «подсветкой» границы и скруглением.
class Epoch8Card extends StatelessWidget {
  const Epoch8Card({
    super.key,
    required this.child,
    this.padding,
    this.onTap,
    this.accentBorder = false,
  });

  final Widget child;
  final EdgeInsetsGeometry? padding;
  final VoidCallback? onTap;
  final bool accentBorder;

  @override
  Widget build(BuildContext context) {
    final content = Padding(
      padding: padding ?? const EdgeInsets.all(Epoch8Layout.cardPadding),
      child: child,
    );

    final deco = BoxDecoration(
      borderRadius: BorderRadius.circular(Epoch8Layout.radiusMd),
      gradient: LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [
          Epoch8Theme.card.withValues(alpha: 0.92),
          Epoch8Theme.card.withValues(alpha: 0.65),
        ],
      ),
      border: Border.all(
        color: accentBorder
            ? Epoch8Theme.accent.withValues(alpha: 0.35)
            : Epoch8Theme.border.withValues(alpha: 0.85),
        width: accentBorder ? 1.25 : 1,
      ),
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
        child: MouseRegion(
          cursor: SystemMouseCursors.click,
          child: box,
        ),
      );
    }
    return box;
  }
}

/// Заголовок секции: мелкий лейбл + крупный заголовок.
class Epoch8SectionHeader extends StatelessWidget {
  const Epoch8SectionHeader({
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
              color: Epoch8Theme.accent.withValues(alpha: 0.9),
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
              color: Epoch8Theme.textMuted,
              height: 1.45,
            ),
          ),
        ],
      ],
    );
  }
}

/// Пустое состояние для списков.
class Epoch8EmptyState extends StatelessWidget {
  const Epoch8EmptyState({
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
                color: Epoch8Theme.accent.withValues(alpha: 0.08),
                border: Border.all(color: Epoch8Theme.border),
              ),
              child: Icon(icon, size: 40, color: Epoch8Theme.accent.withValues(alpha: 0.85)),
            ),
            const SizedBox(height: 20),
            Text(
              title,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
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
class Epoch8StepDots extends StatelessWidget {
  const Epoch8StepDots({
    super.key,
    required this.current,
    required this.total,
  });

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
                ? Epoch8Theme.accent
                : Epoch8Theme.border.withValues(alpha: 0.7),
          ),
        );
      }),
    );
  }
}
