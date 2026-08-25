# Datapipe UI: разделы

Краткий гид по интерфейсу для учебного стенда ключевых точек. В коде/старых скринах может быть надпись Ops; в материалах пишем **Datapipe UI**.

## Навигация

| Раздел | Зачем |
| --- | --- |
| Overview | Общий статус пайплайна |
| Graph | Граф шагов / стадий |
| Runs | История запусков, логи, таблица Steps |
| Image → Cow Keypoints | Кадры, превью |
| Frozen Datasets → Cow Keypoints | Снимки данных перед train |
| Training → Cow Keypoints | Модели и запросы обучения |
| Metrics → Cow Keypoints | Таблицы качества |
| Help | Справка по UI |

Спека обычно подписана как **Cow Keypoints**.

## Runs: как читать карточку

1. Статус: `running` / `completed` / ошибка.
2. Trigger: например `api(annotation)` или `api(train)`.
3. Target label: какая стадия крутилась.
4. Граф внутри стадии: цепочка шагов (export CVAT, download, detector, train-prepare, …).
5. Вкладки:
   - **Logs** — поток логов (эпохи YOLO видны здесь);
   - **Steps** — прогресс по шагам;
   - **Outputs** — артефакты, если есть.

Для демо удобны два скрина:

- завершённый run **annotation**;
- live / завершённый run **train** с логами эпох.

## Frozen Datasets

Freeze фиксирует состав кадров и разметки. Дальше обучение ссылается на конкретный `keypoints_frozen_dataset_id`. Это нужно, чтобы сравнивать модели честно и уметь вернуться к тому же снимку.

В UI: создать / выбрать frozen dataset → затем запуск обучения.

## Training

Список моделей и статусов обучения. Запрос train из UI идёт на label `train-without-freeze` (если freeze уже сделан).

Не ориентируйтесь только на exit code CLI: смотрите статус обучения и появление метрик.

## Metrics

Таблица вида «модель × frozen dataset × subset».

Типичные колонки:

- Pose: precision / recall / mAP50 / mAP50-95;
- Detection: precision / recall / F1.

Фильтры:

- `subset_id` = `val` или `test`;
- при наличии tag-метрик — отдельная таблица / фильтр по `tag_id`.

## Image и Ground truth

Здесь показывают кадры и эталон. Для презентации достаточно нескольких понятных превью с боксом и точками; цифры «сколько всего на диске» в учебные слайды не тащим.

## Связь слайдов walkthrough

| Слайд | Раздел UI |
| --- | --- |
| Разметка попадает в пайплайн | Runs (annotation) |
| Откуда берутся картинки | Image |
| Datapipe UI | Overview |
| Заморозка | Frozen Datasets |
| Запуск / ход обучения | Runs + Training |
| Метрики | Metrics |

## Связанные документы

- [overview.ru.md](overview.ru.md)
- [cow-keypoints-walkthrough.ru.md](cow-keypoints-walkthrough.ru.md)
- [stages-reference.ru.md](stages-reference.ru.md)
