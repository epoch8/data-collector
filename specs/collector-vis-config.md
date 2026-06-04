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

Плагин сам знает формат строки; конфиг только указывает таблицу и базовые опции.

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
