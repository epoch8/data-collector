import 'package:data_collector/core/storage/database.dart';
import 'package:data_collector/core/storage/database_provider.dart';
import 'package:data_collector/features/collection/logic/local_package_cleanup.dart';
import 'package:data_collector/theme/epoch8_theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

Future<void> confirmAndDeleteLocalPackage(
  BuildContext context,
  WidgetRef ref,
  Package pkg,
) async {
  final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Удалить пакет?'),
          content: Text(
            'Пакет ${pkg.id} будет удалён с устройства (данные и фото в локальном кэше). '
            'На сервере копия не удаляется.',
            style: TextStyle(color: Epoch8Theme.textMuted, height: 1.4),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Отмена')),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Удалить')),
          ],
        ),
      ) ??
      false;
  if (!ok || !context.mounted) return;
  await deleteLocalPackageStorage(ref.read(databaseProvider), pkg.id);
  if (!context.mounted) return;
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(content: Text('Пакет ${pkg.id} удалён с устройства')),
  );
}

Future<int?> confirmAndClearUploadedPackagesCache(BuildContext context, WidgetRef ref) async {
  final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Очистить кэш загруженных?'),
          content: Text(
            'Будут удалены только пакеты со статусом «загружен на сервер»: записи в истории и '
            'локальные файлы. Пакеты, которые ещё не отправлены, останутся.',
            style: TextStyle(color: Epoch8Theme.textMuted, height: 1.4),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Отмена')),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Очистить')),
          ],
        ),
      ) ??
      false;
  if (!ok || !context.mounted) return null;
  final n = await deleteCompletedPackagesLocalCache(ref.read(databaseProvider));
  if (!context.mounted) return n;
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(content: Text(n == 0 ? 'Нечего удалять' : 'Удалено пакетов с устройства: $n')),
  );
  return n;
}
