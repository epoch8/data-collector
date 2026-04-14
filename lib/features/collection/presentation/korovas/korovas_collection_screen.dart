import 'dart:convert';
import 'dart:io';

import 'package:data_collector/core/device/camera_metadata_collector.dart';
import 'package:data_collector/core/quality/image_quality_analyzer.dart';
import 'package:data_collector/core/storage/database_provider.dart';
import 'package:data_collector/features/collection/logic/submit_local_package.dart';
import 'package:data_collector/features/collection/presentation/korovas/korovas_keys.dart';
import 'package:data_collector/features/collection/presentation/korovas/korovas_shooting_guide.dart';
import 'package:data_collector/features/collection/providers/wizard_state_provider.dart';
import 'package:data_collector/features/projects/providers/project_providers.dart';
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

/// Form scan → справка по съёмке → 3 ракурса → review & submit (same local DB submit as legacy wizard).
///
/// Состояние [wizardStateProvider] не сбрасываем в [initState]: изменение провайдера
/// в жизненном цикле запрещено Riverpod. После ухода на дашборд провайдер autoDispose
/// очищается сам; при новом входе сессия пустая.
class KorovasCollectionScreen extends ConsumerStatefulWidget {
  const KorovasCollectionScreen({super.key, required this.projectId});

  final String projectId;

  @override
  ConsumerState<KorovasCollectionScreen> createState() => _KorovasCollectionScreenState();
}

class _KorovasCollectionScreenState extends ConsumerState<KorovasCollectionScreen> {
  /// 0 = form, 1 = справка по съёмке, 2..4 = ракурсы, 5 = review
  int _step = 0;

  void _goBack() {
    if (_step <= 0) {
      context.go('/dashboard');
      return;
    }
    setState(() => _step--);
  }

  @override
  Widget build(BuildContext context) {
    // Держим wizardState живым на всех шагах: при autoDispose без подписчика
    // провайдер сбрасывается между сменой детей в AnimatedSwitcher — терялись
    // данные анкеты на экране проверки.
    ref.watch(wizardStateProvider(widget.projectId));

    final projects = ref.watch(mockProjectsProvider);
    final project = projects.firstWhere((p) => p.id == widget.projectId);

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
                tooltip: 'Справка по съёмке',
                onPressed: () => showKorovasShootingHelp(context),
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

  /// Верхняя полоса контекста шага (под AppBar).
  List<Widget> _stepRibbon(BuildContext context) {
    final t = Theme.of(context).textTheme;
    if (_step >= 2 && _step <= 4) {
      final pi = _step - 1;
      return [
        Padding(
          padding: const EdgeInsets.fromLTRB(Epoch8Layout.pagePadding, 10, Epoch8Layout.pagePadding, 6),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('Съёмка', style: t.labelSmall?.copyWith(color: Epoch8Theme.textMuted, letterSpacing: 1.1)),
                  Text(
                    '${korovasPoseGuides[pi - 1].shortLabel} · $pi/3',
                    style: t.labelLarge?.copyWith(color: Epoch8Theme.accent, fontWeight: FontWeight.w800),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Epoch8StepDots(current: pi - 1, total: 3),
            ],
          ),
        ),
      ];
    }
    if (_step == 1) {
      return [
        Padding(
          padding: const EdgeInsets.fromLTRB(Epoch8Layout.pagePadding, 8, Epoch8Layout.pagePadding, 4),
          child: Align(
            alignment: Alignment.centerLeft,
            child: Text(
              'Справка перед съёмкой',
              style: t.titleSmall?.copyWith(color: Epoch8Theme.textMuted, fontWeight: FontWeight.w600),
            ),
          ),
        ),
      ];
    }
    if (_step == 5) {
      return [
        Padding(
          padding: const EdgeInsets.fromLTRB(Epoch8Layout.pagePadding, 10, Epoch8Layout.pagePadding, 4),
          child: Text(
            'Проверка и отправка',
            style: t.labelMedium?.copyWith(color: Epoch8Theme.textMuted, letterSpacing: 0.4),
          ),
        ),
      ];
    }
    if (_step == 0) {
      return [
        Padding(
          padding: const EdgeInsets.fromLTRB(Epoch8Layout.pagePadding, 10, Epoch8Layout.pagePadding, 2),
          child: Text(
            'Анкета',
            style: t.labelMedium?.copyWith(color: Epoch8Theme.textMuted, letterSpacing: 0.4),
          ),
        ),
      ];
    }
    return const [];
  }

