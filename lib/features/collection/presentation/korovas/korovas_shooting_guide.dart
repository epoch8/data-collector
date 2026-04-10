import 'package:data_collector/theme/epoch8_theme.dart';
import 'package:data_collector/theme/epoch8_ui.dart';
import 'package:flutter/material.dart';

/// Справка и обучение по съёмке (по типовой инструкции по съёмке КРС).
/// Названия ракурсов и описания можно уточнить по вашему PDF — см. комментарии внизу файла.
class KorovasPoseGuide {
  const KorovasPoseGuide({
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

/// Три обязательных ракурса (как в методичках по оценке КРС: план, профиль, зад).
const List<KorovasPoseGuide> korovasPoseGuides = [
  KorovasPoseGuide(
    index1Based: 1,
    title: 'Ракурс 1. Вид сверху (план)',
    shortLabel: 'Сверху',
    descriptionLines: [
      'Камера строго над линией спины или с небольшого вылета (как при аэрофотосъёмке в стойле).',
      'В кадре — весь контур тела, голова и крестец не обрезаны; линия спины читается.',
      'Избегайте сильного перспективного сжатия: держите телефон параллельно полу.',
      'При необходимости сделайте несколько кадров с одной точки.',
    ],
    exampleAssetPath: 'assets/korovas/example_pose_placeholder.jpg',
  ),
  KorovasPoseGuide(
    index1Based: 2,
    title: 'Ракурс 2. Вид сбоку (профиль)',
    shortLabel: 'Сбоку',
    descriptionLines: [
      'Полный боковой профиль: голова, шея, корпус, ноги в кадре.',
      'Камера на уровне середины корпуса, оптическая ось перпендикулярно плоскости бока.',
      'Линия спины визуально горизонтальна; без сильного наклона вверх/вниз.',
      'Можно снять несколько кадров (например, слева и справа), если требуется протоколом.',
    ],
    exampleAssetPath: 'assets/korovas/example_pose_placeholder.jpg',
  ),
  KorovasPoseGuide(
    index1Based: 3,
    title: 'Ракурс 3. Вид сзади (задняя проекция)',
    shortLabel: 'Сзади',
    descriptionLines: [
      'Съёмка сзади: симметрия таза, огузка и задних конечностей.',
      'Камера на оси хвоста, на уровне середины корпуса; весь зад в кадре.',
      'Без сильного «рыбьего глаза»; при необходимости — несколько дублей.',
    ],
    exampleAssetPath: 'assets/korovas/example_pose_placeholder.jpg',
  ),
];

const List<String> korovasGeneralShootingTips = [
  'Освещение равномерное: без «выбитых» бликов и глубокой тени на боку.',
  'Животное спокойно; при съёмке в стойле соблюдайте правила безопасности.',
  'Фокус резкий; при слабом свете держите телефон устойчиво или делайте дубли.',
  'Для каждого ракурса можно сделать несколько фото — оставьте лучшие кадры перед отправкой.',
];

/// Полноэкранная справка (перед съёмкой) или содержимое bottom sheet.
class KorovasShootingGuideBody extends StatelessWidget {
  const KorovasShootingGuideBody({super.key, this.showStartButton = false, this.onStart, this.compact = false});

  final bool showStartButton;
  final VoidCallback? onStart;
  /// Уже внутри модального окна — меньше вертикальных отступов.
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final pad = compact ? 12.0 : 16.0;
    return SingleChildScrollView(
      padding: EdgeInsets.fromLTRB(pad, pad, pad, pad + 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Epoch8SectionHeader(
            overline: 'Обучение',
            title: 'Съёмка КРС',
            subtitle:
                'Перед съёмкой ознакомьтесь с ракурсами. Иллюстрации можно заменить в папке assets/korovas.',
          ),
          const SizedBox(height: 16),
          Text('Общие рекомендации', style: Theme.of(context).textTheme.titleSmall?.copyWith(color: Epoch8Theme.accent, fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          ...korovasGeneralShootingTips.map(
            (t) => Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('• ', style: TextStyle(color: Epoch8Theme.accent)),
                  Expanded(child: Text(t, style: Theme.of(context).textTheme.bodyMedium)),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          for (final g in korovasPoseGuides) ...[
            _PoseGuideCard(guide: g),
            SizedBox(height: compact ? 12 : 16),
          ],
          if (showStartButton && onStart != null) ...[
            const SizedBox(height: 8),
            FilledButton(
              onPressed: onStart,
              style: FilledButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 16)),
              child: const Text('Понятно, начать съёмку', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
            ),
          ],
        ],
      ),
    );
  }
}

class _PoseGuideCard extends StatelessWidget {
  const _PoseGuideCard({required this.guide});

  final KorovasPoseGuide guide;

  @override
  Widget build(BuildContext context) {
    return Epoch8Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(guide.title, style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700)),
          const SizedBox(height: 10),
          ClipRRect(
            borderRadius: BorderRadius.circular(Epoch8Layout.radiusSm),
            child: AspectRatio(
              aspectRatio: 4 / 3,
              child: Image.asset(
                guide.exampleAssetPath,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => Container(
                  color: Epoch8Theme.bgElevated,
                  alignment: Alignment.center,
                  child: const Text('Добавьте изображение в assets/korovas/', textAlign: TextAlign.center),
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
                  const Text('– ', style: TextStyle(color: Epoch8Theme.textMuted)),
                  Expanded(
                    child: Text(line, style: Theme.of(context).textTheme.bodySmall?.copyWith(height: 1.35)),
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

Future<void> showKorovasShootingHelp(BuildContext context) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Epoch8Theme.bgDeep,
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
                child: KorovasShootingGuideBody(compact: true),
              ),
            ],
          ),
        ),
      );
    },
  );
}
