import 'dart:convert';
import 'dart:io';

import 'package:data_collector/features/collection/logic/collection_flow_resolver.dart';
import 'package:data_collector/features/collection/logic/submit_local_package.dart';
import 'package:data_collector/features/collection/presentation/flow/package_payload_keys.dart';
import 'package:data_collector/features/collection/presentation/flow/scroll_form_flow_step.dart';
import 'package:data_collector/features/collection/presentation/flow/project_ui.dart';
import 'package:data_collector/features/collection/providers/wizard_state_provider.dart';
import 'package:data_collector/features/projects/providers/project_providers.dart';
import 'package:data_collector/models/project_config.dart';
import 'package:data_collector/theme/epoch8_theme.dart';
import 'package:data_collector/theme/epoch8_ui.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

String _formatDateTime(DateTime d) {
  String two(int n) => n.toString().padLeft(2, '0');
  return '${d.year}-${two(d.month)}-${two(d.day)} ${two(d.hour)}:${two(d.minute)}';
}

/// Сводит значение поля `camera_photo` к списку «кадров» для UI метаданных (путь + exif/derived/…).
List<Map<String, dynamic>> _syntheticShotsFromPoseFieldValue(dynamic v) {
  if (v is Map) {
    return v.entries.map((e) {
      final path = e.key.toString();
      final val = e.value;
      final Map<String, dynamic> meta;
      if (val is Map<String, dynamic>) {
        meta = Map<String, dynamic>.from(val);
      } else if (val is Map) {
        meta = Map<String, dynamic>.from(val.map((k, x) => MapEntry(k.toString(), x)));
      } else {
        meta = <String, dynamic>{};
      }
      return <String, dynamic>{'image_path': path, ...meta};
    }).where((m) => (m['image_path']?.toString() ?? '').isNotEmpty).toList();
  }
  if (v is List) {
    return v
        .map((p) => <String, dynamic>{'image_path': p.toString()})
        .where((m) => (m['image_path']?.toString() ?? '').isNotEmpty)
        .toList();
  }
  if (v is String && v.isNotEmpty) {
    return [<String, dynamic>{'image_path': v}];
  }
  return [];
}

/// `camera_capture_context` без устаревшего `poses`, плюс синтетические `poses` из полей ракурсов.
Map<String, dynamic>? _mergedReviewCameraContext(Map<String, dynamic> answers, List<ConfigField> cameraFields) {
  final raw = answers[PackagePayloadKeys.cameraCaptureContext];
  final base = <String, dynamic>{};
  if (raw is Map) {
    raw.forEach((k, v) {
      base[k.toString()] = v;
    });
  }
  base.remove('poses');
  final poses = <String, dynamic>{};
  for (var i = 0; i < cameraFields.length; i++) {
    final shots = _syntheticShotsFromPoseFieldValue(answers[cameraFields[i].fieldId]);
    if (shots.isNotEmpty) {
      poses['${i + 1}'] = <String, dynamic>{'shots': shots};
    }
  }
  if (poses.isNotEmpty) {
    base['poses'] = poses;
  }
  if (base.isEmpty) return null;
  return base;
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

  String _scrollContinueLabel() {
    final u = ProjectUi(widget.project);
    if (_step + 1 >= _flow.steps.length) return u.str(['flow', 'continue', 'next'], 'Далее');
    if (_flow.steps[_step + 1].kind == CollectionScreenKind.review) {
      return u.str(['flow', 'camera_pose', 'to_review'], 'К проверке');
    }
    return u.str(['flow', 'continue', 'next'], 'Далее');
  }

  int _scrollOrdinal1Based() {
    var n = 0;
    for (var i = 0; i <= _step && i < _flow.steps.length; i++) {
      if (_flow.steps[i].kind == CollectionScreenKind.scrollForm) n++;
    }
    return n;
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
    if (cur.kind == CollectionScreenKind.scrollForm) {
      final totalScroll = _flow.scrollSteps.length;
      final ord = _scrollOrdinal1Based();
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
                    u.str(['flow', 'ribbon', 'scroll_form'], 'Шаг сбора'),
                    style: t.labelSmall?.copyWith(color: Epoch8Theme.textMuted, letterSpacing: 1.1),
                  ),
                  Text(
                    u.tpl(['flow', 'ribbon', 'scroll_counter'], '{cur} из {total}', {'cur': '$ord', 'total': '$totalScroll'}),
                    style: t.labelLarge?.copyWith(color: Epoch8Theme.accent, fontWeight: FontWeight.w800),
                  ),
                ],
              ),
              if (totalScroll > 1) ...[
                const SizedBox(height: 10),
                Epoch8StepDots(current: ord - 1, total: totalScroll),
              ],
            ],
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
      case CollectionScreenKind.scrollForm:
        return ScrollFormFlowStep(
          key: ValueKey('scroll_${cur.id}'),
          project: p,
          projectId: widget.projectId,
          flow: _flow,
          step: cur,
          continueLabel: _scrollContinueLabel(),
          onContinue: () => setState(() => _step++),
        );
      case CollectionScreenKind.review:
        return _FlowReviewStep(
          key: const ValueKey('flow_review'),
          project: p,
          flow: _flow,
          projectId: widget.projectId,
          onEditScrollStep: (int stepIndex) => setState(() => _step = stepIndex),
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
      case CollectionScreenKind.form:
      case CollectionScreenKind.instruction:
      case CollectionScreenKind.cameraPose:
        throw StateError('Unsupported flow step kind ${cur.kind} (resolver allows only scroll_form and review)');
    }
  }
}

