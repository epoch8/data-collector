import 'package:data_collector/models/project_config.dart';

/// Priority bands for `collection_flow: korovas` (see specs/02-data-models-schema.md).
extension KorovasFlowFields on Project {
  static const int _formMaxPriority = 99;
  static const int _briefingMin = 100;
  static const int _briefingMax = 199;
  static const int _cameraMin = 200;
  static const int _cameraMax = 399;

  List<ConfigField> get korovasFormFields {
    final list = config.fields
        .where((f) => f.priority <= _formMaxPriority && (f.type == 'text_input' || f.type == 'datetime'))
        .toList()
      ..sort((a, b) => a.priority.compareTo(b.priority));
    return list;
  }

  bool get korovasHasBriefing =>
      config.fields.any((f) => f.type == 'instruction' && f.priority >= _briefingMin && f.priority <= _briefingMax);

  List<ConfigField> get korovasCameraFields {
    final list = config.fields
        .where((f) => f.type == 'camera_photo' && f.priority >= _cameraMin && f.priority <= _cameraMax)
        .toList()
      ..sort((a, b) => a.priority.compareTo(b.priority));
    return list;
  }

  int get korovasPoseStepStart => korovasHasBriefing ? 2 : 1;

  int get korovasReviewStepIndex => korovasPoseStepStart + korovasCameraFields.length;
}

bool configFieldRequired(ConfigField f) => f.validation?['required'] == true;
