import 'dart:io';

import 'package:exif/exif.dart';

Future<Map<String, dynamic>> readExifSubsetFromFile(String path) async {
  const maxExifValueChars = 8000;
  final out = <String, dynamic>{};
  try {
    final bytes = await File(path).readAsBytes();
    final data = await readExifFromBytes(bytes);
    if (data.isEmpty) return out;

    for (final e in data.entries) {
      final key = e.key.toString();
      final tag = e.value;
      try {
        var s = tag.printable;
        if (s.length > maxExifValueChars) {
          s = '${s.substring(0, maxExifValueChars)}…(truncated, $maxExifValueChars chars max)';
          out['${key}__value_truncated'] = true;
        }
        out[key] = s;
      } catch (_) {
        out[key] = tag.toString();
      }
    }
  } catch (_) {
    // ignore corrupt / missing exif
  }
  return out;
}