class _FlowReviewStep extends ConsumerWidget {
  const _FlowReviewStep({
    super.key,
    required this.project,
    required this.flow,
    required this.projectId,
    required this.onEditScrollStep,
    required this.onSubmit,
  });

  final Project project;
  final ResolvedCollectionFlow flow;
  final String projectId;
  final void Function(int flowStepIndex) onEditScrollStep;
  final Future<void> Function() onSubmit;

  bool _isComplete(Map<String, dynamic> a) {
    for (final f in flow.allFormFields) {
      if (!configFieldRequired(f)) continue;
      final v = a[f.fieldId];
      if (f.type == 'datetime') {
        if (v == null || v.toString().trim().isEmpty) return false;
      } else if (f.type == 'text_input') {
        if (v.toString().trim().isEmpty) return false;
      }
    }
    for (final f in flow.allCameraFields) {
      if (!configFieldRequired(f)) continue;
      if (!CapturedPhotoPaths.hasPhotos(a[f.fieldId])) return false;
    }
    return true;
  }

  /// Заголовок карточки: `flow.steps[].form_title` или только «Шаг n».
  String _reviewScrollBlockTitle(ProjectUi u, ResolvedCollectionStep s, int scrollOrdinal) {
    final label = (s.formTitle ?? '').trim();
    if (label.isNotEmpty) {
      return u.tpl(
        ['flow', 'review', 'scroll_block_title'],
        'Шаг {n}: {form_title}',
        {'n': '$scrollOrdinal', 'form_title': label, 'title': label, 'id': label},
      );
    }
    return u.tpl(
      ['flow', 'review', 'scroll_block_title'],
      'Шаг {n}',
      {'n': '$scrollOrdinal', 'form_title': '', 'title': '', 'id': ''},
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final u = ProjectUi(project);
    final a = ref.watch(wizardStateProvider(projectId));
    final complete = _isComplete(a);
    final cameraCtx = _mergedReviewCameraContext(a, flow.allCameraFields);

    var scrollOrdinal = 0;
    final stepCards = <Widget>[];
    for (var i = 0; i < flow.steps.length; i++) {
      final s = flow.steps[i];
      if (s.kind != CollectionScreenKind.scrollForm) continue;
      scrollOrdinal++;
      stepCards.add(
        _Card(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      _reviewScrollBlockTitle(u, s, scrollOrdinal),
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
                    ),
                  ),
                  TextButton(
                    onPressed: () => onEditScrollStep(i),
                    child: Text(u.str(['flow', 'review', 'edit'], 'Изменить')),
                  ),
                ],
              ),
              const Divider(height: 22),
              if (s.isInstructionOnlyScroll)
                Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Text(
                    u.str(
                      ['flow', 'review', 'instruction_only_hint'],
                      'На этом шаге только инструкция (Markdown) — без полей для проверки.',
                    ),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Epoch8Theme.textMuted),
                  ),
                ),
              if (!s.isInstructionOnlyScroll)
                for (final f in s.fields) ...[
                  if (f.type == 'text_input' || f.type == 'datetime')
                    _reviewLine(
                      f.title,
                      _formatReviewValue(u, f, a[f.fieldId]),
                    )
                  else if (f.type == 'camera_photo') ...[
                    const SizedBox(height: 4),
                    Text(
                      f.title,
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 6),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        for (final p in CapturedPhotoPaths.list(a[f.fieldId]))
                          ClipRRect(
                            borderRadius: BorderRadius.circular(8),
                            child: Image.file(File(p), width: 72, height: 72, fit: BoxFit.cover),
                          ),
                      ],
                    ),
                    if (CapturedPhotoPaths.list(a[f.fieldId]).isEmpty)
                      Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Text(
                          u.str(['flow', 'review', 'no_frames'], 'Нет кадров'),
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Epoch8Theme.textMuted),
                        ),
                      ),
                    const SizedBox(height: 8),
                  ],
                ],
            ],
          ),
        ),
      );
      stepCards.add(const SizedBox(height: 12));
    }
    if (stepCards.isNotEmpty) stepCards.removeLast();

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
              'Проверьте данные. Можно вернуться к любому шагу — введённые значения и снимки сохраняются.',
            ),
          ),
          const SizedBox(height: Epoch8Layout.sectionGap),
          ...stepCards,
          const SizedBox(height: 8),
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

  Widget _reviewLine(String label, String value) {
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
  const _Card({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Epoch8Card(child: child);
  }
}
