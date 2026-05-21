/// Result of laying out `packages/<id>/payload.json` and `blobs/` on disk (spec 07).
final class MaterializedLocalPackage {
  const MaterializedLocalPackage({
    required this.packageId,
    required this.packageDirectoryPath,
    required this.payload,
  });

  final String packageId;
  final String packageDirectoryPath;
  final Map<String, dynamic> payload;
}
