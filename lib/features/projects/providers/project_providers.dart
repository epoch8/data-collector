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
            fieldId: 'annotated_photos',
            priority: 40,
            type: 'collection',
            title: 'Annotated Photos',
            instructions: 'Take photos of the cow and add a comment for each.',
            validation: {'min_items': 1},
            multiple: true,
            subFields: [
              ConfigField(
                fieldId: 'image',
                priority: 1,
                type: 'camera_photo',
                title: 'Photo',
                instructions: '',
              ),
              ConfigField(
                fieldId: 'comment',
                priority: 2,
                type: 'text_input',
                title: 'Comment',
                instructions: '',
              ),
            ],
          ),
        ],
      ),
    ),
  ];
}
