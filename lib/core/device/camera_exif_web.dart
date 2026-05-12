import 'package:cross_file/cross_file.dart';
import 'package:exif/exif.dart';

/// Same field subset as [camera_exif_io], reading bytes via [XFile] (supports `blob:` / `data:` on web).
Future<Map<String, dynamic>> readExifSubsetFromFile(String path) async {
  const maxExifValueChars = 8000;
  final out = <String, dynamic>{};
  if (path.isEmpty) return out;
  try {
    final bytes = await XFile(path).readAsBytes();
    if (bytes.isEmpty) return out;
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
    // corrupt / stripped exif / unreadable blob
  }
  return out;
}
