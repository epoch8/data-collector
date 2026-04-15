import 'dart:convert';

import 'package:data_collector/core/storage/database.dart';
import 'package:data_collector/core/storage/database_provider.dart';
import 'package:data_collector/features/collection/logic/local_package_materializer.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// Persists one completed package: on-disk layout per spec 07 + SQLite index row.
Future<void> submitLocalPackage({
  required WidgetRef ref,
  required BuildContext context,
  required String projectId,
  required Map<String, dynamic> answers,
}) async {
  final db = ref.read(databaseProvider);
  final String packageId = 'pkg_${DateTime.now().millisecondsSinceEpoch}';
  final createdAt = DateTime.now();

  final materialized = await materializeLocalPackage(
    packageId: packageId,
    projectId: projectId,
    createdAt: createdAt,
    answers: answers,
  );

  await db.into(db.packages).insert(
        PackagesCompanion.insert(
          id: packageId,
          projectId: projectId,
          status: 'completed',
          createdAt: createdAt,
          dataJson: jsonEncode(materialized.payload),
        ),
      );

  if (!context.mounted) return;

  ScaffoldMessenger.of(context).showSnackBar(
    const SnackBar(
      content: Text('Package securely saved to local database!'),
      behavior: SnackBarBehavior.floating,
    ),
  );

  context.go('/dashboard');
}
