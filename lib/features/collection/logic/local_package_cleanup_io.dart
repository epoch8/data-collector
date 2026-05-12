import 'dart:io';

import 'package:data_collector/core/package/package_paths.dart';

Future<void> deletePackageDirectoryIfExists(String packageId) async {
  final root = PackagePaths.packageRootFor(packageId);
  if (root.isEmpty) return;
  try {
    final dir = Directory(root);
    if (await dir.exists()) await dir.delete(recursive: true);
  } catch (_) {}
}
