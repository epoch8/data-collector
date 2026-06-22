import 'dart:async';
import 'dart:convert';

import 'package:data_collector/core/presentation/local_capture_thumb.dart';
import 'package:data_collector/core/storage/database_provider.dart';
import 'package:data_collector/features/collection/logic/collection_draft_store.dart';
import 'package:data_collector/features/collection/logic/collection_flow_resolver.dart';
import 'package:data_collector/features/collection/logic/local_package_cleanup.dart';
import 'package:data_collector/features/collection/logic/package_payload_codec.dart';
import 'package:data_collector/features/collection/logic/submit_local_package.dart';
import 'package:data_collector/features/collection/presentation/flow/package_payload_keys.dart';
import 'package:data_collector/features/collection/presentation/flow/scroll_form_flow_step.dart';
import 'package:data_collector/features/collection/providers/wizard_state_provider.dart';
import 'package:data_collector/features/projects/providers/project_providers.dart';
import 'package:data_collector/models/project_config.dart';
import 'package:data_collector/theme/epoch8_theme.dart';
import 'package:data_collector/theme/theme_controller.dart';
import 'package:data_collector/theme/epoch8_loader.dart';
import 'package:data_collector/theme/epoch8_ui.dart';
import 'package:data_collector/l10n/app_localizations.dart';
import 'package:data_collector/l10n/locale_controller.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
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

/// `camera_capture_context` или сохранённый `camera_session` + опционально `camera_debug`;
/// без устаревшего `poses`, плюс синтетические `poses` из полей ракурсов.
Map<String, dynamic>? _mergedReviewCameraContext(Map<String, dynamic> answers, List<ConfigField> cameraFields) {
  final base = <String, dynamic>{};
  void mergeMap(dynamic raw) {
    if (raw is Map) {
      raw.forEach((k, v) {
        base[k.toString()] = v;
      });
    }
  }

  mergeMap(answers[PackagePayloadKeys.cameraCaptureContext]);
  if (base.isEmpty) {
    mergeMap(answers[PackagePayloadKeys.cameraSession]);
    final dbg = answers[PackagePayloadKeys.cameraDebug];
    if (dbg != null) {
      base['_camera_debug'] = dbg;
    }
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
      skipLoadingOnReload: true,
      data: (projects) {
        late Project project;
        try {
          project = projects.firstWhere((p) => p.id == widget.projectId);
        } catch (_) {
          final loc = AppLocalizations.of(context);
          return Scaffold(
            appBar: AppBar(
              title: Text(loc.projectNotFoundShort),
              actions: [
                IconButton(
                  tooltip: loc.languageToggleTooltip,
                  onPressed: toggleAppLocale,
                  icon: Text(loc.languageCodeLabel, style: const TextStyle(fontWeight: FontWeight.w800)),
                ),
              ],
            ),
            body: Center(
              child: Text(loc.addProjectToAssets, textAlign: TextAlign.center),
            ),
          );
        }
        final flow = resolveCollectionFlow(project);
        return _CollectionDraftGate(
          projectId: widget.projectId,
          project: project,
          resolvedFlow: flow,
        );
      },
      loading: () => Scaffold(
        body: Epoch8Loader.center(),
      ),
      error: (e, _) => Scaffold(
        body: Center(child: Text('${AppLocalizations.of(context).loadingConfigError}: $e')),
      ),
    );
  }
}

enum _DraftResumeChoice { continueSession, startOver }

/// Перед сценарием: проверка локального черновика и диалог «продолжить / начать заново».
class _CollectionDraftGate extends ConsumerStatefulWidget {
  const _CollectionDraftGate({
    required this.projectId,
    required this.project,
    required this.resolvedFlow,
  });

  final String projectId;
  final Project project;
  final ResolvedCollectionFlow resolvedFlow;

  @override
  ConsumerState<_CollectionDraftGate> createState() => _CollectionDraftGateState();
}

