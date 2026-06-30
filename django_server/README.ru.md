> **Language / Язык:** [English](README.md) · **Русский**

# django_server

Монолит: мобильный API и веб-админка на **Django-шаблонах** (Bootstrap + `admin.css`).

## Роли

| Роль | Вход | Где назначают проекты | UI |
|------|------|------------------------|-----|
| **Админ** | `/ui/login/` — галочка **Админ-доступ**, логин без `@`, Django **staff** | — | Проекты, Пользователи, Пакеты |
| **Клиент** | `/ui/login/` — без галочки, **email** + Firebase | Пользователи → галочки **Client-admin** | Пакеты |

Отдельных «веб-пользователей» Django нет — только Firebase + колонка Client-admin в таблице пользователей.

## Запуск

```bash
cd django_server
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

- Вход: http://127.0.0.1:8000/ui/login/
- Проекты (staff): http://127.0.0.1:8000/ui/projects/

### Проекты и Git

Конфиг проекта **не хранится в БД** — только в репозитории GitHub: `collector/config.json` (см. [`specs/git-backed-projects.ru.md`](../specs/git-backed-projects.ru.md)).

- При создании проекта: URL репо + SSH deploy key (генерация на сервере или вставка приватного ключа).
- Публичный ключ → GitHub → Deploy keys (**Allow write access**).
- Кнопка «Проверить Git» на карточке проекта — `git pull` и при необходимости seed `config.json`.
- Сохранение в JSON-редакторе = `git commit` + `git push`.
- Кэш клонов: `project_git_cache/` (или `PROJECT_GIT_CACHE_ROOT`).
- Нужны **git** и **ssh-keygen** в PATH; `pip install -r requirements.txt` (пакет `cryptography`).

Миграция `0006_git_backed_projects` удаляет старые записи `Project` из БД (чистый старт).
- Пакеты: http://127.0.0.1:8000/ui/packages/

Пакеты полностью на **Django-шаблонах + Bootstrap**, сборка фронта не требуется:

- **Список** — `ui/packages/list.html`: выбор проекта, чипы статусов, поиск по полю (text/datetime) или ID/email, динамическая колонка, копирование `package_id`. Фильтрация серверная (GET-параметры).
- **Workspace** — `ui/packages/workspace.html`: сайдбар-переключатель пакетов, вкладки **Данные / Медиа / Визуализация / История изменений**, отслеживание изменений и сохранение через POST (`package_manifest_save` + changelog в project SQLite).
- **Визуализация** — конфиг в Git: `collector/viz.json` (слои → `table` в project SQLite + `plugin`). Плагины: `keypoint_korovas`, `depth_map`, `cvat_link`, `yolo_detection`. Импорт: `import_yolo_labels`, `import_depth_map`, `import_cvat_link`. UI: `packages_viz.js` → `/viz-data/`. Пример конфига: `examples/collector/viz.json`; установка в git-кэш: `install_vis_config_example`. Спека: [`specs/collector-vis-config.ru.md`](../specs/collector-vis-config.ru.md).

### Хранение пакетов (per project)

Метаданные и pipeline — **per-project DB** (`database_uri`, default SQLite в `project_db/{project_id}/`). Blobs — **fsspec** (`storage_uri`, default `project_media/{project_id}/`). См. [`specs/project-storage-uris.ru.md`](../specs/project-storage-uris.ru.md).

- Таблицы: `package_session`, `uploaded_blob`, `package_field_change` + pipeline (yolo, depth, …).
- Путь blob: `packages/{package_id}/blobs/...` относительно `storage_uri`.
- Legacy `media_bucket` deprecated → `storage_uri` (`gs://…`).
- Миграция с Django ORM: `migrate_packages_to_project_storage`, `recover_legacy_packages`.

Серверная логика — `api/packages_ui.py` и `api/views_ui.py`.

## Статика

- `api/static/ui/admin.css` — общая тема
- `api/static/ui/packages.css`, `packages_viz.css` — стили пакетов
- `api/static/ui/packages_list.js`, `packages_workspace.js`, `packages_viz.js` — логика пакетов
- `api/static/ui/project_builder.js` — визуальный редактор конфига
- `api/static/ui/login.js` — Firebase-вход на странице логина (без галочки «Админ-доступ»)
