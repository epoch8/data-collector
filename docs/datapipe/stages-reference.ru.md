# Справочник стадий и labels

Учебный артефакт. Labels запускают шаги через CLI или `POST /api/run-with-labels` (путь зависит от стенда: `/run-with-labels` или `/api/run-with-labels`).

Пайплайн: `korovas/experiments/key_points_regression_datapipe`.

## Карта стадий

| Label | Что делает | UI / куда смотреть |
| --- | --- | --- |
| `packages` | Пакеты из remote DB → инференс (опц.) → задачи CVAT → ссылки/GT в remote DB | Runs, CVAT |
| `packages-ingest` | Только ingest пакетов | Runs |
| `packages-inference` | Gradio-инференс пакетов | Runs, remote `cow_inference_result` |
| `packages-cvat` | Создание/синк задач CVAT | CVAT |
| `annotation` | Экспорт CVAT → кадры → GT → split → tags | Image, Runs |
| `cvat` | Часть annotation вокруг CVAT | Runs |
| `train-prepare` | Freeze датасета | Frozen Datasets |
| `train-without-freeze` | Обучение + метрики (без нового freeze) | Training, Metrics, Runs |
| `train` | Полный train-контур (как в CLI) | Runs |
| `train-after` | Пост-обработка после train | Runs |
| `count-metrics` | Подсчёт метрик | Metrics |
| `tag-metrics` | Метрики по тегам | Metrics (tag table) |
| `fiftyone-annotations` | Подготовка аннотаций для FiftyOne | FiftyOne |
| `fiftyone` | Датасет FiftyOne | FiftyOne App |
| `prod_model` | Прод-модель (опц.) | Training / файлы весов |

В Datapipe UI для спеки `cow_keypoints`:

- кнопка freeze → label `train-prepare`;
- запрос обучения → label `train-without-freeze`.

## Порядок для демо «от разметки к метрикам»

```text
1. annotation
2. train-prepare
3. train-without-freeze
4. (опц.) fiftyone
```

Если нужно сначала подтянуть пакеты collector:

```text
1. packages
2. разметка / acceptance в CVAT
3. annotation
4. train-prepare
5. train-without-freeze
```

## CLI (из каталога пайплайна)

```bash
cd experiments/key_points_regression_datapipe
# env уже в .env

datapipe step --labels=stage=annotation run
datapipe step --labels=stage=train-prepare run
datapipe step --labels=stage=train-without-freeze run
```

Через API (порт стенда подставьте свой):

```bash
curl -X POST http://localhost:8010/api/run-with-labels \
  -H "Content-Type: application/json" \
  -d "{\"labels\":[[\"stage\",\"annotation\"]]}"
```

## Webhook CVAT

Типичный контракт (проверьте URL на стенде):

- событие `update:job`;
- проект = `UPLOADED_PACKAGES_CVAT_PROJECT_ID`;
- job: `stage=acceptance` + `state=completed`;
- эффект: запуск `stage=packages`.

URL из Docker CVAT на хост часто вида:

```text
http://host.docker.internal:8010/api/cvat-webhook
```

## Важные таблицы (ориентиры)

| Тема | Таблицы / артефакты |
| --- | --- |
| Freeze | `keypoints_frozen_dataset`, связи с image/GT |
| Модели | `keypoints_model_*`, связь model ↔ frozen dataset |
| Метрики | `keypoints_model_train__metrics_on__frozen_dataset` |
| Теги | `tag`, `image__tag`, `keypoints_model_train__metrics_by_tag_on__subset` |
| Split | `split.json` (ключи = имена CVAT-проектов) |

Точные имена колонок смотрите в `ops_specs.py`.

## Связанные документы

- [pipeline-flow.ru.md](pipeline-flow.ru.md)
- [datapipe-ui.ru.md](datapipe-ui.ru.md)
- [diagnostics-keypoints.ru.md](diagnostics-keypoints.ru.md)
- Readme пайплайна в korovas
