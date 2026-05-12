import 'dart:convert';

bool mightBeFilesystemPath(String s) {
  if (s.length < 4) return false;
  if (s.startsWith('blobs/') || s.startsWith('blobs\\')) return false;
  if (s.startsWith('{') || s.startsWith('[')) return false;
  final head = s.trimLeft().toLowerCase();
  if (head.startsWith('http://') || head.startsWith('https://')) return false;
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

bool _isLikelyWebCaptureRef(String s) {
  final t = s.trimLeft();
  if (t.startsWith('blob:')) return true;
  return t.toLowerCase().startsWith('data:image/');
}

/// For web upload: only capture refs from shallow field values
/// (string, list of strings, or map keys path->meta).
Set<String> collectWebCaptureRefsFromPayloadShallow(dynamic root) {
  if (root is! Map) return {};
  final out = <String>{};
  for (final entry in root.entries) {
    final value = entry.value;
    if (value is String) {
      if (_isLikelyWebCaptureRef(value)) out.add(value);
      continue;
    }
    if (value is List) {
      for (final item in value) {
        if (item is String && _isLikelyWebCaptureRef(item)) {
          out.add(item);
        }
      }
      continue;
    }
    if (value is Map) {
      for (final k in value.keys) {
        final ks = k.toString();
        if (_isLikelyWebCaptureRef(ks)) out.add(ks);
      }
    }
  }
  return out;
}

/// Все строковые ссылки `blobs/…` в JSON (ключи и значения map — пути к кадрам часто в ключах).
void collectBlobLogicalPathsFromPayload(dynamic obj, Set<String> out) {
  if (obj is Map) {
    for (final e in obj.entries) {
      final ks = e.key.toString().replaceAll(r'\', '/');
      if (ks.startsWith('blobs/')) {
        out.add(ks);
      }
      collectBlobLogicalPathsFromPayload(e.value, out);
    }
  } else if (obj is List) {
    for (final v in obj) {
      collectBlobLogicalPathsFromPayload(v, out);
    }
  } else if (obj is String) {
    final s = obj.replaceAll(r'\', '/');
    if (s.startsWith('blobs/')) {
      out.add(s);
    }
  }
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
