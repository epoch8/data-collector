# test_dev — локальная имитация прод-хранилищ

Поднимает **PostgreSQL** и **MinIO (S3)** в Docker, чтобы проверить per-project
`database_uri` / `storage_uri` без реального облака. См. `specs/project-storage-uris.md`.

## 1. Запуск

```bash
cp test_dev/.env.example test_dev/.env        # при желании поменяйте логины/порты
docker compose -f test_dev/docker-compose.yml up -d
```

Что поднимется:

| Сервис | Адрес | Логин / пароль |
|--------|-------|----------------|
| PostgreSQL | `localhost:55432` | `collector` / `collector` |
| MinIO API (S3) | `http://localhost:9000` | `minioadmin` / `minioadmin` |
| MinIO Console | `http://localhost:9001` | `minioadmin` / `minioadmin` |

При старте создаётся бакет `dc-packages` (переменная `INIT_BUCKET`).

## 2. Создать БД проекта (db-per-project)

Каждый проект — отдельная база. Создать вручную:

```bash
docker compose -f test_dev/docker-compose.yml exec postgres \
  createdb -U collector proj_krs_label
```

Или management-командой (заход 2):

```bash
python manage.py create_project_db --project-id=krs-label
```

## 3. Подставить URI в проект (UI)

Проект → **Изменить хранилище**:

- **Бакет для медиа (storage)**:
  ```
  s3://dc-packages/krs-label/
  ```
- **S3 endpoint / ключи** (блок креды, шифруются в БД):
  ```
  endpoint_url = http://localhost:9000
  access key   = minioadmin
  secret key   = minioadmin
  ```
- **PostgreSQL (database_uri)**:
  ```
  postgresql+psycopg2://collector:collector@localhost:55432/proj_krs_label
  ```

Затем на странице проекта — **Проверить хранилище** (должно показать `DB … OK` и `Storage (s3) … OK`).

## 4. Перенести данные в новые хранилища (заход 2)

```bash
python manage.py migrate_project_storage --project-id=krs-label --dry-run
python manage.py migrate_project_storage --project-id=krs-label
```

Команда читает текущие данные (локальный SQLite + папка) и переносит в цель,
указанную в полях `database_uri` / `storage_uri` проекта.

## 5. Остановка

```bash
docker compose -f test_dev/docker-compose.yml down       # сохранить данные
docker compose -f test_dev/docker-compose.yml down -v    # удалить тома (чистый старт)
```

## Заметки

- Креды S3 берутся из поля проекта `storage_options` (вводятся в UI, секрет шифруется
  тем же Fernet-ключом, что и SSH deploy keys). Сервер не требует AWS env-переменных.
- В URI пароль Postgres допустим для dev/test; для прод-секретов — отдельный шаг (см. спеку).
- `gs://` (Google Cloud Storage) поддерживается тем же кодом, креды — через ADC.
