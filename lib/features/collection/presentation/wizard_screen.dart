import 'dart:io';
import 'package:image_picker/image_picker.dart';
import 'package:data_collector/theme/epoch8_theme.dart';
import 'package:data_collector/features/projects/providers/project_providers.dart';
import 'package:data_collector/models/project_config.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:data_collector/features/collection/logic/submit_local_package.dart';

import '../providers/wizard_state_provider.dart';

/// Один длинный экран: все поля из [Project.config] (spec 02), порядок по `priority`.
class CollectionWizardScreen extends ConsumerWidget {
  const CollectionWizardScreen({super.key, required this.projectId});

  final String projectId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(projectsProvider);
    return async.when(
      data: (projects) {
        late Project project;
        try {
          project = projects.firstWhere((p) => p.id == projectId);
        } catch (_) {
          return Scaffold(
            backgroundColor: Epoch8Theme.bgDeep,
            appBar: AppBar(title: const Text('Проект')),
            body: const Center(child: Text('Проект не найден.')),
          );
        }
        return _CollectionWizardLoaded(projectId: projectId, project: project);
      },
      loading: () => const Scaffold(
        backgroundColor: Epoch8Theme.bgDeep,
        body: Center(child: CircularProgressIndicator()),
      ),
      error: (e, _) => Scaffold(
        backgroundColor: Epoch8Theme.bgDeep,
        body: Center(child: Text('Ошибка: $e')),
      ),
    );
  }
}

class _CollectionWizardLoaded extends ConsumerStatefulWidget {
  const _CollectionWizardLoaded({required this.projectId, required this.project});

  final String projectId;
  final Project project;

  @override
  ConsumerState<_CollectionWizardLoaded> createState() => _CollectionWizardLoadedState();
}

class _CollectionWizardLoadedState extends ConsumerState<_CollectionWizardLoaded> {
  late final List<ConfigField> _fields;
  late final List<FocusNode> _focusNodes;
  final Set<String> _editingItemIds = {};

