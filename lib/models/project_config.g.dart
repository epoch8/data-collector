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
  multiple: json['multiple'] as bool?,
);

Map<String, dynamic> _$ConfigFieldToJson(ConfigField instance) =>
    <String, dynamic>{
      'field_id': instance.fieldId,
      'priority': instance.priority,
      'type': instance.type,
      'title': instance.title,
      'instructions': instance.instructions,
      'validation': instance.validation,
      'multiple': instance.multiple,
    };

CollectionFlowStepDecl _$CollectionFlowStepDeclFromJson(
  Map<String, dynamic> json,
) => CollectionFlowStepDecl(
  id: json['id'] as String,
  screen: json['screen'] as String,
  fieldIds: (json['field_ids'] as List<dynamic>?)
      ?.map((e) => e as String)
      .toList(),
  fieldId: json['field_id'] as String?,
  cowIdHints: json['cow_id_hints'] as bool?,
  cowIdFieldId: json['cow_id_field_id'] as String?,
);

Map<String, dynamic> _$CollectionFlowStepDeclToJson(
  CollectionFlowStepDecl instance,
) => <String, dynamic>{
  'id': instance.id,
  'screen': instance.screen,
  'field_ids': instance.fieldIds,
  'field_id': instance.fieldId,
  'cow_id_hints': instance.cowIdHints,
  'cow_id_field_id': instance.cowIdFieldId,
};

CollectionFlowDecl _$CollectionFlowDeclFromJson(Map<String, dynamic> json) =>
    CollectionFlowDecl(
      steps: (json['steps'] as List<dynamic>)
          .map(
            (e) => CollectionFlowStepDecl.fromJson(e as Map<String, dynamic>),
          )
          .toList(),
    );

Map<String, dynamic> _$CollectionFlowDeclToJson(CollectionFlowDecl instance) =>
    <String, dynamic>{'steps': instance.steps.map((e) => e.toJson()).toList()};

ProjectConfig _$ProjectConfigFromJson(Map<String, dynamic> json) =>
    ProjectConfig(
      fields: (json['fields'] as List<dynamic>)
          .map((e) => ConfigField.fromJson(e as Map<String, dynamic>))
          .toList(),
      flow: CollectionFlowDecl.fromJson(json['flow'] as Map<String, dynamic>),
      ui: json['ui'] as Map<String, dynamic>?,
    );

Map<String, dynamic> _$ProjectConfigToJson(ProjectConfig instance) =>
    <String, dynamic>{
      'fields': instance.fields.map((e) => e.toJson()).toList(),
      'flow': instance.flow.toJson(),
      'ui': instance.ui,
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
