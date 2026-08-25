# Схема потока: ключевые точки коров

Статус: учебный артефакт блока Datapipe. Источник правды: `experiments/key_points_regression_datapipe` (readme, `app.py`, `ops_specs.py`).

## Полный контур

```mermaid
flowchart LR
  Packages[Пакеты_collector] --> PackagesStage[stage_packages]
  PackagesStage --> CVAT[CVAT_проекты]
  CVAT --> Annotation[stage_annotation]
  Annotation --> Split[Сплит_и_теги]
  Split --> Freeze[train_prepare_freeze]
  Freeze --> Train[train_without_freeze]
  Train --> Metrics[Метрики]
  Train --> FiftyOne[FiftyOne]
  Metrics --> Prod[prod_model_опц]
```

## Путь walkthrough (разметка уже есть)

На демо часто стартуют не с пустых пакетов, а с готовых проектов CVAT:

```mermaid
flowchart TB
  CVAT[CVAT:_боксы_и_точки] --> Ann[Аннотация]
  Ann --> GT[Ground_truth]
  Ann --> Img[Картинки]
  GT --> Split[Сплит_и_теги]
  Img --> Split
  Split --> Freeze[Заморозка]
  Freeze --> Train[Обучение]
  Train --> Met[Метрики_в_UI]
```

## Стадии подробно

```mermaid
flowchart TB
  subgraph packages [packages]
    P1[package_session_blobs]
    P2[CVAT_задачи]
    P3[cvat_link_GT_в_remote_DB]
    P1 --> P2 --> P3
  end

  subgraph annotation [annotation]
    A1[Экспорт_из_CVAT]
    A2[Кадры]
    A3[GT_keypoints]
    A4[split_json]
    A5[теги]
    A1 --> A2
    A1 --> A3
    A3 --> A4
    A3 --> A5
  end

  subgraph train [train]
    T1[train_prepare_freeze]
    T2[YOLO_pose]
    T3[count_metrics]
    T1 --> T2 --> T3
  end

  packages --> annotation --> train
```

## Где что смотреть

| Этап | Что получается | Где смотреть |
| --- | --- | --- |
| packages | Задачи в CVAT, ссылки в project DB | CVAT, Datapipe Runs, таблицы `cvat_link` |
| annotation | Кадры + GT + split + tags | Datapipe UI → Image / Runs |
| train-prepare | Frozen dataset | Frozen Datasets |
| train-without-freeze | Модель + метрики | Training, Metrics, логи Runs |
| fiftyone | Датасет для просмотра | FiftyOne App (если поднят) |

## Картинки: откуда берутся

Кадры могут лежать в разных местах; пайплайн подтягивает их по настройке проекта:

| Источник | Когда типично |
| --- | --- |
| S3 / MinIO | Пакеты collector, старые проекты с `image_source: s3` |
| CVAT | Кадры уже в задаче разметки |
| Локальный диск | Учебный стенд / копия для отладки |

Не фиксируйте в презентациях «сколько картинок на стенде» как продакшен-цифру: локальный demo и боевые датасеты различаются.

## Ground truth

В рабочем контуре эталон часто уже лежит в CVAT (размеченные кадры). Стадия аннотации забирает готовое. Отдельный «merge разметки» в продакшен-истории walkthrough не нужен: на слайдах достаточно названия **Ground truth**.

## Сплит и теги

| Понятие | Смысл |
| --- | --- |
| **Сплит** | Деление на train / val / test (`split.json`, ключи = имена CVAT-проектов) |
| **Теги** | Метка группы кадров (часто = имя CVAT-проекта) → метрики по группам |

## Связанные документы

- [stages-reference.ru.md](stages-reference.ru.md)
- [cow-keypoints-walkthrough.ru.md](cow-keypoints-walkthrough.ru.md)
- [diagnostics-keypoints.ru.md](diagnostics-keypoints.ru.md)
- Architecture package flow: [`../architecture/package-flow.md`](../architecture/package-flow.md)
