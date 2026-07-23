# Полный бэкап проекта (read-only)

Standalone-скрипт без Django. Скачивает **всё** для восстановления проекта локально.  
**Ничего не удаляет** — ни в Postgres, ни в S3, ни в Git.

## Что попадает в бэкап

```text
{output}/
  backup_manifest.json       ← отчёт: что скачано, когда, счётчики
  manifests.jsonl            ← как в photo-export (для совместимости)
  postgres/
    package_session.jsonl    ← все строки всех таблиц public
    uploaded_blob.jsonl
    package_field_change.jsonl
  s3/
    packages/{uuid}/blobs/…  ← зеркало ключей из бакета
  git-repo/
    collector/config.json
    collector/media/
    collector/viz.json
```

| Источник | Операции | Запись |
|----------|----------|--------|
| Postgres | `SELECT` (readonly session) | только локально |
| S3 | `ListObjectsV2`, `GetObject` | только локально |
| Git | `git clone` (shallow) | только локально |

**Не бэкапится:** Django DB (пользователи, права, `database_uri` в админке) — это настройки сервера, не данных проекта.

---

## Установка

```powershell
cd tools\project-backup
pip install -r requirements.txt
```

Скопируйте `.env.example` → `.env` (не коммитить).

---

## Быстрый старт (PowerShell)

### 1. Креды

```powershell
$env:DATABASE_URL = "postgresql+psycopg2://USER:PASS@HOST:6432/dc-project-korovas?sslmode=require"
$env:AWS_PROFILE = "yandex"
$env:GIT_REMOTE = "git@github.com:org/my-project.git"
```

Для Git по SSH нужен доступ с этой машины (ключ в `~/.ssh` или `GIT_SSH_COMMAND`).

### 2. Dry-run (план без скачивания)

```powershell
python backup_project.py backup `
  --bucket dc-project-korovas `
  --endpoint-url https://storage.yandexcloud.net `
  --output $env:USERPROFILE\Desktop\backup\korovas `
  --dry-run
```

### 3. Полный бэкап

```powershell
python backup_project.py backup `
  --bucket dc-project-korovas `
  --endpoint-url https://storage.yandexcloud.net `
  --git-remote git@github.com:org/my-project.git `
  --output $env:USERPROFILE\Desktop\backup\korovas `
  --skip-existing
```

`--skip-existing` — не перекачивать уже скачанные файлы S3 (удобно для дозагрузки).

### 4. Проверка

```powershell
python backup_project.py verify $env:USERPROFILE\Desktop\backup\korovas
```

---

## Флаги

| Флаг | Назначение |
|------|------------|
| `--dry-run` | Посчитать объём, не писать файлы |
| `--skip-existing` | S3: пропускать уже существующие локальные файлы |
| `--skip-postgres` | Только S3 + Git |
| `--skip-s3` | Только Postgres + Git |
| `--skip-git` | Только Postgres + S3 |
| `--continue-on-error` | Не останавливаться при ошибке одной секции |

---

## Безопасность

- Скрипт **не вызывает** `DELETE`, `DROP`, `aws s3 rm`, `sync --delete`, `git push` и т.п.
- Postgres: сессия `readonly=True`
- Если `git-repo/` уже есть в output — clone **пропускается** (чтобы не перезаписать вручную)
- Пишет **только** в `--output`

---

## Связь с photo-export

`tools/photo-export` — выгрузка **фото по животным** в удобные папки.  
`tools/project-backup` — **полный снимок** (БД + весь S3 prefix + Git).

После бэкапа `manifests.jsonl` в корне output совместим с `download_photos_from_s3.py`, если нужна отдельная раскладка по кличкам.

---

## Восстановление в локальный test_dev

Скрипт `restore_project.py` заливает бэкап в **локальные** Postgres + MinIO
(`test_dev/docker-compose.yml`). По умолчанию **отказывается** писать в облако /
non-localhost (нужен явный `--allow-remote`).

```powershell
# 1. Поднять локальные хранилища
cd c:\Users\admin\Desktop\epoch8\data_collector\data-collector
docker compose -f test_dev/docker-compose.yml up -d

# 2. Залить бэкап
cd tools\project-backup
pip install -r requirements.txt

python restore_project.py restore `
  --backup $env:USERPROFILE\Desktop\backup\korovas `
  --database-url "postgresql://collector:collector@localhost:55432/proj_korovas" `
  --bucket dc-packages `
  --endpoint-url http://localhost:9000 `
  --access-key minioadmin `
  --secret-key minioadmin `
  --wipe --yes
```

Сначала можно `--dry-run` (без `--yes`).

После заливки скрипт печатает URI для админки. Для проекта **korovas**:

- **database_uri:** `postgresql+psycopg2://collector:collector@localhost:55432/proj_korovas`
- **storage_uri:** `s3://dc-packages/`
- **endpoint / keys:** `http://localhost:9000` / `minioadmin` / `minioadmin`

Затем «Проверить хранилище».

| Флаг | Назначение |
|------|------------|
| `--wipe --yes` | Очистить таблицы цели перед заливкой |
| `--skip-existing` | S3: не перезаливать уже существующие ключи |
| `--skip-postgres` / `--skip-s3` | Только одна секция |
| `--key-prefix korovas/` | Класть объекты под префикс (тогда storage_uri = `s3://dc-packages/korovas/`) |
| `--allow-remote` | Разрешить non-localhost (опасно) |

**Не восстанавливается:** Git-репозиторий проекта (в бэкапе мог быть `--skip-git`) —
конфиг форм по-прежнему из `git_remote` проекта в Django.

---

## Восстановление (кратко, вручную)

| Что | Как |
|-----|-----|
| Конфиг | `git-repo/collector/` → push в новый репо |
| Фото | `s3/` → `aws s3 cp` / sync **в бакет** (вручную, осторожно с направлением) |
| БД | из `postgres/*.jsonl` или отдельный `pg_restore` при наличии дампа |

Полное восстановление Postgres из JSONL — отдельная процедура; для архива и аудита JSONL достаточно.
