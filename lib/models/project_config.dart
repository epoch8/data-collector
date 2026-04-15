import 'package:json_annotation/json_annotation.dart';

part 'project_config.g.dart';

/// Matches [specs/02-data-models-schema.md](specs/02-data-models-schema.md).\
/// Extended `type` values understood by the app: `datetime`, `instruction`, `camera_photo`.
@JsonSerializable(explicitToJson: true)
class ConfigField {
  @JsonKey(name: 'field_id')
  final String fieldId;
  final int priority;
  final String type;
  final String title;
  final String instructions;
  final Map<String, dynamic>? validation;
  final List<String>? options;
  final bool? multiple;
  @JsonKey(name: 'sub_fields')
  final List<ConfigField>? subFields;

  ConfigField({
    required this.fieldId,
    required this.priority,
    required this.type,
    required this.title,
    required this.instructions,
    this.validation,
    this.options,
    this.multiple,
    this.subFields,
  });

  factory ConfigField.fromJson(Map<String, dynamic> json) => _$ConfigFieldFromJson(json);
  Map<String, dynamic> toJson() => _$ConfigFieldToJson(this);
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

  CollectionFlowStepDecl({
    required this.id,
    required this.screen,
    this.fieldIds,
    this.fieldId,
    this.cowIdHints,
    this.cowIdFieldId,
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

  ProjectConfig({
    required this.fields,
    required this.flow,
    this.ui,
  });

  factory ProjectConfig.fromJson(Map<String, dynamic> json) => _$ProjectConfigFromJson(json);
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

  factory Project.fromJson(Map<String, dynamic> json) => _$ProjectFromJson(json);
  Map<String, dynamic> toJson() => _$ProjectToJson(this);
}

bool configFieldRequired(ConfigField f) => f.validation?['required'] == true;
