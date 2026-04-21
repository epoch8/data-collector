import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:path/path.dart' as p;
import 'package:shelf/shelf.dart';
import 'package:shelf/shelf_io.dart' as shelf_io;
import 'package:shelf_router/shelf_router.dart';

enum _SessionOutcome { created, resumed, completedConflict }

/// Reference server for [specs/08-server-api-package-upload.md] and
/// [specs/09-server-project-config-delivery.md].
///
/// Run from repo root:
///   dart run mock_server/bin/server.dart
///
/// Android emulator → host: `http://10.0.2.2:8787`
/// Optional auth: `Authorization: Bearer <token>` if `DC_MOCK_TOKEN` is set.
Future<void> main(List<String> args) async {
  final bindArg = args.where((a) => a.startsWith('--bind=')).map((a) => a.substring('--bind='.length)).firstOrNull;
  final hostPort = bindArg ?? Platform.environment['DC_MOCK_BIND'] ?? '0.0.0.0:8787';
  final parts = hostPort.split(':');
  final host = parts.first;
  final port = int.tryParse(parts.length > 1 ? parts[1] : '8787') ?? 8787;

  final repoRoot = _resolveRepoRoot();
  final state = await _ServerState.loadFromAssets(repoRoot);
  final token = Platform.environment['DC_MOCK_TOKEN'];

  final router = Router();
  router.get('/health', (_) => Response.ok('ok'));

  router.get('/v1/projects', (Request req) {
    if (!_authOk(req, token)) return _unauthorized();
    final etag = state.catalogEtag;
    if (req.headers['if-none-match'] == etag) {
      return Response(304);
    }
    return Response.ok(
      jsonEncode({'projects': state.catalog}),
      headers: {
        HttpHeaders.contentTypeHeader: 'application/json; charset=utf-8',
        HttpHeaders.etagHeader: etag,
      },
    );
  });

  router.get('/v1/projects/<projectId>/config', (Request req, String projectId) {
    if (!_authOk(req, token)) return _unauthorized();
    final body = state.fullConfigByProjectId[projectId];
    if (body == null) return Response.notFound(jsonEncode(_err('not_found', 'Unknown project')));
    final etag = state.configEtag[projectId]!;
    if (req.headers['if-none-match'] == etag) {
      return Response(304, headers: {HttpHeaders.etagHeader: etag});
    }
    return Response.ok(
      body,
      headers: {
        HttpHeaders.contentTypeHeader: 'application/json; charset=utf-8',
        HttpHeaders.etagHeader: etag,
      },
    );
  });

  router.post('/v1/projects/<projectId>/packages', (Request req, String projectId) async {
    if (!_authOk(req, token)) return _unauthorized();
    if (!state.fullConfigByProjectId.containsKey(projectId)) {
      return Response.notFound(jsonEncode(_err('not_found', 'Unknown project')));
    }
    final body = await req.readAsString();
    Map<String, dynamic> json;
    try {
      json = jsonDecode(body) as Map<String, dynamic>;
    } catch (_) {
      return Response.badRequest(body: jsonEncode(_err('invalid_json', 'Body must be JSON object')));
    }
    final packageId = json['package_id'] as String?;
    if (packageId == null || packageId.isEmpty) {
      return Response(422, body: jsonEncode(_err('validation', 'package_id required')));
    }
    final outcome = state.startOrResumePackage(projectId: projectId, packageId: packageId);
    if (outcome == _SessionOutcome.completedConflict) {
      return Response(409, body: jsonEncode(_err('conflict', 'Package already completed', {'package_id': packageId})));
    }
    final created = outcome == _SessionOutcome.created;
    return Response(
      created ? HttpStatus.created : HttpStatus.ok,
      body: jsonEncode({
        'package_id': packageId,
        'status': state.packageStatus(projectId, packageId),
      }),
      headers: {HttpHeaders.contentTypeHeader: 'application/json; charset=utf-8'},
    );
  });

  /// [blobPath] is one URL path segment (encode slashes as %2F), e.g. `blobs%2Fimg_0001.jpg`.
  router.put('/v1/projects/<projectId>/packages/<packageId>/blobs/<blobPath>', (Request req, String projectId, String packageId, String blobPath) async {
    if (!_authOk(req, token)) return _unauthorized();
    final decoded = Uri.decodeComponent(blobPath);
    if (decoded.contains('..') || p.isAbsolute(decoded)) {
      return Response(422, body: jsonEncode(_err('invalid_blob_path', decoded)));
    }
    final chunks = await req.read().toList();
    var total = 0;
    for (final c in chunks) {
      total += c.length;
    }
    final bytes = Uint8List(total);
    var o = 0;
    for (final c in chunks) {
      bytes.setRange(o, o + c.length, c);
      o += c.length;
    }
    final written = state.putBlob(projectId, packageId, decoded, bytes);
    if (!written) {
      return Response(409, body: jsonEncode(_err('conflict', 'Invalid package phase or unknown package')));
    }
    return Response.ok(
      jsonEncode({'path': decoded, 'size': bytes.length}),
      headers: {HttpHeaders.contentTypeHeader: 'application/json; charset=utf-8'},
    );
  });

  router.put('/v1/projects/<projectId>/packages/<packageId>/manifest', (Request req, String projectId, String packageId) async {
    if (!_authOk(req, token)) return _unauthorized();
    final raw = await req.readAsString();
    Map<String, dynamic> manifest;
    try {
      manifest = jsonDecode(raw) as Map<String, dynamic>;
    } catch (_) {
      return Response.badRequest(body: jsonEncode(_err('invalid_json', 'Manifest must be JSON')));
    }
    final r = state.putManifest(projectId: projectId, packageId: packageId, manifest: manifest, raw: raw);
    return Response(r.code, body: jsonEncode(r.body), headers: {HttpHeaders.contentTypeHeader: 'application/json; charset=utf-8'});
  });

  router.post('/v1/projects/<projectId>/packages/<packageId>/commit', (Request req, String projectId, String packageId) async {
    if (!_authOk(req, token)) return _unauthorized();
    final r = state.commit(projectId: projectId, packageId: packageId);
    return Response(r.code, body: jsonEncode(r.body), headers: {HttpHeaders.contentTypeHeader: 'application/json; charset=utf-8'});
  });

  router.get('/v1/projects/<projectId>/packages/<packageId>', (Request req, String projectId, String packageId) {
    if (!_authOk(req, token)) return _unauthorized();
    final info = state.getPackage(projectId, packageId);
    if (info == null) return Response.notFound(jsonEncode(_err('not_found', 'Package not found')));
    return Response.ok(jsonEncode(info), headers: {HttpHeaders.contentTypeHeader: 'application/json; charset=utf-8'});
  });

  final handler = Pipeline().addMiddleware(logRequests()).addHandler(router.call);

  final server = await shelf_io.serve(handler, host, port);
  // ignore: avoid_print
  print('data_collector mock server at http://${server.address.host}:${server.port}');
  // ignore: avoid_print
  print('Repo configs loaded: ${state.catalog.length} projects');
}

