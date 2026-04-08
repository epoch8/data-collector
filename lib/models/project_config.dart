import 'package:json_annotation/json_annotation.dart';

part 'project_config.g.dart';

@JsonSerializable(explicitToJson: true)
class ConfigField {
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

@JsonSerializable(explicitToJson: true)
class ProjectConfig {
  final List<ConfigField> fields;

  ProjectConfig({required this.fields});

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
