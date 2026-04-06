import 'dart:io';
import 'package:image_picker/image_picker.dart';
import 'package:data_collector/features/projects/providers/project_providers.dart';
import 'package:data_collector/models/project_config.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'dart:convert';
import 'package:data_collector/core/storage/database.dart';
import 'package:data_collector/core/storage/database_provider.dart';

import '../providers/wizard_state_provider.dart';

class CollectionWizardScreen extends ConsumerStatefulWidget {
  final String projectId;

  const CollectionWizardScreen({super.key, required this.projectId});

  @override
  ConsumerState<CollectionWizardScreen> createState() => _CollectionWizardScreenState();
}

class _CollectionWizardScreenState extends ConsumerState<CollectionWizardScreen> {
  late final List<ConfigField> _fields;
  late final List<FocusNode> _focusNodes;

  @override
  void initState() {
    super.initState();
    
    // We grab the project once assuming it's static for this view
    final projects = ref.read(mockProjectsProvider);
    final project = projects.firstWhere(
      (p) => p.id == widget.projectId, 
      orElse: () => throw Exception('Project Not Found'),
    );
    _fields = project.config.fields.toList()..sort((a, b) => a.priority.compareTo(b.priority));
    
    _focusNodes = List.generate(_fields.length, (index) {
      final node = FocusNode();
      node.addListener(() {
        if (mounted) setState(() {});
      });
      return node;
    });

    // Auto-focus the first field
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_focusNodes.isNotEmpty) {
        _focusNodes.first.requestFocus();
      }
    });
  }

  @override
  void dispose() {
    for (var node in _focusNodes) {
      node.dispose();
    }
    super.dispose();
  }

  void _focusNext(int currentIndex) {
    if (currentIndex + 1 < _focusNodes.length) {
      final nextNode = _focusNodes[currentIndex + 1];
      nextNode.requestFocus();
      if (nextNode.context != null) {
        Scrollable.ensureVisible(
          nextNode.context!,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeInOut,
          alignment: 0.3, // Scroll so the item is slightly below the top
        );
      }
    } else {
      FocusScope.of(context).unfocus();
    }
  }

  @override
  Widget build(BuildContext context) {
    final projects = ref.watch(mockProjectsProvider);
    final project = projects.firstWhere((p) => p.id == widget.projectId);
    final answers = ref.watch(wizardStateProvider(widget.projectId));

    return Scaffold(
      appBar: AppBar(
        title: Text('${project.name} - Data Collection'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: _fields.asMap().entries.map((entry) {
            final index = entry.key;
            final field = entry.value;
            return Padding(
              padding: const EdgeInsets.only(bottom: 32.0),
              child: _buildFieldContent(field, answers, index),
            );
          }).toList(),
        ),
      ),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: ElevatedButton(
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 16),
              backgroundColor: Theme.of(context).colorScheme.primaryContainer,
            ),
            onPressed: () async {
              final db = ref.read(databaseProvider);
              final String packageId = 'pkg_${DateTime.now().millisecondsSinceEpoch}';

              await db.into(db.packages).insert(
                PackagesCompanion.insert(
                  id: packageId,
                  projectId: widget.projectId,
                  status: 'completed',
                  createdAt: DateTime.now(),
                  dataJson: jsonEncode(answers),
                )
              );

              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Package securely saved to local database!'),
                  behavior: SnackBarBehavior.floating,
                )
              );

              context.go('/dashboard');
            },
            child: const Text('Submit Package', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          ),
        ),
      ),
    );
  }

  Widget _buildFieldContent(ConfigField field, Map<String, dynamic> answers, int index) {
    final hasFocus = _focusNodes[index].hasFocus;

    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: hasFocus ? Theme.of(context).colorScheme.primary.withOpacity(0.05) : Colors.transparent,
        border: Border.all(
          color: hasFocus ? Theme.of(context).colorScheme.primary : Colors.grey.shade300,
          width: hasFocus ? 2 : 1,
        ),
        borderRadius: BorderRadius.circular(12)
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(field.title, style: Theme.of(context).textTheme.titleLarge?.copyWith(
            fontWeight: hasFocus ? FontWeight.bold : FontWeight.normal
          )),
          const SizedBox(height: 8),
          Text(field.instructions, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 24),
          if (field.type == 'text_input')
            TextFormField(
              initialValue: answers[field.fieldId] as String?,
              focusNode: _focusNodes[index],
              textInputAction: index < _fields.length - 1 ? TextInputAction.next : TextInputAction.done,
              onFieldSubmitted: (_) => _focusNext(index),
              onChanged: (val) => ref.read(wizardStateProvider(widget.projectId).notifier).updateField(field.fieldId, val),
              decoration: const InputDecoration(border: OutlineInputBorder()),
            )
          else if (field.type == 'dropdown')
            DropdownButtonFormField<String>(
              initialValue: answers[field.fieldId] as String?,
              focusNode: _focusNodes[index],
              decoration: const InputDecoration(border: OutlineInputBorder()),
              items: field.options?.map((opt) => DropdownMenuItem(value: opt, child: Text(opt))).toList() ?? [],
              onChanged: (val) {
                ref.read(wizardStateProvider(widget.projectId).notifier).updateField(field.fieldId, val);
                // In dropdowns, selection conceptually finishes the field
                if (hasFocus) _focusNext(index);
              },
            )
          else if (field.type == 'camera_photo')
            Focus(
              focusNode: _focusNodes[index],
              child: Container(
                constraints: const BoxConstraints(minHeight: 200),
                padding: const EdgeInsets.symmetric(vertical: 24),
                decoration: BoxDecoration(
                  color: Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.grey.shade400, width: 1),
                ),
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      ElevatedButton.icon(
                        icon: const Icon(Icons.camera_alt),
                        onPressed: () async {
                          final picker = ImagePicker();
                          final XFile? photo = await picker.pickImage(
                            source: ImageSource.camera,
                            imageQuality: 85,
                            preferredCameraDevice: CameraDevice.rear,
                          );
                          if (photo == null) return;
                          if (field.multiple == true) {
                            final currentPhotos = List<String>.from(answers[field.fieldId] as List? ?? []);
                            currentPhotos.add(photo.path);
                            ref.read(wizardStateProvider(widget.projectId).notifier).updateField(field.fieldId, currentPhotos);
                          } else {
                            ref.read(wizardStateProvider(widget.projectId).notifier).updateField(field.fieldId, photo.path);
                          }
                          _focusNodes[index].requestFocus();
                        },
                        label: Text(field.multiple == true ? 'Take Another Photo' : 'Capture Photo'),
                      ),
                      if (answers[field.fieldId] != null) ...[
                        const SizedBox(height: 16),
                        if (field.multiple == true) ...[
                          Text('${(answers[field.fieldId] as List).length} Photos Captured', style: const TextStyle(color: Colors.green, fontWeight: FontWeight.bold)),
                          const SizedBox(height: 8),
                          Wrap(
                            spacing: 4,
                            runSpacing: 8,
                            children: (answers[field.fieldId] as List).asMap().entries.map((item) {
                              final pathIndex = item.key;
                              return Stack(
                                children: [
                                  Container(
                                    width: 60, height: 60,
                                    margin: const EdgeInsets.only(top: 8, right: 8),
                                    decoration: BoxDecoration(borderRadius: BorderRadius.circular(8)),
                                    child: ClipRRect(
                                      borderRadius: BorderRadius.circular(8),
                                      child: Image.file(File(item.value as String), width: 60, height: 60, fit: BoxFit.cover),
                                    ),
                                  ),
                                  Positioned(
                                    top: 0, right: 0,
                                    child: InkWell(
                                      onTap: () {
                                        final currentPhotos = List<String>.from(answers[field.fieldId] as List);
                                        currentPhotos.removeAt(pathIndex);
                                        if (currentPhotos.isEmpty) {
                                          ref.read(wizardStateProvider(widget.projectId).notifier).updateField(field.fieldId, null);
                                        } else {
                                          ref.read(wizardStateProvider(widget.projectId).notifier).updateField(field.fieldId, currentPhotos);
                                        }
                                        _focusNodes[index].requestFocus();
                                      },
                                      child: Container(
                                        padding: const EdgeInsets.all(2),
                                        decoration: const BoxDecoration(color: Colors.red, shape: BoxShape.circle),
                                        child: const Icon(Icons.close, size: 16, color: Colors.white),
                                      ),
                                    ),
                                  )
                                ],
                              );
                            }).toList(),
                          )
                        ] else ...[
                          const Text('Photo Saved ✓', style: TextStyle(color: Colors.green, fontWeight: FontWeight.bold)),
                          const SizedBox(height: 8),
                          Stack(
                            children: [
                              Container(
                                width: 60, height: 60,
                                margin: const EdgeInsets.only(top: 8, right: 8),
                                decoration: BoxDecoration(borderRadius: BorderRadius.circular(8)),
                                child: ClipRRect(
                                  borderRadius: BorderRadius.circular(8),
                                  child: Image.file(File(answers[field.fieldId] as String), width: 60, height: 60, fit: BoxFit.cover),
                                ),
                              ),
                              Positioned(
                                top: 0, right: 0,
                                child: InkWell(
                                  onTap: () {
                                    ref.read(wizardStateProvider(widget.projectId).notifier).updateField(field.fieldId, null);
                                    _focusNodes[index].requestFocus();
                                  },
                                  child: Container(
                                    padding: const EdgeInsets.all(2),
                                    decoration: const BoxDecoration(color: Colors.red, shape: BoxShape.circle),
                                    child: const Icon(Icons.close, size: 16, color: Colors.white),
                                  ),
                                ),
                              )
                            ],
                          )
                        ]
                      ]
                    ],
                  ),
                ),
              ),
            )
          else
            Text('Unknown config field type: ${field.type}', style: const TextStyle(color: Colors.red)),
          
          if (hasFocus)
            Padding(
              padding: const EdgeInsets.only(top: 24.0),
              child: Align(
                alignment: Alignment.centerRight,
                child: ElevatedButton.icon(
                  onPressed: () => _focusNext(index),
                  icon: const Icon(Icons.check),
                  label: Text(index == _fields.length - 1 ? 'Finish Focus' : 'Save & Next'),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
