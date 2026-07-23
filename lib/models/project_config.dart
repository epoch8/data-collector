import 'package:json_annotation/json_annotation.dart';

part 'project_config.g.dart';

/// Matches [specs/02-data-models-schema.md](specs/02-data-models-schema.md).
/// `type` values used by the app: `text_input`, `datetime`, `instruction`,
/// `camera_photo`, `single_choice`.
@JsonSerializable(explicitToJson: true)
class ConfigFieldOption {
  final String value;
  final String label;

  ConfigFieldOption({required this.value, required this.label});

  factory ConfigFieldOption.fromJson(Map<String, dynamic> json) =>
      _$ConfigFieldOptionFromJson(json);
  Map<String, dynamic> toJson() => _$ConfigFieldOptionToJson(this);
}

/// Matches [specs/02-data-models-schema.md](specs/02-data-models-schema.md).
@JsonSerializable(explicitToJson: true)
class ConfigField {
  @JsonKey(name: 'field_id')
  final String fieldId;

  /// Устарело: порядок полей задаётся порядком в `flow.steps[].field_ids` и порядком строк в редакторе.
  @JsonKey(defaultValue: 0)
  final int priority;
  final String type;
  final String title;
  final String instructions;
  final Map<String, dynamic>? validation;
  final bool? multiple;

  /// Варианты для `single_choice`. В JSON: список `{value, label}` или строк.
  @JsonKey(fromJson: _optionsFromJson, toJson: _optionsToJson)
  final List<ConfigFieldOption>? options;

  ConfigField({
    required this.fieldId,
    this.priority = 0,
    required this.type,
    required this.title,
    required this.instructions,
    this.validation,
    this.multiple,
    this.options,
  });

  factory ConfigField.fromJson(Map<String, dynamic> json) =>
      _$ConfigFieldFromJson(json);
  Map<String, dynamic> toJson() => _$ConfigFieldToJson(this);

  /// Подпись выбранного значения `single_choice` (или само value, если не найдено).
  String? labelForChoice(String? value) {
    if (value == null || value.isEmpty) return value;
    for (final o in options ?? const <ConfigFieldOption>[]) {
      if (o.value == value) return o.label;
    }
    return value;
  }
}

List<ConfigFieldOption>? _optionsFromJson(dynamic raw) {
  if (raw == null) return null;
  if (raw is! List) return null;
  final out = <ConfigFieldOption>[];
  for (final item in raw) {
    if (item is String) {
      final s = item.trim();
      if (s.isEmpty) continue;
      out.add(ConfigFieldOption(value: s, label: s));
    } else if (item is Map) {
      final value = (item['value'] ?? item['label'] ?? '').toString().trim();
      final label = (item['label'] ?? item['value'] ?? '').toString().trim();
      if (value.isEmpty) continue;
      out.add(
        ConfigFieldOption(value: value, label: label.isEmpty ? value : label),
      );
    }
  }
  return out.isEmpty ? null : out;
}

List<Map<String, String>>? _optionsToJson(List<ConfigFieldOption>? options) {
  if (options == null || options.isEmpty) return null;
  return [
    for (final o in options) {'value': o.value, 'label': o.label},
  ];
}

/// One screen in `config.flow.steps` — drives routing and widgets, not field definitions.
@JsonSerializable(explicitToJson: true)
class CollectionFlowStepDecl {
  final String id;
  final String screen;
  @JsonKey(name: 'field_ids')
  final List<String>? fieldIds;
  @JsonKey(name: 'field_id')
  final String? fieldId;

  /// When true on a `form` step: suggest values from previous packages (see [cowIdFieldId]).
  @JsonKey(name: 'cow_id_hints')
  final bool? cowIdHints;

  /// `field_id` of the text field used for cow/subject matching; defaults to first `text_input` in the step.
  @JsonKey(name: 'cow_id_field_id')
  final String? cowIdFieldId;

  /// Подпись шага на экране проверки (вместо латинского `id`).
  @JsonKey(name: 'form_title')
  final String? formTitle;

  CollectionFlowStepDecl({
    required this.id,
    required this.screen,
    this.fieldIds,
    this.fieldId,
    this.cowIdHints,
    this.cowIdFieldId,
    this.formTitle,
  });

  factory CollectionFlowStepDecl.fromJson(Map<String, dynamic> json) =>
      _$CollectionFlowStepDeclFromJson(json);
  Map<String, dynamic> toJson() => _$CollectionFlowStepDeclToJson(this);
}

@JsonSerializable(explicitToJson: true)
class CollectionFlowDecl {
  final List<CollectionFlowStepDecl> steps;

  CollectionFlowDecl({required this.steps});

  factory CollectionFlowDecl.fromJson(Map<String, dynamic> json) =>
      _$CollectionFlowDeclFromJson(json);
  Map<String, dynamic> toJson() => _$CollectionFlowDeclToJson(this);
}

@JsonSerializable(explicitToJson: true)
class ProjectConfig {
  final List<ConfigField> fields;

  /// Required: defines every screen (scroll or multi-step). The app does not infer flows from priorities.
  final CollectionFlowDecl flow;

  /// Optional nested strings / templates for flow UI and shooting guide (`ProjectUi`).
  final Map<String, dynamic>? ui;

  ProjectConfig({required this.fields, required this.flow, this.ui});

  factory ProjectConfig.fromJson(Map<String, dynamic> json) =>
      _$ProjectConfigFromJson(json);
  Map<String, dynamic> toJson() => _$ProjectConfigToJson(this);
}

@JsonSerializable(explicitToJson: true)
class Project {
  final String id;
  final String name;
  final String version;
  final ProjectConfig config;

  Project({
    required this.id,
    required this.name,
    required this.version,
    required this.config,
  });

  factory Project.fromJson(Map<String, dynamic> json) =>
      _$ProjectFromJson(json);
  Map<String, dynamic> toJson() => _$ProjectToJson(this);
}

bool configFieldRequired(ConfigField f) => f.validation?['required'] == true;
