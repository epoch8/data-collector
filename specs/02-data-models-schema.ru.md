> **Language / Язык:** [English](02-data-models-schema.md) · **Русский**

# Data Models & Config Schema

Статус: **актуально** (июнь 2026). Источник правды для парсинга на клиенте: `lib/models/project_config.dart`, `collection_flow_resolver.dart`.

## 1. Project JSON (корень файла)

Файл `collector/config.json` в Git-репозитории проекта (или bundled `assets/config/*.json` для офлайн-демо).

```json
{
  "id": "korovas-2026",
  "name": "Korovas RGB-D Capture",
  "version": "1.0",
  "config": {
    "fields": [ /* см. §2 */ ],
    "flow": {
      "steps": [ /* см. §3 */ ]
    },
    "ui": { /* опционально, см. json-driven-collection-ui.ru.md */ }
  }
}
```

- **`id`** — совпадает с `project_id` в Django и в URL API.
- **`version`** — семантическая версия для отображения; серверная «версия конфига» для кэша — Git SHA (`last_synced_sha` → `config_version` в каталоге).

## 2. Поля (`config.fields`)

Справочник всех полей сбора. Ключи в JSON: **`field_id`**, **`type`**, **`title`**, **`instructions`**, опционально **`validation`**, **`multiple`** (для `camera_photo`).

Поддерживаемые типы:

| `type` | Значение в payload | Примечание |
|--------|-------------------|------------|
| `text_input` | строка | `validation.required` |
| `datetime` | ISO 8601 строка | |
| `instruction` | не пишется в payload | Markdown в `instructions`; картинки из `collector/media/` |
| `camera_photo` | map path → metadata | `multiple` + `min_items`; см. §5 |

```json
{
  "field_id": "cow_identifier",
  "type": "text_input",
  "title": "Идентификатор",
  "instructions": "Уникальный код коровы.",
  "validation": { "required": true }
}
```

## 3. Сценарий (`config.flow.steps`)

**Только два типа экранов** (legacy `form` / `instruction` / `camera_pose` удалены):

| `screen` | Назначение |
|----------|------------|
| `scroll_form` | Один скролл-экран; поля задаются **`field_ids`** (порядок = порядок на экране). |
| `review` | Финальная проверка перед сохранением пакета. |

Правила валидации (сервер + клиент):

- Каждое поле из `fields` должно встретиться **ровно в одном** шаге `scroll_form`.
- У `scroll_form` — непустой `field_ids`.
- Опционально у шага: `form_title` (подпись на review), `cow_id_hints`, `cow_id_field_id`.

```json
{
  "flow": {
    "steps": [
      {
        "id": "main",
        "screen": "scroll_form",
        "form_title": "Анкета",
        "field_ids": ["cow_identifier", "scan_notes", "pose_front"]
      },
      {
        "id": "check",
        "screen": "review"
      }
    ]
  }
}
```

Гайд для авторов: [config/09-project-json-builder-guide.ru.md](config/09-project-json-builder-guide.ru.md).

## 4. Django ORM (каталог платформы)

`django_server/api/models.py`:

| Модель | Назначение |
|--------|------------|
| **CollectorUser** | `firebase_uid`, `email`; M2M `mobile_projects` (API `/v1/*`), M2M `admin_projects` (client-admin `/ui/packages/`) |
| **GitCredential** | SSH deploy key (Fernet-шифрование приватного ключа) |
| **Project** | `project_id` (PK), `name`, `git_remote`, `git_default_ref`, `git_credential`, `last_synced_sha`, `database_uri`, `database_options_encrypted`, `storage_uri`, `storage_options_encrypted`, deprecated `media_bucket` |

Конфиг проекта **не хранится** в Django ORM.

## 5. Per-project DB (SQLAlchemy)

Таблицы в БД проекта (`api/project_db.py`, миграции Alembic):

**Приём пакетов:**

- `package_session` — фазы `awaiting_blobs` / `ready_to_commit` / `completed` / `failed`
- `uploaded_blob` — логический путь + `storage_path` относительно `storage_uri`
- `package_field_change` — changelog правок манифеста в админке

**Pipeline (заполняется импортом / внешними job, не мобильным upload):**

- `cow_keypoint_annotation`, `cow_inference_result`, `yolo_detection`, `depth_map`, `cvat_link`

## 6. Flutter local models

| Слой | Файл | Содержимое |
|------|------|------------|
| Конфиг | `project_config.dart` | `Project`, `ProjectConfig`, `ConfigField`, `CollectionFlowDecl` |
| Пакет (DTO) | `package.dart` | `CollectedPackage` |
| Локальный индекс | `core/storage/database.dart` (Drift) | `packages`: `id`, `projectId`, `status`, `dataJson`, `serverDeliveryState`, `serverDeliveryError` (schema v3) |

## 7. Package payload (манифест)

Структура каталога и JSON — [07-package-payload-structure.ru.md](07-package-payload-structure.ru.md).

Минимальный пример `payload.json`:

```json
{
  "package_id": "pkg_1234567890",
  "project_id": "korovas-2026",
  "status": "completed",
  "created_at": "2026-04-08T14:22:00Z",
  "data": {
    "cow_identifier": "Bessie-99",
    "scan_notes": ""
  }
}
```

Пути к фото в `data` — **относительные** (`blobs/...`) после materialization. На сервере при `PUT manifest` добавляется `submitted_by: { firebase_uid, email }`.
