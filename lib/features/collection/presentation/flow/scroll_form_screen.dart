import 'dart:io';
import 'package:image_picker/image_picker.dart';
import 'package:data_collector/theme/epoch8_theme.dart';
import 'package:data_collector/theme/epoch8_loader.dart';
import 'package:data_collector/features/projects/providers/project_providers.dart';
import 'package:data_collector/models/project_config.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:data_collector/features/collection/logic/submit_local_package.dart';
import 'package:data_collector/l10n/app_localizations.dart';
import 'package:data_collector/l10n/locale_controller.dart';

import 'package:data_collector/features/collection/providers/wizard_state_provider.dart';

/// Устаревший экран: все поля из [Project.config.fields] в порядке объявления в JSON.
class ScrollFormCollectionScreen extends ConsumerWidget {
  const ScrollFormCollectionScreen({super.key, required this.projectId});

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
          final loc = AppLocalizations.of(context);
          return Scaffold(
            backgroundColor: Epoch8Theme.bgDeep,
            appBar: AppBar(title: Text(loc.project)),
            body: Center(child: Text(loc.projectNotFoundShortDot)),
          );
        }
        return _ScrollFormLoaded(projectId: projectId, project: project);
      },
      loading: () => Scaffold(
        backgroundColor: Epoch8Theme.bgDeep,
        body: Epoch8Loader.center(),
      ),
      error: (e, _) => Scaffold(
        backgroundColor: Epoch8Theme.bgDeep,
        body: Center(child: Text('${AppLocalizations.of(context).errorPrefix}: $e')),
      ),
    );
  }
}

class _ScrollFormLoaded extends ConsumerStatefulWidget {
  const _ScrollFormLoaded({required this.projectId, required this.project});

  final String projectId;
  final Project project;

  @override
  ConsumerState<_ScrollFormLoaded> createState() => _ScrollFormLoadedState();
}

class _ScrollFormLoadedState extends ConsumerState<_ScrollFormLoaded> {
  late final List<ConfigField> _fields;
  late final List<FocusNode> _focusNodes;

  @override
  void initState() {
    super.initState();
    _fields = List<ConfigField>.from(widget.project.config.fields);
    
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
    final loc = AppLocalizations.of(context);
    final project = widget.project;
    final answers = ref.watch(wizardStateProvider(widget.projectId));

    return Scaffold(
      backgroundColor: Epoch8Theme.bgDeep,
      appBar: AppBar(
        title: Text(project.name, maxLines: 1, overflow: TextOverflow.ellipsis),
        actions: [
          IconButton(
            tooltip: loc.languageToggleTooltip,
            onPressed: toggleAppLocale,
            icon: Text(loc.languageCodeLabel, style: const TextStyle(fontWeight: FontWeight.w800)),
          ),
        ],
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
            child: Text(loc.submitPackage, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          ),
        ),
      ),
    );
  }

  Widget _buildFieldContent(ConfigField field, Map<String, dynamic> answers, int index) {
    final loc = AppLocalizations.of(context);
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
                        label: Text(field.multiple == true ? loc.takeAnotherPhoto : loc.capturePhoto),
                      ),
                      if (answers[field.fieldId] != null) ...[
                        const SizedBox(height: 16),
                        if (field.multiple == true) ...[
                          Text(
                            '${(answers[field.fieldId] as List).length} ${loc.photosCaptured}',
                            style: TextStyle(color: Epoch8Theme.accent, fontWeight: FontWeight.bold),
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
                                        decoration: BoxDecoration(color: Epoch8Theme.danger, shape: BoxShape.circle),
                                        child: Icon(Icons.close, size: 16, color: Epoch8Theme.bgDeep),
                                      ),
                                    ),
                                  )
                                ],
                              );
                            }).toList(),
                          )
                        ] else ...[
                          Text('${loc.photoSaved} ✓', style: TextStyle(color: Epoch8Theme.accent, fontWeight: FontWeight.bold)),
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
                                    decoration: BoxDecoration(color: Epoch8Theme.danger, shape: BoxShape.circle),
                                    child: Icon(Icons.close, size: 16, color: Epoch8Theme.bgDeep),
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
            Text(
              '${loc.unsupportedFieldType} ${loc.supportedFieldTypes} (${field.type})',
              style: TextStyle(color: Epoch8Theme.danger),
            ),
          
          if (hasFocus)
            Padding(
              padding: const EdgeInsets.only(top: 24.0),
              child: Align(
                alignment: Alignment.centerRight,
                child: FilledButton.icon(
                  onPressed: () => _focusNext(index),
                  icon: const Icon(Icons.check),
                  label: Text(index == _fields.length - 1 ? loc.finishFocus : loc.saveAndNext),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

