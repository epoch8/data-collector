import 'package:data_collector/core/presentation/local_capture_thumb.dart';
import 'package:data_collector/core/device/camera_metadata_collector.dart';
import 'package:data_collector/core/storage/database_provider.dart';
import 'package:data_collector/core/quality/image_quality_analyzer.dart';
import 'package:data_collector/features/collection/logic/collection_flow_resolver.dart';
import 'package:data_collector/features/collection/logic/package_payload_codec.dart';
import 'package:data_collector/features/collection/presentation/flow/package_payload_keys.dart';
import 'package:data_collector/features/collection/presentation/flow/project_example_image.dart';
import 'package:data_collector/features/collection/providers/wizard_state_provider.dart';
import 'package:data_collector/models/project_config.dart';
import 'package:data_collector/theme/epoch8_theme.dart';
import 'package:data_collector/theme/theme_controller.dart';
import 'package:data_collector/theme/epoch8_ui.dart';
import 'package:data_collector/l10n/app_localizations.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

String _formatDateTime(DateTime d) {
  String two(int n) => n.toString().padLeft(2, '0');
  return '${d.year}-${two(d.month)}-${two(d.day)} ${two(d.hour)}:${two(d.minute)}';
}

/// Один шаг сценария: только поля из `scroll_form` (текст, дата, markdown-инструкция, камера).
class ScrollFormFlowStep extends ConsumerStatefulWidget {
  const ScrollFormFlowStep({
    super.key,
    required this.project,
    required this.projectId,
    required this.flow,
    required this.step,
    required this.continueLabel,
    required this.onContinue,
    this.onPhotoChanged,
  });

  final Project project;
  final String projectId;
  final ResolvedCollectionFlow flow;
  final ResolvedCollectionStep step;
  final String continueLabel;
  final VoidCallback onContinue;

  /// Триггер сохранения черновика после изменения снимков (на web игнорируется родителем).
  final VoidCallback? onPhotoChanged;

  @override
  ConsumerState<ScrollFormFlowStep> createState() => _ScrollFormFlowStepState();
}

class _ScrollFormFlowStepState extends ConsumerState<ScrollFormFlowStep> {
  final Map<String, TextEditingController> _textCtrls = {};
  final Map<String, DateTime> _dateTimes = {};

  /// Нельзя вызывать `ref` из [dispose] — элемент уже «мертвый»; нотификатор держим с initState.
  late final WizardState _wizardNotifier;

  @override
  void initState() {
    super.initState();
    _wizardNotifier = ref.read(wizardStateProvider(widget.projectId).notifier);
    final s = ref.read(wizardStateProvider(widget.projectId));
    for (final f in widget.step.fields) {
      if (f.type == 'text_input') {
        _textCtrls[f.fieldId] = TextEditingController(
          text: s[f.fieldId]?.toString() ?? '',
        );
      } else if (f.type == 'datetime') {
        _dateTimes[f.fieldId] = _parseDt(s[f.fieldId]) ?? DateTime.now();
      }
    }
    appBrightnessNotifier.addListener(_onBrightnessChanged);
  }

  DateTime? _parseDt(dynamic v) {
    if (v == null) return null;
    if (v is DateTime) return v;
    if (v is String) return DateTime.tryParse(v);
    return null;
  }

  @override
  void dispose() {
    appBrightnessNotifier.removeListener(_onBrightnessChanged);
    _persistToWizard();
    for (final c in _textCtrls.values) {
      c.dispose();
    }
    super.dispose();
  }

  void _onBrightnessChanged() {
    if (mounted) setState(() {});
  }

  void _persistToWizard() {
    for (final e in _textCtrls.entries) {
      _wizardNotifier.updateField(e.key, e.value.text.trim());
    }
    for (final e in _dateTimes.entries) {
      _wizardNotifier.updateField(e.key, e.value.toIso8601String());
    }
  }

  /// Текст/дата должны попадать в [wizardStateProvider] при вводе — иначе черновик в БД
  /// (слушатель в [CollectionFlowScreen]) не видит их до нажатия «Далее».
  void _syncTextFieldToWizard(String fieldId, String text) {
    ref
        .read(wizardStateProvider(widget.projectId).notifier)
        .updateField(fieldId, text);
  }

  void _syncDatetimeToWizard(String fieldId, DateTime dt) {
    ref
        .read(wizardStateProvider(widget.projectId).notifier)
        .updateField(fieldId, dt.toIso8601String());
  }

  bool _stepValid(Map<String, dynamic> answers) {
    for (final f in widget.step.fields) {
      if (!configFieldRequired(f)) continue;
      if (f.type == 'text_input') {
        final t = _textCtrls[f.fieldId]?.text.trim() ?? '';
        if (t.isEmpty) return false;
      } else if (f.type == 'datetime') {
        /* ok */
      } else if (f.type == 'instruction') {
        /* контент в конфиге */
      } else if (f.type == 'camera_photo') {
        if (!CapturedPhotoPaths.hasPhotos(answers[f.fieldId])) return false;
      }
    }
    return true;
  }