  @override
  void initState() {
    super.initState();
    _fields = widget.project.config.fields.toList()..sort((a, b) => a.priority.compareTo(b.priority));
    
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
    final project = widget.project;
    final answers = ref.watch(wizardStateProvider(widget.projectId));

    return Scaffold(
      backgroundColor: Epoch8Theme.bgDeep,
      appBar: AppBar(
        title: Text(project.name, maxLines: 1, overflow: TextOverflow.ellipsis),
      ),
      body: Container(
        decoration: Epoch8Theme.screenGradient(),
        child: SingleChildScrollView(
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
      ),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: FilledButton(
            style: FilledButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 16),
            ),
            onPressed: () async {
              await submitLocalPackage(
                ref: ref,
                context: context,
                projectId: widget.projectId,
                answers: answers,
              );
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
        color: hasFocus
            ? Epoch8Theme.accent.withValues(alpha: 0.08)
            : Epoch8Theme.card.withValues(alpha: 0.35),
        border: Border.all(
          color: hasFocus ? Epoch8Theme.accent : Epoch8Theme.border,
          width: hasFocus ? 2 : 1,
        ),
        borderRadius: BorderRadius.circular(16),
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
                  color: Epoch8Theme.bgElevated,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Epoch8Theme.border, width: 1),
                ),
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      FilledButton.icon(
                        icon: const Icon(Icons.camera_alt_outlined),
                        onPressed: () async {
                          final picker = ImagePicker();
                          final XFile? photo = await picker.pickImage(
                            source: (Platform.isAndroid || Platform.isIOS) ? ImageSource.camera : ImageSource.gallery,
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
                          Text(
                            '${(answers[field.fieldId] as List).length} Photos Captured',
                            style: const TextStyle(color: Epoch8Theme.accent, fontWeight: FontWeight.bold),
                          ),
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
                                        decoration: const BoxDecoration(color: Epoch8Theme.danger, shape: BoxShape.circle),
                                        child: const Icon(Icons.close, size: 16, color: Epoch8Theme.bgDeep),
                                      ),
                                    ),
                                  )
                                ],
                              );
                            }).toList(),
                          )
                        ] else ...[
                          const Text('Photo Saved ✓', style: TextStyle(color: Epoch8Theme.accent, fontWeight: FontWeight.bold)),
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
                                    decoration: const BoxDecoration(color: Epoch8Theme.danger, shape: BoxShape.circle),
                                    child: const Icon(Icons.close, size: 16, color: Epoch8Theme.bgDeep),
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
          else if (field.type == 'collection')
            Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (answers[field.fieldId] != null) ...[
                  ...((answers[field.fieldId] as List).map((item) {
                    final itemMap = item as Map<String, dynamic>;
                    final itemId = itemMap['item_id'] as String;
                    
                    if (_editingItemIds.contains(itemId)) {
                       return Padding(
                         padding: const EdgeInsets.only(bottom: 8.0, top: 4.0),
                         child: InlineCollectionForm(
                           key: ValueKey('edit_$itemId'),
                           field: field,
                           initialDraft: itemMap,
                           onSave: (newItem) {
                             final currentList = List<Map<String, dynamic>>.from(answers[field.fieldId] as List);
                             final existingIndex = currentList.indexWhere((e) => e['item_id'] == itemId);
                             if (existingIndex >= 0) {
                               currentList[existingIndex] = newItem;
                               ref.read(wizardStateProvider(widget.projectId).notifier).updateField(field.fieldId, currentList);
                             }
                             setState(() => _editingItemIds.remove(itemId));
                           },
                           onCancel: () {
                             setState(() => _editingItemIds.remove(itemId));
                           }
                         )
                       );
                    }

                    return Card(
                      key: ValueKey(itemId),
                      child: ListTile(
                        onTap: () {
                           setState(() => _editingItemIds.add(itemId));
                        },
                        leading: itemMap['image'] != null ? Container(
                          width: 40, height: 40,
                          decoration: BoxDecoration(borderRadius: BorderRadius.circular(4)),
                          clipBehavior: Clip.hardEdge,
                          child: Image.file(File(itemMap['image'] as String), fit: BoxFit.cover)
                        ) : null,
                        title: Text(itemMap['comment']?.toString() ?? 'No Comment'),
                        subtitle: Text(DateTime.fromMillisecondsSinceEpoch(itemMap['timestamp'] as int).toString().split('.')[0]),
                        trailing: IconButton(
                          icon: const Icon(Icons.delete_outline, color: Epoch8Theme.danger),
                          onPressed: () {
                             final currentList = List<Map<String, dynamic>>.from(answers[field.fieldId] as List);
                             currentList.removeWhere((e) => e['item_id'] == itemId);
                             if (currentList.isEmpty) {
                               ref.read(wizardStateProvider(widget.projectId).notifier).updateField(field.fieldId, null);
                             } else {
                               ref.read(wizardStateProvider(widget.projectId).notifier).updateField(field.fieldId, currentList);
                             }
                          },
                        ),
                      ),
                    );
                  }).toList()),
                  const SizedBox(height: 16),
                ],
                const Divider(),
                InlineCollectionForm(
                  key: ValueKey('new_${field.fieldId}'),
                  field: field,
                  onSave: (newItem) {
                    _focusNodes[index].requestFocus();
                    final currentList = List<Map<String, dynamic>>.from(answers[field.fieldId] as List? ?? []);
                    currentList.add(newItem);
                    ref.read(wizardStateProvider(widget.projectId).notifier).updateField(field.fieldId, currentList);
                  },
                )
              ]
            )
          else
            Text('Unknown config field type: ${field.type}', style: const TextStyle(color: Epoch8Theme.danger)),
          
          if (hasFocus)
            Padding(
              padding: const EdgeInsets.only(top: 24.0),
              child: Align(
                alignment: Alignment.centerRight,
                child: FilledButton.icon(
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

class InlineCollectionForm extends StatefulWidget {
  final ConfigField field;
  final Map<String, dynamic>? initialDraft;
  final ValueChanged<Map<String, dynamic>> onSave;
  final VoidCallback? onCancel;

  const InlineCollectionForm({
    super.key, 
    required this.field, 
    this.initialDraft,
    required this.onSave,
    this.onCancel
  });

  @override
  State<InlineCollectionForm> createState() => InlineCollectionFormState();
}

class InlineCollectionFormState extends State<InlineCollectionForm> {
  late Map<String, dynamic> _draft;
  final _formKey = GlobalKey<FormState>();

  @override
  void initState() {
    super.initState();
    _draft = widget.initialDraft != null ? Map<String, dynamic>.from(widget.initialDraft!) : {};
  }

  @override
  Widget build(BuildContext context) {
    final itemFields = widget.field.subFields ?? [];

    return Form(
      key: _formKey,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Epoch8Theme.bgElevated,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Epoch8Theme.accent.withValues(alpha: 0.25), width: 1),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              _draft.containsKey('item_id') ? 'Edit Item' : 'Draft New Item',
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Epoch8Theme.accent),
            ),
            const SizedBox(height: 16),
            ...itemFields.map((subF) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(subF.title, style: const TextStyle(fontWeight: FontWeight.w600)),
                    const SizedBox(height: 8),
                    if (subF.type == 'text_input')
                      TextFormField(
                        initialValue: _draft[subF.fieldId] as String?,
                        onChanged: (val) => _draft[subF.fieldId] = val,
                        key: ValueKey('${_draft['item_id'] ?? 'new'}_${subF.fieldId}'),
                        decoration: InputDecoration(
                          border: const OutlineInputBorder(),
                          isDense: true,
                          fillColor: Epoch8Theme.card,
                          filled: true,
                        ),
                      )
                    else if (subF.type == 'camera_photo')
                      Row(
                        children: [
                          FilledButton.icon(
                            icon: const Icon(Icons.camera_alt_outlined),
                            onPressed: () async {
                              final picker = ImagePicker();
                              final source = (Platform.isAndroid || Platform.isIOS) ? ImageSource.camera : ImageSource.gallery;
                              final XFile? photo = await picker.pickImage(
                                source: source,
                                preferredCameraDevice: CameraDevice.rear,
                              );
                              if (photo != null) {
                                setState(() => _draft[subF.fieldId] = photo.path);
                              }
                            },
                            label: Text(_draft[subF.fieldId] != null ? 'Retake Photo' : 'Capture Photo'),
                          ),
                          if (_draft[subF.fieldId] != null) ...[
                            const SizedBox(width: 16),
                            Container(
                              width: 40, height: 40,
                              decoration: BoxDecoration(borderRadius: BorderRadius.circular(8)),
                              clipBehavior: Clip.hardEdge,
                              child: Image.file(File(_draft[subF.fieldId] as String), fit: BoxFit.cover)
                            ),
                          ]
                        ]
                      )
                  ]
                )
              );
            }).toList(),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                if (widget.onCancel != null)
                  TextButton(
                    onPressed: widget.onCancel,
                    child: const Text('Cancel'),
                  ),
                const SizedBox(width: 8),
                FilledButton.icon(
                  onPressed: () {
                    _draft['item_id'] ??= 'item_${DateTime.now().millisecondsSinceEpoch}';
                    _draft['timestamp'] ??= DateTime.now().millisecondsSinceEpoch;
                    widget.onSave({..._draft});
                    
                    if (widget.initialDraft == null) {
                      // Only clear draft if this is a "new item" form
                      setState(() {
                        _draft = {};
                        _formKey.currentState?.reset();
                      });
                    }
                  },
                  icon: const Icon(Icons.check),
                  label: Text(_draft.containsKey('item_id') ? 'Save Changes' : 'Save Item'),
                )
              ],
            )
          ],
        )
      )
    );
  }
}

