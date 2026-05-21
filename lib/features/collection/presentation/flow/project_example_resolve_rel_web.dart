import 'package:data_collector/core/api/dio_provider.dart';
import 'package:data_collector/features/collection/presentation/flow/project_example_dio_image.dart';
import 'package:data_collector/features/collection/presentation/flow/project_example_media.dart';
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
  final uri = exampleGuideImageUri(project, assetPath);
  if (uri == null) return null;

  final dio = ref.read(dioProvider);
  if (dio != null) {
    final bytes = await fetchProjectExampleImageBytes(dio, uri);
    if (bytes != null) {
      return Image.memory(
        bytes,
        fit: fit,
        errorBuilder: (ctx, _, __) => errorPlaceholder(ctx),
      );
    }
    if (projectExampleUriSameApiOrigin(uri)) {
      return null;
    }
  }

  return Image.network(
    uri.toString(),
    fit: fit,
    headers: imageAuthHeadersForProjectExamples(),
    errorBuilder: (ctx, _, __) => errorPlaceholder(ctx),
  );
}