class _CollectionDraftGateState extends ConsumerState<_CollectionDraftGate> {
  bool _ready = false;
  int _initialStep = 0;
  String? _draftPackageId;
  DateTime? _draftCreatedAt;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _runGate());
  }

  Future<void> _runGate() async {
    // На web восстановление сессии отключено: нет надёжной ФС, blob-ссылки живут
    // лишь в текущем документе, а гонки автосохранения раньше теряли «Отправленные» пакеты.
    if (kIsWeb) {
      ref.read(wizardStateProvider(widget.projectId).notifier).reset();
      if (mounted) setState(() => _ready = true);
      return;
    }

    final db = ref.read(databaseProvider);
    final draft = await selectLatestDraftForProject(db, widget.projectId);
    if (!mounted) return;

    if (draft == null) {
      ref.read(wizardStateProvider(widget.projectId).notifier).reset();
      setState(() => _ready = true);
      return;
    }

    final loc = AppLocalizations.of(context);
    final choice = await showDialog<_DraftResumeChoice>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        title: Text(loc.flowDraftDialogTitle),
        content: Text(
          loc.flowDraftDialogBody,
          style: const TextStyle(height: 1.35),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, _DraftResumeChoice.startOver),
            child: Text(loc.flowDraftStartFresh),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, _DraftResumeChoice.continueSession),
            child: Text(loc.flowDraftContinue),
          ),
        ],
      ),
    );

    if (!mounted) return;

    if (choice == null) {
      context.go('/dashboard');
      return;
    }

    if (choice == _DraftResumeChoice.startOver) {
      await deleteLocalPackageStorage(db, draft.id);
      ref.read(wizardStateProvider(widget.projectId).notifier).reset();
      setState(() {
        _ready = true;
        _initialStep = 0;
        _draftPackageId = null;
        _draftCreatedAt = null;
      });
      return;
    }

    final data = unpackPackageFormData(draft.dataJson);
    var step = draftFlowStepFromUnpackedData(data);
    data.remove(PackagePayloadKeys.collectionDraftFlowStep);
    ref.read(wizardStateProvider(widget.projectId).notifier).replaceAll(data);

    final maxStep = widget.resolvedFlow.steps.length - 1;
    if (step < 0) step = 0;
    if (step > maxStep) step = maxStep > 0 ? maxStep : 0;

    setState(() {
      _ready = true;
      _initialStep = step;
      _draftPackageId = draft.id;
      _draftCreatedAt = draft.createdAt;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (!_ready) {
      return PopScope(
        canPop: false,
        onPopInvokedWithResult: (didPop, result) {
          if (!didPop) context.go('/dashboard');
        },
        child: Scaffold(
          appBar: AppBar(
            title: Text(widget.project.name),
            actions: [
              IconButton(
                tooltip: AppLocalizations.of(context).languageToggleTooltip,
                onPressed: toggleAppLocale,
                icon: Text(AppLocalizations.of(context).languageCodeLabel, style: const TextStyle(fontWeight: FontWeight.w800)),
              ),
            ],
          ),
          body: Epoch8Loader.center(),
        ),
      );
    }
    return _FlowStepShell(
      projectId: widget.projectId,
      project: widget.project,
      resolvedFlow: widget.resolvedFlow,
      initialFlowStepIndex: _initialStep,
      initialDraftPackageId: _draftPackageId,
      initialDraftCreatedAt: _draftCreatedAt,
    );
  }
}

class _FlowStepShell extends ConsumerStatefulWidget {
  const _FlowStepShell({
    required this.projectId,
    required this.project,
    required this.resolvedFlow,
    this.initialFlowStepIndex = 0,
    this.initialDraftPackageId,
    this.initialDraftCreatedAt,
  });

  final String projectId;
  final Project project;
  final ResolvedCollectionFlow resolvedFlow;
  final int initialFlowStepIndex;
  final String? initialDraftPackageId;
  final DateTime? initialDraftCreatedAt;

  @override
  ConsumerState<_FlowStepShell> createState() => _FlowStepShellState();
}

