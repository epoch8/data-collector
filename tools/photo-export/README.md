# Выгрузка фото из S3 по животным и ракурсам

Standalone-набор скриптов (без Django). Скачивает фото из Yandex Object Storage / S3 и раскладывает по папкам:

```text
{output}/
  {cow_name}/                    ← кличка (или другое поле)
    01_photo_profile_left/
      img_0001.jpg
    02_photo_profile_right/
      ...
  _export_index.csv              ← индекс: что откуда скачано
```

**На проде ничего не меняется** — только чтение из Postgres и S3, запись файлов локально.

---

## Что нужно

- Python 3.10+
- Доступ к **project Postgres** (манifests)
- Доступ к **S3-бакету** (фото)

Для проекта **krs-label** (проверено):

| Параметр | Значение |
|----------|----------|
| S3 endpoint | `https://storage.yandexcloud.net` |
| Bucket | `dc-project-korovas` |
| Prefix | *(пустой)* |
| AWS profile | `yandex` (если настроен `aws configure`) |

---

## Установка

```powershell
cd tools\photo-export
pip install -r requirements.txt
```

Скопируйте `.env.example` в `.env` и заполните (`.env` не коммитить).

---

## Быстрый старт (PowerShell)

### 0. Креды S3

**Вариант A — AWS profile** (если уже делали `aws configure --profile yandex`):

```powershell
$env:AWS_PROFILE = "yandex"
```

**Вариант B — ключи в команде:**

```powershell
$env:S3_ENDPOINT_URL = "https://storage.yandexcloud.net"
$env:AWS_ACCESS_KEY_ID = "..."
$env:AWS_SECRET_ACCESS_KEY = "..."
```

### 1. Проверить S3

```powershell
python download_photos_from_s3.py list `
  --endpoint-url https://storage.yandexcloud.net `
  --bucket dc-project-korovas
```

### 2. Выгрузить манифесты из Postgres

```powershell
$env:DATABASE_URL = "postgresql+psycopg2://USER:PASS@HOST:6432/dc-project-korovas?sslmode=require"

python export_manifests.py -o manifests.jsonl --all-phases
```

`--all-phases` — все пакеты из БД (не только `completed`). Без флага по умолчанию только `completed`.

### 3. Dry-run (план без скачивания)

```powershell
python download_photos_from_s3.py download `
  --endpoint-url https://storage.yandexcloud.net `
  --bucket dc-project-korovas `
  --manifests manifests.jsonl `
  --output $env:USERPROFILE\Desktop\export\korovas `
  --animal-field cow_name `
  --all-phases `
  --dry-run
```

Config проекта **не нужен** — ракурсы (`photo_top`, `photo_profile_left`, …) берутся автоматически из `manifest.data`.

### 4. Скачать

```powershell
python download_photos_from_s3.py download `
  --endpoint-url https://storage.yandexcloud.net `
  --bucket dc-project-korovas `
  --manifests manifests.jsonl `
  --output $env:USERPROFILE\Desktop\export\korovas `
  --animal-field cow_name `
  --all-phases `
  --skip-existing
```

---

## Папки животных

| Флаг | Папка по полю |
|------|----------------|
| `--animal-field cow_name` | кличка / имя (`1`, `10`, `буренка`, …) |
| `--animal-field cow_identifier` | ID (`29183`, `ru1npn8vgn7`, …) |

По умолчанию в авто-режиме: `cow_name`.

---

## Файлы в этой папке

| Файл | Назначение |
|------|------------|
| `export_manifests.py` | Шаг 2: Postgres → `manifests.jsonl` (SELECT only) |
| `export_manifests.sql` | То же через `psql`, если установлен |
| `download_photos_from_s3.py` | list / download из S3 |
| `requirements.txt` | `boto3`, `psycopg2-binary` |
| `.env.example` | шаблон переменных |

---

## Частые проблемы

**Не все файлы скачались**

- В S3 может быть больше пакетов, чем в `manifests.jsonl`. Переэкспортируйте с `--all-phases`.
- Скачиваются только фото, упомянутые в manifest (поля с `blobs/*`). «Сироты» в S3 без записи в БД — отдельно.

**`FileNotFoundError: D:\...`**

- Диска `D:` может не быть. Используйте путь на `C:`, напр. `$env:USERPROFILE\Desktop\export\korovas`.

**0 файлов при download**

- Неверный `config.json` другого проекта. Запускайте **без** `--config` (авто-режим).

**Access Denied на S3**

- Проверьте profile / ключи и `--endpoint-url`.

---

## Безопасность

- Postgres: только `SELECT`
- S3: только `ListObjects` / `GetObject`
- Локально: создаётся только папка `--output`

Не запускайте `aws s3 rm`, `sync` с перепутанным направлением и т.п.
