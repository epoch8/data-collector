import 'package:data_collector/core/api/api_environment.dart';
import 'package:data_collector/core/api/dio_provider.dart';
import 'package:data_collector/features/projects/project_asset_cache.dart';
import 'package:data_collector/models/project_config.dart';
import 'package:data_collector/theme/epoch8_theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

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
  final rel = projectAssetStorageRelativePath(path);
  if (rel == null) {
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

/// Картинка примера: сначала локальный кэш (`server_project_cache/project_assets`), затем одна загрузка с API.
Widget projectExampleImage({
  required Project project,
  required String assetPath,
  required BoxFit fit,
  required Widget Function(BuildContext context) errorPlaceholder,
}) {
  return ProjectExampleImage(
    project: project,
    assetPath: assetPath,
    fit: fit,
    errorPlaceholder: errorPlaceholder,
  );
}

class ProjectExampleImage extends ConsumerStatefulWidget {
  const ProjectExampleImage({
    super.key,
    required this.project,
    required this.assetPath,
    required this.fit,
    required this.errorPlaceholder,
  });

  final Project project;
  final String assetPath;
  final BoxFit fit;
  final Widget Function(BuildContext context) errorPlaceholder;

  @override
  ConsumerState<ProjectExampleImage> createState() => _ProjectExampleImageState();
}

class _ProjectExampleImageState extends ConsumerState<ProjectExampleImage> {
  Widget? _image;
  bool _ready = false;

  @override
  void initState() {
    super.initState();
    _resolve();
  }

  @override
  void didUpdateWidget(ProjectExampleImage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.project.id != widget.project.id || oldWidget.assetPath != widget.assetPath) {
      setState(() {
        _ready = false;
        _image = null;
      });
      _resolve();
    }
  }

  Future<void> _resolve() async {
    final path = widget.assetPath;
    final trimmed = path.trim();

    if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
      final u = Uri.tryParse(trimmed);
      if (u != null && mounted) {
        setState(() {
          _image = Image.network(
            u.toString(),
            fit: widget.fit,
            headers: _imageAuthHeaders(),
            errorBuilder: (ctx, _, __) => widget.errorPlaceholder(ctx),
          );
          _ready = true;
        });
      }
      return;
    }

    final rel = projectAssetStorageRelativePath(path);
    if (rel != null && ApiEnvironment.isConfigured) {
      final file = await cachedProjectAssetFile(widget.project.id, rel);
      if (await file.exists() && mounted) {
        setState(() {
          _image = Image.file(
            file,
            fit: widget.fit,
            errorBuilder: (ctx, _, __) => widget.errorPlaceholder(ctx),
          );
          _ready = true;
        });
        return;
      }

      final dio = ref.read(dioProvider);
      final uri = exampleGuideImageUri(widget.project, path);
      if (dio != null && uri != null) {
        try {
          await ensureProjectAssetCached(
            dio: dio,
            projectId: widget.project.id,
            relativePath: rel,
            downloadUri: uri,
          );
        } catch (_) {
          /* fallback: Image.network */
        }
        if (await file.exists() && mounted) {
          setState(() {
            _image = Image.file(
              file,
              fit: widget.fit,
              errorBuilder: (ctx, _, __) => widget.errorPlaceholder(ctx),
            );
            _ready = true;
          });
          return;
        }
        if (mounted) {
          setState(() {
            _image = Image.network(
              uri.toString(),
              fit: widget.fit,
              headers: _imageAuthHeaders(),
              errorBuilder: (ctx, _, __) => widget.errorPlaceholder(ctx),
            );
            _ready = true;
          });
          return;
        }
      }
    }

    if (trimmed.startsWith('assets/') && mounted) {
      setState(() {
        _image = Image.asset(
          trimmed,
          fit: widget.fit,
          errorBuilder: (ctx, _, __) => widget.errorPlaceholder(ctx),
        );
        _ready = true;
      });
      return;
    }

    if (mounted) {
      setState(() {
        _image = null;
        _ready = true;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_ready) {
      return Container(
        constraints: const BoxConstraints(minHeight: 80),
        alignment: Alignment.center,
        color: Epoch8Theme.bgElevated,
        child: const SizedBox(
          width: 28,
          height: 28,
          child: CircularProgressIndicator(strokeWidth: 2),
        ),
      );
    }
    if (_image != null) {
      return _image!;
    }
    return Builder(builder: (ctx) => widget.errorPlaceholder(ctx));
  }
}