  String? _cowMatchFieldId() {
    final id = widget.step.cowIdFieldId;
    if (id != null && widget.step.fields.any((f) => f.fieldId == id)) return id;
    for (final f in widget.step.fields) {
      if (f.type == 'text_input' && f.fieldId == 'cow_identifier')
        return f.fieldId;
    }
    return widget.step.fields
        .where((f) => f.type == 'text_input')
        .firstOrNull
        ?.fieldId;
  }

  @override
  Widget build(BuildContext context) {
    final answers = ref.watch(wizardStateProvider(widget.projectId));
    final useCow = widget.step.cowIdHints;
    final cowMatch = _cowMatchFieldId();
    final cowCtrl = cowMatch != null ? _textCtrls[cowMatch] : null;
    final typedCowId = cowCtrl?.text.trim() ?? '';
    final typedLower = typedCowId.toLowerCase();

    final packages =
        ref.watch(packagesStreamProvider).asData?.value ?? const [];
    final matchedIds = <String>{};
    Map<String, dynamic>? exactData;
    DateTime? exactCreatedAt;

    if (useCow && typedLower.isNotEmpty && cowCtrl != null) {
      for (final pkg in packages) {
        if (pkg.projectId != widget.projectId) continue;
        if (pkg.status == 'draft') continue;
        final payload = unpackPackageFormData(pkg.dataJson);
        final existingCowId = _payloadCowId(payload, cowMatch) ?? '';
        if (existingCowId.isEmpty) continue;
        final existingLower = existingCowId.toLowerCase();
        if (existingLower.contains(typedLower)) matchedIds.add(existingCowId);
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

    void prefillFrom(Map<String, dynamic> data) {
      setState(() {
        for (final f in widget.step.fields) {
          if (f.type == 'datetime') {
            final pt = _parseDt(data[f.fieldId]);
            if (pt != null) _dateTimes[f.fieldId] = pt;
          } else if (f.type == 'text_input') {
            final c = _textCtrls[f.fieldId];
            if (c != null && data[f.fieldId] != null) {
              c.text = data[f.fieldId].toString();
            }
          }
        }
      });
      _persistToWizard();
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(
        Epoch8Layout.pagePadding,
        8,
        Epoch8Layout.pagePadding,
        28,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          for (final f in widget.step.fields) ...[
            _FieldCard(
              child: _buildField(
                context,
                f,
                answers,
                useCow: useCow,
                cowMatch: cowMatch,
                typedCowId: typedCowId,
                typedLower: typedLower,
                hasExactMatch: hasExactMatch,
                hasAnyMatches: hasAnyMatches,
                matchedIds: matchedIds,
                cowCtrl: cowCtrl,
                exactData: exactData,
                prefillFrom: prefillFrom,
              ),
            ),
            const SizedBox(height: 16),
          ],
          FilledButton(
            onPressed: _stepValid(answers)
                ? () {
                    _persistToWizard();
                    widget.onContinue();
                  }
                : null,
            child: Text(widget.continueLabel),
          ),
        ],
      ),
    );
  }

  String? _payloadCowId(Map<String, dynamic> payload, String? key) {
    final a = key != null ? payload[key]?.toString().trim() : null;
    if (a != null && a.isNotEmpty) return a;
    final b =
        payload['cow_identifier']?.toString().trim() ??
        payload['cow_id']?.toString().trim();
    if (b != null && b.isNotEmpty) return b;
    return null;
  }

  Widget _buildField(
    BuildContext context,
    ConfigField f,
    Map<String, dynamic> answers, {
    required bool useCow,
    required String? cowMatch,
    required String typedCowId,
    required String typedLower,
    required bool hasExactMatch,
    required bool hasAnyMatches,
    required Set<String> matchedIds,
    required TextEditingController? cowCtrl,
    required Map<String, dynamic>? exactData,
    required void Function(Map<String, dynamic>) prefillFrom,
  }) {
    final loc = AppLocalizations.of(context);
    switch (f.type) {
      case 'text_input':
        final c = _textCtrls[f.fieldId];
        if (c == null) return const SizedBox.shrink();
        final isCowId = cowMatch != null && f.fieldId == cowMatch;
        if (useCow && isCowId) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                f.title,
                style: Theme.of(
                  context,
                ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: c,
                decoration: InputDecoration(
                  hintText: f.instructions,
                  helperText: typedCowId.isEmpty
                      ? null
                      : hasExactMatch
                      ? loc.flowFormSubjectHintExact
                      : hasAnyMatches
                      ? loc.flowFormSubjectHintSimilar
                      : loc.flowFormSubjectHintNew,
                  helperStyle: TextStyle(
                    color: hasExactMatch
                        ? Epoch8Theme.success
                        : hasAnyMatches
                        ? Epoch8Theme.accent
                        : Epoch8Theme.textMuted,
                  ),
                ),
                onChanged: (_) {
                  _syncTextFieldToWizard(f.fieldId, c.text);
                  setState(() {});
                },
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
                          cc.selection = TextSelection.fromPosition(
                            TextPosition(offset: cc.text.length),
                          );
                          _syncTextFieldToWizard(f.fieldId, cc.text);
                        }
                        setState(() {});
                      },
                    );
                  }).toList(),
                ),
              ],
              if (hasExactMatch && exactData != null) ...[
                const SizedBox(height: 8),
                TextButton.icon(
                  onPressed: () => prefillFrom(exactData),
                  icon: const Icon(Icons.auto_fix_high_outlined, size: 18),
                  label: Text(loc.flowFormPrefillButton),
                ),
              ],
            ],
          );
        }
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              f.title,
              style: Theme.of(
                context,
              ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: c,
              decoration: InputDecoration(hintText: f.instructions),
              onChanged: (_) {
                _syncTextFieldToWizard(f.fieldId, c.text);
                setState(() {});
              },
            ),
          ],
        );
      case 'datetime':
        final dt = _dateTimes[f.fieldId] ?? DateTime.now();
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              f.title,
              style: Theme.of(
                context,
              ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(child: Text(_formatDateTime(dt.toLocal()))),
                TextButton(
                  onPressed: () async {
                    final d = await showDatePicker(
                      context: context,
                      initialDate: dt,
                      firstDate: DateTime(2020),
                      lastDate: DateTime(2100),
                    );
                    if (d == null || !mounted) return;
                    final t = await showTimePicker(
                      context: context,
                      initialTime: TimeOfDay.fromDateTime(dt),
                    );
                    if (t == null || !mounted) return;
                    setState(() {
                      _dateTimes[f.fieldId] = DateTime(
                        d.year,
                        d.month,
                        d.day,
                        t.hour,
                        t.minute,
                      );
                    });
                    _syncDatetimeToWizard(f.fieldId, _dateTimes[f.fieldId]!);
                  },
                  child: Text(loc.flowFormDatetimeChange),
                ),
              ],
            ),
          ],
        );
      case 'instruction':
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (f.instructions.trim().isNotEmpty)
              MarkdownBody(
                data: f.instructions,
                selectable: true,
                styleSheet: MarkdownStyleSheet.fromTheme(Theme.of(context))
                    .copyWith(
                      p: Theme.of(
                        context,
                      ).textTheme.bodyMedium?.copyWith(height: 1.45),
                      h1: Theme.of(context).textTheme.headlineSmall,
                      h2: Theme.of(context).textTheme.titleLarge,
                    ),
                imageBuilder: (uri, title, alt) {
                  final ref = markdownImageRefFromUri(uri);
                  if (ref == null || ref.isEmpty) {
                    return const SizedBox.shrink();
                  }
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 10),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(
                        Epoch8Layout.radiusMd,
                      ),
                      child: projectExampleImage(
                        project: widget.project,
                        assetPath: ref,
                        fit: BoxFit.contain,
                        errorPlaceholder: (_) => Container(
                          color: Epoch8Theme.bgElevated,
                          alignment: Alignment.center,
                          padding: const EdgeInsets.all(16),
                          child: Text(
                            loc.flowCameraPoseExampleAssetMissing,
                            textAlign: TextAlign.center,
                            style: TextStyle(color: Epoch8Theme.textMuted),
                          ),
                        ),
                      ),
                    ),
                  );
                },
              )
            else
              Text(
                loc.flowFormInstructionEmpty,
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: Epoch8Theme.textMuted),
              ),
          ],
        );
      case 'camera_photo':
        final poseIdx = widget.flow.cameraPoseIndex1Based(f);
        final total = widget.flow.cameraPoseCount;
        return _ScrollCameraBlock(
          project: widget.project,
          projectId: widget.projectId,
          field: f,
          poseIndex1Based: poseIdx,
          totalPoses: total,
          onPhotoChanged: widget.onPhotoChanged,
        );
      default:
        return Text(
          '${loc.unsupportedFieldType} (${f.type})',
          style: TextStyle(color: Epoch8Theme.danger),
        );
    }
  }
}

