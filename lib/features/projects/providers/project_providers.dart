import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../../../models/project_config.dart';

part 'project_providers.g.dart';

@riverpod
List<Project> mockProjects(Ref ref) {
  return [
    Project(
      id: 'korovas-2026',
      name: 'Korovas',
      version: '1.0',
      config: ProjectConfig(
        fields: [
          ConfigField(
            fieldId: 'cow_identifier',
            priority: 10,
            type: 'text_input',
            title: 'Cow Identifier',
            instructions: 'Enter the unique string identifier for the cow.',
            validation: {'required': true},
          ),
          ConfigField(
            fieldId: 'front_photo',
            priority: 20,
            type: 'camera_photo',
            title: 'Front Photo',
            instructions:
                'Take a clear photo of the front of the cow. Ensure the entire cow is visible.',
            validation: {'required': true},
          ),
          ConfigField(
            fieldId: 'side_photos',
            priority: 40,
            type: 'camera_photo',
            title: 'Additional Photos',
            instructions: 'Take multiple photos covering all angles.',
            validation: {'min_items': 2},
            multiple: true,
          ),
        ],
      ),
    ),
  ];
}
