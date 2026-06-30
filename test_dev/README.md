> **Language / Язык:** **English** · [Русский](README.ru.md)

# test_dev — local prod-storage emulation

Runs **PostgreSQL** and **MinIO (S3)** in Docker to test per-project
`database_uri` / `storage_uri` without a real cloud. See `specs/project-storage-uris.md`.

## 1. Launch

```bash
cp test_dev/.env.example test_dev/.env        # optionally change logins/ports
docker compose -f test_dev/docker-compose.yml up -d
```

What comes up:

| Service | Address | Login / password |
|---------|---------|------------------|
| PostgreSQL | `localhost:55432` | `collector` / `collector` |
| MinIO API (S3) | `http://localhost:9000` | `minioadmin` / `minioadmin` |
| MinIO Console | `http://localhost:9001` | `minioadmin` / `minioadmin` |

On startup, bucket `dc-packages` is created (`INIT_BUCKET` variable).

## 2. Create project DB (db-per-project)

Each project has its own database. Create manually:

```bash
docker compose -f test_dev/docker-compose.yml exec postgres \
  createdb -U collector proj_krs_label
```

Or via management command (step 2):

```bash
python manage.py create_project_db --project-id=krs-label
```

## 3. Set URIs in project (UI)

Project → **Edit storage**:

- **Media bucket (storage)**:
  ```
  s3://dc-packages/krs-label/
  ```
- **S3 endpoint / keys** (credentials block, encrypted in DB):
  ```
  endpoint_url = http://localhost:9000
  access key   = minioadmin
  secret key   = minioadmin
  ```
- **PostgreSQL (database_uri)**:
  ```
  postgresql+psycopg2://collector:collector@localhost:55432/proj_krs_label
  ```

Then on the project page — **Test storage** (should show `DB … OK` and `Storage (s3) … OK`).

## 4. Migrate data to new storage (step 2)

```bash
python manage.py migrate_project_storage --project-id=krs-label --dry-run
python manage.py migrate_project_storage --project-id=krs-label
```

The command reads current data (local SQLite + folder) and migrates to the target
specified in the project's `database_uri` / `storage_uri` fields.

## 5. Shutdown

```bash
docker compose -f test_dev/docker-compose.yml down       # keep data
docker compose -f test_dev/docker-compose.yml down -v    # remove volumes (clean start)
```

## Notes

- S3 credentials come from the project's `storage_options` field (entered in UI, secret encrypted
  with the same Fernet key as SSH deploy keys). Server does not require AWS env variables.
- Postgres password in URI is acceptable for dev/test; for prod secrets — separate step (see spec).
- `gs://` (Google Cloud Storage) is supported by the same code, credentials via ADC.
