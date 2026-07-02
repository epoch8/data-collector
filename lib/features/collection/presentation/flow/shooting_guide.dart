import 'package:data_collector/features/collection/presentation/flow/project_example_image.dart';
import 'package:data_collector/l10n/app_localizations.dart';
import 'package:data_collector/models/project_config.dart';
import 'package:data_collector/theme/epoch8_theme.dart';
import 'package:data_collector/theme/epoch8_ui.dart';
import 'package:data_collector/features/collection/presentation/flow/project_ui.dart';
import 'package:flutter/material.dart';

/// One pose card in the shooting guide (from `ui.shooting_guide.pose_cards` or built-in fallback).
class PoseGuide {
  const PoseGuide({
    required this.index1Based,
    required this.title,
    required this.shortLabel,
    required this.descriptionLines,
    required this.exampleAssetPath,
  });

  final int index1Based;
  final String title;
  final String shortLabel;
  final List<String> descriptionLines;
  final String exampleAssetPath;
}

const String _defaultExampleAsset =
    'assets/placeholders/example_pose_placeholder.jpg';

final List<PoseGuide> _builtinPoseGuides = [
  PoseGuide(
    index1Based: 1,
    title: '',
    shortLabel: '',
    descriptionLines: const [],
    exampleAssetPath: _defaultExampleAsset,
  ),
];

List<PoseGuide> _parsePoseCardsFromProject(Project project) {
  final cards = ProjectUi(project).listAt(['shooting_guide', 'pose_cards']);
  if (cards == null || cards.isEmpty) return const [];
  final out = <PoseGuide>[];
  for (var i = 0; i < cards.length; i++) {
    final e = cards[i];
    if (e is! Map) continue;
    final m = Map<String, dynamic>.from(e);
    final idx = (m['index_1based'] as num?)?.toInt() ?? i + 1;
    final title = m['title'] as String? ?? '';
    final short = m['short_label'] as String? ?? title;
    final linesRaw = m['description_lines'];
    final lines = linesRaw is List
        ? linesRaw.map((x) => x.toString()).where((s) => s.isNotEmpty).toList()
        : const <String>[];
    final asset = m['example_asset_path'] as String? ?? _defaultExampleAsset;
    out.add(
      PoseGuide(
        index1Based: idx,
        title: title,
        shortLabel: short,
        descriptionLines: lines,
        exampleAssetPath: asset,
      ),
    );
  }
  return out;
}

/// Pose card for step [poseIndex1Based]: JSON `pose_cards` order matches camera steps, else [field] + builtins.
PoseGuide resolvePoseGuide(
  Project project,
  int poseIndex1Based,
  ConfigField field,
) {
  final parsed = _parsePoseCardsFromProject(project);
  if (parsed.isNotEmpty) {
    final i = poseIndex1Based - 1;
    if (i >= 0 && i < parsed.length) {
      final g = parsed[i];
      if (g.title.isEmpty && g.descriptionLines.isEmpty) {
        return PoseGuide(
          index1Based: poseIndex1Based,
          title: field.title,
          shortLabel: field.title,
          descriptionLines: _linesFromInstructions(field.instructions),
          exampleAssetPath: g.exampleAssetPath.isNotEmpty
              ? g.exampleAssetPath
              : _defaultExampleAsset,
        );
      }
      return PoseGuide(
        index1Based: poseIndex1Based,
        title: g.title.isNotEmpty ? g.title : field.title,
        shortLabel: g.shortLabel.isNotEmpty ? g.shortLabel : field.title,
        descriptionLines: g.descriptionLines.isNotEmpty
            ? g.descriptionLines
            : _linesFromInstructions(field.instructions),
        exampleAssetPath: g.exampleAssetPath,
      );
    }
  }
  final bi = poseIndex1Based - 1;
  if (bi >= 0 && bi < _builtinPoseGuides.length) {
    return PoseGuide(
      index1Based: poseIndex1Based,
      title: field.title,
      shortLabel: field.title,
      descriptionLines: _linesFromInstructions(field.instructions),
      exampleAssetPath: _builtinPoseGuides[bi].exampleAssetPath,
    );
  }
  return PoseGuide(
    index1Based: poseIndex1Based,
    title: field.title,
    shortLabel: field.title,
    descriptionLines: _linesFromInstructions(field.instructions),
    exampleAssetPath: _defaultExampleAsset,
  );
}

