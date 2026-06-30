> **Language / Язык:** [English](git-backed-projects.md) · **Русский**

# Git-backed projects (конфиг проекта в репозитории)

Статус: **реализовано** (июнь 2026). Код: `django_server/api/project_git.py`, `project_config_service.py`, миграция `0006_git_backed_projects`.

## Решения (v1)

| # | Вопрос | Решение |
|---|--------|---------|
| 1 | Репозиторий ↔ проект | **1 репозиторий = 1 проект** |
| 2 | Подключение | SSH deploy key; приватный ключ Fernet-шифрование в `GitCredential` |
| 3 | Ключи | **Отдельный deploy key на каждый проект** |
| 4 | Путь к конфигу | **`collector/config.json`** (константа `CONFIG_REL_PATH`) |
| 5 | Медиа примеров | **`collector/media/`** в том же репо |
| 6 | Сбой Git | **Жёсткая ошибка** — без отдачи устаревшего конфига из Django |
| 7 | Кто меняет конфиг | **Django UI** → `git commit` + `git push` |

## Django DB (каталог)

Модель **Project** — указатель на Git, **без** `raw_json`.

| Поле | Назначение |
|------|------------|
| `project_id` (PK) | = `id` в `collector/config.json` |
| `name` | Для списков |
| `git_remote` | SSH URL (`git@github.com:org/repo.git`) |
| `git_default_ref` | Ветка, default `main` |
| `git_credential` | FK → `GitCredential` |
| `last_synced_sha`, `last_synced_at`, `sync_error` | Диагностика sync |
| `database_uri`, `storage_uri`, `*_options_encrypted` | Per-project data storage (см. [project-storage-uris.ru.md](project-storage-uris.ru.md)) |
| `media_bucket` | **Deprecated** → `storage_uri` |

**Не в Git:** пакеты, blobs, пользователи Firebase, права `CollectorUser`.

## Layout репозитория

```
my-project/
  collector/
    config.json       # Project JSON (fields, flow, ui)
    media/            # статика для инструкций
    viz.json          # визуализация в админке (опционально)
```

## Кэш на сервере

```
{PROJECT_GIT_CACHE_ROOT}/{project_id}/
```

Default: `django_server/project_git_cache/`.

- Перед чтением/записью: `git fetch` + hard reset на `origin/{ref}`.
- Rate limit pull: `PROJECT_GIT_PULL_MIN_INTERVAL_SEC` (default 300s), `force=True` в админке.
- При ошибке — 502/503, **без** fallback на старый JSON.

## Потоки

### Создание проекта (staff)

`/ui/projects/new/`: `project_id`, name, GitHub URL → SSH, deploy key (генерация или вставка OpenSSH; `.ppk` отклоняется).

1. `GitCredential` + `Project`.
2. `git ls-remote` / shallow clone — проверка доступа.
3. Seed `collector/config.json` если отсутствует (при write key).
4. Опционально: блок «Хранилище данных» (Postgres / S3 / GCS).

### Чтение (мобилка, admin)

1. Pull в кэш.
2. Read + validate `collector/config.json`.
3. API: raw JSON; **ETag** = `last_synced_sha`.

Медиа: `GET /v1/projects/{id}/assets/{path}` из `collector/media/`.

### Изменение конфига

`/ui/projects/{id}/config/` (JSON editor) или `/config/builder/` (визуальный):

1. Pull.
2. Write file + validate (`project_config_validate.py`).
3. `git add` → `commit` → `push origin HEAD:{ref}`.
4. Update `last_synced_sha`.

Конфликт non-fast-forward → ошибка пользователю (merge UI — backlog).

### Медиа в Git

`/ui/projects/{id}/media/` — upload/delete → commit в `collector/media/`.

## API

| Endpoint | Поведение |
|----------|-----------|
| `GET /v1/projects` | Каталог; `config_version` = SHA prefix |
| `GET /v1/projects/{id}/config` | Raw JSON; ETag = SHA; `304` |
| `GET /v1/projects/{id}/assets/{path}` | Binary из git cache |

Admin JSON API: `/ui/api/v1/projects/{id}/config`.

## Миграция с legacy

- `0006_git_backed_projects` — удаление старых `Project` без Git.
- Bundled `assets/config/` — только офлайн-fallback клиента, не source of truth сервера.

## Backlog (вне v1)

- Webhook GitHub для auto-pull.
- Pin `config_git_sha` на `PackageSession`.
- Monorepo (несколько проектов в одном репо).
- HTTPS + PAT вместо SSH.
