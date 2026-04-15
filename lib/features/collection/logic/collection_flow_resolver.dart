import 'package:data_collector/models/project_config.dart';

/// Declarative screen kinds (`flow.steps[].screen` in project JSON).
enum CollectionScreenKind {
  form,
  instruction,
  cameraPose,
  review,
  scrollForm,
}

class ResolvedCollectionStep {
  const ResolvedCollectionStep({
    required this.id,
    required this.kind,
    required this.fields,
    this.poseIndex1Based,
    this.poseTotal,
    this.cowIdHints = false,
    this.cowIdFieldId,
  });

  final String id;
  final CollectionScreenKind kind;
  final List<ConfigField> fields;
  final int? poseIndex1Based;
  final int? poseTotal;
  final bool cowIdHints;
  final String? cowIdFieldId;
}

class ResolvedCollectionFlow {
  const ResolvedCollectionFlow({required this.steps});

  final List<ResolvedCollectionStep> steps;

  bool get isSingleScrollOnly =>
      steps.length == 1 && steps.single.kind == CollectionScreenKind.scrollForm;

  int get cameraPoseCount =>
      steps.where((s) => s.kind == CollectionScreenKind.cameraPose).length;

  int? get reviewStepIndex {
    final i = steps.indexWhere((s) => s.kind == CollectionScreenKind.review);
    return i >= 0 ? i : null;
  }

  List<ConfigField> get allFormFields => [
        for (final s in steps)
          if (s.kind == CollectionScreenKind.form) ...s.fields,
      ];

  List<ConfigField> get allCameraFields => [
        for (final s in steps)
          if (s.kind == CollectionScreenKind.cameraPose) ...s.fields,
      ];

  int indexOfFirstForm() => steps.indexWhere((s) => s.kind == CollectionScreenKind.form);

  int indexOfCameraPose(int poseIndex1Based) {
    var seen = 0;
    for (var j = 0; j < steps.length; j++) {
      if (steps[j].kind == CollectionScreenKind.cameraPose) {
        seen++;
        if (seen == poseIndex1Based) return j;
      }
    }
    return 0;
  }

  /// Group history by extracted subject id (e.g. cow) only when the flow is set up for that:
  /// several camera poses **and** a form step with [cowIdHints] or a `cow_identifier` field.
  ///
  /// Multi-pose retail / product flows without a subject id must stay a flat package list.
  bool get shouldGroupHistoryBySubject {
    if (cameraPoseCount <= 1) return false;
    for (final s in steps) {
      if (s.kind != CollectionScreenKind.form) continue;
      if (s.cowIdHints) return true;
      if (s.fields.any((f) => f.fieldId == 'cow_identifier')) return true;
    }
    return false;
  }
}

CollectionScreenKind _parseScreen(String raw) {
  final s = raw.trim().toLowerCase().replaceAll('-', '_');
  switch (s) {
    case 'form':
      return CollectionScreenKind.form;
    case 'instruction':
      return CollectionScreenKind.instruction;
    case 'camera_pose':
    case 'cameraphoto':
      return CollectionScreenKind.cameraPose;
    case 'review':
      return CollectionScreenKind.review;
    case 'scroll_form':
    case 'scrollform':
      return CollectionScreenKind.scrollForm;
    default:
      throw FormatException('Unknown flow screen "$raw"');
  }
}

/// Builds the screen list for [Project] — entirely from `config.flow` and `config.fields`.
ResolvedCollectionFlow resolveCollectionFlow(Project project) {
  return _fromDecl(project, project.config.flow);
}

