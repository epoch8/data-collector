> **Language / Язык:** [English](README.md) · **Русский**

# test_dev — локальная имитация прод-хранилищ

Поднимает **PostgreSQL** и **MinIO (S3)** в Docker, чтобы проверить per-project
`database_uri` / `storage_uri` без реального облака. См. [`specs/project-storage-uris.ru.md`](../specs/project-storage-uris.ru.md).

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
| Приёмник webhook | `http://localhost:18080` | — |

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

## 5. Приёмник webhook (on_commit)

Сервис `acceptance` принимает исходящий webhook, который `django_server` дёргает при
**commit** пакета (первый успешный `POST …/commit`). Нужен, чтобы проверить, что при
приёме пакета что-то реально доходит до внешней ручки.

Webhook настраивается **per-project в Git** в **отдельном** файле `collector/pipeline.json`
(не в форме `collector/config.json`), блок `on_commit`. Файл опционален — если его нет,
`enabled: false` или у проекта нет git-remote, ничего не дёргается.

```json
{
  "version": 1,
  "on_commit": {
    "enabled": true,
    "url": "http://localhost:18080/api/run-with-labels",
    "method": "POST",
    "headers": { "Content-Type": "application/json" },
    "body": { "labels": [["stage", "packages"]] },
    "timeout_seconds": 10
  }
}
```

- `body` отправляется **как есть**. Если не задан — уходит дефолт `{ "event": "package.committed", "project_id", "package_id" }`.
- `project_id` / `package_id` всегда передаются в заголовках `X-Data-Collector-Project-Id` / `X-Data-Collector-Package-Id`.

Посмотреть принятые вызовы:

```bash
curl http://localhost:18080/health       # {"status":"ok"}
curl http://localhost:18080/requests     # последние webhooks (новые сверху)
docker compose -f test_dev/docker-compose.yml logs -f acceptance
```

Быстрая ручная проверка (имитация webhook):

```bash
curl -X POST http://localhost:18080/api/run-with-labels \
  -H 'Content-Type: application/json' \
  -d '{"labels":[["stage","packages"]]}'
```

## 6. Остановка

```bash
docker compose -f test_dev/docker-compose.yml down       # сохранить данные
docker compose -f test_dev/docker-compose.yml down -v    # удалить тома (чистый старт)
```

## Заметки

- Креды S3 берутся из поля проекта `storage_options` (вводятся в UI, секрет шифруется
  тем же Fernet-ключом, что и SSH deploy keys). Сервер не требует AWS env-переменных.
- В URI пароль Postgres допустим для dev/test; для прод-секретов — отдельный шаг (см. спеку).
- `gs://` (Google Cloud Storage) поддерживается тем же кодом, креды — через ADC.
