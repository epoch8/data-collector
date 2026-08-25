# Datapipe: учебный блок

Презентации + справочники рядом. Стиль как у `docs/architecture/`.

## Сборка презентаций

```bash
# Вводная (фреймворк)
python docs/datapipe/generate_presentation.py

# Живой стенд: ключевые точки коров
python docs/datapipe/generate_cow_keypoints_walkthrough.py
```

| Файл | Содержание |
| --- | --- |
| `Datapipe.pptx` | Зачем Datapipe, граф, UI, связь с Data Collector |
| `Datapipe-Cow-Keypoints-Walkthrough.pptx` | CVAT → аннотация → заморозка → обучение → метрики |

Перед сборкой закройте PPTX в PowerPoint. Большие pptx в git обычно не коммитим.

## Слайды walkthrough (15)

| # | Слайд |
| --- | --- |
| 1 | Обложка |
| 2 | Маршрут |
| 3 | CVAT: проекты |
| 4 | CVAT: как выглядит разметка |
| 5 | Разметка попадает в пайплайн |
| 6 | Откуда берутся картинки |
| 7 | Ground truth |
| 8 | Сплит и теги |
| 9 | Datapipe UI |
| 10 | Заморозка датасета |
| 11 | Запуск обучения |
| 12 | Ход обучения |
| 13 | Что видит модель |
| 14 | Метрики |
| 15 | Закрытие |

## Справочники

| Файл | Содержание |
| --- | --- |
| [`overview.ru.md`](overview.ru.md) | Что такое Datapipe в нашем контуре, Datapipe UI, связь с collector |
| [`pipeline-flow.ru.md`](pipeline-flow.ru.md) | Mermaid: поток ключевых точек |
| [`stages-reference.ru.md`](stages-reference.ru.md) | Стадии и labels |
| [`datapipe-ui.ru.md`](datapipe-ui.ru.md) | Разделы Datapipe UI |
| [`cow-keypoints-walkthrough.ru.md`](cow-keypoints-walkthrough.ru.md) | Сценарий демо по walkthrough |
| [`local-run-keypoints.ru.md`](local-run-keypoints.ru.md) | Локальный стенд keypoints |
| [`diagnostics-keypoints.ru.md`](diagnostics-keypoints.ru.md) | Типичные сбои и куда смотреть |

## Медиа

| Папка | Содержание |
| --- | --- |
| [`img/pitch/`](img/pitch/README.md) | Скрины вводной презентации |
| [`img/cow-keypoints-walkthrough/`](img/cow-keypoints-walkthrough/) | UI, GT, train, CVAT для walkthrough |
| [`img/cow-keypoints-walkthrough/cvat/`](img/cow-keypoints-walkthrough/cvat/README.md) | Скрины CVAT |

## Связанные материалы

- Architecture (стадии 0–4, local run collector→CVAT): `docs/architecture/`
- E2E Korovas: `docs/e2e-korovas/`
- Скилл агента: `korovas/.claude/skills/setup-key-points-regression-datapipe/SKILL.md`
- Readme пайплайна: `korovas/experiments/key_points_regression_datapipe/readme.md`
- План артефактов: `docs/training-materials.ru.md`
