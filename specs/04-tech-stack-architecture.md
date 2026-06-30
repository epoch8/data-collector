> **Language / Язык:** **English** · [Русский](04-tech-stack-architecture.ru.md)

# Tech Stack & Architecture

Status: **current** (June 2026).

## 1. Repository

| Path | Purpose |
|------|------------|
| `lib/`, `pubspec.yaml` | Flutter client (Android, iOS, Web) |
| `django_server/` | Django 5.x: API `/v1/*`, admin `/ui/`, Django admin `/admin/` |
| `assets/config/` | Bundled offline configs (7 demo projects) |
| `test_dev/` | Docker Compose: Postgres + MinIO for local URI testing |
| `specs/` | Product documentation and diagrams |
| `docs/` | Engineering notes; `docs/business/` — commercial materials |
| `legacy/` | Not used in the main pipeline (see `legacy/README.md`) |

Reference Shelf server for specs 08–09 (`legacy/mock_server/`, not production) and
the planned separate `client-admin` SPA (build artifacts only) are in `legacy/`.
Admin UI is **Django templates** in `django_server/`, not a separate frontend.

## 2. Flutter client

| Component | Library / version |
|-----------|---------------------|
| SDK | Dart `^3.11.4` |
| State | `flutter_riverpod`, `riverpod_annotation` |
| DB | `drift ^2.31.0`, `sqlite3_flutter_libs` |
| HTTP | `dio ^5.9.2` |
| Auth | `firebase_core ^3.8.1`, `firebase_auth ^5.3.4` |
| Routing | `go_router ^17.2.0` |
| Serialization | `freezed_annotation`, `json_annotation` |
| Other | `connectivity_plus`, `image_picker`, `exif`, `shared_preferences`, `flutter_markdown` |

### `lib/` structure

```text
lib/
├── main.dart, bootstrap.dart, firebase_options.dart
├── core/
│   ├── api/           # ApiEnvironment, dioProvider (Firebase Bearer)
│   ├── storage/       # Drift AppDatabase
│   ├── package/       # PackagePaths (on-disk blobs)
│   ├── device/        # Camera channel, EXIF
│   ├── quality/       # Image quality analysis
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

Platform splits: `*_io.dart` / `*_web.dart` for DB, upload, assets, camera.

## 3. Django server

| Component | Library |
|-----------|------------|
| Framework | Django `>=5.0,<6` |
| CORS | `django-cors-headers` |
| Auth | `firebase-admin` |
| Catalog prod | PostgreSQL + `django-storages[google]` (GCS static) |
| Project data | SQLAlchemy `>=2.0`, Alembic, `fsspec` + `gcsfs` / `s3fs` |
| Secrets | `cryptography` (Fernet for SSH keys, DB/S3 creds) |

### `django_server/api/` structure

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

## 4. Storage

| Layer | Local dev | Production (platform) |
|------|-----------|------------------------|
| Django catalog | SQLite `db.sqlite3` | PostgreSQL |
| Per-project DB | SQLite `project_db/{id}/` (default) | Postgres URI in `Project.database_uri` |
| Per-project blobs | `file://project_media/{id}/` (default) | `gs://` / `s3://` in `Project.storage_uri` |
| Project config | Git cache `project_git_cache/{id}/` | same |

Per-project defaults **do not depend** on `DJANGO_ENV`. See [project-storage-uris.md](project-storage-uris.md).

## 5. Network and authorization

```text
Flutter                    Django
  │ Firebase ID token        │ verify_id_token → CollectorUser
  │ Authorization: Bearer    │ filter projects by mobile_projects
  └────── GET/POST /v1/* ────┘

Staff: Django session (is_staff)
Client-admin: Firebase → session ui_collector_pk → admin_projects
```

`APPEND_SLASH = False` — paths without trailing `/`.

## 6. Not used / deferred

- `workmanager` / `flutter_background_service` — background upload queue.
- Separate React/Vite admin SPA.
- Django ORM for package sessions (removed in migration `0009`).