ResolvedCollectionFlow _fromDecl(Project project, CollectionFlowDecl decl) {
  if (decl.steps.length > 1) {
    for (final st in decl.steps) {
      if (_parseScreen(st.screen) == CollectionScreenKind.scrollForm) {
        throw FormatException(
          'flow step "${st.id}": scroll_form is only allowed as the sole step',
        );
      }
    }
  }

  final byId = {for (final f in project.config.fields) f.fieldId: f};
  final totalCams = decl.steps
      .where((st) => _parseScreen(st.screen) == CollectionScreenKind.cameraPose)
      .length;
  var camDone = 0;
  final steps = <ResolvedCollectionStep>[];

  for (final st in decl.steps) {
    final kind = _parseScreen(st.screen);
    switch (kind) {
      case CollectionScreenKind.scrollForm:
        final ids = st.fieldIds;
        final fields = ids == null || ids.isEmpty
            ? (project.config.fields.toList()
              ..sort((a, b) => a.priority.compareTo(b.priority)))
            : [
                for (final id in ids)
                  byId[id] ?? (throw FormatException('flow step "${st.id}": unknown field_id "$id"')),
              ];
        steps.add(
          ResolvedCollectionStep(id: st.id, kind: kind, fields: fields),
        );
      case CollectionScreenKind.form:
        final ids = st.fieldIds;
        if (ids == null || ids.isEmpty) {
          throw FormatException('flow step "${st.id}": form requires field_ids');
        }
        final fields = <ConfigField>[];
        for (final id in ids) {
          final f =
              byId[id] ?? (throw FormatException('flow step "${st.id}": unknown field_id "$id"'));
          const allowed = {'text_input', 'datetime'};
          if (!allowed.contains(f.type)) {
            throw FormatException(
              'flow step "${st.id}": field "$id" has type ${f.type}, allowed: $allowed',
            );
          }
          fields.add(f);
        }
        final hintField = st.cowIdFieldId;
        if (hintField != null && !fields.any((x) => x.fieldId == hintField)) {
          throw FormatException(
            'flow step "${st.id}": cow_id_field_id "$hintField" is not in field_ids',
          );
        }
        steps.add(
          ResolvedCollectionStep(
            id: st.id,
            kind: kind,
            fields: fields,
            cowIdHints: st.cowIdHints == true,
            cowIdFieldId: st.cowIdFieldId,
          ),
        );
      case CollectionScreenKind.instruction:
        final id = st.fieldId;
        if (id == null || id.isEmpty) {
          throw FormatException('flow step "${st.id}": instruction requires field_id');
        }
        final f =
            byId[id] ?? (throw FormatException('flow step "${st.id}": unknown field_id "$id"'));
        if (f.type != 'instruction') {
          throw FormatException(
            'flow step "${st.id}": field "$id" must have type instruction, got ${f.type}',
          );
        }
        steps.add(
          ResolvedCollectionStep(id: st.id, kind: kind, fields: [f]),
        );
      case CollectionScreenKind.cameraPose:
        final id = st.fieldId;
        if (id == null || id.isEmpty) {
          throw FormatException('flow step "${st.id}": camera_pose requires field_id');
        }
        final f =
            byId[id] ?? (throw FormatException('flow step "${st.id}": unknown field_id "$id"'));
        if (f.type != 'camera_photo') {
          throw FormatException(
            'flow step "${st.id}": field "$id" must have type camera_photo, got ${f.type}',
          );
        }
        camDone++;
        steps.add(
          ResolvedCollectionStep(
            id: st.id,
            kind: kind,
            fields: [f],
            poseIndex1Based: camDone,
            poseTotal: totalCams,
          ),
        );
      case CollectionScreenKind.review:
        steps.add(
          ResolvedCollectionStep(id: st.id, kind: kind, fields: const []),
        );
    }
  }
  final hasCamera = decl.steps.any(
    (st) => _parseScreen(st.screen) == CollectionScreenKind.cameraPose,
  );
  final hasReview = decl.steps.any(
    (st) => _parseScreen(st.screen) == CollectionScreenKind.review,
  );
  if (hasCamera && !hasReview) {
    steps.add(
      const ResolvedCollectionStep(
        id: 'review',
        kind: CollectionScreenKind.review,
        fields: <ConfigField>[],
      ),
    );
  }
  return ResolvedCollectionFlow(steps: steps);
}
