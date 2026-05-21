import 'package:flutter/foundation.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

/// Cached app documents path for resolving [spec 07](specs/07-package-payload-structure.md) `blobs/` references.
abstract final class PackagePaths {
  static String? _documentsPath;

  static Future<void> init() async {
    if (kIsWeb) {
      _documentsPath = null;
      return;
    }
    final d = await getApplicationDocumentsDirectory();
    _documentsPath = d.path;
  }

  static String? get documentsPath => _documentsPath;

  static String packageRootFor(String packageId) {
    final base = _documentsPath;
    if (base == null || base.isEmpty) return '';
    return p.join(base, 'packages', packageId);
  }

  /// Turns `blobs/name.jpg` into an absolute path under `packages/<packageId>/`.
  static String resolveMediaReference(String ref, String packageId) {
    if (ref.isEmpty) return ref;
    final norm = ref.replaceAll('\\', '/');
    if (norm.startsWith('blobs/')) {
      final root = packageRootFor(packageId);
      if (root.isEmpty) return ref;
      final tail = norm.substring('blobs/'.length);
      return p.join(root, 'blobs', tail);
    }
    return ref;
  }
}
