# Git-backed projects (конфиг проекта в репозитории)

Статус: **решения зафиксированы**, реализация — поэтапно.

## Решения (v1)

| # | Вопрос | Решение |
|---|--------|---------|
| 1 | Репозиторий ↔ проект | **1 репозиторий = 1 проект** |
| 2 | Подключение | Админ вставляет **ссылку на GitHub-репо**; доступ — **SSH deploy key** (приватный ключ в data-collector, публичный — в Deploy keys репо) |
| 3 | Ключи | **Отдельный deploy key на каждый проект** (свой репо → свой ключ) |
| 4 | Путь к конфигу | **Фиксированный:** `collector/config.json` |
| 5 | Медиа примеров (camera_pose и т.д.) | **В том же репо:** `collector/media/` |
| 6 | Сбой Git (сеть, ключ, нет файла) | **Жёсткая ошибка** — без отдачи устаревшего конфига из Django |
| 7 | Кто меняет конфиг | **Только Django UI** → изменение = `git commit` + `git push` в репо проекта |

## Что остаётся в Django DB (каталог)

Модель **Project** — указатель на Git, **без** `raw_json` как source of truth.

Рекомендуемые поля:

- `project_id` (PK) — совпадает с `id` в `collector/config.json`
- `name` — для списков (можно синхронизировать из JSON после pull)
- `git_remote` — SSH URL, напр. `git@github.com:org/my-project.git`
- `git_default_ref` — ветка, по умолчанию `main`
- `config_path` — константа `collector/config.json` (не редактируется в UI v1)
- `git_credential` — FK на зашифрованный SSH-ключ проекта
- `last_synced_sha`, `last_synced_at`, `sync_error` — диагностика последнего pull/push

**Не в Git:** пакеты (`PackageSession`), blobs, манифесты, пользователи Firebase, права доступа к проектам.

## GitHub + SSH — достаточно ли?

**Да**, для приватного репо на GitHub достаточно **Deploy key**:

1. При создании проекта в Django генерируется или загружается пара ключей.
2. **Публичный** ключ показывается в UI: «Добавьте в GitHub → Settings → Deploy keys».
3. Для записи конфига из Django ключ должен быть с **Allow write access**.
4. В Django хранится только **приватный** ключ (шифрование at rest).

Ссылку из UI (`https://github.com/org/repo`) нормализуем в SSH:

`git@github.com:org/repo.git`

HTTPS + токен — **не** используем в v1.

Проверка при создании: `git ls-remote` (или shallow `git clone`) с `GIT_SSH_COMMAND` и ключом проекта.

## Layout репозитория проекта

```
my-project/
  README.md
  collector/
    config.json       # полный Project JSON (fields, flow, ui, admin_ui, …)
    media/            # статика для конфига (примеры ракурсов и т.д.)
    viz.json          # визуализация: table + plugin (см. specs/collector-vis-config.md)
```

### `collector/config.json`

- Тот же контракт, что валидирует `validate_project_payload` сегодня.
- `id` === `project_id` в Django.
- Версионирование — **история Git**, не отдельное поле `config_version` в БД (поле `version` в JSON можно оставить для мобилки).

### `collector/media/`

- Относительные пути в конфиге, напр. `collector/media/pose_front.jpg`.
- API/статика: отдача через clone-кэш или отдельный URL prefix `/ui/projects/{id}/git-media/...` после pull.

## Кэш рабочей копии на сервере

```
{PROJECT_GIT_CACHE_ROOT}/{project_id}/
```

- Перед чтением/записью конфига: `git fetch` + `checkout` на `git_default_ref`.
- При ошибке — 503/502 с понятным сообщением, **без** fallback на старый JSON из БД.

## Потоки

### Создание проекта (staff)

1. Ввод: `project_id`, `name`, URL репо (GitHub), загрузка **приватного** SSH-ключа (или генерация на сервере).
2. Сохранить `Project` + `GitCredential`.
3. `git ls-remote` — проверка доступа.
4. Если в репо нет `collector/config.json` — опционально **seed commit** (пустой валидный конфиг) + push (если write key).
5. Иначе — clone + валидация существующего `config.json`.

### Чтение конфига (мобилка `/v1/...`, admin)

1. Pull в кэш.
2. Прочитать `collector/config.json`, validate.
3. Отдать JSON как сейчас.

### Изменение конфига (только Django admin)

1. Pull (чтобы не затереть чужие коммиты без явной ошибки).
2. Записать `collector/config.json`.
3. `git add` → `git commit` → `git push`.
4. Обновить `last_synced_sha` в Project.
5. При non-fast-forward / конфликте — ошибка пользователю (merge UI — позже).

**Внешние push в репо** возможны технически, но продуктово конфиг «редактируется» только из Django; расхождение ловим на pull перед save.

## API / UI (замена текущего)

| Сейчас | Будет |
|--------|--------|
| `Project.raw_json` | удалить / deprecated |
| `get_project_config()` → `json.loads(raw_json)` | `ProjectConfigService.load_from_git(project_id)` |
| POST config editor → `project.save()` | `ProjectConfigService.commit_config(project_id, data, message)` |
| `assets/config/*.json` | не source of truth; legacy в `_legacy/` |

## Вне scope v1

- Monorepo (несколько проектов в одном репо).
- HTTPS + PAT вместо SSH.
- Webhook GitHub для auto-pull (можно позже).
- Pin `config_git_sha` на `PackageSession` (воспроизводимость пакета) — отдельный шаг.
- Project DB (`cow_inference`, `depth_cow`) — после стабилизации Git-конфига.

## Legacy

Текущие проекты (`korovas-2026`, …) не мигрируем автоматически. Конфиги и assets переносятся вручную в `_legacy/`; новые проекты — только по этой спеке.

## Реализация (порядок)

1. Модели `GitCredential`, новый `Project` (миграция, убрать `raw_json`).
2. `git_service.py`: normalize GitHub URL, clone/pull, read/write file, commit/push.
3. Подключить `get_project_config` и UI save.
4. Форма «Новый проект»: URL + ключ + «Проверить доступ».
5. Отдача `collector/media/` из кэша.
6. Spec + README в `django_server/`.
