/// Относительный ключ файла в хранилище проекта (как в `GET …/assets/{key}`), без процент-кодирования.
/// `null` для абсолютных URL и прочих путей, которые не мапятся на этот API.
String? projectAssetStorageRelativePath(String rawPath) {
  var p0 = rawPath.trim().replaceAll(r'\', '/');
  if (p0.isEmpty) return null;
  if (p0.startsWith('./')) {
    p0 = p0.substring(2);
  }
  if (p0.startsWith('http://') || p0.startsWith('https://')) {
    return null;
  }
  if (p0.startsWith('/v1/')) {
    return null;
  }
  final String rel;
  if (p0.startsWith('assets/')) {
    rel = p0.substring('assets/'.length);
  } else if (!p0.contains('://') && !p0.startsWith('/')) {
    rel = p0;
  } else {
    return null;
  }
  if (rel.isEmpty || rel.split('/').contains('..')) {
    return null;
  }
  return rel;
}
