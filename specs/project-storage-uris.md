> **Language / Язык:** **English** · [Русский](project-storage-uris.ru.md)

# Per-project storage: database URI + fsspec URI

Status: **implemented v1** (June 2026). Code: `api/project_storage_config.py`, `project_db.py`, `project_media.py`, migrations `0010`–`0011`.

Related documents: [git-backed-projects.md](git-backed-projects.md), [main-scheme/11-stack.drawio](main-scheme/11-stack.drawio).

## Why

Project data (packages, pipeline) is separated from the platform catalog (Django ORM). Two URIs per project define **where** metadata and blobs live, independent of `DJANGO_ENV`.

## Decisions (v1)

| # | Question | Decision |
|---|----------|----------|
| 1 | Where URIs live | Django `Project.database_uri`, `storage_uri` (+ encrypted options) |
| 2 | Project DB | **SQLAlchemy 2.x** + **Alembic** |
| 3 | Blobs | **fsspec** — `file://`, `gs://`, `s3://` |
| 4 | Empty URIs | Defaults: SQLite + `file://` under `PROJECT_DB_ROOT` / `PROJECT_MEDIA_ROOT` |
| 5 | GCS/S3 credentials | `storage_options_encrypted` (Fernet JSON); Postgres user/pass — `database_options_encrypted` |
| 6 | Single Postgres | Supported: separate **DB per project** (`migrate_all_projects_to_postgres`) or schema in shared DB |
| 7 | `media_bucket` | **Deprecated** → converted to `gs://{bucket}/` |

Default **does not depend** on `DJANGO_ENV`. Empty fields = SQLite on server disk (often NFS/PVC in prod).

## Project model

| Field | Example | Purpose |
|-------|---------|---------|
| `database_uri` | `postgresql+psycopg2://host:5432/myproject_db` | SQLAlchemy URL **without** login/password |
| `database_options_encrypted` | Fernet JSON `{user, password}` | DB credentials |
| `storage_uri` | `gs://bucket/` / `s3://bucket/prefix/` / `file:///path/` | Blob root |
| `storage_options_encrypted` | Fernet JSON `{endpoint_url, key, secret}` | S3/MinIO etc. |

### Defaults (NULL / empty string)

```text
database_uri → sqlite:///{PROJECT_DB_ROOT}/{project_id}/project.sqlite3
storage_uri  → file:///{PROJECT_MEDIA_ROOT}/{project_id}/
```

Env: `PROJECT_DB_ROOT`, `PROJECT_MEDIA_ROOT` (see `collector_site/settings.py`).

### Examples

| Environment | database_uri | storage_uri |
|-------------|--------------|-------------|
| local dev | (empty → SQLite) | (empty → file) |
| prod korovas | `postgresql+psycopg2://…` | `gs://korovas-dc-korovas-2026/` |
| test_dev MinIO | `postgresql+psycopg2://localhost:55432/…` | `s3://minio-bucket/project-id/` |

Trailing slash on `storage_uri` is required.

## Data layout

### Project DB (SQLAlchemy)

`api/project_db.py`:

- Packages: `package_session`, `uploaded_blob`, `package_field_change`
- Pipeline: `cow_keypoint_annotation`, `cow_inference_result`, `yolo_detection`, `depth_map`, `cvat_link`

Alembic: `api/alembic/` — `upgrade head` on project initialization.

### Storage (fsspec)

```text
packages/{package_id}/blobs/{logical_path}
```

In `uploaded_blob.storage_path` — relative path from `storage_uri` root.

## UI (staff)

`/ui/projects/new/` and project card — **Data storage** block:

- Empty → default SQLite + local folder.
- Fields: Postgres host/db, GCS bucket name, S3 endpoint — or raw URI in "Advanced".
- **Verify storage** button — connect, `SELECT 1`, Alembic migrate, list bucket root.

`media_bucket` hidden in form; on opening old projects migrated to `storage_uri`.

## Flows

### Package upload

1. Resolve URIs (`project_storage_config.resolve_project_storage`).
2. SQLAlchemy session for session/blob rows.
3. `fsspec` open for file writes.

### SQLite → Postgres migration

```bash
python manage.py migrate_all_projects_to_postgres
# or targeted: migrate_project_sqlite_to_postgres --project-id=...
```

## Platform catalog vs project data

| | Django ORM | Per-project |
|--|------------|-------------|
| Purpose | Users, Project catalog, Git keys | Packages, pipeline |
| Local | `db.sqlite3` | `project_db/{id}/` |
| Prod | PostgreSQL + GCS (static) | URI per project |

## Backlog

- Automatic migration of all projects to Yandex Cloud / Postgres by default (see [todo](todo)).
- Signed URL for blob download instead of stream through Django.
- URI in Git config — not planned.
- DataPipe integration — separate stage.

## Tests

Minimum: default URIs, round-trip blob on `file://`, Alembic upgrade on clean SQLite/Postgres. See `django_server/api/tests/` (if added).
