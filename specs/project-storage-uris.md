# Per-project storage: database URI + fsspec URI

Статус: **решения зафиксированы (v1)**, реализация — поэтапно.

Связанные документы: [git-backed-projects.md](git-backed-projects.md), диаграмма [main-scheme/11-stack.drawio](main-scheme/11-stack.drawio).

## Зачем

Сейчас данные проекта (не каталог платформы) разнесены по разным механизмам:

| Что | Сейчас | Проблема |
|-----|--------|----------|
| Метаданные пакетов + pipeline | `project_db/{id}/project.sqlite3`, raw `sqlite3` | нет единых миграций, сложно переехать на Postgres |
| Blobs пакетов | `project_media.py`: локальная папка или GCS по `DJANGO_ENV` | логика завязана на глобальный режим, не на проект |
| Коровы (korovas) | тот же SQLite | нужен Postgres без переписывания всего кода |

**Цель v1:** два URI на проект — `database_uri` и `storage_uri`. Код платформы не ветвится по `DJANGO_ENV` для данных проекта; окружение задаётся явно в каталоге.

## Решения (v1)

| # | Вопрос | Решение |
|---|--------|---------|
| 1 | Где хранятся URI | В **Django DB**, модель `Project`. Не в `collector/config.json` (там только схема сбора и пайплайны) |
| 2 | Доступ к project DB | **SQLAlchemy 2.x** + **Alembic** (миграции per engine). Django ORM — только для каталога платформы |
| 3 | Доступ к blobs | **fsspec** (`filesystem(url)`). Один API для `file://`, `gs://`, `s3://` |
| 4 | Пустые URI | Сервер подставляет **дефолты** из `project_id` — **SQLite + папка на диске сервера** (как сейчас; в prod это часто смонтированный сетевой диск) |
| 8 | UI при создании проекта | Staff **может указать** Postgres и GCS/S3-бакет; если не указал — остаётся режим «локально на сервере» (SQLite + `file://`) |
| 5 | Креды для GCS/S3 | Через стандарт окружения (ADC, `GOOGLE_APPLICATION_CREDENTIALS`, AWS env). В URI секреты не кладём |
| 6 | Один Postgres на все проекты | **Да, v1:** одна БД, **отдельная schema на проект** (`korovas_2026`, …). Отдельная БД на проект — позже |
| 7 | DataPipe / cowmetric | **Вне scope v1.** Сначала SQLAlchemy-слой в `django_server`; интеграция с DataPipe — отдельный шаг |

## Модель Project (новые поля)

Добавить к существующим полям (`git_remote`, `media_bucket`, …):

| Поле | Пример | Назначение |
|------|--------|------------|
| `database_uri` | `sqlite:////data/project_db/korovas-2026/project.sqlite3` | SQLAlchemy URL для пакетов + pipeline-таблиц |
| `storage_uri` | `file:///data/project_media/korovas-2026/` | Корень blobs пакетов через fsspec |

Поле `media_bucket` — **deprecated** после миграции: значение конвертируется в `gs://{bucket}/` при первом сохранении.

### Дефолты (если поле пустое)

```text
database_uri → sqlite:///{PROJECT_DB_ROOT}/{project_id}/project.sqlite3
storage_uri  → file:///{PROJECT_MEDIA_ROOT}/{project_id}/
```

Пути `PROJECT_DB_ROOT` и `PROJECT_MEDIA_ROOT` — как в `django_server/collector_site/settings.py` сегодня. В production их обычно монтируют на **общий сетевой диск** (NFS, PVC в k8s и т.п.) — поведение то же, что «как раньше»: один файл `project.sqlite3` и каталог медиа на шаре, без облачного бакета и без Postgres.

**Важно:** дефолт не зависит от `DJANGO_ENV`. Режим «сетевой диск + SQLite» — это осознанный выбор «поля пустые», а не «мы в local».

### Примеры по окружениям