String _resolveRepoRoot() {
  // mock_server/bin/server.dart → repo root is ../..
  final here = File(Platform.script.toFilePath()).parent;
  return p.normalize(p.join(here.path, '..', '..'));
}

bool _authOk(Request req, String? expectedToken) {
  if (expectedToken == null || expectedToken.isEmpty) return true;
  final h = req.headers['authorization'];
  if (h == null) return false;
  const p = 'Bearer ';
  if (!h.startsWith(p)) return false;
  return h.substring(p.length).trim() == expectedToken;
}

Response _unauthorized() => Response(
      401,
      body: jsonEncode(_err('unauthorized', 'Missing or invalid bearer token')),
      headers: {HttpHeaders.contentTypeHeader: 'application/json; charset=utf-8'},
    );

Map<String, Object?> _err(String code, String message, [Object? details]) => {
      'error': {
        'code': code,
        'message': message,
        if (details != null) 'details': details,
      },
    };

class _ServerState {
  _ServerState({
    required this.catalog,
    required this.catalogEtag,
    required this.fullConfigByProjectId,
    required this.configEtag,
  });

  final List<Map<String, dynamic>> catalog;
  final String catalogEtag;
  final Map<String, String> fullConfigByProjectId;
  final Map<String, String> configEtag;

  final Map<String, Map<String, _PackageSession>> _byProject = {};

  static Future<_ServerState> loadFromAssets(String repoRoot) async {
    final manifestPath = p.join(repoRoot, 'assets', 'config', 'projects.json');
    final manifestFile = File(manifestPath);
    if (!await manifestFile.exists()) {
      throw StateError('Missing $manifestPath');
    }
    final manifest = jsonDecode(await manifestFile.readAsString()) as Map<String, dynamic>;
    final paths = (manifest['projects'] as List<dynamic>).map((e) => e.toString()).toList();

    final catalog = <Map<String, dynamic>>[];
    final fullById = <String, String>{};
    final etags = <String, String>{};

    for (final rel in paths) {
      final abs = p.join(repoRoot, rel);
      final raw = await File(abs).readAsString();
      final map = jsonDecode(raw) as Map<String, dynamic>;
      final id = map['id'] as String?;
      if (id == null) continue;
      final ver = (map['version'] ?? '1').toString();
      final etag = 'W/"$id-$ver-${raw.hashCode}"';
      catalog.add({
        'project_id': id,
        'name': map['name'] ?? id,
        'config_version': ver,
        'updated_at': DateTime.now().toUtc().toIso8601String(),
      });
      fullById[id] = raw;
      etags[id] = etag;
    }

    final catalogRaw = jsonEncode(catalog);
    final catalogEtag = 'W/"catalog-${catalogRaw.hashCode}"';

    return _ServerState(
      catalog: catalog,
      catalogEtag: catalogEtag,
      fullConfigByProjectId: fullById,
      configEtag: etags,
    );
  }

