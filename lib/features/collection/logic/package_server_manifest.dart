import 'dart:convert';
import 'dart:io';

import 'package:data_collector/bootstrap.dart';
import 'package:data_collector/core/package/package_paths.dart';
import 'package:data_collector/core/storage/database.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart';
import 'package:path/path.dart' as p;

/// Те же поля, что добавляются перед [PUT …/manifest] в [uploadDriftPackageToServer].
void injectSubmittedByIntoServerManifest(Map<String, dynamic> manifest) {
  if (kIsWeb) return;
  if (!firebaseInitialized) return;
  final user = FirebaseAuth.instance.currentUser;
  if (user == null) return;
  manifest['submitted_by'] = <String, dynamic>{
    'firebase_uid': user.uid,
    'email': user.email ?? '',
  };
}

/// Содержимое `payload.json` на диске или снимок из SQLite — **до** `submitted_by`.
Future<Map<String, dynamic>> loadPackagePayloadMap(Package pkg) async {
  if (kIsWeb) {
    return Map<String, dynamic>.from(jsonDecode(pkg.dataJson) as Map);
  }
  final root = PackagePaths.packageRootFor(pkg.id);
  if (root.isEmpty) {
    return Map<String, dynamic>.from(jsonDecode(pkg.dataJson) as Map);
  }
  final payloadFile = File(p.join(root, 'payload.json'));
  if (await payloadFile.exists()) {
    return jsonDecode(await payloadFile.readAsString()) as Map<String, dynamic>;
  }
  return Map<String, dynamic>.from(jsonDecode(pkg.dataJson) as Map);
}
