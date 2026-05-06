import 'package:flutter/material.dart';

import 'theme_controller.dart';

/// Палитра одного цветового режима.
class _Palette {
  const _Palette({
    required this.bgDeep,
    required this.bgElevated,
    required this.card,
    required this.border,
    required this.accent,
    required this.accentDim,
    required this.textPrimary,
    required this.textMuted,
    required this.danger,
    required this.success,
    required this.gradientTop,
    required this.gradientBottom,
  });

  final Color bgDeep;
  final Color bgElevated;
  final Color card;
  final Color border;
  final Color accent;
  final Color accentDim;
  final Color textPrimary;
  final Color textMuted;
  final Color danger;
  final Color success;
  final Color gradientTop;
  final Color gradientBottom;
}

/// Тема EPOCH8: одинаковая структура, разные цвета между светлой/тёмной.
abstract final class Epoch8Theme {
  static const _Palette _dark = _Palette(
    bgDeep: Color(0xFF060A0E),
    bgElevated: Color(0xFF0D1319),
    card: Color(0xFF111A24),
    border: Color(0xFF1E2A3A),
    accent: Color(0xFF2DD4BF),
    accentDim: Color(0xFF0D9488),
    textPrimary: Color(0xFFF1F5F9),
    textMuted: Color(0xFF94A3B8),
    danger: Color(0xFFF87171),
    success: Color(0xFF34D399),
    gradientTop: Color(0xFF0D1A28),
    gradientBottom: Color(0xFF05080C),
  );

  static const _Palette _light = _Palette(
    bgDeep: Color(0xFFF3F7FB),
    bgElevated: Color(0xFFFFFFFF),
    card: Color(0xFFFFFFFF),
    border: Color(0xFFD6DFEA),
    accent: Color(0xFF0D9488),
    accentDim: Color(0xFF14B8A6),
    textPrimary: Color(0xFF0F172A),
    textMuted: Color(0xFF475569),
    danger: Color(0xFFDC2626),
    success: Color(0xFF059669),
    gradientTop: Color(0xFFE8F0F7),
    gradientBottom: Color(0xFFFFFFFF),
  );

  static bool get _isLight => appBrightnessNotifier.value == Brightness.light;
  static _Palette get _p => _isLight ? _light : _dark;

  /// Цвет «таблетки» под TabBar внутри AppBar — отдельный токен, чтобы
  /// контейнер был хорошо виден на светлой теме (где scaffold почти белый).
  static Color get tabBarSurface =>
      _isLight ? _light.bgElevated : _dark.card.withValues(alpha: 0.55);
  static Color get tabBarBorder =>
      _isLight ? _light.border : Colors.transparent;

  // --- Реактивные токены: используются в виджетах напрямую ---
  static Color get bgDeep => _p.bgDeep;
  static Color get bgElevated => _p.bgElevated;
  static Color get card => _p.card;
  static Color get border => _p.border;
  static Color get accent => _p.accent;
  static Color get accentDim => _p.accentDim;
  static Color get textPrimary => _p.textPrimary;
  static Color get textMuted => _p.textMuted;
  static Color get danger => _p.danger;
  static Color get success => _p.success;

  static ThemeData get dark => _buildTheme(_dark, Brightness.dark);
  static ThemeData get light => _buildTheme(_light, Brightness.light);

