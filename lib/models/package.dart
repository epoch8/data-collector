import 'package:json_annotation/json_annotation.dart';

part 'package.g.dart';

@JsonSerializable(explicitToJson: true)
class CollectedPackage {
  final String packageId;
  final String projectId;
  final String status;
  final DateTime createdAt;
  final Map<String, dynamic> data;

  CollectedPackage({
    required this.packageId,
    required this.projectId,
    required this.status,
    required this.createdAt,
    required this.data,
  });

  factory CollectedPackage.fromJson(Map<String, dynamic> json) => _$CollectedPackageFromJson(json);
  Map<String, dynamic> toJson() => _$CollectedPackageToJson(this);
}
