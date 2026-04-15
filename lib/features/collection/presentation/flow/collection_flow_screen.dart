import 'dart:convert';
import 'dart:io';

import 'package:data_collector/core/device/camera_metadata_collector.dart';
import 'package:data_collector/core/quality/image_quality_analyzer.dart';
import 'package:data_collector/core/storage/database_provider.dart';
import 'package:data_collector/features/collection/logic/collection_flow_resolver.dart';
import 'package:data_collector/features/collection/logic/package_payload_codec.dart';
import 'package:data_collector/features/collection/logic/submit_local_package.dart';
import 'package:data_collector/features/collection/presentation/flow/package_payload_keys.dart';
import 'package:data_collector/features/collection/presentation/flow/scroll_form_screen.dart';
import 'package:data_collector/features/collection/presentation/flow/project_ui.dart';
import 'package:data_collector/features/collection/presentation/flow/shooting_guide.dart';
import 'package:data_collector/features/collection/providers/wizard_state_provider.dart';
import 'package:data_collector/features/projects/providers/project_providers.dart';
import 'package:data_collector/models/project_config.dart';
import 'package:data_collector/theme/epoch8_theme.dart';
import 'package:data_collector/theme/epoch8_ui.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

String _formatDateTime(DateTime d) {
  String two(int n) => n.toString().padLeft(2, '0');
  return '${d.year}-${two(d.month)}-${two(d.day)} ${two(d.hour)}:${two(d.minute)}';
}

/// Единая точка входа: `config.flow` из JSON — либо один шаг `scroll_form`, либо пошаговый сценарий.
class CollectionFlowScreen extends ConsumerStatefulWidget {
  const CollectionFlowScreen({super.key, required this.projectId});

  final String projectId;

  @override
  ConsumerState<CollectionFlowScreen> createState() => _CollectionFlowScreenState();
}

class _CollectionFlowScreenState extends ConsumerState<CollectionFlowScreen> {
  @override
  Widget build(BuildContext context) {
    ref.watch(wizardStateProvider(widget.projectId));
    final async = ref.watch(projectsProvider);
    return async.when(
      data: (projects) {
        late Project project;
        try {
          project = projects.firstWhere((p) => p.id == widget.projectId);
        } catch (_) {
          return Scaffold(
            backgroundColor: Epoch8Theme.bgDeep,
            appBar: AppBar(title: const Text('Проект не найден')),
            body: const Center(
              child: Text('Добавьте проект в assets/config/projects.json', textAlign: TextAlign.center),
            ),
          );
        }
        final flow = resolveCollectionFlow(project);
        if (flow.isSingleScrollOnly) {
          return ScrollFormCollectionScreen(projectId: widget.projectId);
        }
        return _FlowStepShell(
          projectId: widget.projectId,
          project: project,
          resolvedFlow: flow,
        );
      },
      loading: () => const Scaffold(
        backgroundColor: Epoch8Theme.bgDeep,
        body: Center(child: CircularProgressIndicator()),
      ),
      error: (e, _) => Scaffold(
        backgroundColor: Epoch8Theme.bgDeep,
        body: Center(child: Text('Ошибка загрузки конфига: $e')),
      ),
    );
  }
}

class _FlowStepShell extends ConsumerStatefulWidget {
  const _FlowStepShell({
    required this.projectId,
    required this.project,
    required this.resolvedFlow,
  });

  final String projectId;
  final Project project;
  final ResolvedCollectionFlow resolvedFlow;

  @override
  ConsumerState<_FlowStepShell> createState() => _FlowStepShellState();
}

class _FlowStepShellState extends ConsumerState<_FlowStepShell> {
  int _step = 0;

  void _goBack() {
    if (_step <= 0) {
      context.go('/dashboard');
      return;
    }
    setState(() => _step--);
  }

  ResolvedCollectionFlow get _flow => widget.resolvedFlow;

  String _formContinueLabel() {
    final u = ProjectUi(widget.project);
    if (_step + 1 >= _flow.steps.length) return u.str(['flow', 'continue', 'next'], 'Далее');
    switch (_flow.steps[_step + 1].kind) {
      case CollectionScreenKind.instruction:
        return u.str(['flow', 'continue', 'to_briefing'], 'Далее: справка по съёмке');
      case CollectionScreenKind.cameraPose:
        return u.str(['flow', 'continue', 'to_capture'], 'Далее: съёмка');
      default:
        return u.str(['flow', 'continue', 'next'], 'Далее');
    }
  }

