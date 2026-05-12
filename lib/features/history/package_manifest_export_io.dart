import 'dart:io';

import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

Future<void> shareJsonFileWithOsShareSheet({
  required BuildContext context,
  required String body,
  required String fileName,
  required String subject,
  required String shareText,
}) async {
  final dir = await getTemporaryDirectory();
  final file = File('${dir.path}/$fileName');
  await file.writeAsString(body);

  await Share.shareXFiles(
    [XFile(file.path, mimeType: 'application/json', name: fileName)],
    subject: subject,
    text: shareText,
  );
}
