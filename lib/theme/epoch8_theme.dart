import 'package:flutter/material.dart';

/// Тёмная тема в духе tech / data — чистые поверхности, бирюзовый акцент, без визуального шума.
abstract final class Epoch8Theme {
  static const Color bgDeep = Color(0xFF060A0E);
  static const Color bgElevated = Color(0xFF0D1319);
  static const Color card = Color(0xFF111A24);
  static const Color border = Color(0xFF1E2A3A);
  static const Color accent = Color(0xFF2DD4BF);
  static const Color accentDim = Color(0xFF0D9488);
  static const Color textPrimary = Color(0xFFF1F5F9);
  static const Color textMuted = Color(0xFF94A3B8);
  static const Color danger = Color(0xFFF87171);
  static const Color success = Color(0xFF34D399);

  static ThemeData get dark {
    final base = ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: bgDeep,
    );
    return base.copyWith(
      colorScheme: ColorScheme.dark(
        surface: bgElevated,
        primary: accent,
        onPrimary: bgDeep,
        secondary: accentDim,
        onSurface: textPrimary,
        error: danger,
        outline: border,
        surfaceContainerHighest: card,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: true,
        foregroundColor: textPrimary,
        surfaceTintColor: Colors.transparent,
        titleTextStyle: TextStyle(
          color: textPrimary,
          fontSize: 18,
          fontWeight: FontWeight.w600,
          letterSpacing: -0.2,
        ),
      ),
      tabBarTheme: TabBarThemeData(
        labelColor: accent,
        unselectedLabelColor: textMuted,
        indicatorColor: accent,
        dividerColor: Colors.transparent,
        indicatorSize: TabBarIndicatorSize.tab,
        labelStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
        unselectedLabelStyle: const TextStyle(fontWeight: FontWeight.w500, fontSize: 14),
        overlayColor: MaterialStatePropertyAll(accent.withValues(alpha: 0.08)),
      ),
      cardTheme: CardThemeData(
        color: card,
        elevation: 0,
        shadowColor: Colors.black54,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: border, width: 1),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: bgElevated,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: accent, width: 1.5),
        ),
        labelStyle: const TextStyle(color: textMuted),
        hintStyle: TextStyle(color: textMuted.withValues(alpha: 0.72)),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: accent,
          foregroundColor: bgDeep,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 16),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          textStyle: const TextStyle(fontWeight: FontWeight.w700, letterSpacing: 0.2, fontSize: 15),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: bgElevated,
          foregroundColor: accent,
          elevation: 0,
          side: const BorderSide(color: border),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: textPrimary,
          side: const BorderSide(color: border),
          padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: accent,
          textStyle: const TextStyle(fontWeight: FontWeight.w600),
        ),
      ),
      iconButtonTheme: IconButtonThemeData(
        style: IconButton.styleFrom(
          foregroundColor: textMuted,
          hoverColor: accent.withValues(alpha: 0.08),
          highlightColor: accent.withValues(alpha: 0.12),
        ),
      ),
      textTheme: const TextTheme(
        headlineSmall: TextStyle(
          color: textPrimary,
          fontSize: 24,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.4,
          height: 1.25,
        ),
        titleLarge: TextStyle(
          color: textPrimary,
          fontSize: 22,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.35,
          height: 1.25,
        ),
        titleMedium: TextStyle(
          color: textPrimary,
          fontSize: 17,
          fontWeight: FontWeight.w600,
          letterSpacing: -0.1,
        ),
        titleSmall: TextStyle(
          color: textPrimary,
          fontSize: 15,
          fontWeight: FontWeight.w600,
        ),
        bodyLarge: TextStyle(color: textPrimary, height: 1.5, fontSize: 16),
        bodyMedium: TextStyle(color: textMuted, height: 1.45, fontSize: 14),
        bodySmall: TextStyle(color: textMuted, fontSize: 12, height: 1.35),
        labelLarge: TextStyle(
          color: accent,
          fontWeight: FontWeight.w700,
          letterSpacing: 2,
          fontSize: 11,
        ),
        labelSmall: TextStyle(
          color: textMuted,
          fontSize: 11,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.5,
        ),
      ),
      dividerTheme: DividerThemeData(color: border.withValues(alpha: 0.7), thickness: 1),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: bgElevated,
        contentTextStyle: const TextStyle(color: textPrimary, fontSize: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14), side: const BorderSide(color: border)),
        behavior: SnackBarBehavior.floating,
        elevation: 8,
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: card,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22), side: const BorderSide(color: border)),
        titleTextStyle: const TextStyle(color: textPrimary, fontSize: 20, fontWeight: FontWeight.w700),
      ),
      bottomSheetTheme: const BottomSheetThemeData(
        backgroundColor: bgDeep,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(22)),
        ),
        dragHandleColor: border,
      ),
      progressIndicatorTheme: const ProgressIndicatorThemeData(color: accent, linearTrackColor: border),
      listTileTheme: ListTileThemeData(
        iconColor: accent,
        textColor: textPrimary,
        titleTextStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 16),
        subtitleTextStyle: const TextStyle(color: textMuted, fontSize: 13, height: 1.35),
        contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 8),
      ),
    );
  }

  /// Фон экрана: лёгкий градиент + «пятно» акцента сверху.
  static BoxDecoration screenGradient() => BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            const Color(0xFF0D1A28).withValues(alpha: 0.98),
            bgDeep,
            const Color(0xFF05080C),
          ],
          stops: const [0.0, 0.42, 1.0],
        ),
      );
}