  Widget _buildStep(BuildContext context) {
    switch (_step) {
      case 0:
        return _KorovasFormScan(
          key: const ValueKey('korovas_form'),
          projectId: widget.projectId,
          onContinue: () => setState(() => _step = 1),
        );
      case 1:
        return _KorovasShootingBriefing(
          key: const ValueKey('korovas_briefing'),
          onContinue: () => setState(() => _step = 2),
        );
      case 2:
      case 3:
      case 4:
        final poseIndex = _step - 1;
        return _KorovasPoseStep(
          key: ValueKey('korovas_pose_$poseIndex'),
          projectId: widget.projectId,
          poseIndex: poseIndex,
          guide: korovasPoseGuides[poseIndex - 1],
          onNext: () => setState(() => _step++),
        );
      case 5:
        return _KorovasReviewStep(
          key: const ValueKey('korovas_review'),
          projectId: widget.projectId,
          onEditForm: () => setState(() => _step = 0),
          onEditPose: (int poseIndex) => setState(() => _step = poseIndex + 1),
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
      default:
        return const SizedBox.shrink();
    }
  }
}

class _KorovasFormScan extends ConsumerStatefulWidget {
  const _KorovasFormScan({
    super.key,
    required this.projectId,
    required this.onContinue,
  });

  final String projectId;
  final VoidCallback onContinue;

  @override
  ConsumerState<_KorovasFormScan> createState() => _KorovasFormScanState();
}

class _KorovasFormScanState extends ConsumerState<_KorovasFormScan> {
  late DateTime _scanTime;
  late final TextEditingController _cowId;
  late final TextEditingController _age;
  late final TextEditingController _weight;
  late final TextEditingController _breed;

  @override
  void initState() {
    super.initState();
    final s = ref.read(wizardStateProvider(widget.projectId));
    _scanTime = _parseScanTime(s[KorovasKeys.scanTime]) ?? DateTime.now();
    _cowId = TextEditingController(text: s[KorovasKeys.cowId]?.toString() ?? '');
    _age = TextEditingController(text: s[KorovasKeys.cowAge]?.toString() ?? '');
    _weight = TextEditingController(text: s[KorovasKeys.cowWeight]?.toString() ?? '');
    _breed = TextEditingController(text: s[KorovasKeys.cowBreed]?.toString() ?? '');
  }

  DateTime? _parseScanTime(dynamic v) {
    if (v == null) return null;
    if (v is DateTime) return v;
    if (v is String) return DateTime.tryParse(v);
    return null;
  }

  @override
  void dispose() {
    _cowId.dispose();
    _age.dispose();
    _weight.dispose();
    _breed.dispose();
    super.dispose();
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
    return _cowId.text.trim().isNotEmpty &&
        _age.text.trim().isNotEmpty &&
        _weight.text.trim().isNotEmpty &&
        _breed.text.trim().isNotEmpty;
  }

  void _saveToState() {
    final n = ref.read(wizardStateProvider(widget.projectId).notifier);
    n.updateField(KorovasKeys.scanTime, _scanTime.toIso8601String());
    n.updateField(KorovasKeys.cowId, _cowId.text.trim());
    n.updateField(KorovasKeys.cowAge, _age.text.trim());
    n.updateField(KorovasKeys.cowWeight, _weight.text.trim());
    n.updateField(KorovasKeys.cowBreed, _breed.text.trim());
  }

