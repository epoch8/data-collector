> **Language / Язык:** [English](project-storage-uris.md) · **Русский**

# Per-project storage: database URI + fsspec URI

Статус: **реализовано v1** (июнь 2026). Код: `api/project_storage_config.py`, `project_db.py`, `project_media.py`, миграции `0010`–`0011`.

Связанные документы: [git-backed-projects.ru.md](git-backed-projects.ru.md), [main-scheme/11-stack.drawio](main-scheme/11-stack.drawio).

## Зачем

Данные проекта (пакеты, pipeline) отделены от каталога платформы (Django ORM). Два URI на проект задают, **где** лежат метаданные и blobs, независимо от `DJANGO_ENV`.

## Решения (v1)

| # | Вопрос | Решение |
|---|--------|---------|
| 1 | Где URI | Django `Project.database_uri`, `storage_uri` (+ encrypted options) |
| 2 | Project DB | **SQLAlchemy 2.x** + **Alembic** |
| 3 | Blobs | **fsspec** — `file://`, `gs://`, `s3://` |
| 4 | Пустые URI | Дефолты: SQLite + `file://` под `PROJECT_DB_ROOT` / `PROJECT_MEDIA_ROOT` |
| 5 | Креды GCS/S3 | `storage_options_encrypted` (Fernet JSON); Postgres user/pass — `database_options_encrypted` |
| 6 | Один Postgres | Поддерживается: отдельная **БД на проект** (`migrate_all_projects_to_postgres`) или schema в общей БД |
| 7 | `media_bucket` | **Deprecated** → конвертация в `gs://{bucket}/` |

Дефолт **не зависит** от `DJANGO_ENV`. Пустые поля = SQLite на диске сервера (часто NFS/PVC в prod).

## Модель Project

| Поле | Пример | Назначение |
|------|--------|------------|
| `database_uri` | `postgresql+psycopg2://host:5432/myproject_db` | SQLAlchemy URL **без** логина/пароля |
| `database_options_encrypted` | Fernet JSON `{user, password}` | Креды БД |
| `storage_uri` | `gs://bucket/` / `s3://bucket/prefix/` / `file:///path/` | Корень blobs |
| `storage_options_encrypted` | Fernet JSON `{endpoint_url, key, secret}` | S3/MinIO и т.п. |

### Дефолты (NULL / пустая строка)

```text
database_uri → sqlite:///{PROJECT_DB_ROOT}/{project_id}/project.sqlite3
storage_uri  → file:///{PROJECT_MEDIA_ROOT}/{project_id}/
```

Env: `PROJECT_DB_ROOT`, `PROJECT_MEDIA_ROOT` (см. `collector_site/settings.py`).

### Примеры

| Окружение | database_uri | storage_uri |
|-----------|--------------|-------------|
| local dev | (пусто → SQLite) | (пусто → file) |
| prod korovas | `postgresql+psycopg2://…` | `gs://korovas-dc-korovas-2026/` |
| test_dev MinIO | `postgresql+psycopg2://localhost:55432/…` | `s3://minio-bucket/project-id/` |

Trailing slash у `storage_uri` обязателен.

## Layout данных

### Project DB (SQLAlchemy)

`api/project_db.py`:

- Packages: `package_session`, `uploaded_blob`, `package_field_change`
- Pipeline: `cow_keypoint_annotation`, `cow_inference_result`, `yolo_detection`, `depth_map`, `cvat_link`

Alembic: `api/alembic/` — `upgrade head` при инициализации проекта.

### Storage (fsspec)

```text
packages/{package_id}/blobs/{logical_path}
```

В `uploaded_blob.storage_path` — относительный путь от корня `storage_uri`.

## UI (staff)

`/ui/projects/new/` и карточка проекта — блок **«Хранилище данных»**:

- Пусто → дефолт SQLite + локальная папка.
- Поля: Postgres host/db, GCS bucket name, S3 endpoint — или raw URI в «Дополнительно».
- Кнопка **«Проверить хранилище»** — connect, `SELECT 1`, Alembic migrate, list bucket root.

`media_bucket` в форме скрыт; при открытии старых проектов мигрируется в `storage_uri`.

## Потоки

### Upload пакета

1. Resolve URIs (`project_storage_config.resolve_project_storage`).
2. SQLAlchemy session для session/blob rows.
3. `fsspec` open для записи файлов.

### Миграция SQLite → Postgres

```bash
python manage.py migrate_all_projects_to_postgres
# или точечно: migrate_project_sqlite_to_postgres --project-id=...
```

## Каталог платформы vs данные проекта

| | Django ORM | Per-project |
|--|------------|-------------|
| Назначение | Users, Project catalog, Git keys | Packages, pipeline |
| Local | `db.sqlite3` | `project_db/{id}/` |
| Prod | PostgreSQL + GCS (static) | URI per project |

## Backlog

- Автоматическая миграция всех проектов на Yandex Cloud / Postgres по умолчанию (см. [todo](todo)).
- Signed URL для blob download вместо stream через Django.
- URI в Git-конфиге — не планируется.
- DataPipe integration — отдельный этап.

## Тесты

Минимум: дефолтные URI, round-trip blob на `file://`, Alembic upgrade на чистой SQLite/Postgres. См. `django_server/api/tests/` (если добавлены).
