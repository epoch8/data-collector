import 'package:data_collector/core/api/api_environment.dart';
import 'package:data_collector/models/project_config.dart';
import 'package:flutter/material.dart';

/// Путь из Markdown `![](...)`: относительные `uploads/…`, `assets/…`, абсолютные URL.
String? markdownImageRefFromUri(Uri uri) {
  if (uri.scheme == 'http' || uri.scheme == 'https') {
    return uri.toString();
  }
  if (uri.scheme == 'data') {
    return null;
  }
  // `Uri.tryParse('uploads/a.jpg')` в Dart часто даёт host=`uploads`, path=`/a.jpg` — без этого
  // теряется первый сегмент пути и ассет на сервере не находится.
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
  final String rel;
  if (p.startsWith('assets/')) {
    rel = p.substring('assets/'.length);
  } else if (!p.contains('://') && !p.startsWith('/')) {
    rel = p;
  } else {
    return null;
  }
  if (rel.isEmpty || rel.split('/').contains('..')) {
    return null;
  }
  final enc = rel.split('/').where((s) => s.isNotEmpty).map(Uri.encodeComponent).join('/');
  return Uri.parse('$base/v1/projects/${project.id}/assets/$enc');
}

Map<String, String>? _imageAuthHeaders() {
  final t = ApiEnvironment.bearerToken.trim();
  if (t.isEmpty) return null;
  return {'Authorization': 'Bearer $t'};
}

/// Картинка примера из конфига: с сервера при `API_BASE_URL`, иначе из bundle.
Widget projectExampleImage({
  required Project project,
  required String assetPath,
  required BoxFit fit,
  required Widget Function(BuildContext context) errorPlaceholder,
}) {
  final uri = exampleGuideImageUri(project, assetPath);
  if (uri != null) {
    return Image.network(
      uri.toString(),
      fit: fit,
      headers: _imageAuthHeaders(),
      errorBuilder: (ctx, _, __) => errorPlaceholder(ctx),
    );
  }
  final bundled = assetPath.trim();
  if (bundled.startsWith('assets/')) {
    return Image.asset(
      bundled,
      fit: fit,
      errorBuilder: (ctx, _, __) => errorPlaceholder(ctx),
    );
  }
  return Builder(
    builder: (ctx) => errorPlaceholder(ctx),
  );
}