  Map<String, dynamic> _decodePackageData(String rawJson) {
    try {
      final data = jsonDecode(rawJson);
      if (data is Map<String, dynamic>) return data;
    } catch (_) {
      // ignore malformed rows in local db
    }
    return <String, dynamic>{};
  }

  void _prefillFrom(Map<String, dynamic> data) {
    setState(() {
      _age.text = data[KorovasKeys.cowAge]?.toString() ?? _age.text;
      _weight.text = data[KorovasKeys.cowWeight]?.toString() ?? _weight.text;
      _breed.text = data[KorovasKeys.cowBreed]?.toString() ?? _breed.text;
      final parsedTime = _parseScanTime(data[KorovasKeys.scanTime]);
      if (parsedTime != null) {
        _scanTime = parsedTime;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final packages = ref.watch(packagesStreamProvider).asData?.value ?? const [];
    final typedCowId = _cowId.text.trim();
    final typedLower = typedCowId.toLowerCase();
    final matchedIds = <String>{};
    DateTime? exactCreatedAt;
    Map<String, dynamic>? exactData;

    if (typedLower.isNotEmpty) {
      for (final pkg in packages) {
        final payload = _decodePackageData(pkg.dataJson);
        final existingCowId = payload[KorovasKeys.cowId]?.toString().trim() ?? '';
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

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(Epoch8Layout.pagePadding, 8, Epoch8Layout.pagePadding, 28),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Epoch8SectionHeader(
            overline: 'Шаг 1',
            title: 'Данные скана',
            subtitle: 'Время скана подставляется с устройства; при необходимости измените.',
          ),
          const SizedBox(height: Epoch8Layout.sectionGap),
          _Card(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Время скана', style: Theme.of(context).textTheme.titleSmall),
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
                      label: const Text('Изменить'),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          _Card(
            accentBorder: true,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Параметры коровы',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 14),
                TextField(
                  controller: _cowId,
                  decoration: InputDecoration(
                    labelText: 'ID коровы',
                    hintText: 'Например: COW-00124',
                    helperText: typedCowId.isEmpty
                        ? null
                        : hasExactMatch
                            ? 'ID найден в локальной истории'
                            : hasAnyMatches
                                ? 'Есть похожие ID в истории'
                                : 'Новый ID (в истории не найден)',
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
                          _cowId.text = id;
                          _cowId.selection = TextSelection.fromPosition(
                            TextPosition(offset: _cowId.text.length),
                          );
                          setState(() {});
                        },
                      );
                    }).toList(),
                  ),
                ],
                if (hasExactMatch) ...[
                  const SizedBox(height: 10),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: TextButton.icon(
                      onPressed: () => _prefillFrom(exactData!),
                      icon: const Icon(Icons.auto_fix_high_outlined, size: 18),
                      label: const Text('Предзаполнить поля из последней записи'),
                    ),
                  ),
                ],
                const SizedBox(height: 12),
                TextField(
                  controller: _age,
                  decoration: const InputDecoration(
                    labelText: 'Возраст коровы',
                    hintText: 'Например: 3 года',
                  ),
                  onChanged: (_) => setState(() {}),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _weight,
                  decoration: const InputDecoration(
                    labelText: 'Вес коровы',
                    hintText: 'Например: 450 кг',
                  ),
                  onChanged: (_) => setState(() {}),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _breed,
                  decoration: const InputDecoration(
                    labelText: 'Порода коровы',
                    hintText: 'Например: Голштинская',
                  ),
                  onChanged: (_) => setState(() {}),
                ),
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
            child: const Text('Далее: справка по съёмке'),
          ),
        ],
      ),
    );
  }
}

class _KorovasShootingBriefing extends StatelessWidget {
  const _KorovasShootingBriefing({super.key, required this.onContinue});

  final VoidCallback onContinue;

  @override
  Widget build(BuildContext context) {
    return KorovasShootingGuideBody(showStartButton: true, onStart: onContinue);
  }
}

class _KorovasPoseStep extends ConsumerStatefulWidget {
  const _KorovasPoseStep({
    super.key,
    required this.projectId,
    required this.poseIndex,
    required this.guide,
    required this.onNext,
  });

