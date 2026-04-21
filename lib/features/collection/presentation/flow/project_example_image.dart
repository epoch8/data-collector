import 'package:data_collector/core/api/api_environment.dart';
import 'package:data_collector/models/project_config.dart';
import 'package:flutter/material.dart';

/// Собирает URL примера для гайда: `assets/...` при включённом API → `/v1/projects/{id}/assets/...` на сервере.
Uri? exampleGuideImageUri(Project project, String path) {
  if (path.isEmpty) return null;
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return Uri.tryParse(path);
  }
  final base = ApiEnvironment.normalizedBaseUrl();
  if (base.isEmpty) return null;
  if (path.startsWith('/v1/')) {
    return Uri.parse(base).resolve(path);
  }
  if (path.startsWith('assets/')) {
    final rel = path.substring('assets/'.length);
    final enc = rel.split('/').map(Uri.encodeComponent).join('/');
    return Uri.parse('$base/v1/projects/${project.id}/assets/$enc');
  }
  return null;
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
  return Image.asset(
    assetPath,
    fit: fit,
    errorBuilder: (ctx, _, __) => errorPlaceholder(ctx),
  );
}
