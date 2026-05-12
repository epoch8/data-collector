import 'package:data_collector/core/api/api_environment.dart';
import 'package:data_collector/features/collection/presentation/flow/project_example_media.dart';
import 'project_example_resolve_rel_io.dart' if (dart.library.html) 'project_example_resolve_rel_web.dart' as rel_preview;
import 'package:data_collector/models/project_config.dart';
import 'package:data_collector/theme/epoch8_theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

export 'project_example_media.dart' show exampleGuideImageUri, markdownImageRefFromUri, projectAssetStorageRelativePath;

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
            headers: imageAuthHeadersForProjectExamples(),
            errorBuilder: (ctx, _, __) => widget.errorPlaceholder(ctx),
          );
          _ready = true;
        });
      }
      return;
    }

    final rel = projectAssetStorageRelativePath(path);
    if (rel != null && ApiEnvironment.isConfigured) {
      final w = await rel_preview.buildProjectRelAssetPreview(
        ref: ref,
        project: widget.project,
        assetPath: path,
        rel: rel,
        fit: widget.fit,
        errorPlaceholder: widget.errorPlaceholder,
      );
      if (w != null && mounted) {
        setState(() {
          _image = w;
          _ready = true;
        });
        return;
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
