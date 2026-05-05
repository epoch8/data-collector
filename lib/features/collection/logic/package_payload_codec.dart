import 'dart:convert';

import 'package:data_collector/features/collection/presentation/flow/package_payload_keys.dart';

/// Убирает служебные ключи черновика перед материализацией и отправкой.
void stripCollectionDraftKeys(Map<String, dynamic> data) {
  data.remove(PackagePayloadKeys.collectionDraftFlowStep);
}

/// Decodes SQLite [Package.dataJson] per [spec 07](specs/07-package-payload-structure.md):
/// envelope `{ package_id, project_id, created_at, data }` or legacy flat map.
Map<String, dynamic> decodePackageEnvelope(String? dataJson) {
  if (dataJson == null || dataJson.isEmpty) return {};
  try {
    final decoded = jsonDecode(dataJson);
    if (decoded is! Map) return {};
    return Map<String, dynamic>.from(decoded);
  } catch (_) {
    return {};
  }
}

/// Form answers and blob-relative paths live under `data` for spec-shaped payloads.
Map<String, dynamic> unpackPackageFormData(String? dataJson) {
  final env = decodePackageEnvelope(dataJson);
  final inner = env['data'];
  if (env.containsKey('package_id') && inner is Map) {
    return Map<String, dynamic>.from(inner);
  }
  return env;
}

String? readPackageIdFromStoredJson(String? dataJson) {
  final env = decodePackageEnvelope(dataJson);
  final id = env['package_id'];
  if (id == null) return null;
  final s = id.toString();
  return s.isEmpty ? null : s;
}