List<String> _linesFromInstructions(String instructions) {
  final t = instructions.trim();
  if (t.isEmpty) return const [];
  return t.split('\n').map((s) => s.trim()).where((s) => s.isNotEmpty).toList();
}

class ShootingGuideBody extends StatelessWidget {
  const ShootingGuideBody({
    super.key,
    required this.project,
    this.showStartButton = false,
    this.onStart,
    this.compact = false,

    /// Если false — только колонка без собственного [SingleChildScrollView] (родитель скроллит).
    this.scrollable = true,
  });

  final Project project;
  final bool showStartButton;
  final VoidCallback? onStart;
  final bool compact;
  final bool scrollable;

  @override
  Widget build(BuildContext context) {
    final loc = AppLocalizations.of(context);
    final ui = ProjectUi(project);
    final pad = compact ? 12.0 : 16.0;
    final tips = ui.strings(['shooting_guide', 'general_tips'], const []);
    final poseCards = _parsePoseCardsFromProject(project);

    final inner = Padding(
      padding: EdgeInsets.fromLTRB(pad, pad, pad, pad + 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Epoch8SectionHeader(
            overline: loc.shootingGuideSectionOverline,
            title: loc.shootingGuideSectionTitle,
            subtitle: ui.str(['shooting_guide', 'section_subtitle'], ''),
          ),
          const SizedBox(height: 16),
          Text(
            loc.shootingGuideGeneralTipsHeading,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
              color: Epoch8Theme.accent,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 8),
          ...tips.map(
            (t) => Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('• ', style: TextStyle(color: Epoch8Theme.accent)),
                  Expanded(
                    child: Text(
                      t,
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          for (final g in poseCards) ...[
            _PoseGuideCard(
              project: project,
              guide: g,
              assetMissingHint: loc.shootingGuideAssetMissing,
              emptyImagePlaceholder: loc.flowReviewEmptyValue,
            ),
            SizedBox(height: compact ? 12 : 16),
          ],
          if (showStartButton && onStart != null) ...[
            const SizedBox(height: 8),
            FilledButton(
              onPressed: onStart,
              style: FilledButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
              child: Text(
                loc.shootingGuideStartButton,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ],
      ),
    );

    if (!scrollable) return inner;
    return SingleChildScrollView(child: inner);
  }
}

class _PoseGuideCard extends StatelessWidget {
  const _PoseGuideCard({
    required this.project,
    required this.guide,
    required this.assetMissingHint,
    required this.emptyImagePlaceholder,
  });

  final Project project;
  final PoseGuide guide;
  final String assetMissingHint;
  final String emptyImagePlaceholder;

  @override
  Widget build(BuildContext context) {
    return Epoch8Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            guide.title,
            style: Theme.of(
              context,
            ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 10),
          ClipRRect(
            borderRadius: BorderRadius.circular(Epoch8Layout.radiusSm),
            child: AspectRatio(
              aspectRatio: 4 / 3,
              child: projectExampleImage(
                project: project,
                assetPath: guide.exampleAssetPath,
                fit: BoxFit.cover,
                errorPlaceholder: (ctx) => Container(
                  color: Epoch8Theme.bgElevated,
                  alignment: Alignment.center,
                  child: Text(
                    assetMissingHint.isNotEmpty
                        ? assetMissingHint
                        : emptyImagePlaceholder,
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Epoch8Theme.textMuted),
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 10),
          ...guide.descriptionLines.map(
            (line) => Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('– ', style: TextStyle(color: Epoch8Theme.textMuted)),
                  Expanded(
                    child: Text(
                      line,
                      style: Theme.of(
                        context,
                      ).textTheme.bodySmall?.copyWith(height: 1.35),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

Future<void> showShootingHelp(BuildContext context, Project project) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Theme.of(context).scaffoldBackgroundColor,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
    ),
    builder: (ctx) {
      final h = MediaQuery.sizeOf(ctx).height * 0.88;
      return SafeArea(
        child: SizedBox(
          height: h,
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Epoch8Theme.border,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              Expanded(
                child: ShootingGuideBody(project: project, compact: true),
              ),
            ],
          ),
        ),
      );
    },
  );
}
