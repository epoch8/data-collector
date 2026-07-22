import 'package:data_collector/core/device/package_camera_sanitizer.dart';
import 'local_package_materializer_disk_io.dart'
    if (dart.library.html) 'local_package_materializer_disk_web.dart';
import 'package:data_collector/features/collection/logic/local_package_materializer_models.dart';
import 'package:data_collector/features/collection/logic/local_package_materializer_payload_utils.dart';
import 'package:data_collector/features/collection/logic/package_payload_codec.dart';
import 'package:flutter/foundation.dart';

export 'local_package_materializer_models.dart' show MaterializedLocalPackage;

/// Builds on-disk layout from [spec 07](specs/07-package-payload-structure.md) and the envelope JSON for SQLite.
Future<MaterializedLocalPackage> materializeLocalPackage({
  required String packageId,
  required String projectId,
  required DateTime createdAt,
  required Map<String, dynamic> answers,
  String formId = 'default',
  String? formName,
  String? formVersion,
}) async {
  final createdUtc = createdAt.toUtc();
  final data = deepPayloadCopy(answers);
  stripCollectionDraftKeys(data);
  sanitizePackageCameraPayload(data);
  if (kIsWeb) {
    final payload = envelopePayload(
      packageId,
      projectId,
      createdUtc,
      data,
      formId: formId,
      formName: formName,
      formVersion: formVersion,
    );
    return MaterializedLocalPackage(
      packageId: packageId,
      packageDirectoryPath: '',
      payload: payload,
    );
  }
  return materializeOnDisk(
    packageId: packageId,
    projectId: projectId,
    createdUtc: createdUtc,
    data: data,
    formId: formId,
    formName: formName,
    formVersion: formVersion,
  );
}