  @override
  Widget build(BuildContext context) {
    ref.watch(wizardStateProvider(widget.projectId));
    final project = widget.project;

    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) {
        if (!didPop) _goBack();
      },
      child: Scaffold(
        backgroundColor: Epoch8Theme.bgDeep,
        appBar: AppBar(
          leading: IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: _goBack,
          ),
          title: Text(
            project.name,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          actions: [
            if (_step >= 1)
              IconButton(
                icon: const Icon(Icons.help_outline),
                tooltip: ProjectUi(project).str(['flow', 'app_bar', 'shooting_help_tooltip'], 'Справка по съёмке'),
                onPressed: () => showShootingHelp(context, widget.project),
              ),
          ],
        ),
        body: Container(
          decoration: Epoch8Theme.screenGradient(),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              ..._stepRibbon(context),
              Expanded(
                child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 280),
                  switchInCurve: Curves.easeOutCubic,
                  switchOutCurve: Curves.easeInCubic,
                  child: _buildStep(context),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  List<Widget> _stepRibbon(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final u = ProjectUi(widget.project);
    if (_step < 0 || _step >= _flow.steps.length) return const [];
    final cur = _flow.steps[_step];
    final cams = _flow.cameraPoseCount;

    if (cur.kind == CollectionScreenKind.cameraPose) {
      final slot = cur.poseIndex1Based ?? 1;
      final fieldTitle = cur.fields.isNotEmpty ? cur.fields.single.title : '';
      final sep = u.str(['flow', 'ribbon', 'pose_counter_sep'], '·');
      return [
        Padding(
          padding: const EdgeInsets.fromLTRB(Epoch8Layout.pagePadding, 10, Epoch8Layout.pagePadding, 6),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    u.str(['flow', 'ribbon', 'shooting'], 'Съёмка'),
                    style: t.labelSmall?.copyWith(color: Epoch8Theme.textMuted, letterSpacing: 1.1),
                  ),
                  Text(
                    '$fieldTitle $sep $slot/$cams',
                    style: t.labelLarge?.copyWith(color: Epoch8Theme.accent, fontWeight: FontWeight.w800),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Epoch8StepDots(current: slot - 1, total: cams),
            ],
          ),
        ),
      ];
    }
    if (cur.kind == CollectionScreenKind.instruction) {
      return [
        Padding(
          padding: const EdgeInsets.fromLTRB(Epoch8Layout.pagePadding, 8, Epoch8Layout.pagePadding, 4),
          child: Align(
            alignment: Alignment.centerLeft,
            child: Text(
              cur.fields.isNotEmpty
                  ? cur.fields.first.title
                  : u.str(['flow', 'ribbon', 'instruction_fallback'], 'Справка перед съёмкой'),
              style: t.titleSmall?.copyWith(color: Epoch8Theme.textMuted, fontWeight: FontWeight.w600),
            ),
          ),
        ),
      ];
    }
    if (cur.kind == CollectionScreenKind.review) {
      return [
        Padding(
          padding: const EdgeInsets.fromLTRB(Epoch8Layout.pagePadding, 10, Epoch8Layout.pagePadding, 4),
          child: Text(
            u.str(['flow', 'ribbon', 'review'], 'Проверка и отправка'),
            style: t.labelMedium?.copyWith(color: Epoch8Theme.textMuted, letterSpacing: 0.4),
          ),
        ),
      ];
    }
    if (cur.kind == CollectionScreenKind.form) {
      return [
        Padding(
          padding: const EdgeInsets.fromLTRB(Epoch8Layout.pagePadding, 10, Epoch8Layout.pagePadding, 2),
          child: Text(
            u.str(['flow', 'ribbon', 'form'], 'Анкета'),
            style: t.labelMedium?.copyWith(color: Epoch8Theme.textMuted, letterSpacing: 0.4),
          ),
        ),
      ];
    }
    return const [];
  }

  Widget _buildStep(BuildContext context) {
    final p = widget.project;
    if (_step < 0 || _step >= _flow.steps.length) return const SizedBox.shrink();
    final cur = _flow.steps[_step];

    switch (cur.kind) {
      case CollectionScreenKind.form:
        return _FlowFormStep(
          key: ValueKey('flow_form_${cur.id}'),
          project: p,
          projectId: widget.projectId,
          formFields: cur.fields,
          useCowHints: cur.cowIdHints,
          cowMatchFieldId: cur.cowIdFieldId ??
              () {
                for (final f in cur.fields) {
                  if (f.type == 'text_input') return f.fieldId;
                }
                return null;
              }(),
          continueLabel: _formContinueLabel(),
          onContinue: () => setState(() => _step++),
        );
      case CollectionScreenKind.instruction:
        return _InstructionBriefingStep(
          key: ValueKey('flow_instruction_${cur.id}'),
          project: p,
          onContinue: () => setState(() => _step++),
        );
      case CollectionScreenKind.cameraPose:
        final field = cur.fields.single;
        final poseIdx = cur.poseIndex1Based ?? 1;
        final total = cur.poseTotal ?? _flow.cameraPoseCount;
        return _CameraPoseStep(
          key: ValueKey('flow_pose_${field.fieldId}'),
          project: p,
          projectId: widget.projectId,
          poseField: field,
          storageKey: field.fieldId,
          poseIndex1Based: poseIdx,
          totalPoses: total,
          onNext: () => setState(() => _step++),
        );
      case CollectionScreenKind.review:
        return _FlowReviewStep(
          key: ValueKey('flow_review'),
          project: p,
          formFields: _flow.allFormFields,
          cameraFields: _flow.allCameraFields,
          projectId: widget.projectId,
          onEditForm: () {
            final i = _flow.indexOfFirstForm();
            setState(() => _step = i >= 0 ? i : 0);
          },
          onEditPose: (int poseIndex1Based) =>
              setState(() => _step = _flow.indexOfCameraPose(poseIndex1Based)),
          onSubmit: () async {
            final answers = ref.read(wizardStateProvider(widget.projectId));
            await submitLocalPackage(
              ref: ref,
              context: context,
              projectId: widget.projectId,
              answers: answers,
            );
          },
        );
      case CollectionScreenKind.scrollForm:
        return const SizedBox.shrink();
    }
  }
}

class _FlowFormStep extends ConsumerStatefulWidget {
  const _FlowFormStep({
    super.key,
    required this.project,
    required this.projectId,
    required this.formFields,
    required this.useCowHints,
    required this.cowMatchFieldId,
    required this.continueLabel,
    required this.onContinue,
  });

  final Project project;
  final String projectId;
  final List<ConfigField> formFields;
  final bool useCowHints;
  final String? cowMatchFieldId;
  final String continueLabel;
  final VoidCallback onContinue;

  @override
  ConsumerState<_FlowFormStep> createState() => _FlowFormStepState();
}

class _FlowFormStepState extends ConsumerState<_FlowFormStep> {
  DateTime _scanTime = DateTime.now();
  ConfigField? _scanField;
  final Map<String, TextEditingController> _textCtrls = {};

