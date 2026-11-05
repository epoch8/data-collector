import 'package:data_collector/core/storage/database.dart';
import 'package:data_collector/l10n/app_localizations.dart';
import 'package:data_collector/theme/kalmgu_theme.dart';
import 'package:flutter/material.dart';

/// Цвет рамки карточки по статусу доставки на сервер.
Color historyPackageBorderColor(String serverDeliveryState) {
  switch (serverDeliveryState) {
    case 'completed':
      return KalmguTheme.success.withValues(alpha: 0.82);
    case 'failed':
      return KalmguTheme.danger.withValues(alpha: 0.88);
    case 'uploading':
      return KalmguTheme.accent.withValues(alpha: 0.9);
    case 'pending':
    default:
      return const Color(0xFFF59E0B).withValues(alpha: 0.88);
  }
}

/// Рамка для группы пакетов (по субъекту): приоритет ошибка → есть незагруженные → все на сервере.
Color historyGroupBorderColor(List<Package> packages) {
  if (packages.isEmpty) return KalmguTheme.border.withValues(alpha: 0.85);
  if (packages.any((p) => p.serverDeliveryState == 'failed')) {
    return KalmguTheme.danger.withValues(alpha: 0.82);
  }
  if (packages.any((p) => p.serverDeliveryState != 'completed')) {
    return const Color(0xFFF59E0B).withValues(alpha: 0.85);
  }
  return KalmguTheme.success.withValues(alpha: 0.78);
}

String deliveryStateShort(BuildContext context, String serverDeliveryState) {
  return AppLocalizations.of(context).deliveryStateLabel(serverDeliveryState);
}
