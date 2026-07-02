import 'package:data_collector/core/api/dio_provider.dart';
import 'package:data_collector/features/collection/presentation/flow/project_example_media.dart';
import 'package:data_collector/features/projects/project_asset_cache_io.dart';
import 'package:data_collector/models/project_config.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

Future<Widget?> buildProjectRelAssetPreview({
  required WidgetRef ref,
  required Project project,
  required String assetPath,
  required String rel,
  required BoxFit fit,
  required Widget Function(BuildContext context) errorPlaceholder,
}) async {
  final file = await cachedProjectAssetFile(project.id, rel);
  if (await file.exists()) {
    return Image.file(
      file,
      fit: fit,
      errorBuilder: (ctx, _, __) => errorPlaceholder(ctx),
    );
  }

  final dio = ref.read(dioProvider);
  final uri = exampleGuideImageUri(project, assetPath);
  if (dio != null && uri != null) {
    try {
      await ensureProjectAssetCached(
        dio: dio,
        projectId: project.id,
        relativePath: rel,
        downloadUri: uri,
      );
    } catch (_) {
      /* fallback: Image.network */
    }
    if (await file.exists()) {
      return Image.file(
        file,
        fit: fit,
        errorBuilder: (ctx, _, __) => errorPlaceholder(ctx),
      );
    }
    return Image.network(
      uri.toString(),
      fit: fit,
      headers: imageAuthHeadersForProjectExamples(),
      errorBuilder: (ctx, _, __) => errorPlaceholder(ctx),
    );
  }
  return null;
}
