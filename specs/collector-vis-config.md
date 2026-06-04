# collector/viz.json — визуализация пакета

Отдельный конфиг в Git-репозитории проекта (не в `collector/config.json`).

## Путь

```
collector/viz.json
```

Django читает файл из кэша Git после `pull` (как `collector/config.json`).

## Схема (v1)

```json
{
  "version": 1,
  "join_key": "manifest_blob_key",
  "layers": [
    {
      "id": "gt",
      "label": "GT",
      "plugin": "keypoint_korovas",
      "table": "cow_keypoint_annotation",
      "palette": "gt",
      "default_visible": false
    },
    {
      "id": "inference",
      "label": "Inference",
      "plugin": "keypoint_korovas",
      "table": "cow_inference_result",
      "palette": "inference",
      "default_visible": true
    },
    {
      "id": "depth",
      "label": "Глубина",
      "plugin": "depth_map",
      "table": "cow_inference_result",
      "default_visible": false
    }
  ]
}
```

| Поле | Описание |
|------|----------|
| `version` | Пока только `1` |
| `join_key` | Фиксировано: `manifest_blob_key` — связь строки таблицы с blob пакета |
| `layers[].id` | Уникальный id слоя в UI |
| `layers[].plugin` | Id встроенного плагина (см. ниже) |
| `layers[].table` | Таблица project SQLite |
| `layers[].palette` | Для `keypoint_korovas`: `gt` \| `inference` (цвета оверлея) |
| `layers[].default_visible` | Включён ли слой при открытии вкладки |

## Плагины (реализованы в django_server)

| plugin | table | Поведение |
|--------|-------|-----------|
| `keypoint_korovas` | `cow_keypoint_annotation` | GT: `annotation.points`, CVAT link |
| `keypoint_korovas` | `cow_inference_result` | Inference: keypoints, bbox, segments, metrics |
| `depth_map` | `cow_inference_result` | `.npy` из `depth_blob_key` / `depth_map.depth_url` |
| `yolo_detection` | `yolo_detection` | BBox из `detections.boxes` (импорт YOLO `.txt`) |

Плагин сам знает формат строки; конфиг указывает таблицу и **опции классов** (см. ниже).

### Комментарии в `collector/viz.json`

Поддерживаются построчные комментарии `//` (вне строк в кавычках). Шаблон с пояснениями: `django_server/examples/collector/viz_yolo.json`.

### Слой `yolo_detection` — единая схема полей

Общие поля слоя (как у всех плагинов): `id`, `label`, `plugin`, `table`, `palette`, `default_visible`.

Дополнительно **только** для `yolo_detection`:

| Поле | Описание |
|------|----------|
| `include_classes` | `[0, 1]` — какие class id из YOLO `.txt` рисовать; поле убрать = все |
| `classes` | `{"0": "имя"}` или `{"0": {"name": "…", "color": "#hex"}}` — подписи и цвета по id |

Устарело (ошибка валидации): `class_names`, `class_colors` — всё в `classes`.

Пример для другого проекта (та же таблица `yolo_detection`, другие имена):

```json
{
  "id": "det",
  "label": "Детекции",
  "plugin": "yolo_detection",
  "table": "yolo_detection",
  "palette": "yolo",
  "default_visible": true,
  "include_classes": [0, 1],
  "classes": {
    "0": { "name": "Вымень", "color": "#06b6d4" },
    "1": { "name": "Соска", "color": "#a855f7" }
  }
}
```

Пример для YOLO-проекта: `django_server/examples/collector/viz_yolo.json`. Импорт разметки:

```bash
python manage.py import_yolo_labels <project_id> <package_id> path/to/labels.txt --blob blobs/img_0001.jpg
```

## Когда показывается вкладка «Визуализация»

1. В репо есть валидный `collector/viz.json`
2. В project SQLite есть хотя бы одна строка для `package_id` в таблице любого слоя

## API

`GET /ui/projects/{project_id}/packages/{package_id}/viz-data/`

```json
{
  "version": 1,
  "join_key": "manifest_blob_key",
  "layers": [ … ],
  "data": {
    "gt": [ … ],
    "inference": [ … ]
  }
}
```

Пример файла: `django_server/examples/collector/viz.json`.
