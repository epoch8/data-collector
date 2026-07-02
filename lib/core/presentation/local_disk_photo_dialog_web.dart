import 'package:data_collector/l10n/app_localizations.dart';
import 'package:flutter/material.dart';

bool _isNetworkLikePreviewPath(String path) {
  final p = path.trim();
  return p.startsWith('blob:') ||
      p.startsWith('http://') ||
      p.startsWith('https://') ||
      p.startsWith('data:');
}

Future<void> showLocalDiskPhotoDialog(BuildContext context, String path) async {
  final loc = AppLocalizations.of(context);
  if (!_isNetworkLikePreviewPath(path)) {
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(loc.fileNotFound),
        content: Text(loc.webExportNotSupported),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: Text(loc.close),
          ),
        ],
      ),
    );
    return;
  }

  await showDialog<void>(
    context: context,
    builder: (ctx) => Dialog(
      backgroundColor: Colors.black,
      insetPadding: const EdgeInsets.all(10),
      child: Stack(
        children: [
          Positioned.fill(
            child: InteractiveViewer(
              minScale: 0.8,
              maxScale: 6,
              child: Center(
                child: Image.network(
                  path,
                  fit: BoxFit.contain,
                  errorBuilder: (_, __, ___) => Center(
                    child: Text(
                      loc.fileNotFound,
                      style: const TextStyle(color: Colors.white70),
                    ),
                  ),
                ),
              ),
            ),
          ),
          Positioned(
            right: 8,
            top: 8,
            child: IconButton(
              onPressed: () => Navigator.of(ctx).pop(),
              icon: const Icon(Icons.close, color: Colors.white),
              tooltip: loc.close,
            ),
          ),
        ],
      ),
    ),
  );
}
