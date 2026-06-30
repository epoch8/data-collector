> **Language / Язык:** [English](04-tech-stack-architecture.md) · **Русский**

# Tech Stack & Architecture

Статус: **актуально** (июнь 2026).

## 1. Репозиторий

| Путь | Назначение |
|------|------------|
| `lib/`, `pubspec.yaml` | Flutter-клиент (Android, iOS, Web) |
| `django_server/` | Django 5.x: API `/v1/*`, админка `/ui/`, Django admin `/admin/` |
| `assets/config/` | Bundled offline-конфиги (7 демо-проектов) |
| `test_dev/` | Docker Compose: Postgres + MinIO для локальной проверки URI |
| `specs/` | Продуктовая документация и диаграммы |
| `docs/` | Инженерные заметки; `docs/business/` — коммерческие материалы |
| `legacy/` | Неиспользуемое в основном пайплайне (см. `legacy/README.md`) |

Reference Shelf-сервер под спеки 08–09 (`legacy/mock_server/`, не production) и
задумывавшийся отдельный SPA `client-admin` (только артефакты сборки) вынесены в `legacy/`.
Админка — это **Django templates** в `django_server/`, не отдельный фронтенд.

## 2. Flutter-клиент

| Компонент | Библиотека / версия |
|-----------|---------------------|
| SDK | Dart `^3.11.4` |
| State | `flutter_riverpod`, `riverpod_annotation` |
| DB | `drift ^2.31.0`, `sqlite3_flutter_libs` |
| HTTP | `dio ^5.9.2` |
| Auth | `firebase_core ^3.8.1`, `firebase_auth ^5.3.4` |
| Routing | `go_router ^17.2.0` |
| Serialization | `freezed_annotation`, `json_annotation` |
| Прочее | `connectivity_plus`, `image_picker`, `exif`, `shared_preferences`, `flutter_markdown` |

### Структура `lib/`

```text
lib/
├── main.dart, bootstrap.dart, firebase_options.dart
├── core/
│   ├── api/           # ApiEnvironment, dioProvider (Firebase Bearer)
│   ├── storage/       # Drift AppDatabase
│   ├── package/       # PackagePaths (on-disk blobs)
│   ├── device/        # Camera channel, EXIF
│   ├── quality/       # Анализ качества изображений
│   └── presentation/  # Thumbs, photo dialogs (io/web splits)
├── features/
│   ├── projects/      # Catalog, server sync, providers
│   ├── collection/    # Wizard, upload, materializer
│   ├── sync/          # ServerSyncTab
│   ├── history/       # Local history
│   └── help/
├── models/            # project_config.dart, package.dart
├── theme/             # Epoch8 design system
└── l10n/              # RU/EN
```

Платформенные сплиты: `*_io.dart` / `*_web.dart` для DB, upload, assets, camera.

## 3. Django-сервер

| Компонент | Библиотека |
|-----------|------------|
| Framework | Django `>=5.0,<6` |
| CORS | `django-cors-headers` |
| Auth | `firebase-admin` |
| Каталог prod | PostgreSQL + `django-storages[google]` (GCS static) |
| Project data | SQLAlchemy `>=2.0`, Alembic, `fsspec` + `gcsfs` / `s3fs` |
| Secrets | `cryptography` (Fernet для SSH keys, DB/S3 creds) |

### Структура `django_server/api/`

```text
api/
├── models.py              # CollectorUser, Project, GitCredential
├── project_db.py          # SQLAlchemy schema + package CRUD
├── project_media.py       # fsspec blob I/O
├── project_storage_config.py  # URI resolver
├── project_git.py         # clone/pull/commit/push
├── project_config_service.py
├── views.py               # /v1/* mobile API
├── views_ui.py, packages_ui.py  # /ui/ HTML + JSON helpers
├── urls.py, urls_ui.py, urls_ui_api.py
├── viz_plugins/           # keypoint_korovas, depth_map, yolo_detection, cvat_link
└── static/ui/             # admin.css, packages_*.js, project_builder.js
```

## 4. Хранилища

| Слой | Local dev | Production (платформа) |
|------|-----------|------------------------|
| Django catalog | SQLite `db.sqlite3` | PostgreSQL |
| Per-project DB | SQLite `project_db/{id}/` (default) | Postgres URI в `Project.database_uri` |
| Per-project blobs | `file://project_media/{id}/` (default) | `gs://` / `s3://` в `Project.storage_uri` |
| Project config | Git cache `project_git_cache/{id}/` | то же |

Дефолты per-project **не зависят** от `DJANGO_ENV`. См. [project-storage-uris.ru.md](project-storage-uris.ru.md).

## 5. Сеть и авторизация

```text
Flutter                    Django
  │ Firebase ID token        │ verify_id_token → CollectorUser
  │ Authorization: Bearer    │ filter projects by mobile_projects
  └────── GET/POST /v1/* ────┘

Staff: Django session (is_staff)
Client-admin: Firebase → session ui_collector_pk → admin_projects
```

`APPEND_SLASH = False` — пути без завершающего `/`.

## 6. Не используется / отложено

- `workmanager` / `flutter_background_service` — фоновая очередь upload.
- Отдельный React/Vite admin SPA.
- Django ORM для package sessions (удалено в migration `0009`).
