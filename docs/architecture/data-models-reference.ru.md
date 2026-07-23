# Справочник моделей данных

Учебный справочник блока «Архитектура». Полные спеки: [`02-data-models-schema.ru.md`](../../specs/02-data-models-schema.ru.md), [`07-package-payload-structure.ru.md`](../../specs/07-package-payload-structure.ru.md), [`project-storage-uris.ru.md`](../../specs/project-storage-uris.ru.md). Код: `django_server/api/project_db.py`, `lib/models/`.

## 1. Package на диске

```text
packages/<package_id>/
  ├── payload.json
  └── blobs/
      ├── pose_front.jpg
      └── ...
```

На сервере корень — `Project.storage_uri`; в БД путь: `packages/{package_id}/blobs/...`. Base64 в JSON **запрещён**.

## 2. `payload.json`

| Поле | Описание |
| --- | --- |
| `package_id` | UUID от клиента |
| `project_id` | Должен совпадать с URL API |
| `status` | `completed` при submit |
| `created_at` | ISO 8601 |
| `data` | Ответы полей конфига + метаданные камеры |
| `submitted_by` | Добавляет сервер при PUT manifest: `firebase_uid`, `email` |

### Значения в `data`

| Тип поля конфига | Формат |
| --- | --- |
| `text_input` | строка |
| `single_choice` | строка (`value` варианта) |
| `datetime` | ISO строка |
| `camera_photo` | map `blobs/...` → metadata |
| `instruction` | не пишется в payload |

### Метаданные камеры (после materialize)

- `data.camera_session` — компактный снимок сессии
- `data.camera_debug` — полный контекст для отладки
- На каждое фото: `frame_camera`, `camera_supplement`, `collected_at`

## 3. Django ORM (каталог платформы)

Модели в `django_server/api/models.py` — **не** хранят конфиг проекта и не хранят пакеты.

| Модель | Назначение |
| --- | --- |
| **CollectorUser** | `firebase_uid`, `email`; M2M `mobile_projects` (`/v1/*`), M2M `admin_projects` (client-admin `/ui/`) |
| **GitCredential** | SSH deploy key (Fernet) |
| **Project** | `project_id`, `name`, Git remote/ref/credential, `last_synced_sha`, `database_uri`, `storage_uri`, encrypted options |

Конфиг: Git → `collector/config.json` (+ `viz.json`, `pipeline.json`, `media/`).

## 4. Per-project DB (SQLAlchemy)

URI: `Project.database_uri` (дефолт — SQLite под `PROJECT_DB_ROOT`).

### Приём пакетов

| Таблица | Ключевые поля | Смысл |
| --- | --- | --- |
| `package_session` | `package_id`, `project_id`, `phase`, `manifest_json`, `failure_reason`, uploader | Сессия upload |
| `uploaded_blob` | `package_id`, `logical_path`, `storage_path`, `sha256`, `size_bytes` | Учтённый blob |
| `package_field_change` | `field_id`, before/after, `verifier_email` | Changelog правок в админке |

**Фазы** `package_session.phase`: `awaiting_blobs` → `ready_to_commit` → `completed` | `failed`.

### Pipeline / ML (не мобильный upload)

| Таблица | Назначение |
| --- | --- |
| `cow_keypoint_annotation` | GT keypoints (из CVAT / импорт) |
| `cow_inference_result` | Результат модели + опционально depth |
| `yolo_detection` | Детекции YOLO |
| `depth_map` | Карта глубины |
| `cvat_link` | Ссылка на задачу CVAT |

Связка с фото: `manifest_blob_key` (логический путь blob в манифесте).

## 5. Flutter (локально)

| Слой | Где | Содержимое |
| --- | --- | --- |
| Конфиг | `project_config.dart` | Project, fields, flow |
| Пакет DTO | `package.dart` | `CollectedPackage` |
| Drift | `core/storage/database.dart` | `packages`: id, projectId, status, dataJson, `serverDeliveryState`, `serverDeliveryError` |

| `status` | `serverDeliveryState` |
| --- | --- |
| `draft` / `completed` | `pending` / `uploading` / `completed` / `failed` |

## 6. Хранилища — шпаргалка

| Слой | Local | Prod (пример) |
| --- | --- | --- |
| Catalog (Django) | SQLite | PostgreSQL |
| Project DB | SQLite `project_db/{id}/` | Postgres URI |
| Blobs | `file://project_media/{id}/` | `gs://` / `s3://` |
| Config | Git cache | то же |

Дефолты per-project **не зависят** от `DJANGO_ENV`.

## 7. Куда смотреть при инциденте

| Симптом | Таблица / файл |
| --- | --- |
| Пакет «завис» на upload | `package_session.phase`, Drift `serverDeliveryState` |
| Нет фото в админке | `uploaded_blob` + объект в `storage_uri` |
| Пустой инференс | `cow_inference_result` |
| Нет разметки / CVAT | `cow_keypoint_annotation`, `cvat_link` |
| Нет проекта в мобилке | `CollectorUser.mobile_projects`, Git sync |

См. также [diagnostics-checklist.ru.md](diagnostics-checklist.ru.md) и [korovas-broken/cases.md](korovas-broken/cases.md).
