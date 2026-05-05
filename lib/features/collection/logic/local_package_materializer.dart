import 'dart:convert';
import 'dart:io';

import 'package:data_collector/core/device/package_camera_sanitizer.dart';
import 'package:data_collector/features/collection/logic/package_payload_codec.dart';
import 'package:flutter/foundation.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

/// Result of laying out `packages/<id>/payload.json` and `blobs/` on disk (spec 07).
final class MaterializedLocalPackage {
  const MaterializedLocalPackage({
    required this.packageId,
    required this.packageDirectoryPath,
    required this.payload,
  });

  final String packageId;
  final String packageDirectoryPath;
  final Map<String, dynamic> payload;
}

/// Builds on-disk layout from [spec 07](specs/07-package-payload-structure.md) and the envelope JSON for SQLite.
Future<MaterializedLocalPackage> materializeLocalPackage({
  required String packageId,
  required String projectId,
  required DateTime createdAt,
  required Map<String, dynamic> answers,
}) async {
  final createdUtc = createdAt.toUtc();
  if (kIsWeb) {
    final data = _deepJsonCopy(answers);
    stripCollectionDraftKeys(data);
    sanitizePackageCameraPayload(data);
    final payload = _envelope(packageId, projectId, createdUtc, data);
    return MaterializedLocalPackage(
      packageId: packageId,
      packageDirectoryPath: '',
      payload: payload,
    );
  }

  final docs = await getApplicationDocumentsDirectory();
  final root = p.join(docs.path, 'packages', packageId);
  final blobsDir = p.join(root, 'blobs');
  await Directory(blobsDir).create(recursive: true);

  final data = _deepJsonCopy(answers);
  stripCollectionDraftKeys(data);
  sanitizePackageCameraPayload(data);
  final absToRel = <String, String>{};
  var blobCounter = 0;

  Future<void> ensureBlob(String absPath) async {
    if (absToRel.containsKey(absPath)) return;
    final file = File(absPath);
    if (!await file.exists()) return;
    blobCounter++;
    final ext = p.extension(absPath);
    final name = 'img_${blobCounter.toString().padLeft(4, '0')}$ext';
    const rel = 'blobs/'; // posix-style inside JSON
    final relPath = '$rel$name';
    await file.copy(p.join(blobsDir, name));
    absToRel[absPath] = relPath;
  }

  final candidates = <String>{};
  void collect(dynamic node) {
    if (node is Map) {
      for (final k in node.keys) {
        final ks = k is String ? k : k.toString();
        if (_mightBeFilesystemPath(ks)) {
          candidates.add(ks);
        }
        collect(node[k]);
      }
    } else if (node is List) {
      for (final v in node) {
        collect(v);
      }
    } else if (node is String) {
      if (_mightBeFilesystemPath(node)) {
        candidates.add(node);
      }
    }
  }

  collect(data);
  for (final c in candidates) {
    await ensureBlob(c);
  }

  _replacePaths(data, absToRel);

  final payload = _envelope(packageId, projectId, createdUtc, data);
  final payloadFile = File(p.join(root, 'payload.json'));
  await payloadFile.writeAsString(const JsonEncoder.withIndent('  ').convert(payload));

  return MaterializedLocalPackage(
    packageId: packageId,
    packageDirectoryPath: root,
    payload: payload,
  );
}

bool _mightBeFilesystemPath(String s) {
  if (s.length < 4) return false;
  if (s.startsWith('blobs/') || s.startsWith('blobs\\')) return false;
  if (s.startsWith('{') || s.startsWith('[')) return false;
  return s.contains('/') || s.contains(r'\');
}

Map<String, dynamic> _deepJsonCopy(Map<String, dynamic> m) {
  return Map<String, dynamic>.from(jsonDecode(jsonEncode(m)) as Map);
}

void _replacePaths(dynamic node, Map<String, String> absToRel) {
  if (node is Map) {
    final entries = node.entries.toList();
    node.clear();
    for (final e in entries) {
      final ks = e.key is String ? e.key as String : e.key.toString();
      final newKey = absToRel[ks] ?? ks;
      var v = e.value;
      _replacePaths(v, absToRel);
      node[newKey] = v;
    }
  } else if (node is List<dynamic>) {
    for (var i = 0; i < node.length; i++) {
      final v = node[i];
      if (v is String && absToRel.containsKey(v)) {
        node[i] = absToRel[v];
      } else {
        _replacePaths(v, absToRel);
      }
    }
  }
}

Map<String, dynamic> _envelope(
  String packageId,
  String projectId,
  DateTime createdUtc,
  Map<String, dynamic> data,
) {
  return {
    'package_id': packageId,
    'project_id': projectId,
    'created_at': createdUtc.toIso8601String(),
    'data': data,
  };
}
