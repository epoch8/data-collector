import 'package:data_collector/core/storage/database.dart';
import 'package:data_collector/theme/epoch8_theme.dart';
import 'package:flutter/material.dart';

/// Цвет рамки карточки по статусу доставки на сервер.
Color historyPackageBorderColor(String serverDeliveryState) {
  switch (serverDeliveryState) {
    case 'completed':
      return Epoch8Theme.success.withValues(alpha: 0.82);
    case 'failed':
      return Epoch8Theme.danger.withValues(alpha: 0.88);
    case 'uploading':
      return Epoch8Theme.accent.withValues(alpha: 0.9);
    case 'pending':
    default:
      return const Color(0xFFF59E0B).withValues(alpha: 0.88);
  }
}

/// Рамка для группы пакетов (корова): приоритет ошибка → есть незагруженные → все на сервере.
Color historyGroupBorderColor(List<Package> packages) {
  if (packages.isEmpty) return Epoch8Theme.border.withValues(alpha: 0.85);
  if (packages.any((p) => p.serverDeliveryState == 'failed')) {
    return Epoch8Theme.danger.withValues(alpha: 0.82);
  }
  if (packages.any((p) => p.serverDeliveryState != 'completed')) {
    return const Color(0xFFF59E0B).withValues(alpha: 0.85);
  }
  return Epoch8Theme.success.withValues(alpha: 0.78);
}

String deliveryStateShortRu(String serverDeliveryState) {
  switch (serverDeliveryState) {
    case 'completed':
      return 'Сервер: загружен';
    case 'failed':
      return 'Сервер: ошибка отправки';
    case 'uploading':
      return 'Сервер: отправка…';
    case 'pending':
    default:
      return 'Сервер: не загружен';
  }
}