  final String projectId;
  /// 1..3
  final int poseIndex;
  final KorovasPoseGuide guide;
  final VoidCallback onNext;

  @override
  ConsumerState<_KorovasPoseStep> createState() => _KorovasPoseStepState();
}

class _KorovasPoseStepState extends ConsumerState<_KorovasPoseStep> {
  final _picker = ImagePicker();

  String get _key => KorovasKeys.pose(widget.poseIndex);

  Future<void> _pickImage(ImageSource source) async {
    // Keep original quality for new captures; preview scaling is done only in UI.
    final x = await _picker.pickImage(source: source);
    if (x == null || !mounted) return;

    if (!kIsWeb) {
      final quality = await analyzeCaptureQuality(x.path);
      if (!mounted) return;
      if (!quality.isAcceptable) {
        final useAnyway = await showDialog<bool>(
          context: context,
          barrierDismissible: false,
          builder: (ctx) => AlertDialog(
            title: const Text('Проверка качества кадра'),
            content: SingleChildScrollView(child: Text(quality.userMessage)),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx, true),
                child: const Text('Всё равно использовать'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: const Text('Переснять'),
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
      poseIndex1Based: widget.poseIndex,
      imagePath: x.path,
    );
    if (!mounted) return;
    final answers = ref.read(wizardStateProvider(widget.projectId));
    final paths = List<String>.from(KorovasPosePaths.list(answers[_key]))..add(x.path);
    ref.read(wizardStateProvider(widget.projectId).notifier).updateField(_key, paths);
    setState(() {});
  }

  void _removePhoto(String path) {
    CameraMetadataCollector.removePoseShotByPath(
      ref: ref,
      projectId: widget.projectId,
      poseIndex1Based: widget.poseIndex,
      imagePath: path,
    );
    final answers = ref.read(wizardStateProvider(widget.projectId));
    final paths = List<String>.from(KorovasPosePaths.list(answers[_key]))..remove(path);
    ref.read(wizardStateProvider(widget.projectId).notifier).updateField(_key, paths.isEmpty ? null : paths);
    setState(() {});
  }

  void _clearAll() {
    CameraMetadataCollector.removePoseMetadata(
      ref: ref,
      projectId: widget.projectId,
      poseIndex1Based: widget.poseIndex,
    );
    ref.read(wizardStateProvider(widget.projectId).notifier).updateField(_key, null);
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final answers = ref.watch(wizardStateProvider(widget.projectId));
    final paths = KorovasPosePaths.list(answers[_key]);

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(Epoch8Layout.pagePadding, 8, Epoch8Layout.pagePadding, 28),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            widget.guide.title,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 12),
          ...widget.guide.descriptionLines.map(
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
                  'Пример ракурса',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
                ),
              ),
              TextButton.icon(
                onPressed: () => showKorovasShootingHelp(context),
                icon: const Icon(Icons.help_outline, size: 18),
                label: const Text('Справка'),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(Epoch8Layout.radiusMd),
            child: AspectRatio(
              aspectRatio: 4 / 3,
              child: Image.asset(
                widget.guide.exampleAssetPath,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => Container(
                  color: Epoch8Theme.bgElevated,
                  alignment: Alignment.center,
                  child: const Padding(
                    padding: EdgeInsets.all(16),
                    child: Text(
                      'Положите файл примера в assets/korovas/',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: Epoch8Theme.textMuted),
                    ),
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 20),
          Text('Ваши кадры (${paths.length})', style: Theme.of(context).textTheme.titleSmall),
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
                    'Добавьте кадры камерой или из галереи',
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
                    'Добавить ещё',
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
                        label: const Text('Камера'),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => _pickImage(ImageSource.gallery),
                        icon: const Icon(Icons.photo_library_outlined, size: 20),
                        label: const Text('Галерея'),
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
              label: const Text('Удалить все кадры этого ракурса'),
            ),
          ],
          const SizedBox(height: 24),
          FilledButton(
            onPressed: paths.isNotEmpty ? widget.onNext : null,
            style: FilledButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 16)),
            child: Text(
              widget.poseIndex < 3 ? 'Далее' : 'К проверке',
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

class _KorovasReviewStep extends ConsumerWidget {
  const _KorovasReviewStep({
    super.key,
    required this.projectId,
    required this.onEditForm,
    required this.onEditPose,
    required this.onSubmit,
  });

  final String projectId;
  final VoidCallback onEditForm;
  final void Function(int poseIndex) onEditPose;
  final Future<void> Function() onSubmit;

  bool _isComplete(Map<String, dynamic> a) {
    if (a[KorovasKeys.scanTime] == null) return false;
    if ((a[KorovasKeys.cowAge] as String?)?.trim().isEmpty ?? true) return false;
    if ((a[KorovasKeys.cowWeight] as String?)?.trim().isEmpty ?? true) return false;
    if ((a[KorovasKeys.cowBreed] as String?)?.trim().isEmpty ?? true) return false;
    for (var i = 1; i <= 3; i++) {
      if (!KorovasPosePaths.hasPhotos(a[KorovasKeys.pose(i)])) return false;
    }
    return true;
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final a = ref.watch(wizardStateProvider(projectId));
    final complete = _isComplete(a);
    DateTime? st;
    final raw = a[KorovasKeys.scanTime];
    if (raw is String) st = DateTime.tryParse(raw)?.toLocal();
    final cameraCtx = a[KorovasKeys.cameraContext] as Map<String, dynamic>?;

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(Epoch8Layout.pagePadding, 8, Epoch8Layout.pagePadding, 32),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Epoch8SectionHeader(
            overline: 'Финиш',
            title: 'Проверка и отправка',
            subtitle:
                'Проверьте данные. Можно вернуться к анкете или к любому ракурсу — снимки сохраняются, их можно заменить.',
          ),
          const SizedBox(height: Epoch8Layout.sectionGap),
          _Card(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(child: Text('Анкета', style: Theme.of(context).textTheme.titleSmall)),
                    TextButton(onPressed: onEditForm, child: const Text('Изменить')),
                  ],
                ),
                const Divider(height: 24),
                _line('Время скана', st != null ? _formatDateTime(st) : '—'),
                _line('Возраст', a[KorovasKeys.cowAge]?.toString() ?? '—'),
                _line('Вес', a[KorovasKeys.cowWeight]?.toString() ?? '—'),
                _line('Порода', a[KorovasKeys.cowBreed]?.toString() ?? '—'),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Text('Фотографии по ракурсам', style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          for (var i = 1; i <= 3; i++) ...[
            _Card(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          korovasPoseGuides[i - 1].title,
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                      ),
                      TextButton(
                        onPressed: () => onEditPose(i),
                        child: const Text('Изменить'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      for (final p in KorovasPosePaths.list(a[KorovasKeys.pose(i)]))
                        ClipRRect(
                          borderRadius: BorderRadius.circular(8),
                          child: Image.file(File(p), width: 72, height: 72, fit: BoxFit.cover),
                        ),
                    ],
                  ),
                  if (KorovasPosePaths.list(a[KorovasKeys.pose(i)]).isEmpty)
                    Text('Нет кадров', style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Epoch8Theme.textMuted)),
                ],
              ),
            ),
            if (i < 3) const SizedBox(height: 8),
          ],
          const SizedBox(height: 16),
          _CameraMetaReviewPanel(cameraContext: cameraCtx),
          const SizedBox(height: 24),
          FilledButton(
            onPressed: complete
                ? () async {
                    await onSubmit();
                  }
                : null,
            child: const Text('Отправить данные'),
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
}

/// Сворачиваемый блок метаданных камеры / устройства для экрана проверки.
class _CameraMetaReviewPanel extends StatelessWidget {
  const _CameraMetaReviewPanel({this.cameraContext});

  final Map<String, dynamic>? cameraContext;

  static String? _subtitle(Map<String, dynamic> ctx) {
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
              fxHint = 'fₓ≈${_fmtNum(d['preferred_fx_px_estimate'])} px';
              break outer;
            }
          }
        }
        final d = v['derived'];
        if (d is Map && d['preferred_fx_px_estimate'] != null) {
          fxHint = 'fₓ≈${_fmtNum(d['preferred_fx_px_estimate'])} px';
          break;
        }
      }
    }
    final parts = <String>[];
    if (model != null && model.isNotEmpty) parts.add(model);
    if (fxHint != null) parts.add(fxHint);
    return parts.isEmpty ? 'Нажмите, чтобы развернуть' : parts.join(' · ');
  }

  static String _fmtNum(dynamic v) {
    if (v is double) return v.toStringAsFixed(v.abs() >= 1000 ? 0 : 1);
    if (v is int) return v.toString();
    return v.toString();
  }

  @override
  Widget build(BuildContext context) {
    final ctx = cameraContext;
    if (ctx == null || ctx.isEmpty) {
      return _Card(
        child: Row(
          children: [
            Icon(Icons.info_outline, size: 20, color: Epoch8Theme.textMuted.withValues(alpha: 0.9)),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                'Мета-параметры камеры появятся после съёмки поз.',
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
                      'Мета-параметры камеры',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _subtitle(ctx) ?? '',
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
              'Устройство',
              _deviceRows(ctx['device']),
            ),
            _metaSection(
              context,
              'Нативная камера (задняя)',
              _nativeRows(ctx['native_back_camera']),
            ),
            ..._poseMetaSections(context, ctx['poses']),
            Theme(
              data: Theme.of(context).copyWith(dividerColor: Epoch8Theme.border),
              child: ExpansionTile(
                tilePadding: EdgeInsets.zero,
                title: Text(
                  'Полный JSON (копирование)',
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

  List<Widget> _deviceRows(dynamic device) {
    if (device is! Map) return [const Text('—', style: TextStyle(color: Epoch8Theme.textMuted))];
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

  List<Widget> _nativeRows(dynamic native) {
    if (native is! Map || native.isEmpty) {
      return [const Text('Нет данных с нативного API', style: TextStyle(color: Epoch8Theme.textMuted, fontSize: 13))];
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

  List<Widget> _poseMetaSections(BuildContext context, dynamic poses) {
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
                'Ракурс $idx — кадр ${si + 1}',
                _shotMetaRows(derived, exif),
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
              'Ракурс $idx — оценки',
              _shotMetaRows(derived, exif),
            ),
          ),
        );
      }
    }
    return list;
  }

  List<Widget> _shotMetaRows(dynamic derived, dynamic exif) {
    return [
      if (derived is Map) ...[
        if (derived['preferred_fx_px_estimate'] != null)
          _selLine('preferred_fx_px_estimate', derived['preferred_fx_px_estimate']),
        if (derived['fx_px_from_exif_focal_and_native_sensor'] != null)
          _selLine('fx_px (EXIF focal × сенсор)', derived['fx_px_from_exif_focal_and_native_sensor']),
        if (derived['fx_px_from_35mm_equiv'] != null)
          _selLine('fx_px (35mm equiv)', derived['fx_px_from_35mm_equiv']),
        if (derived['fx_px_from_native_mm'] != null)
          _selLine('fx_px (натив)', derived['fx_px_from_native_mm']),
      ],
      if (exif is Map && exif.isNotEmpty) ...[
        const SizedBox(height: 8),
        const Text('Фрагмент EXIF', style: TextStyle(fontSize: 12, color: Epoch8Theme.textMuted)),
        const SizedBox(height: 4),
        ...exif.entries.take(12).map((e) => Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: SelectableText(
                '${e.key}: ${e.value}',
                style: const TextStyle(fontSize: 12, height: 1.3),
              ),
            )),
        if (exif.length > 12)
          Text('… ещё ${exif.length - 12} полей', style: TextStyle(fontSize: 11, color: Epoch8Theme.textMuted)),
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