  static ThemeData _buildTheme(_Palette p, Brightness brightness) {
    final base = ThemeData(
      useMaterial3: true,
      brightness: brightness,
      scaffoldBackgroundColor: p.bgDeep,
    );
    final colorScheme = brightness == Brightness.dark
        ? ColorScheme.dark(
            surface: p.bgElevated,
            primary: p.accent,
            onPrimary: p.bgDeep,
            secondary: p.accentDim,
            onSurface: p.textPrimary,
            error: p.danger,
            outline: p.border,
            surfaceContainerHighest: p.card,
          )
        : ColorScheme.light(
            surface: p.bgElevated,
            primary: p.accent,
            onPrimary: Colors.white,
            secondary: p.accentDim,
            onSurface: p.textPrimary,
            error: p.danger,
            outline: p.border,
            surfaceContainerHighest: p.card,
          );

    return base.copyWith(
      colorScheme: colorScheme,
      appBarTheme: AppBarTheme(
        backgroundColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: true,
        foregroundColor: p.textPrimary,
        surfaceTintColor: Colors.transparent,
        titleTextStyle: TextStyle(
          color: p.textPrimary,
          fontSize: 18,
          fontWeight: FontWeight.w600,
          letterSpacing: -0.2,
        ),
      ),
      tabBarTheme: TabBarThemeData(
        labelColor: p.accent,
        unselectedLabelColor: p.textMuted,
        indicatorColor: p.accent,
        dividerColor: Colors.transparent,
        indicatorSize: TabBarIndicatorSize.tab,
        labelStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
        unselectedLabelStyle: const TextStyle(fontWeight: FontWeight.w500, fontSize: 14),
        overlayColor: WidgetStatePropertyAll(p.accent.withValues(alpha: 0.08)),
      ),
      cardTheme: CardThemeData(
        color: p.card,
        elevation: 0,
        shadowColor: Colors.black54,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(color: p.border, width: 1),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: p.bgElevated,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: p.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: p.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: p.accent, width: 1.5),
        ),
        labelStyle: TextStyle(color: p.textMuted),
        hintStyle: TextStyle(color: p.textMuted.withValues(alpha: 0.72)),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: p.accent,
          foregroundColor: brightness == Brightness.dark ? p.bgDeep : Colors.white,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 16),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          textStyle: const TextStyle(fontWeight: FontWeight.w700, letterSpacing: 0.2, fontSize: 15),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: p.bgElevated,
          foregroundColor: p.accent,
          elevation: 0,
          side: BorderSide(color: p.border),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: p.textPrimary,
          side: BorderSide(color: p.border),
          padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: p.accent,
          textStyle: const TextStyle(fontWeight: FontWeight.w600),
        ),
      ),
      iconButtonTheme: IconButtonThemeData(
        style: IconButton.styleFrom(
          foregroundColor: p.textMuted,
          hoverColor: p.accent.withValues(alpha: 0.08),
          highlightColor: p.accent.withValues(alpha: 0.12),
        ),
      ),
      textTheme: TextTheme(
        headlineSmall: TextStyle(
          color: p.textPrimary,
          fontSize: 24,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.4,
          height: 1.25,
        ),
        titleLarge: TextStyle(
          color: p.textPrimary,
          fontSize: 22,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.35,
          height: 1.25,
        ),
        titleMedium: TextStyle(
          color: p.textPrimary,
          fontSize: 17,
          fontWeight: FontWeight.w600,
          letterSpacing: -0.1,
        ),
        titleSmall: TextStyle(
          color: p.textPrimary,
          fontSize: 15,
          fontWeight: FontWeight.w600,
        ),
        bodyLarge: TextStyle(color: p.textPrimary, height: 1.5, fontSize: 16),
        bodyMedium: TextStyle(color: p.textMuted, height: 1.45, fontSize: 14),
        bodySmall: TextStyle(color: p.textMuted, fontSize: 12, height: 1.35),
        labelLarge: TextStyle(
          color: p.accent,
          fontWeight: FontWeight.w700,
          letterSpacing: 2,
          fontSize: 11,
        ),
        labelSmall: TextStyle(
          color: p.textMuted,
          fontSize: 11,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.5,
        ),
      ),
      dividerTheme: DividerThemeData(color: p.border.withValues(alpha: 0.7), thickness: 1),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: p.bgElevated,
        contentTextStyle: TextStyle(color: p.textPrimary, fontSize: 14),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: BorderSide(color: p.border),
        ),
        behavior: SnackBarBehavior.floating,
        elevation: brightness == Brightness.dark ? 8 : 4,
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: p.card,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(22),
          side: BorderSide(color: p.border),
        ),
        titleTextStyle: TextStyle(color: p.textPrimary, fontSize: 20, fontWeight: FontWeight.w700),
      ),
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: p.bgDeep,
        surfaceTintColor: Colors.transparent,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(22)),
        ),
        dragHandleColor: p.border,
      ),
      progressIndicatorTheme: ProgressIndicatorThemeData(color: p.accent, linearTrackColor: p.border),
      listTileTheme: ListTileThemeData(
        iconColor: p.accent,
        textColor: p.textPrimary,
        titleTextStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 16),
        subtitleTextStyle: TextStyle(color: p.textMuted, fontSize: 13, height: 1.35),
        contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 8),
      ),
    );
  }

  /// Фон экрана: лёгкий градиент под текущую тему.
  static BoxDecoration screenGradient() {
    final p = _p;
    return BoxDecoration(
      gradient: LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [
          p.gradientTop.withValues(alpha: _isLight ? 1.0 : 0.98),
          p.bgDeep,
          p.gradientBottom,
        ],
        stops: const [0.0, 0.42, 1.0],
      ),
    );
  }
}
