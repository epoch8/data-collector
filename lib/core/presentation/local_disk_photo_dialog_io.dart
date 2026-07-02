import 'dart:io';

import 'package:data_collector/l10n/app_localizations.dart';
import 'package:flutter/material.dart';

Future<void> showLocalDiskPhotoDialog(BuildContext context, String path) async {
  await showDialog<void>(
    context: context,
    builder: (context) {
      final file = File(path);
      return Dialog(
        backgroundColor: Colors.black,
        insetPadding: const EdgeInsets.all(10),
        child: Stack(
          children: [
            Positioned.fill(
              child: file.existsSync()
                  ? InteractiveViewer(
                      minScale: 0.8,
                      maxScale: 6,
                      child: Center(
                        child: Image.file(file, fit: BoxFit.contain),
                      ),
                    )
                  : Center(
                      child: Text(
                        AppLocalizations.of(context).fileNotFound,
                        style: const TextStyle(color: Colors.white70),
                      ),
                    ),
            ),
            Positioned(
              right: 8,
              top: 8,
              child: IconButton(
                onPressed: () => Navigator.of(context).pop(),
                icon: const Icon(Icons.close, color: Colors.white),
                tooltip: AppLocalizations.of(context).close,
              ),
            ),
          ],
        ),
      );
    },
  );
}
