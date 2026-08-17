# Walkthrough: ключевые точки в Datapipe UI

Сценарий демо под презентацию `Datapipe-Cow-Keypoints-Walkthrough.pptx`.
Цель: показать путь от размеченных кадров до метрик модели без лишних цифр стенда.

## Сообщение на 30 секунд

CVAT хранит разметку. Datapipe UI забирает её, готовит набор, обучает модель и показывает метрики в одной ленте запусков.

## Маршрут рассказа

| Шаг | Что говорим | Что показываем |
| --- | --- | --- |
| 1 | Разметка живёт в CVAT | Проекты / задача / job с боксом и точками |
| 2 | Пайплайн забирает готовое | Run стадии annotation в Datapipe UI |
| 3 | Кадры могут быть в S3, CVAT или локально | Image в UI (без перечисления «N файлов») |
| 4 | Эталон уже есть | Ground truth / превью кадров |
| 5 | Делим данные и помечаем группы | Сплит и теги (идея стадии) |
| 6 | Весь путь виден в UI | Overview |
| 7 | Перед train фиксируем снимок | Frozen Datasets |
| 8 | Запускаем обучение | Runs / Training |
| 9 | Смотрим эпохи | Логи train |
| 10 | Контроль батчей | Примеры train batch |
| 11 | Итог качества | Metrics |

## Что не обещать на этом демо

- Точные counts локального стенда как продакшен-объём (датасетов больше, локально часто урезанный контур).
- Отдельный «merge» разметки в проде walkthrough: на слайде достаточно **Ground truth**.
- Полный collector→packages, если демо стартует с уже размеченных проектов.

## Чек-лист перед съёмкой / показом

1. Datapipe UI открывается (обычно `http://localhost:8010`).
2. CVAT открывается (`http://localhost:8080`, Host `localhost`).
3. Есть хотя бы один завершённый annotation run.
4. Есть frozen dataset.
5. Есть train run (хотя бы частично) и строка в Metrics.
6. Скрины / медиа для PPTX лежат в `img/cow-keypoints-walkthrough/`.

## Сборка презентации

```bash
python docs/datapipe/generate_cow_keypoints_walkthrough.py
```

Медиа:

| Папка | Файлы |
| --- | --- |
| `ui/` | overview, annotation run, runs, train logs, images, frozen, metrics |
| `cvat/` | `project.png`, `task.png`, `job.png` |
| `gt/` | примеры эталона |
| `train/` | батчи / labels |

## После демо: куда углубиться

- Локальный bring-up: [local-run-keypoints.ru.md](local-run-keypoints.ru.md)
- Labels: [stages-reference.ru.md](stages-reference.ru.md)
- Сбои: [diagnostics-keypoints.ru.md](diagnostics-keypoints.ru.md)
- Стык с collector: [`../architecture/local-run-korovas-datapipe.ru.md`](../architecture/local-run-korovas-datapipe.ru.md)
- Скилл агента: `setup-key-points-regression-datapipe`