class _FieldCard extends StatelessWidget {
  const _FieldCard({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Epoch8Theme.card.withValues(alpha: 0.35),
        border: Border.all(color: Epoch8Theme.border),
        borderRadius: BorderRadius.circular(16),
      ),
      child: child,
    );
  }
}

class _ScrollCameraBlock extends ConsumerStatefulWidget {
  const _ScrollCameraBlock({
    required this.project,
    required this.projectId,
    required this.field,
    required this.poseIndex1Based,
    required this.totalPoses,
    this.onPhotoChanged,
  });

  final Project project;
  final String projectId;
  final ConfigField field;
  final int poseIndex1Based;
  final int totalPoses;

  /// Сигнал родителю: пора зафиксировать состояние сборки на диск.
  final VoidCallback? onPhotoChanged;

  @override
  ConsumerState<_ScrollCameraBlock> createState() => _ScrollCameraBlockState();
}

class _ScrollCameraBlockState extends ConsumerState<_ScrollCameraBlock> {
  final _picker = ImagePicker();

  String get _key => widget.field.fieldId;

  Future<void> _pick(ImageSource source) async {
    final x = await _picker.pickImage(source: source);
    if (x == null || !mounted) return;

    if (!kIsWeb) {
      final quality = await analyzeCaptureQuality(x.path);
      if (!mounted) return;
      if (!quality.isAcceptable) {
        final loc = AppLocalizations.of(context);
        final useAnyway = await showDialog<bool>(
          context: context,
          barrierDismissible: false,
          builder: (ctx) => AlertDialog(
            title: Text(loc.flowCameraPoseQualityTitle),
            content: SingleChildScrollView(child: Text(quality.userMessage)),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx, true),
                child: Text(loc.flowCameraPoseUseAnyway),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: Text(loc.flowCameraPoseRetake),
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
      poseFieldId: _key,
      imagePath: x.path,
    );
    if (!mounted) return;
    setState(() {});
    widget.onPhotoChanged?.call();
  }

  void _remove(String path) {
    CameraMetadataCollector.removePoseShotByPath(
      ref: ref,
      projectId: widget.projectId,
      poseFieldId: _key,
      imagePath: path,
    );
    setState(() {});
    widget.onPhotoChanged?.call();
  }

  void _clear() {
    CameraMetadataCollector.stripLegacyContextPoses(
      ref: ref,
      projectId: widget.projectId,
    );
    ref
        .read(wizardStateProvider(widget.projectId).notifier)
        .updateField(_key, null);
    setState(() {});
    widget.onPhotoChanged?.call();
  }

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context);
    final answers = ref.watch(wizardStateProvider(widget.projectId));
    final paths = CapturedPhotoPaths.list(answers[_key]);
    const sep = '·';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Expanded(
              child: Text(
                widget.field.title,
                style: Theme.of(
                  context,
                ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w600),
              ),
            ),
            Text(
              '${widget.poseIndex1Based}$sep${widget.totalPoses}',
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                color: Epoch8Theme.accent,
                fontWeight: FontWeight.w800,
              ),
            ),
          ],
        ),
        if (widget.field.instructions.trim().isNotEmpty) ...[
          const SizedBox(height: 8),
          Text(
            widget.field.instructions,
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(height: 1.35),
          ),
        ],
        const SizedBox(height: 16),
        Text(
          loc.flowCameraPoseYourShots(paths.length),
          style: Theme.of(context).textTheme.titleSmall,
        ),
        const SizedBox(height: 8),
        if (paths.isEmpty)
          Text(
            loc.flowCameraPoseEmptyHint,
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: Epoch8Theme.textMuted),
          )
        else
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (var i = 0; i < paths.length; i++)
                _Thumb(
                  path: paths[i],
                  index: i + 1,
                  onRemove: () => _remove(paths[i]),
                ),
            ],
          ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: FilledButton.icon(
                onPressed: () => _pick(ImageSource.camera),
                icon: const Icon(Icons.photo_camera_outlined),
                label: Text(loc.flowCameraPoseCamera),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () => _pick(ImageSource.gallery),
                icon: const Icon(Icons.photo_library_outlined),
                label: Text(loc.flowCameraPoseGallery),
              ),
            ),
          ],
        ),
        if (paths.isNotEmpty)
          TextButton.icon(
            onPressed: _clear,
            icon: Icon(Icons.delete_sweep_outlined, color: Epoch8Theme.danger),
            label: Text(loc.flowCameraPoseClearAll),
          ),
      ],
    );
  }
}

class _Thumb extends StatelessWidget {
  const _Thumb({
    required this.path,
    required this.index,
    required this.onRemove,
  });

  final String path;
  final int index;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    return Stack(
      clipBehavior: Clip.none,
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: localCaptureThumbnail(path, size: 88),
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
            child: Text(
              '$index',
              style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
            ),
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
              child: Padding(
                padding: const EdgeInsets.all(4),
                child: Icon(Icons.close, size: 16, color: Epoch8Theme.bgDeep),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

extension _FirstOrNull<E> on Iterable<E> {
  E? get firstOrNull {
    final i = iterator;
    return i.moveNext() ? i.current : null;
  }
}