  @override
  void initState() {
    super.initState();
    final s = ref.read(wizardStateProvider(widget.projectId));
    ConfigField? scan;
    for (final f in widget.formFields) {
      if (f.type == 'datetime') {
        if (scan == null) {
          scan = f;
          _scanTime = _parseScanTime(s[f.fieldId]) ?? DateTime.now();
        }
      } else if (f.type == 'text_input') {
        _textCtrls[f.fieldId] = TextEditingController(text: s[f.fieldId]?.toString() ?? '');
      }
    }
    _scanField = scan;
  }

  DateTime? _parseScanTime(dynamic v) {
    if (v == null) return null;
    if (v is DateTime) return v;
    if (v is String) return DateTime.tryParse(v);
    return null;
  }

  @override
  void dispose() {
    for (final c in _textCtrls.values) {
      c.dispose();
    }
    super.dispose();
  }

  TextEditingController? _cowCtrl() {
    final id = widget.cowMatchFieldId;
    if (id == null) return null;
    return _textCtrls[id];
  }

  Future<void> _pickDateTime() async {
    final d = await showDatePicker(
      context: context,
      initialDate: _scanTime,
      firstDate: DateTime(2020),
      lastDate: DateTime(2100),
    );
    if (d == null || !mounted) return;
    final t = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(_scanTime),
    );
    if (t == null || !mounted) return;
    setState(() {
      _scanTime = DateTime(d.year, d.month, d.day, t.hour, t.minute);
    });
  }

  bool get _formValid {
    for (final f in widget.formFields) {
      if (!configFieldRequired(f)) continue;
      if (f.type == 'datetime') continue;
      final c = _textCtrls[f.fieldId];
      if (c == null || c.text.trim().isEmpty) return false;
    }
    return true;
  }

  void _saveToState() {
    final n = ref.read(wizardStateProvider(widget.projectId).notifier);
    if (_scanField != null) {
      n.updateField(_scanField!.fieldId, _scanTime.toIso8601String());
    }
    for (final e in _textCtrls.entries) {
      n.updateField(e.key, e.value.text.trim());
    }
  }

  void _prefillFrom(Map<String, dynamic> data) {
    setState(() {
      if (_scanField != null) {
        final pt = _parseScanTime(data[_scanField!.fieldId]);
        if (pt != null) _scanTime = pt;
      }
      for (final f in widget.formFields) {
        if (f.type != 'text_input') continue;
        final c = _textCtrls[f.fieldId];
        if (c != null && data[f.fieldId] != null) {
          c.text = data[f.fieldId].toString();
        }
      }
    });
  }

  String? _payloadCowId(Map<String, dynamic> payload) {
    final key = widget.cowMatchFieldId;
    final a = key != null ? payload[key]?.toString().trim() : null;
    if (a != null && a.isNotEmpty) return a;
    final b = payload['cow_identifier']?.toString().trim() ?? payload['cow_id']?.toString().trim();
    if (b != null && b.isNotEmpty) return b;
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final u = ProjectUi(widget.project);
    final packages = ref.watch(packagesStreamProvider).asData?.value ?? const [];
    final cowCtrl = _cowCtrl();
    final typedCowId = cowCtrl?.text.trim() ?? '';
    final typedLower = typedCowId.toLowerCase();
    final matchedIds = <String>{};
    DateTime? exactCreatedAt;
    Map<String, dynamic>? exactData;

    if (widget.useCowHints && typedLower.isNotEmpty && cowCtrl != null) {
      for (final pkg in packages) {
        if (pkg.projectId != widget.projectId) continue;
        final payload = unpackPackageFormData(pkg.dataJson);
        final existingCowId = _payloadCowId(payload) ?? '';
        if (existingCowId.isEmpty) continue;
        final existingLower = existingCowId.toLowerCase();
        if (existingLower.contains(typedLower)) {
          matchedIds.add(existingCowId);
        }
        if (existingLower == typedLower) {
          if (exactCreatedAt == null || pkg.createdAt.isAfter(exactCreatedAt)) {
            exactCreatedAt = pkg.createdAt;
            exactData = payload;
          }
        }
      }
    }

    final hasAnyMatches = matchedIds.isNotEmpty;
    final hasExactMatch = exactData != null;

    final textFields = widget.formFields.where((f) => f.type == 'text_input').toList()
      ..sort((a, b) => a.priority.compareTo(b.priority));

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(Epoch8Layout.pagePadding, 8, Epoch8Layout.pagePadding, 28),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Epoch8SectionHeader(
            overline: u.str(['flow', 'form', 'step_overline'], 'Шаг 1'),
            title: _scanField != null
                ? u.str(['flow', 'form', 'scan_section_title'], 'Данные скана')
                : u.str(['flow', 'form', 'form_section_title_fallback'], 'Анкета'),
            subtitle: _scanField?.instructions ??
                (widget.formFields.isNotEmpty ? widget.formFields.first.instructions : ''),
          ),
          const SizedBox(height: Epoch8Layout.sectionGap),
          if (_scanField != null) ...[
            _Card(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(_scanField!.title, style: Theme.of(context).textTheme.titleSmall),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          _formatDateTime(_scanTime.toLocal()),
                          style: Theme.of(context).textTheme.bodyLarge,
                        ),
                      ),
                      TextButton.icon(
                        onPressed: _pickDateTime,
                        icon: const Icon(Icons.edit_calendar_outlined, size: 20),
                        label: Text(u.str(['flow', 'form', 'datetime_change'], 'Изменить')),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),
          ],
          _Card(
            accentBorder: true,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  widget.useCowHints
                      ? u.str(['flow', 'form', 'fields_heading_cow'], 'Параметры коровы')
                      : u.str(['flow', 'form', 'fields_heading_default'], 'Поля'),
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 14),
                for (var i = 0; i < textFields.length; i++) ...[
                  if (i > 0) const SizedBox(height: 12),
                  _buildTextFieldRow(
                    context,
                    field: textFields[i],
                    typedCowId: typedCowId,
                    typedLower: typedLower,
                    hasExactMatch: hasExactMatch,
                    hasAnyMatches: hasAnyMatches,
                    matchedIds: matchedIds,
                    cowCtrl: cowCtrl,
                    exactData: exactData,
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: Epoch8Layout.sectionGap),
          FilledButton(
            onPressed: _formValid
                ? () {
                    _saveToState();
                    widget.onContinue();
                  }
                : null,
            child: Text(widget.continueLabel),
          ),
        ],
      ),
    );
  }

  Widget _buildTextFieldRow(
    BuildContext context, {
    required ConfigField field,
    required String typedCowId,
    required String typedLower,
    required bool hasExactMatch,
    required bool hasAnyMatches,
    required Set<String> matchedIds,
    required TextEditingController? cowCtrl,
    required Map<String, dynamic>? exactData,
  }) {
    final c = _textCtrls[field.fieldId];
    if (c == null) return const SizedBox.shrink();

    final isCowId = widget.cowMatchFieldId != null && field.fieldId == widget.cowMatchFieldId;
    if (widget.useCowHints && isCowId) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            controller: c,
            decoration: InputDecoration(
              labelText: field.title,
              hintText: field.instructions,
              helperText: typedCowId.isEmpty
                  ? null
                  : hasExactMatch
                      ? ProjectUi(widget.project).str(['flow', 'form', 'cow_hint_exact'], 'ID найден в локальной истории')
                      : hasAnyMatches
                          ? ProjectUi(widget.project).str(['flow', 'form', 'cow_hint_similar'], 'Есть похожие ID в истории')
                          : ProjectUi(widget.project).str(['flow', 'form', 'cow_hint_new'], 'Новый ID (в истории не найден)'),
              helperStyle: TextStyle(
                color: hasExactMatch
                    ? Epoch8Theme.success
                    : hasAnyMatches
                        ? Epoch8Theme.accent
                        : Epoch8Theme.textMuted,
              ),
              suffixIcon: typedCowId.isEmpty
                  ? null
                  : Icon(
                      hasExactMatch ? Icons.verified_outlined : (hasAnyMatches ? Icons.search : Icons.add_circle_outline),
                      color: hasExactMatch
                          ? Epoch8Theme.success
                          : (hasAnyMatches ? Epoch8Theme.accent : Epoch8Theme.textMuted),
                    ),
            ),
            onChanged: (_) => setState(() {}),
          ),
          if (typedCowId.isNotEmpty && hasAnyMatches) ...[
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: matchedIds.take(6).map((id) {
                final isExact = id.toLowerCase() == typedLower;
                return ActionChip(
                  label: Text(id),
                  backgroundColor: isExact
                      ? Epoch8Theme.success.withValues(alpha: 0.18)
                      : Epoch8Theme.bgElevated,
                  side: BorderSide(
                    color: isExact
                        ? Epoch8Theme.success.withValues(alpha: 0.6)
                        : Epoch8Theme.border,
                  ),
                  onPressed: () {
                    final cc = cowCtrl;
                    if (cc != null) {
                      cc.text = id;
                      cc.selection = TextSelection.fromPosition(TextPosition(offset: cc.text.length));
                    }
                    setState(() {});
                  },
                );
              }).toList(),
            ),
          ],
          if (hasExactMatch && exactData != null) ...[
            const SizedBox(height: 10),
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton.icon(
                onPressed: () => _prefillFrom(exactData),
                icon: const Icon(Icons.auto_fix_high_outlined, size: 18),
                label: Text(ProjectUi(widget.project).str(['flow', 'form', 'prefill_button'], 'Предзаполнить поля из последней записи')),
              ),
            ),
          ],
        ],
      );
    }

    return TextField(
      controller: c,
      decoration: InputDecoration(
        labelText: field.title,
        hintText: field.instructions,
      ),
      onChanged: (_) => setState(() {}),
    );
  }
}

