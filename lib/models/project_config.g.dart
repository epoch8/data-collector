// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'project_config.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

ConfigField _$ConfigFieldFromJson(Map<String, dynamic> json) => ConfigField(
  fieldId: json['field_id'] as String,
  priority: (json['priority'] as num).toInt(),
  type: json['type'] as String,
  title: json['title'] as String,
  instructions: json['instructions'] as String,
  validation: json['validation'] as Map<String, dynamic>?,
  options: (json['options'] as List<dynamic>?)
      ?.map((e) => e as String)
      .toList(),
  multiple: json['multiple'] as bool?,
  subFields: (json['sub_fields'] as List<dynamic>?)
      ?.map((e) => ConfigField.fromJson(e as Map<String, dynamic>))
      .toList(),
);

Map<String, dynamic> _$ConfigFieldToJson(ConfigField instance) =>
    <String, dynamic>{
      'field_id': instance.fieldId,
      'priority': instance.priority,
      'type': instance.type,
      'title': instance.title,
      'instructions': instance.instructions,
      'validation': instance.validation,
      'options': instance.options,
      'multiple': instance.multiple,
      'sub_fields': instance.subFields?.map((e) => e.toJson()).toList(),
    };

ProjectConfig _$ProjectConfigFromJson(Map<String, dynamic> json) =>
    ProjectConfig(
      fields: (json['fields'] as List<dynamic>)
          .map((e) => ConfigField.fromJson(e as Map<String, dynamic>))
          .toList(),
      collectionFlow: json['collection_flow'] as String?,
    );

Map<String, dynamic> _$ProjectConfigToJson(ProjectConfig instance) =>
    <String, dynamic>{
      'collection_flow': instance.collectionFlow,
      'fields': instance.fields.map((e) => e.toJson()).toList(),
    };

Project _$ProjectFromJson(Map<String, dynamic> json) => Project(
  id: json['id'] as String,
  name: json['name'] as String,
  version: json['version'] as String,
  config: ProjectConfig.fromJson(json['config'] as Map<String, dynamic>),
);

Map<String, dynamic> _$ProjectToJson(Project instance) => <String, dynamic>{
  'id': instance.id,
  'name': instance.name,
  'version': instance.version,
  'config': instance.config.toJson(),
};
