import 'package:data_collector/models/project_config.dart';

/// Resolves copy from [Project.config.ui] (nested maps). Missing keys use [fallback].
final class ProjectUi {
  ProjectUi(this.project);

  final Project project;

  Map<String, dynamic>? get _root => project.config.ui;

  dynamic _walk(Iterable<String> keys) {
    dynamic cur = _root;
    for (final k in keys) {
      if (cur is! Map) return null;
      cur = cur[k];
    }
    return cur;
  }

  /// String at path; empty string in JSON counts as missing → [fallback].
  String str(Iterable<String> keys, String fallback) {
    final v = _walk(keys);
    if (v == null) return fallback;
    final s = v.toString();
    return s.isEmpty ? fallback : s;
  }

  /// List of strings (e.g. tips); missing or empty → [fallback].
  List<String> strings(Iterable<String> keys, List<String> fallback) {
    final v = _walk(keys);
    if (v is! List) return fallback;
    final out = v.map((e) => e.toString()).where((s) => s.isNotEmpty).toList();
    return out.isEmpty ? fallback : out;
  }

  /// Raw list at path or null.
  List<dynamic>? listAt(Iterable<String> keys) {
    final v = _walk(keys);
    return v is List ? v : null;
  }

  /// Template from config at [keys], or [fallbackTemplate], then `{var}` substitution.
  String tpl(Iterable<String> keys, String fallbackTemplate, Map<String, String> vars) {
    final raw = _walk(keys);
    final template = (raw is String && raw.isNotEmpty) ? raw : fallbackTemplate;
    var r = template;
    for (final e in vars.entries) {
      r = r.replaceAll('{${e.key}}', e.value);
    }
    return r;
  }
}
