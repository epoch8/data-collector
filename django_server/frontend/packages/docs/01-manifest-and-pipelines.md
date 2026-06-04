# 01 — Manifest пакета и пайплайны

## 1. Единица данных

**Пакет** на платформе = `PackageSession` + `UploadedBlob[]` + `manifest_json`.

## 2. Корень manifest

Обязательные и служебные поля (уже есть или добавляются платформой):

| Поле | Кто пишет | Назначение |
|------|-----------|------------|
| `package_id` | мобилка | UUID пакета |
| `project_id` | мобилка | должен совпадать с URL upload |
| `created_at` | мобилка | ISO-время создания |
| `submitted_by` | платформа | `{ firebase_uid, email }` при PUT manifest |
| `data` | мобилка (+ правки с UI) | ответы формы |
| `pipeline_results` | платформа | результаты пайплайнов после `commit` |
| `_ui_meta` | платформа (опц.) | лог прогонов, ошибки, hints для виджетов |

## 3. Слой `data` то что мы получаем с формы в МП

Содержимое определяется **project config** (`config.fields`, `config.flow`).

Типичные паттерны (пример Korovas):

- скаляры: `cow_identifier`, `cow_age`, `scan_time`, …
- `camera_photo` / pose-поля: объект или map `path → metadata`, где `path` = `blobs/...`
- вложенные объекты: `camera_session`, `camera_debug`, per-shot `frame_camera`, `camera_supplement`

**Правила для UI:**

- любая строка, начинающаяся с `blobs/`, — ссылка на бинарь сессии;
- правка скаляров в client-admin → PATCH соответствующего пути в `data`;
- при сохранении платформа **повторно проверяет** наличие всех blob-ссылок (как при PUT manifest).

## 4. Слой `pipeline_results` (машинная обработка)

Пишется **только django_server** (воркеры после `commit`). client-admin читает и может править подмножество (например, ручная коррекция keypoints в `annotations`).

### 4.1. `pipeline_results.inference`

```json
{
  "runs": [
    {
      "run_id": "uuid",
      "pipeline_id": "inference",
      "version": "korovas-v3",
      "status": "done",
      "started_at": "2026-05-20T12:00:00Z",
      "finished_at": "2026-05-20T12:00:05Z",
      "metrics": {
        "withers_height_cm": 142,
        "body_length_cm": 168
      },
      "raw": {}
    }
  ],
  "latest": "uuid"
}
```

- `metrics` — плоский или вложенный объект для **MetricsTable** (сравнение с `data.*`).
- `raw` — полный ответ модели (readonly в UI, expandable JSON).

### 4.2. `pipeline_results.cvat`

```json
{
  "task_id": 12345,
  "project_slug": "korovas",
  "status": "completed",
  "export_url": null,
  "updated_at": "2026-05-20T13:00:00Z"
}
```

UI: статус, кнопка **Open in CVAT** (deep link), readonly пока нет export в JSON.

### 4.3. `pipeline_results.annotations`

Массив или map по ключу кадра (`blob path` или `field_id/shot_id`):

```json
{
  "blobs/pose_1/shot_0.jpg": {
    "format": "coco_keypoints",
    "skeleton_id": "korovas_v1",
    "points": [[120.5, 340.0, 2], [130.0, 350.0, 2]],
    "labels": ["withers", "hook"],
    "source": "inference",
    "revision": 1
  }
}
```

Форматы (расширяемый enum): `coco_keypoints`, `polygon`, `bbox`, `cvat_xml_ref` (только ссылка, тело подтягивается пайплайном).

## 5. Пайплайны в project config

В **одном** project config (тот же JSON, что отдаётся мобилке) добавляется секция `config.pipelines`:

```json
{
  "id": "korovas-2026",
  "name": "Korovas",
  "config": {
    "fields": [],
    "flow": {},
    "pipelines": [
      {
        "id": "inference",
        "type": "inference",
        "trigger": "on_commit",
        "inference_version_id": "korovas-v3"
      },
      {
        "id": "cvat_export",
        "type": "cvat",
        "trigger": "on_commit",
        "depends_on": ["inference"],
        "cvat_project": "korovas"
      }
    ]
  }
}
```


