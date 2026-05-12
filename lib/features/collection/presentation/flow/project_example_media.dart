import 'package:data_collector/core/api/api_environment.dart';
import 'package:data_collector/models/project_config.dart';

import '../../../projects/project_asset_paths.dart';

export '../../../projects/project_asset_paths.dart' show projectAssetStorageRelativePath;

/// Путь из Markdown `![](...)`: относительные `uploads/…`, `assets/…`, абсолютные URL.
String? markdownImageRefFromUri(Uri uri) {
  if (uri.scheme == 'http' || uri.scheme == 'https') {
    return uri.toString();
  }
  if (uri.scheme == 'data') {
    return null;
  }
  final authoritySplitRelative = uri.scheme.isEmpty &&
      uri.hasAuthority &&
      uri.host.isNotEmpty &&
      uri.userInfo.isEmpty;
  String p;
  if (authoritySplitRelative) {
    final tail = uri.path;
    final tailNorm = tail.isEmpty || tail == '/'
        ? ''
        : (tail.startsWith('/') ? tail.substring(1) : tail);
    p = tailNorm.isEmpty ? uri.host : '${uri.host}/$tailNorm';
  } else {
    p = uri.path;
    if (p.isEmpty) {
      p = uri.hasAuthority ? '${uri.host}${uri.path}' : uri.toString();
    }
  }
  p = p.trim().replaceAll(r'\', '/');
  if (p.startsWith('./')) {
    p = p.substring(2);
  }
  if (p.startsWith('/')) {
    p = p.substring(1);
  }
  return p.isEmpty ? null : p;
}

/// URL файла из медиа проекта: `assets/…` (как в JSON), либо относительный путь из админки (`uploads/…`).
/// При заданном [ApiEnvironment.baseUrl] → `GET /v1/projects/{id}/assets/{encoded}`.
Uri? exampleGuideImageUri(Project project, String path) {
  var p = path.trim().replaceAll(r'\', '/');
  if (p.isEmpty) return null;
  if (p.startsWith('./')) {
    p = p.substring(2);
  }
  if (p.startsWith('http://') || p.startsWith('https://')) {
    return Uri.tryParse(p);
  }
  final base = ApiEnvironment.normalizedBaseUrl();
  if (base.isEmpty) return null;
  if (p.startsWith('/v1/')) {
    return Uri.parse('$base$p');
  }
  final rel = projectAssetStorageRelativePath(path);
  if (rel == null) {
    return null;
  }
  final enc = rel.split('/').where((s) => s.isNotEmpty).map(Uri.encodeComponent).join('/');
  return Uri.parse('$base/v1/projects/${project.id}/assets/$enc');
}

Map<String, String>? imageAuthHeadersForProjectExamples() {
  final t = ApiEnvironment.bearerToken.trim();
  if (t.isEmpty) return null;
  return {'Authorization': 'Bearer $t'};
}