class _FlowStepShellState extends ConsumerState<_FlowStepShell> with WidgetsBindingObserver {
  late int _step;
  String? _packageId;
  DateTime? _createdAtForRow;
  /// После «Отправить» не писать черновик поверх `completed`.
  bool _draftSaveSuspended = false;
  bool _submitting = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _step = widget.initialFlowStepIndex;
    _packageId = widget.initialDraftPackageId;
    _createdAtForRow = widget.initialDraftCreatedAt;
    appBrightnessNotifier.addListener(_onBrightnessChanged);
  }

  @override
  void dispose() {
    appBrightnessNotifier.removeListener(_onBrightnessChanged);
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  void _onBrightnessChanged() {
    if (mounted) setState(() {});
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused || state == AppLifecycleState.inactive) {
      unawaited(_persistDraftNow());
    }
  }

  /// Точечное сохранение черновика. Вызывается только по явным триггерам
  /// (фото добавлено/удалено, переход между шагами, lifecycle paused).
  /// На web — no-op: черновики не поддерживаются (см. `_CollectionDraftGate`).
  Future<void> _persistDraftNow() async {
    if (kIsWeb) return;
    if (!mounted || _draftSaveSuspended) return;
    final answers = ref.read(wizardStateProvider(widget.projectId));
    if (answers.isEmpty) return;

    _packageId ??= 'pkg_${DateTime.now().millisecondsSinceEpoch}';
    _createdAtForRow ??= DateTime.now();

    await upsertCollectionDraft(
      db: ref.read(databaseProvider),
      packageId: _packageId!,
      projectId: widget.projectId,
      answers: answers,
      flowStep: _step,
      createdAt: _createdAtForRow!,
    );
    if (!mounted) return;
  }

  Future<void> _goBack() async {
    if (_submitting) return;
    if (_step <= 0) {
      await _persistDraftNow();
      if (!mounted) return;
      context.go('/dashboard');
      return;
    }
    setState(() => _step--);
    unawaited(_persistDraftNow());
  }

  ResolvedCollectionFlow get _flow => widget.resolvedFlow;

  int get _maxStepIndex => _flow.steps.length - 1;

  /// Не даём уйти за последний шаг (двойной тап «К проверке» → пустой экран).
  void _advanceToNextStep() {
    if (_step >= _maxStepIndex) return;
    setState(() => _step++);
    unawaited(_persistDraftNow());
  }

  String _scrollContinueLabel(BuildContext context) {
    final loc = AppLocalizations.of(context);
    if (_step + 1 >= _flow.steps.length) return loc.flowNext;
    if (_flow.steps[_step + 1].kind == CollectionScreenKind.review) {
      return loc.flowToReview;
    }
    return loc.flowNext;
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
        if (!didPop) unawaited(_goBack());
      },
      child: Scaffold(
        appBar: AppBar(
          leading: IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: () => unawaited(_goBack()),
          ),
          title: Text(
            project.name,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          actions: [
            IconButton(
              tooltip: AppLocalizations.of(context).languageToggleTooltip,
              onPressed: toggleAppLocale,
              icon: Text(AppLocalizations.of(context).languageCodeLabel, style: const TextStyle(fontWeight: FontWeight.w800)),
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
    final loc = AppLocalizations.of(context);
    if (_step < 0 || _step >= _flow.steps.length) return const [];
    final cur = _flow.steps[_step];

    if (cur.kind == CollectionScreenKind.review) {
      return [
        Padding(
          padding: const EdgeInsets.fromLTRB(Epoch8Layout.pagePadding, 10, Epoch8Layout.pagePadding, 4),
          child: Text(
            loc.flowRibbonReview,
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
                    loc.flowRibbonScrollForm,
                    style: t.labelSmall?.copyWith(color: Epoch8Theme.textMuted, letterSpacing: 1.1),
                  ),
                  Text(
                    loc.flowScrollCounter(ord, totalScroll),
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
          continueLabel: _scrollContinueLabel(context),
          onContinue: _advanceToNextStep,
          onPhotoChanged: () {
            unawaited(_persistDraftNow());
          },
        );
      case CollectionScreenKind.review:
        return _FlowReviewStep(
          key: ValueKey('flow_review_$_step'),
          project: p,
          flow: _flow,
          projectId: widget.projectId,
          submitting: _submitting,
          onEditScrollStep: (int stepIndex) {
            if (_submitting) return;
            setState(() => _step = stepIndex.clamp(0, _maxStepIndex));
            unawaited(_persistDraftNow());
          },
          onSubmit: () async {
            if (_submitting) return;
            await _persistDraftNow();
            if (!context.mounted) return;
            _draftSaveSuspended = true;
            setState(() => _submitting = true);
            final answers = Map<String, dynamic>.from(ref.read(wizardStateProvider(widget.projectId)));
            await submitLocalPackage(
              ref: ref,
              context: context,
              projectId: widget.projectId,
              answers: answers,
              existingDraftPackageId: _packageId,
              draftCreatedAt: _createdAtForRow,
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
    this.submitting = false,
  });

  final Project project;
  final ResolvedCollectionFlow flow;
  final String projectId;
  final void Function(int flowStepIndex) onEditScrollStep;
  final Future<void> Function() onSubmit;
  final bool submitting;

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
  String _reviewScrollBlockTitle(AppLocalizations loc, ResolvedCollectionStep s, int scrollOrdinal) {
    final label = (s.formTitle ?? '').trim();
    if (label.isNotEmpty) {
      return loc.flowReviewScrollBlockTitle(scrollOrdinal, label);
    }
    return loc.flowReviewScrollBlockStepOnly(scrollOrdinal);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final loc = AppLocalizations.of(context);
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
                      _reviewScrollBlockTitle(loc, s, scrollOrdinal),
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
                    ),
                  ),
                  TextButton(
                    onPressed: () => onEditScrollStep(i),
                    child: Text(loc.flowReviewEdit),
                  ),
                ],
              ),
              const Divider(height: 22),
              if (s.isInstructionOnlyScroll)
                Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Text(
                    loc.flowReviewInstructionOnlyHint,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Epoch8Theme.textMuted),
                  ),
                ),
              if (!s.isInstructionOnlyScroll)
                for (final f in s.fields) ...[
                  if (f.type == 'text_input' || f.type == 'datetime')
                    _reviewLine(
                      f.title,
                      _formatReviewValue(loc, f, a[f.fieldId]),
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
                            child: localCaptureThumbnail(p, size: 72),
                          ),
                      ],
                    ),
                    if (CapturedPhotoPaths.list(a[f.fieldId]).isEmpty)
                      Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Text(
                          loc.flowReviewNoFrames,
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
            overline: loc.flowReviewHeaderOverline,
            title: loc.flowReviewHeaderTitle,
            subtitle: loc.flowReviewHeaderSubtitle,
          ),
          const SizedBox(height: Epoch8Layout.sectionGap),
          ...stepCards,
          const SizedBox(height: 8),
          _CameraMetaReviewPanel(cameraContext: cameraCtx),
          const SizedBox(height: 24),
          FilledButton(
            onPressed: complete && !submitting
                ? () async {
                    await onSubmit();
                  }
                : null,
            child: submitting
                ? SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(strokeWidth: 2, color: Theme.of(context).colorScheme.onPrimary),
                  )
                : Text(loc.flowReviewSubmit),
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
          SizedBox(width: 110, child: Text(label, style: TextStyle(color: Epoch8Theme.textMuted))),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }

  String _formatReviewValue(AppLocalizations loc, ConfigField f, dynamic v) {
    final dash = loc.flowReviewEmptyValue;
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
  const _CameraMetaReviewPanel({this.cameraContext});

  final Map<String, dynamic>? cameraContext;

  static String? _subtitle(AppLocalizations loc, Map<String, dynamic> ctx) {
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
            final fc = sh['frame_camera'];
            if (fc is Map && fc['fx_px'] != null) {
              fxHint = loc.flowCameraMetaFxEstimate(_fmtNum(fc['fx_px']));
              break outer;
            }
            final d = _shotDerivedMap(sh);
            if (d != null && d['preferred_fx_px_estimate'] != null) {
              fxHint = loc.flowCameraMetaFxEstimate(_fmtNum(d['preferred_fx_px_estimate']));
              break outer;
            }
          }
        }
        final fc0 = v['frame_camera'];
        if (fc0 is Map && fc0['fx_px'] != null) {
          fxHint = loc.flowCameraMetaFxEstimate(_fmtNum(fc0['fx_px']));
          break;
        }
        final d = _shotDerivedMap(v);
        if (d != null && d['preferred_fx_px_estimate'] != null) {
          fxHint = loc.flowCameraMetaFxEstimate(_fmtNum(d['preferred_fx_px_estimate']));
          break;
        }
      }
    }
    final parts = <String>[];
    if (model != null && model.isNotEmpty) parts.add(model);
    if (fxHint != null) parts.add(fxHint);
    return parts.isEmpty
        ? loc.flowCameraMetaTapToExpand
        : parts.join(' · ');
  }

  static String _fmtNum(dynamic v) {
    if (v is double) return v.toStringAsFixed(v.abs() >= 1000 ? 0 : 1);
    if (v is int) return v.toString();
    return v.toString();
  }

  static Map<String, dynamic>? _shotDerivedMap(Map<dynamic, dynamic> sh) {
    final d = sh['derived'];
    if (d is Map<String, dynamic>) return d;
    if (d is Map) return Map<String, dynamic>.from(d.map((k, v) => MapEntry(k.toString(), v)));
    final sup = sh['camera_supplement'];
    if (sup is Map) {
      final inner = sup['derived'];
      if (inner is Map<String, dynamic>) return inner;
      if (inner is Map) return Map<String, dynamic>.from(inner.map((k, v) => MapEntry(k.toString(), v)));
    }
    return null;
  }

  static Map<String, dynamic>? _shotExifMap(Map<dynamic, dynamic> sh) {
    final x = sh['exif'];
    if (x is Map<String, dynamic>) return x;
    if (x is Map) return Map<String, dynamic>.from(x.map((k, v) => MapEntry(k.toString(), v)));
    final sup = sh['camera_supplement'];
    if (sup is Map) {
      final inner = sup['exif'];
      if (inner is Map<String, dynamic>) return inner;
      if (inner is Map) return Map<String, dynamic>.from(inner.map((k, v) => MapEntry(k.toString(), v)));
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context);
    final ctx = cameraContext;
    if (ctx == null || ctx.isEmpty) {
      return _Card(
        child: Row(
          children: [
            Icon(Icons.info_outline, size: 20, color: Epoch8Theme.textMuted.withValues(alpha: 0.9)),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                loc.flowCameraMetaEmptyNotice,
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
                      loc.flowCameraMetaTileTitle,
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _subtitle(loc, Map<String, dynamic>.from(ctx)) ?? '',
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
              loc.flowCameraMetaSectionDevice,
              _deviceRows(loc, ctx['device']),
            ),
            _metaSection(
              context,
              loc.flowCameraMetaSectionNative,
              _nativeRows(loc, ctx['native_back_camera']),
            ),
            ..._poseMetaSections(context, loc, ctx['poses']),
            Theme(
              data: Theme.of(context).copyWith(dividerColor: Epoch8Theme.border),
              child: ExpansionTile(
                tilePadding: EdgeInsets.zero,
                title: Text(
                  loc.flowCameraMetaJsonSection,
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

  List<Widget> _deviceRows(AppLocalizations loc, dynamic device) {
    if (device is! Map) {
      return [
        Text(loc.flowReviewEmptyValue, style: TextStyle(color: Epoch8Theme.textMuted)),
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

  List<Widget> _nativeRows(AppLocalizations loc, dynamic native) {
    if (native is! Map || native.isEmpty) {
      return [
        Text(
          loc.flowCameraMetaNativeEmpty,
          style: TextStyle(color: Epoch8Theme.textMuted, fontSize: 13),
        ),
      ];
    }
    final m = <String, dynamic>{};
    native.forEach((k, v) => m[k.toString()] = v);
    final priority = [
      'source',
      'metadata_schema_version',
      'primary_focal_length_mm',
      'focal_lengths_mm',
      'lens_intrinsic_calibration_px',
      'lens_intrinsic_calibration_order',
      'lens_distortion',
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
      String text;
      if (k == 'camera2_characteristics' && v is Map) {
        text = '$k: ${loc.flowCameraMetaNativeMapSummary(v.length)}';
      } else {
        text = '$k: $v';
      }
      out.add(Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: SelectableText(text, style: const TextStyle(fontSize: 13, height: 1.35)),
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

  List<Widget> _poseMetaSections(BuildContext context, AppLocalizations loc, dynamic poses) {
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
          final shotMap = Map<dynamic, dynamic>.from(sh);
          list.add(
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: _metaSection(
                context,
                loc.flowCameraMetaPoseShotTitle(idx, si + 1),
                _shotMetaRows(loc, shotMap),
              ),
            ),
          );
        }
      } else {
        final shotMap = Map<dynamic, dynamic>.from(p);
        list.add(
          Padding(
            padding: const EdgeInsets.only(top: 12),
            child: _metaSection(
              context,
              loc.flowCameraMetaPoseDerivedTitle(idx),
              _shotMetaRows(loc, shotMap),
            ),
          ),
        );
      }
    }
    return list;
  }

  List<Widget> _shotMetaRows(AppLocalizations loc, Map<dynamic, dynamic> shot) {
    final fc = shot['frame_camera'];
    final derived = _shotDerivedMap(shot);
    final exif = _shotExifMap(shot);
    return [
      if (fc is Map) ...[
        Text(
          loc.flowCameraMetaFrameCameraHeading,
          style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Epoch8Theme.accent),
        ),
        const SizedBox(height: 4),
        if (fc['fx_px'] != null) _selLine('fx_px', fc['fx_px']),
        if (fc['fy_px'] != null) _selLine('fy_px', fc['fy_px']),
        if (fc['cx_px'] != null) _selLine('cx_px', fc['cx_px']),
        if (fc['cy_px'] != null) _selLine('cy_px', fc['cy_px']),
        if (fc['image_width_px'] != null) _selLine('image_width_px', fc['image_width_px']),
        if (fc['image_height_px'] != null) _selLine('image_height_px', fc['image_height_px']),
        if (fc['intrinsics_source'] != null) _selLine('intrinsics_source', fc['intrinsics_source']),
        if (fc['focal_length_mm'] != null) _selLine('focal_length_mm', fc['focal_length_mm']),
        const SizedBox(height: 8),
      ],
      if (derived != null) ...[
        Text(
          loc.flowCameraMetaDerivedHeading,
          style: TextStyle(fontSize: 12, color: Epoch8Theme.textMuted),
        ),
        const SizedBox(height: 4),
        if (derived['preferred_fx_px_estimate'] != null)
          _selLine('preferred_fx_px_estimate', derived['preferred_fx_px_estimate']),
        if (derived['fx_px_from_exif_focal_and_native_sensor'] != null)
          _selLine(
            loc.flowCameraMetaLabelFxExif,
            derived['fx_px_from_exif_focal_and_native_sensor'],
          ),
        if (derived['fx_px_from_35mm_equiv'] != null)
          _selLine(
            loc.flowCameraMetaLabelFx35mm,
            derived['fx_px_from_35mm_equiv'],
          ),
        if (derived['fx_px_from_native_mm'] != null)
          _selLine(
            loc.flowCameraMetaLabelFxNative,
            derived['fx_px_from_native_mm'],
          ),
        const SizedBox(height: 8),
      ],
      if (exif != null && exif.isNotEmpty) ...[
        Text(
          loc.flowCameraMetaExifHeading,
          style: TextStyle(fontSize: 12, color: Epoch8Theme.textMuted),
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
            loc.flowCameraMetaExifMore(exif.length - 12),
            style: TextStyle(fontSize: 11, color: Epoch8Theme.textMuted),
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