| Окружение | `database_uri` | `storage_uri` |
|-----------|----------------|---------------|
| local dev | `sqlite:///…/project_db/simple-photo-2026/project.sqlite3` | `file:///…/project_media/simple-photo-2026/` |
| prod (korovas) | `postgresql://user:pass@host:5432/collector?options=-csearch_path%3Dkorovas_2026` | `gs://korovas-dc-korovas-2026/` |
| prod (MinIO) | `postgresql://…` | `s3://minio-bucket/korovas-2026/` |

Trailing slash у `storage_uri` обязателен.

## Layout данных (не меняется)

### Внутри project DB (SQLAlchemy)

Те же таблицы, что в `api/project_db.py` сегодня:

- `package_session`, `uploaded_blob`, `package_field_change`
- pipeline: `cow_keypoint_annotation`, `cow_inference_result`, `yolo_detection`, `depth_map`, `cvat_link`, …

Схема описывается SQLAlchemy `Table` / declarative models; Alembic ведёт версию (`schema_meta` можно убрать в пользу `alembic_version`).

### Внутри storage (fsspec)

Относительные пути как сейчас:

```text
packages/{package_id}/blobs/img_0001.jpg
```

В БД в `uploaded_blob.storage_path` хранится этот относительный путь; `storage_uri` — только корень.

## Архитектура кода (целевая)

```text
django_server/api/
  project_storage/
    database.py      # engine/session из database_uri
    models.py        # SQLAlchemy metadata
    migrations/      # Alembic (или общий alembic per deployment)
    packages.py      # бывшая логика project_db + project_packages
    blobs.py         # бывшая project_media через fsspec
```

- `project_db.py` и `project_media.py` — тонкие фасады → deprecated → удалить.
- Вызовы из `packages_ui.py`, viz-плагинов, management commands идут через новый слой.

**Django ORM** (`Project`, `CollectorUser`, `GitCredential`) не трогаем.

## UI: создание и редактирование проекта (staff)

Форма **«Новый проект»** (`/ui/projects/new/`) и карточка проекта дополняются блоком **«Хранилище данных»** (опционально, можно свернуть).

### Режим по умолчанию (ничего не заполнять)

Подходит для большинства новых проектов и полностью повторяет текущее поведение:

| | |
|---|---|
| База | SQLite: `project_db/{project_id}/project.sqlite3` на `PROJECT_DB_ROOT` |
| Медиа | Папка: `project_media/{project_id}/` на `PROJECT_MEDIA_ROOT` |
| В БД | `database_uri` и `storage_uri` **пустые** (резолвятся в рантайме) |

В подписи к блоку: *«Если не указано — данные на диске сервера (SQLite), как раньше»*.

### Явное указание (prod / korovas)

Staff заполняет только то, что нужно; остальное остаётся дефолтом.

| Поле в UI | Куда пишется | Пример |
|-----------|--------------|--------|
| **GCS-бакет** (имя, без `gs://`) | `storage_uri` | `korovas-dc-korovas-2026` → `gs://korovas-dc-korovas-2026/` |
| **PostgreSQL** — хост, БД, schema (или одна строка URI в «Дополнительно») | `database_uri` | schema `korovas_2026` в общей БД `collector` |

В v1 в форме **не** показываем сырой URI по умолчанию — только понятные поля + ссылка «Дополнительно: полный database_uri / storage_uri» для power users.

Кнопка **«Проверить хранилище»** на карточке проекта (аналог «Проверить Git»):

1. Подключиться к engine / fsspec.
2. Для SQLite/`file` — создать каталог при отсутствии.
3. Для Postgres — `SELECT 1`, наличие schema, `alembic upgrade head` при пустой schema.
4. Для GCS — `fs.exists` или list на корне бакета.

Редактирование URI **после создания** — на странице проекта (staff). Смена с SQLite на Postgres — только через миграцию данных (не «переключатель в один клик» без скрипта).

Поле `media_bucket` в форме **убираем**; при открытии старых проектов значение мигрируется в `storage_uri`.

## Потоки

### Создание проекта (staff)