  Map<String, Map<String, _PackageSession>> get sessions => _byProject;

  _SessionOutcome startOrResumePackage({required String projectId, required String packageId}) {
    final proj = _byProject.putIfAbsent(projectId, () => {});
    final existing = proj[packageId];
    if (existing != null) {
      if (existing.phase == _PackagePhase.completed) return _SessionOutcome.completedConflict;
      return _SessionOutcome.resumed;
    }
    proj[packageId] = _PackageSession(packageId: packageId);
    return _SessionOutcome.created;
  }

  String packageStatus(String projectId, String packageId) {
    final s = _byProject[projectId]?[packageId];
    if (s == null) return 'unknown';
    return switch (s.phase) {
      _PackagePhase.awaitingBlobs => 'awaiting_blobs',
      _PackagePhase.readyToCommit => 'ready_to_commit',
      _PackagePhase.completed => 'completed',
      _PackagePhase.failed => 'failed',
    };
  }

  bool putBlob(String projectId, String packageId, String path, List<int> bytes) {
    final s = _byProject[projectId]?[packageId];
    if (s == null) return false;
    if (s.phase == _PackagePhase.completed || s.phase == _PackagePhase.failed) return false;
    s.blobs[path] = Uint8List.fromList(bytes);
    s.phase = _PackagePhase.awaitingBlobs;
    return true;
  }

  _JsonResponse putManifest({
    required String projectId,
    required String packageId,
    required Map<String, dynamic> manifest,
    required String raw,
  }) {
    final s = _byProject[projectId]?[packageId];
    if (s == null) {
      return _JsonResponse(404, _err('not_found', 'Start package session first'));
    }
    if (s.phase == _PackagePhase.completed) {
      return _JsonResponse(200, {'status': 'completed', 'package_id': packageId});
    }
    final urlPid = manifest['project_id'] as String?;
    if (urlPid == null) {
      return _JsonResponse(422, _err('validation', 'project_id required in manifest', {'field': 'project_id'}));
    }
    if (urlPid != projectId) {
      return _JsonResponse(
        422,
        _err('project_id_mismatch', 'Manifest project_id must match URL', {'expected': projectId, 'actual': urlPid}),
      );
    }
    final missing = _missingBlobPaths(manifest, s.blobs.keys.toSet());
    if (missing.isNotEmpty) {
      return _JsonResponse(
        422,
        _err('missing_blobs', 'Manifest references blobs not uploaded yet', missing),
      );
    }
    s.manifestJson = raw;
    s.phase = _PackagePhase.readyToCommit;
    return _JsonResponse(200, {'status': 'ready_to_commit', 'package_id': packageId});
  }

  _JsonResponse commit({required String projectId, required String packageId}) {
    final s = _byProject[projectId]?[packageId];
    if (s == null) {
      return _JsonResponse(404, _err('not_found', 'Package not found'));
    }
    if (s.phase == _PackagePhase.completed) {
      return _JsonResponse(200, {'status': 'completed', 'package_id': packageId, 'idempotent': true});
    }
    if (s.phase != _PackagePhase.readyToCommit || s.manifestJson == null) {
      return _JsonResponse(409, _err('invalid_phase', 'Manifest not accepted; call PUT manifest first'));
    }
    s.phase = _PackagePhase.completed;
    return _JsonResponse(200, {'status': 'completed', 'package_id': packageId});
  }

  Map<String, Object?>? getPackage(String projectId, String packageId) {
    final s = _byProject[projectId]?[packageId];
    if (s == null) return null;
    return {
      'package_id': packageId,
      'status': packageStatus(projectId, packageId),
      'blobs': s.blobs.keys.toList()..sort(),
    };
  }
}

class _PackageSession {
  _PackageSession({required this.packageId});

  final String packageId;
  final Map<String, Uint8List> blobs = {};
  String? manifestJson;
  _PackagePhase phase = _PackagePhase.awaitingBlobs;
}

enum _PackagePhase { awaitingBlobs, readyToCommit, completed, failed }

class _JsonResponse {
  _JsonResponse(this.code, this.body);
  final int code;
  final Object body;
}

List<String> _missingBlobPaths(Map<String, dynamic> manifest, Set<String> uploaded) {
  final refs = <String>{};
  void walk(dynamic n) {
    if (n is Map) {
      for (final e in n.entries) {
        walk(e.value);
      }
    } else if (n is List) {
      for (final e in n) {
        walk(e);
      }
    } else if (n is String) {
      final s = n.replaceAll('\\', '/');
      if (s.startsWith('blobs/')) refs.add(s);
    }
  }

  walk(manifest);
  final missing = <String>[];
  for (final r in refs) {
    if (!uploaded.contains(r)) missing.add(r);
  }
  return missing;
}

extension<T> on Iterable<T> {
  T? get firstOrNull {
    final i = iterator;
    if (!i.moveNext()) return null;
    return i.current;
  }
}
