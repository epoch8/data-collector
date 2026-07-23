import 'dart:convert';
import 'dart:io';

import 'package:data_collector/features/collection/logic/local_package_materializer_models.dart';
import 'package:data_collector/features/collection/logic/local_package_materializer_payload_utils.dart';
import 'package:data_collector/features/collection/presentation/flow/package_payload_keys.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

Future<MaterializedLocalPackage> materializeOnDisk({
  required String packageId,
  required String projectId,
  required DateTime createdUtc,
  required Map<String, dynamic> data,
  String formId = 'default',
  String? formName,
  String? formVersion,
}) async {
  final docs = await getApplicationDocumentsDirectory();
  final root = p.join(docs.path, 'packages', packageId);
  final blobsDir = p.join(root, 'blobs');
  await Directory(blobsDir).create(recursive: true);

  final absToRel = <String, String>{};
  var blobCounter = 0;

  Future<void> ensureBlob(String absPath) async {
    if (absToRel.containsKey(absPath)) return;
    final file = File(absPath);
    if (!await file.exists()) return;
    blobCounter++;
    final ext = p.extension(absPath);
    final name = 'img_${blobCounter.toString().padLeft(4, '0')}$ext';
    const rel = 'blobs/';
    final relPath = '$rel$name';
    await file.copy(p.join(blobsDir, name));
    absToRel[absPath] = relPath;
  }

  final candidates = <String>{};
  void collect(dynamic node) {
    if (node is Map) {
      for (final k in node.keys) {
        final fieldKey = k is String ? k : k.toString();
        if (fieldKey == PackagePayloadKeys.cameraDebug) {
          continue;
        }
        final ks = fieldKey;
        if (mightBeFilesystemPath(ks)) {
          candidates.add(ks);
        }
        collect(node[k]);
      }
    } else if (node is List) {
      for (final v in node) {
        collect(v);
      }
    } else if (node is String) {
      if (mightBeFilesystemPath(node)) {
        candidates.add(node);
      }
    }
  }

  collect(data);
  for (final c in candidates) {
    await ensureBlob(c);
  }

  replacePathsInPayload(data, absToRel);

  final payload = envelopePayload(
    packageId,
    projectId,
    createdUtc,
    data,
    formId: formId,
    formName: formName,
    formVersion: formVersion,
  );
  final payloadFile = File(p.join(root, 'payload.json'));
  await payloadFile.writeAsString(
    const JsonEncoder.withIndent('  ').convert(payload),
  );

  return MaterializedLocalPackage(
    packageId: packageId,
    packageDirectoryPath: root,
    payload: payload,
  );
}
