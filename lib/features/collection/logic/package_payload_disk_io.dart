import 'dart:convert';
import 'dart:io';

import 'package:data_collector/core/package/package_paths.dart';
import 'package:path/path.dart' as p;

Future<Map<String, dynamic>?> readPayloadJsonFromDiskIfPresent(
  String packageId,
) async {
  final root = PackagePaths.packageRootFor(packageId);
  if (root.isEmpty) return null;
  final payloadFile = File(p.join(root, 'payload.json'));
  if (await payloadFile.exists()) {
    return jsonDecode(await payloadFile.readAsString()) as Map<String, dynamic>;
  }
  return null;
}