1. Как сейчас: `project_id`, имя, Git URL, deploy key.
2. Опционально: GCS-бакет и/или Postgres (см. UI выше).
3. Если блок хранилища пуст — `database_uri` и `storage_uri` не сохраняются (NULL) → дефолты SQLite + папка на диске.
4. `bootstrap_new_project`: Git seed, как сейчас.
5. При первом пакете или по «Проверить хранилище»: Alembic `upgrade head`, создание каталогов на диске.

### Чтение / запись пакета

1. Загрузить `Project`, собрать `database_uri` / `storage_uri` (с дефолтами).
2. DB: SQLAlchemy session; blobs: `fs = fsspec.filesystem(storage_uri)` → `fs.open(rel_path, "wb")`.
3. Отдача файла в UI: локально — `FileResponse`; для `gs://` / `s3://` — redirect на signed URL или stream через fsspec (зафиксировать в реализации: v1 — stream через сервер для admin, signed URL — опционально).

### Миграция korovas на Postgres (пункт todo «коровы на Post»)

1. Поднять Postgres, создать schema `korovas_2026` (имя = `project_id` с заменой `-` → `_`).
2. `alembic upgrade head` на schema.
3. Скрипт: SQLite → Postgres (`sqlite3` dump / pandas / custom INSERT).
4. В `Project` для `korovas-2026`: выставить `database_uri` на Postgres.
5. `storage_uri` → `gs://korovas-dc-korovas-2026/` (или текущий bucket из `media_bucket`).
6. Прогнать smoke: список пакетов, открытие workspace, viz (yolo, depth).

Откат: вернуть `database_uri` на sqlite (данные в SQLite не удалять до стабилизации).

## Замена текущего кода

| Сейчас | Будет |
|--------|--------|
| `sqlite3.connect` в `project_db.py` | `sqlalchemy.create_engine(database_uri)` |
| `schema_meta` + ручной DDL | Alembic revisions |
| `if DJANGO_ENV == production` в `project_media.py` | `fsspec.filesystem(storage_uri)` |
| `Project.media_bucket` | `storage_uri` (`gs://…`) |
| `PROJECT_MEDIA_BUCKET_TEMPLATE` | только fallback при пустом `storage_uri` в prod |

## Тесты (минимум v1)

1. **Дефолты URI** — пустые поля → ожидаемые `sqlite` / `file` пути.
2. **Round-trip blob** — `write_blob` + `read_blob` на tmp `file://` и (опционально CI) in-memory / moto для `s3://`.
3. **Round-trip package** — создать session, blob, manifest через SQLAlchemy-слой; прочитать обратно.
4. **Миграция schema** — Alembic upgrade с нуля на чистой SQLite и на Postgres schema.
5. **Регрессия korovas** — после миграции на Post: N пакетов, pipeline-таблицы на месте.

## Вне scope v1

- DataPipe / отдельный `pipeline-server-app` внутри django_server.
- URI в Git-конфиге.
- Автоматическая миграция всех проектов с SQLite на Postgres.
- Webhook / multi-region replication для storage.
- Креды внутри URI (`postgresql://user:pass@…` в БД — допустимо для v1 korovas; позже — secret manager + шаблон URI).

## Порядок реализации

1. Спека (этот файл) + поля `database_uri`, `storage_uri` в `Project` (nullable).
2. UI: блок «Хранилище» в `project_new` / `project_detail`, кнопка «Проверить хранилище».
3. `project_storage/blobs.py` на fsspec; переключить `project_media.py` на фасад.
4. SQLAlchemy models + Alembic для SQLite (паритет с текущей схемой).
5. Перенести CRUD пакетов с `sqlite3` на SQLAlchemy.
6. Management command: `migrate_project_sqlite_to_postgres --project-id=korovas-2026`.
7. Миграция korovas в prod; deprecate `media_bucket`.
8. Тесты из раздела выше.

## Legacy

- Существующие файлы `project_db/*/project.sqlite3` и `project_media/*/` **не переименовываем** — дефолтные URI указывают на те же пути.
- Проекты без Postgres продолжают работать на SQLite до явной смены URI.
