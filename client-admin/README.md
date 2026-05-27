# client-admin

Веб-админка для просмотра и правки **принятых пакетов** data-collector.

**Платформа** (`django_server`) — приём пакетов, хранение manifest и blobs.  
**client-admin** — UI ядра: поля формы (`data`) по `config.fields`, галерея медиа (`blobs/*`).

## v1 — что реализовано

- Вкладки **Данные** и **Медиа** (без Pipelines, JSON, плагинов)
- **Данные:** только `text_input` / `datetime` по шагам `config.flow` (заголовок = `form_title`), без instruction и без фото
- **Медиа:** все `blobs` пакета, бейдж «в форме» для файлов из `data`
- Widget Resolver, lightbox, навигация по полям, Ctrl+S, toast
- Правка `manifest.data` для пакетов в статусе `completed`
- API `/admin-api/v1/*` в django_server (dev без auth)
- Mock-режим для offline UI

## Запуск

**1. Django (платформа)**

```bash
cd django_server
python manage.py migrate
python manage.py load_projects_from_assets   # если проекты ещё не в БД
python manage.py runserver
```

**2. client-admin**

```bash
cd client-admin
npm install
npm run dev
```

Открыть http://localhost:5173 — Vite проксирует `/admin-api` на `http://127.0.0.1:8000`.

**Mock без django:**

```bash
VITE_USE_MOCK=true npm run dev
```

## Документы

| Файл | О чём |
|------|--------|
| [00-overview.md](docs/00-overview.md) | Зачем и общая схема |
| [01-manifest-and-pipelines.md](docs/01-manifest-and-pipelines.md) | JSON пакета |
| [02-package-workspace.md](docs/02-package-workspace.md) | Экран пакета |
| [03-field-widgets.md](docs/03-field-widgets.md) | Виджеты |
| [05-api-contract.md](docs/05-api-contract.md) | HTTP API |

## API (dev)

| Метод | Путь |
|-------|------|
| GET | `/admin-api/v1/projects` |
| GET | `/admin-api/v1/projects/{id}/packages?phase=` |
| GET | `/admin-api/v1/projects/{id}/packages/{pkg}/workspace` |
| PATCH | `/admin-api/v1/projects/{id}/packages/{pkg}/manifest` |
| GET | `/admin-api/v1/projects/{id}/packages/{pkg}/blobs/{pk}/preview` |
