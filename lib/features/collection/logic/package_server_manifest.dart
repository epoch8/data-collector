import 'dart:convert';

import 'package:data_collector/bootstrap.dart';
import 'package:data_collector/core/storage/database.dart';
import 'package_payload_disk_io.dart' if (dart.library.html) 'package_payload_disk_web.dart' as payload_disk;
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart';

/// Те же поля, что добавляются перед [PUT …/manifest] в [uploadDriftPackageToServer].
void injectSubmittedByIntoServerManifest(Map<String, dynamic> manifest) {
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
  final fromDisk = await payload_disk.readPayloadJsonFromDiskIfPresent(pkg.id);
  if (fromDisk != null) return fromDisk;
  return Map<String, dynamic>.from(jsonDecode(pkg.dataJson) as Map);
}
