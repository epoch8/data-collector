import 'package:data_collector/features/collection/logic/local_package_materializer_models.dart';

Future<MaterializedLocalPackage> materializeOnDisk({
  required String packageId,
  required String projectId,
  required DateTime createdUtc,
  required Map<String, dynamic> data,
}) async {
  throw UnsupportedError('materializeOnDisk is not used on web');
}
