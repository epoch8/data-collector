// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'package.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

CollectedPackage _$CollectedPackageFromJson(Map<String, dynamic> json) =>
    CollectedPackage(
      packageId: json['packageId'] as String,
      projectId: json['projectId'] as String,
      status: json['status'] as String,
      createdAt: DateTime.parse(json['createdAt'] as String),
      data: json['data'] as Map<String, dynamic>,
    );

Map<String, dynamic> _$CollectedPackageToJson(CollectedPackage instance) =>
    <String, dynamic>{
      'packageId': instance.packageId,
      'projectId': instance.projectId,
      'status': instance.status,
      'createdAt': instance.createdAt.toIso8601String(),
      'data': instance.data,
    };