class _InstructionBriefingStep extends StatelessWidget {
  const _InstructionBriefingStep({super.key, required this.project, required this.onContinue});

  final Project project;
  final VoidCallback onContinue;

  @override
  Widget build(BuildContext context) {
    return ShootingGuideBody(project: project, showStartButton: true, onStart: onContinue);
  }
}

class _CameraPoseStep extends ConsumerStatefulWidget {
  const _CameraPoseStep({
    super.key,
    required this.project,
    required this.projectId,
    required this.poseField,
    required this.storageKey,
    required this.poseIndex1Based,
    required this.totalPoses,
    required this.onNext,
  });

  final Project project;
  final String projectId;
  final ConfigField poseField;
  /// Ключ в [wizardState] и в payload (`field_id` из конфига).
  final String storageKey;
  /// 1..n — порядок ракурса для `camera_capture_context.poses`.
  final int poseIndex1Based;
  final int totalPoses;
  final VoidCallback onNext;

  @override
  ConsumerState<_CameraPoseStep> createState() => _CameraPoseStepState();
}

class _CameraPoseStepState extends ConsumerState<_CameraPoseStep> {
  final _picker = ImagePicker();

  String get _key => widget.storageKey;

  Future<void> _pickImage(ImageSource source) async {
    // Keep original quality for new captures; preview scaling is done only in UI.
    final x = await _picker.pickImage(source: source);
    if (x == null || !mounted) return;

    if (!kIsWeb) {
      final quality = await analyzeCaptureQuality(x.path);
      if (!mounted) return;
      if (!quality.isAcceptable) {
        final qu = ProjectUi(widget.project);
        final useAnyway = await showDialog<bool>(
          context: context,
          barrierDismissible: false,
          builder: (ctx) => AlertDialog(
            title: Text(qu.str(['flow', 'camera_pose', 'quality_dialog', 'title'], 'Проверка качества кадра')),
            content: SingleChildScrollView(child: Text(quality.userMessage)),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx, true),
                child: Text(qu.str(['flow', 'camera_pose', 'quality_dialog', 'use_anyway'], 'Всё равно использовать')),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: Text(qu.str(['flow', 'camera_pose', 'quality_dialog', 'retake'], 'Переснять')),
              ),
            ],
          ),
        );
        if (useAnyway != true) return;
      }
    }

    await CameraMetadataCollector.attachPoseMetadata(
      ref: ref,
      projectId: widget.projectId,
      poseIndex1Based: widget.poseIndex1Based,
      imagePath: x.path,
    );
    if (!mounted) return;
    final answers = ref.read(wizardStateProvider(widget.projectId));
    final paths = List<String>.from(CapturedPhotoPaths.list(answers[_key]))..add(x.path);
    ref.read(wizardStateProvider(widget.projectId).notifier).updateField(_key, paths);
    setState(() {});
  }

  void _removePhoto(String path) {
    CameraMetadataCollector.removePoseShotByPath(
      ref: ref,
      projectId: widget.projectId,
      poseIndex1Based: widget.poseIndex1Based,
      imagePath: path,
    );
    final answers = ref.read(wizardStateProvider(widget.projectId));
    final paths = List<String>.from(CapturedPhotoPaths.list(answers[_key]))..remove(path);
    ref.read(wizardStateProvider(widget.projectId).notifier).updateField(_key, paths.isEmpty ? null : paths);
    setState(() {});
  }

  void _clearAll() {
    CameraMetadataCollector.removePoseMetadata(
      ref: ref,
      projectId: widget.projectId,
      poseIndex1Based: widget.poseIndex1Based,
    );
    ref.read(wizardStateProvider(widget.projectId).notifier).updateField(_key, null);
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final u = ProjectUi(widget.project);
    final guide = resolvePoseGuide(widget.project, widget.poseIndex1Based, widget.poseField);
    final answers = ref.watch(wizardStateProvider(widget.projectId));
    final paths = CapturedPhotoPaths.list(answers[_key]);

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(Epoch8Layout.pagePadding, 8, Epoch8Layout.pagePadding, 28),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            guide.title,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 12),
          ...guide.descriptionLines.map(
            (line) => Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('• ', style: TextStyle(color: Epoch8Theme.accent)),
                  Expanded(
                    child: Text(line, style: Theme.of(context).textTheme.bodyMedium?.copyWith(height: 1.35)),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: Text(
                  u.str(['flow', 'camera_pose', 'example_heading'], 'Пример ракурса'),
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
                ),
              ),
              TextButton.icon(
                onPressed: () => showShootingHelp(context, widget.project),
                icon: const Icon(Icons.help_outline, size: 18),
                label: Text(u.str(['flow', 'camera_pose', 'help_button'], 'Справка')),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(Epoch8Layout.radiusMd),
            child: AspectRatio(
              aspectRatio: 4 / 3,
              child: Image.asset(
                guide.exampleAssetPath,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => Container(
                  color: Epoch8Theme.bgElevated,
                  alignment: Alignment.center,
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Text(
                      u.str(['flow', 'camera_pose', 'example_asset_missing'], ''),
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Epoch8Theme.textMuted),
                    ),
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 20),
          Text(
            u.tpl(['flow', 'camera_pose', 'your_shots_heading'], 'Ваши кадры ({count})', {'count': '${paths.length}'}),
            style: Theme.of(context).textTheme.titleSmall,
          ),
          const SizedBox(height: 8),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(Epoch8Layout.radiusMd),
              border: Border.all(color: Epoch8Theme.border.withValues(alpha: 0.9)),
              color: Epoch8Theme.bgElevated.withValues(alpha: 0.5),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (paths.isEmpty) ...[
                  Icon(
                    Icons.add_photo_alternate_outlined,
                    size: 44,
                    color: Epoch8Theme.textMuted.withValues(alpha: 0.55),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    u.str(['flow', 'camera_pose', 'empty_hint'], 'Добавьте кадры камерой или из галереи'),
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Epoch8Theme.textMuted),
                  ),
                  const SizedBox(height: 18),
                ] else ...[
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      for (var i = 0; i < paths.length; i++)
                        _PoseThumbTile(
                          path: paths[i],
                          index: i + 1,
                          onRemove: () => _removePhoto(paths[i]),
                        ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Text(
                    u.str(['flow', 'camera_pose', 'add_more'], 'Добавить ещё'),
                    style: Theme.of(context).textTheme.labelMedium?.copyWith(color: Epoch8Theme.textMuted),
                  ),
                  const SizedBox(height: 10),
                ],
                Row(
                  children: [
                    Expanded(
                      child: FilledButton.icon(
                        onPressed: () => _pickImage(ImageSource.camera),
                        icon: const Icon(Icons.photo_camera_outlined, size: 20),
                        label: Text(u.str(['flow', 'camera_pose', 'camera'], 'Камера')),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => _pickImage(ImageSource.gallery),
                        icon: const Icon(Icons.photo_library_outlined, size: 20),
                        label: Text(u.str(['flow', 'camera_pose', 'gallery'], 'Галерея')),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          if (paths.isNotEmpty) ...[
            const SizedBox(height: 8),
            TextButton.icon(
              onPressed: _clearAll,
              icon: const Icon(Icons.delete_sweep_outlined, color: Epoch8Theme.danger),
              label: Text(u.str(['flow', 'camera_pose', 'clear_all_poses'], 'Удалить все кадры этого ракурса')),
            ),
          ],
          const SizedBox(height: 24),
          FilledButton(
            onPressed: (!configFieldRequired(widget.poseField) || paths.isNotEmpty) ? widget.onNext : null,
            style: FilledButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 16)),
            child: Text(
              widget.poseIndex1Based < widget.totalPoses
                  ? u.str(['flow', 'camera_pose', 'next'], 'Далее')
                  : u.str(['flow', 'camera_pose', 'to_review'], 'К проверке'),
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}

class _PoseThumbTile extends StatelessWidget {
  const _PoseThumbTile({required this.path, required this.index, required this.onRemove});

  final String path;
  final int index;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    return Stack(
      clipBehavior: Clip.none,
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(10),
          child: Image.file(
            File(path),
            width: 104,
            height: 104,
            fit: BoxFit.cover,
          ),
        ),
        Positioned(
          left: 4,
          top: 4,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
              color: Epoch8Theme.bgDeep.withValues(alpha: 0.75),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Text('$index', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600)),
          ),
        ),
        Positioned(
          right: -4,
          top: -4,
          child: Material(
            color: Epoch8Theme.danger,
            shape: const CircleBorder(),
            child: InkWell(
              onTap: onRemove,
              customBorder: const CircleBorder(),
              child: const Padding(
                padding: EdgeInsets.all(4),
                child: Icon(Icons.close, size: 16, color: Epoch8Theme.bgDeep),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _FlowReviewStep extends ConsumerWidget {
  const _FlowReviewStep({
    super.key,
    required this.project,
    required this.formFields,
    required this.cameraFields,
    required this.projectId,
    required this.onEditForm,
    required this.onEditPose,
    required this.onSubmit,
  });

  final Project project;
  final List<ConfigField> formFields;
  final List<ConfigField> cameraFields;
  final String projectId;
  final VoidCallback onEditForm;
  final void Function(int poseIndex) onEditPose;
  final Future<void> Function() onSubmit;

  bool _isComplete(Map<String, dynamic> a) {
    for (final f in formFields) {
      if (!configFieldRequired(f)) continue;
      final v = a[f.fieldId];
      if (f.type == 'datetime') {
        if (v == null || v.toString().trim().isEmpty) return false;
      } else if (f.type == 'text_input') {
        if (v.toString().trim().isEmpty) return false;
      }
    }
    for (var i = 0; i < cameraFields.length; i++) {
      final f = cameraFields[i];
      if (!configFieldRequired(f)) continue;
      if (!CapturedPhotoPaths.hasPhotos(a[f.fieldId])) return false;
    }
    return true;
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final u = ProjectUi(project);
    final a = ref.watch(wizardStateProvider(projectId));
    final complete = _isComplete(a);
    final cameraCtx = a[PackagePayloadKeys.cameraCaptureContext] as Map<String, dynamic>?;

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(Epoch8Layout.pagePadding, 8, Epoch8Layout.pagePadding, 32),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Epoch8SectionHeader(
            overline: u.str(['flow', 'review', 'header_overline'], 'Финиш'),
            title: u.str(['flow', 'review', 'header_title'], 'Проверка и отправка'),
            subtitle: u.str(
              ['flow', 'review', 'header_subtitle'],
              'Проверьте данные. Можно вернуться к анкете или к любому ракурсу — снимки сохраняются, их можно заменить.',
            ),
          ),
          const SizedBox(height: Epoch8Layout.sectionGap),
          _Card(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        u.str(['flow', 'review', 'form_card_title'], 'Анкета'),
                        style: Theme.of(context).textTheme.titleSmall,
                      ),
                    ),
                    TextButton(onPressed: onEditForm, child: Text(u.str(['flow', 'review', 'edit'], 'Изменить'))),
                  ],
                ),
                const Divider(height: 24),
                for (final f in formFields) ...[
                  _line(
                    f.title,
                    _formatReviewValue(u, f, a[f.fieldId]),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 16),
          Text(
            u.str(['flow', 'review', 'photos_section_title'], 'Фотографии по ракурсам'),
            style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 8),
          for (var i = 0; i < cameraFields.length; i++) ...[
            _Card(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          cameraFields[i].title,
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                      ),
                      TextButton(
                        onPressed: () => onEditPose(i + 1),
                        child: Text(u.str(['flow', 'review', 'edit'], 'Изменить')),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      for (final p in CapturedPhotoPaths.list(a[cameraFields[i].fieldId]))
                        ClipRRect(
                          borderRadius: BorderRadius.circular(8),
                          child: Image.file(File(p), width: 72, height: 72, fit: BoxFit.cover),
                        ),
                    ],
                  ),
                  if (CapturedPhotoPaths.list(a[cameraFields[i].fieldId]).isEmpty)
                    Text(
                      u.str(['flow', 'review', 'no_frames'], 'Нет кадров'),
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Epoch8Theme.textMuted),
                    ),
                ],
              ),
            ),
            if (i < cameraFields.length - 1) const SizedBox(height: 8),
          ],
          const SizedBox(height: 16),
          _CameraMetaReviewPanel(project: project, cameraContext: cameraCtx),
          const SizedBox(height: 24),
          FilledButton(
            onPressed: complete
                ? () async {
                    await onSubmit();
                  }
                : null,
            child: Text(u.str(['flow', 'review', 'submit'], 'Отправить данные')),
          ),
        ],
      ),
    );
  }

  Widget _line(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(width: 110, child: Text(label, style: const TextStyle(color: Epoch8Theme.textMuted))),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }

  String _formatReviewValue(ProjectUi u, ConfigField f, dynamic v) {
    final dash = u.str(['flow', 'review', 'empty_value'], '—');
    if (v == null) return dash;
    if (f.type == 'datetime') {
      final st = DateTime.tryParse(v.toString())?.toLocal();
      return st != null ? _formatDateTime(st) : v.toString();
    }
    final s = v.toString().trim();
    return s.isEmpty ? dash : s;
  }
}

