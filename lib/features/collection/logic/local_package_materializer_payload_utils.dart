import 'dart:convert';

bool mightBeFilesystemPath(String s) {
  if (s.length < 4) return false;
  if (s.startsWith('blobs/') || s.startsWith('blobs\\')) return false;
  if (s.startsWith('{') || s.startsWith('[')) return false;
  if (s.startsWith('blob:') || s.startsWith('data:')) return true;
  return s.contains('/') || s.contains(r'\');
}

/// Paths to binary captures (disk, `blob:`, `data:`) under [root] — same rules as on-disk materialization.
Set<String> collectFilesystemLikePathsFromPayload(dynamic root) {
  final out = <String>{};
  void collect(dynamic node) {
    if (node is Map) {
      for (final k in node.keys) {
        final ks = k is String ? k : k.toString();
        if (mightBeFilesystemPath(ks)) {
          out.add(ks);
        }
        collect(node[k]);
      }
    } else if (node is List) {
      for (final v in node) {
        collect(v);
      }
    } else if (node is String) {
      if (mightBeFilesystemPath(node)) {
        out.add(node);
      }
    }
  }

  collect(root);
  return out;
}

Map<String, dynamic> deepPayloadCopy(Map<String, dynamic> m) {
  return Map<String, dynamic>.from(jsonDecode(jsonEncode(m)) as Map);
}

void replacePathsInPayload(dynamic node, Map<String, String> absToRel) {
  if (node is Map) {
    final entries = node.entries.toList();
    node.clear();
    for (final e in entries) {
      final ks = e.key is String ? e.key as String : e.key.toString();
      final newKey = absToRel[ks] ?? ks;
      final v = e.value;
      replacePathsInPayload(v, absToRel);
      node[newKey] = v;
    }
  } else if (node is List<dynamic>) {
    for (var i = 0; i < node.length; i++) {
      final v = node[i];
      if (v is String && absToRel.containsKey(v)) {
        node[i] = absToRel[v];
      } else {
        replacePathsInPayload(v, absToRel);
      }
    }
  }
}

Map<String, dynamic> envelopePayload(
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
