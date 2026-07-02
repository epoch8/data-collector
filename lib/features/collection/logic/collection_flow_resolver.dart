import 'package:data_collector/models/project_config.dart';

/// Declarative screen kinds (`flow.steps[].screen` in project JSON).
enum CollectionScreenKind { form, instruction, cameraPose, review, scrollForm }

class ResolvedCollectionStep {
  const ResolvedCollectionStep({
    required this.id,
    required this.kind,
    required this.fields,
    this.formTitle,
    this.poseIndex1Based,
    this.poseTotal,
    this.cowIdHints = false,
    this.cowIdFieldId,
  });

  final String id;
  final CollectionScreenKind kind;
  final List<ConfigField> fields;

  /// Подпись для review из `flow.steps[].form_title`.
  final String? formTitle;

  /// Шаг `scroll_form`, где нет полей для ввода/съёмки — только текстовые инструкции в конфиге.
  bool get isInstructionOnlyScroll =>
      kind == CollectionScreenKind.scrollForm &&
      fields.isNotEmpty &&
      fields.every((f) => f.type == 'instruction');
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

  int get cameraPoseCount => steps
      .where((s) => s.kind == CollectionScreenKind.scrollForm)
      .expand((s) => s.fields)
      .where((f) => f.type == 'camera_photo')
      .length;

  int? get reviewStepIndex {
    final i = steps.indexWhere((s) => s.kind == CollectionScreenKind.review);
    return i >= 0 ? i : null;
  }

  /// Текстовые/дата поля со всех шагов scroll_form (для review).
  List<ConfigField> get allFormFields => [
    for (final s in steps)
      if (s.kind == CollectionScreenKind.scrollForm)
        for (final f in s.fields)
          if (f.type == 'text_input' || f.type == 'datetime') f,
  ];

  List<ConfigField> get allCameraFields => [
    for (final s in steps)
      if (s.kind == CollectionScreenKind.scrollForm)
        for (final f in s.fields)
          if (f.type == 'camera_photo') f,
  ];

  List<ResolvedCollectionStep> get scrollSteps =>
      steps.where((s) => s.kind == CollectionScreenKind.scrollForm).toList();

  int indexOfFirstForm() =>
      steps.indexWhere((s) => s.kind == CollectionScreenKind.form);

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

  /// Индекс шага [flow.steps], где встречается поле (только scroll_form).
  int indexOfScrollStepContainingField(String fieldId) {
    for (var i = 0; i < steps.length; i++) {
      final s = steps[i];
      if (s.kind != CollectionScreenKind.scrollForm) continue;
      if (s.fields.any((f) => f.fieldId == fieldId)) return i;
    }
    return 0;
  }

  /// Глобальный номер ракурса (1..N) для поля camera_photo по порядку шагов scroll_form.
  int cameraPoseIndex1Based(ConfigField poseField) {
    var n = 0;
    for (final s in steps) {
      if (s.kind != CollectionScreenKind.scrollForm) continue;
      for (final f in s.fields) {
        if (f.type != 'camera_photo') continue;
        n++;
        if (f.fieldId == poseField.fieldId) return n;
      }
    }
    return 1;
  }

  /// Группировать историю по субъекту: несколько camera_photo и поле идентификатора субъекта на scroll-шаге.
  bool get shouldGroupHistoryBySubject {
    if (cameraPoseCount <= 1) return false;
    for (final s in steps) {
      if (s.kind != CollectionScreenKind.scrollForm) continue;
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

/// Собирает экраны только из шагов `scroll_form` и опционально `review`.
ResolvedCollectionFlow resolveCollectionFlow(Project project) {
  return _fromDecl(project, project.config.flow);
}

ResolvedCollectionFlow _fromDecl(Project project, CollectionFlowDecl decl) {
  if (decl.steps.isEmpty) {
    throw FormatException('flow.steps must not be empty');
  }

  for (final st in decl.steps) {
    final k = _parseScreen(st.screen);
    if (k != CollectionScreenKind.scrollForm &&
        k != CollectionScreenKind.review) {
      throw FormatException(
        'flow step "${st.id}": only scroll_form and review are supported (got ${st.screen})',
      );
    }
  }

  final byId = {for (final f in project.config.fields) f.fieldId: f};
  final assigned = <String>{};

  final steps = <ResolvedCollectionStep>[];

  for (final st in decl.steps) {
    final kind = _parseScreen(st.screen);
    switch (kind) {
      case CollectionScreenKind.scrollForm:
        final ids = st.fieldIds;
        if (ids == null || ids.isEmpty) {
          throw FormatException(
            'flow step "${st.id}": scroll_form requires non-empty field_ids',
          );
        }
        final fields = <ConfigField>[];
        for (final id in ids) {
          if (!assigned.add(id)) {
            throw FormatException(
              'flow step "${st.id}": field_id "$id" is already used in another step',
            );
          }
          final f =
              byId[id] ??
              (throw FormatException(
                'flow step "${st.id}": unknown field_id "$id"',
              ));
          fields.add(f);
        }
        steps.add(
          ResolvedCollectionStep(
            id: st.id,
            kind: kind,
            fields: fields,
            formTitle: st.formTitle,
            cowIdHints: st.cowIdHints == true,
            cowIdFieldId: st.cowIdFieldId,
          ),
        );
      case CollectionScreenKind.review:
        steps.add(
          ResolvedCollectionStep(id: st.id, kind: kind, fields: const []),
        );
      case CollectionScreenKind.form:
      case CollectionScreenKind.instruction:
      case CollectionScreenKind.cameraPose:
        break;
    }
  }

  for (final f in project.config.fields) {
    if (!assigned.contains(f.fieldId)) {
      throw FormatException(
        'field "${f.fieldId}" is not listed in any scroll_form step',
      );
    }
  }

  return ResolvedCollectionFlow(steps: steps);
}