/// Сворачиваемый блок метаданных камеры / устройства для экрана проверки.
class _CameraMetaReviewPanel extends StatelessWidget {
  const _CameraMetaReviewPanel({required this.project, this.cameraContext});

  final Project project;
  final Map<String, dynamic>? cameraContext;

  static String? _subtitle(ProjectUi u, Map<String, dynamic> ctx) {
    final dev = ctx['device'];
    String? model;
    if (dev is Map) {
      model = dev['model']?.toString() ?? dev['machine']?.toString();
    }
    final poses = ctx['poses'];
    String? fxHint;
    if (poses is Map && poses.isNotEmpty) {
      outer:
      for (final v in poses.values) {
        if (v is! Map) continue;
        final shots = v['shots'];
        if (shots is List) {
          for (final sh in shots) {
            if (sh is! Map) continue;
            final d = sh['derived'];
            if (d is Map && d['preferred_fx_px_estimate'] != null) {
              fxHint = u.tpl(
                ['flow', 'camera_meta', 'fx_estimate'],
                'fₓ≈{value} px',
                {'value': _fmtNum(d['preferred_fx_px_estimate'])},
              );
              break outer;
            }
          }
        }
        final d = v['derived'];
        if (d is Map && d['preferred_fx_px_estimate'] != null) {
          fxHint = u.tpl(
            ['flow', 'camera_meta', 'fx_estimate'],
            'fₓ≈{value} px',
            {'value': _fmtNum(d['preferred_fx_px_estimate'])},
          );
          break;
        }
      }
    }
    final parts = <String>[];
    if (model != null && model.isNotEmpty) parts.add(model);
    if (fxHint != null) parts.add(fxHint);
    return parts.isEmpty
        ? u.str(['flow', 'camera_meta', 'expand_hint'], 'Нажмите, чтобы развернуть')
        : parts.join(' · ');
  }

  static String _fmtNum(dynamic v) {
    if (v is double) return v.toStringAsFixed(v.abs() >= 1000 ? 0 : 1);
    if (v is int) return v.toString();
    return v.toString();
  }

  @override
  Widget build(BuildContext context) {
    final u = ProjectUi(project);
    final ctx = cameraContext;
    if (ctx == null || ctx.isEmpty) {
      return _Card(
        child: Row(
          children: [
            Icon(Icons.info_outline, size: 20, color: Epoch8Theme.textMuted.withValues(alpha: 0.9)),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                u.str(['flow', 'camera_meta', 'empty_notice'], 'Мета-параметры камеры появятся после съёмки поз.'),
                style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Epoch8Theme.textMuted),
              ),
            ),
          ],
        ),
      );
    }

    return _Card(
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          initiallyExpanded: false,
          tilePadding: EdgeInsets.zero,
          expandedAlignment: Alignment.topLeft,
          expandedCrossAxisAlignment: CrossAxisAlignment.start,
          iconColor: Epoch8Theme.accent,
          collapsedIconColor: Epoch8Theme.textMuted,
          title: Row(
            children: [
              Icon(Icons.tune, size: 22, color: Epoch8Theme.accent.withValues(alpha: 0.95)),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      u.str(['flow', 'camera_meta', 'tile_title'], 'Мета-параметры камеры'),
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _subtitle(u, Map<String, dynamic>.from(ctx)) ?? '',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Epoch8Theme.textMuted),
                    ),
                  ],
                ),
              ),
            ],
          ),
          children: [
            const Divider(height: 20),
            _metaSection(
              context,
              u.str(['flow', 'camera_meta', 'section_device'], 'Устройство'),
              _deviceRows(u, ctx['device']),
            ),
            _metaSection(
              context,
              u.str(['flow', 'camera_meta', 'section_native'], 'Нативная камера (задняя)'),
              _nativeRows(u, ctx['native_back_camera']),
            ),
            ..._poseMetaSections(context, u, ctx['poses']),
            Theme(
              data: Theme.of(context).copyWith(dividerColor: Epoch8Theme.border),
              child: ExpansionTile(
                tilePadding: EdgeInsets.zero,
                title: Text(
                  u.str(['flow', 'camera_meta', 'json_section'], 'Полный JSON (копирование)'),
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(color: Epoch8Theme.textMuted),
                ),
                children: [
                  const SizedBox(height: 8),
                  SelectableText(
                    const JsonEncoder.withIndent('  ').convert(ctx),
                    style: TextStyle(
                      fontFamily: 'monospace',
                      fontSize: 11,
                      height: 1.35,
                      color: Epoch8Theme.textMuted,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  List<Widget> _deviceRows(ProjectUi u, dynamic device) {
    if (device is! Map) {
      return [
        Text(u.str(['flow', 'camera_meta', 'dash'], '—'), style: const TextStyle(color: Epoch8Theme.textMuted)),
      ];
    }
    final m = <String, dynamic>{};
    device.forEach((k, v) => m[k.toString()] = v);
    final order = ['platform', 'model', 'machine', 'brand', 'manufacturer', 'device', 'sdk_int', 'release', 'system_version'];
    final lines = <String>[];
    for (final k in order) {
      if (m[k] != null) lines.add('$k: ${m[k]}');
    }
    for (final e in m.entries) {
      if (order.contains(e.key)) continue;
      lines.add('${e.key}: ${e.value}');
    }
    return lines.map((s) => Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: SelectableText(s, style: const TextStyle(fontSize: 13, height: 1.35)),
        )).toList();
  }

  List<Widget> _nativeRows(ProjectUi u, dynamic native) {
    if (native is! Map || native.isEmpty) {
      return [
        Text(
          u.str(['flow', 'camera_meta', 'native_empty'], 'Нет данных с нативного API'),
          style: const TextStyle(color: Epoch8Theme.textMuted, fontSize: 13),
        ),
      ];
    }
    final m = <String, dynamic>{};
    native.forEach((k, v) => m[k.toString()] = v);
    final priority = [
      'source',
      'primary_focal_length_mm',
      'focal_lengths_mm',
      'sensor_physical_width_mm',
      'sensor_physical_height_mm',
      'sensor_pixel_array_width',
      'sensor_pixel_array_height',
      'estimated_fx_px',
      'estimated_fy_px',
      'estimated_cx_px',
      'estimated_cy_px',
      'video_field_of_view_deg',
      'fov_model_note',
      'error',
    ];
    final done = <String>{};
    final out = <Widget>[];
    void addLine(String k, dynamic v) {
      out.add(Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: SelectableText('$k: $v', style: const TextStyle(fontSize: 13, height: 1.35)),
      ));
    }

    for (final k in priority) {
      if (m.containsKey(k)) {
        addLine(k, m[k]);
        done.add(k);
      }
    }
    for (final e in m.entries) {
      if (done.contains(e.key)) continue;
      addLine(e.key, e.value);
    }
    return out;
  }

  List<Widget> _poseMetaSections(BuildContext context, ProjectUi u, dynamic poses) {
    if (poses is! Map || poses.isEmpty) return [];
    final list = <Widget>[];
    final keys = poses.keys.map((k) => int.tryParse(k.toString())).whereType<int>().toList()..sort();
    for (final idx in keys) {
      final p = poses['$idx'];
      if (p is! Map) continue;
      final shots = p['shots'];
      if (shots is List && shots.isNotEmpty) {
        for (var si = 0; si < shots.length; si++) {
          final sh = shots[si];
          if (sh is! Map) continue;
          final derived = sh['derived'];
          final exif = sh['exif'];
          list.add(
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: _metaSection(
                context,
                u.tpl(
                  ['flow', 'camera_meta', 'pose_shot_title'],
                  'Ракурс {idx} — кадр {shot}',
                  {'idx': '$idx', 'shot': '${si + 1}'},
                ),
                _shotMetaRows(u, derived, exif),
              ),
            ),
          );
        }
      } else {
        final derived = p['derived'];
        final exif = p['exif'];
        list.add(
          Padding(
            padding: const EdgeInsets.only(top: 12),
            child: _metaSection(
              context,
              u.tpl(
                ['flow', 'camera_meta', 'pose_derived_title'],
                'Ракурс {idx} — оценки',
                {'idx': '$idx'},
              ),
              _shotMetaRows(u, derived, exif),
            ),
          ),
        );
      }
    }
    return list;
  }

  List<Widget> _shotMetaRows(ProjectUi u, dynamic derived, dynamic exif) {
    return [
      if (derived is Map) ...[
        if (derived['preferred_fx_px_estimate'] != null)
          _selLine('preferred_fx_px_estimate', derived['preferred_fx_px_estimate']),
        if (derived['fx_px_from_exif_focal_and_native_sensor'] != null)
          _selLine(
            u.str(['flow', 'camera_meta', 'label_fx_exif'], 'fx_px (EXIF focal × сенсор)'),
            derived['fx_px_from_exif_focal_and_native_sensor'],
          ),
        if (derived['fx_px_from_35mm_equiv'] != null)
          _selLine(
            u.str(['flow', 'camera_meta', 'label_fx_35mm'], 'fx_px (35mm equiv)'),
            derived['fx_px_from_35mm_equiv'],
          ),
        if (derived['fx_px_from_native_mm'] != null)
          _selLine(
            u.str(['flow', 'camera_meta', 'label_fx_native'], 'fx_px (натив)'),
            derived['fx_px_from_native_mm'],
          ),
      ],
      if (exif is Map && exif.isNotEmpty) ...[
        const SizedBox(height: 8),
        Text(
          u.str(['flow', 'camera_meta', 'exif_heading'], 'Фрагмент EXIF'),
          style: const TextStyle(fontSize: 12, color: Epoch8Theme.textMuted),
        ),
        const SizedBox(height: 4),
        ...exif.entries.take(12).map((e) => Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: SelectableText(
                '${e.key}: ${e.value}',
                style: const TextStyle(fontSize: 12, height: 1.3),
              ),
            )),
        if (exif.length > 12)
          Text(
            u.tpl(['flow', 'camera_meta', 'exif_more'], '… ещё {n} полей', {'n': '${exif.length - 12}'}),
            style: const TextStyle(fontSize: 11, color: Epoch8Theme.textMuted),
          ),
      ],
    ];
  }

  Widget _selLine(String label, dynamic v) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: SelectableText('$label: $v', style: const TextStyle(fontSize: 13, height: 1.35)),
    );
  }

  Widget _metaSection(BuildContext context, String title, List<Widget> children) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: Theme.of(context).textTheme.titleSmall?.copyWith(color: Epoch8Theme.accent)),
        const SizedBox(height: 8),
        ...children,
      ],
    );
  }
}

class _Card extends StatelessWidget {
  const _Card({required this.child, this.accentBorder = false});

  final Widget child;
  final bool accentBorder;

  @override
  Widget build(BuildContext context) {
    return Epoch8Card(accentBorder: accentBorder, child: child);
  }
}
