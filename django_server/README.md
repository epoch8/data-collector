# django_server

Монолит: мобильный API и веб-админка на **Django-шаблонах** (Bootstrap + `admin.css`).

## Роли

| Роль | Вход | Где назначают проекты | UI |
|------|------|------------------------|-----|
| **Админ** | `/ui/login/` — логин без `@`, Django **staff** | — | Проекты, Пользователи, Пакеты |
| **Клиент** | `/ui/login/` — **email** + Firebase | Пользователи → галочки **Client-admin** | Пакеты |

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
- Пакеты: http://127.0.0.1:8000/ui/packages/

Пакеты (бывший client-admin) полностью на **Django-шаблонах + Bootstrap**, сборка фронта не требуется:

- **Список** — `ui/packages/list.html`: выбор проекта, чипы статусов, поиск по полю (text/datetime) или ID/email, динамическая колонка, копирование `package_id`. Фильтрация серверная (GET-параметры).
- **Workspace** — `ui/packages/workspace.html`: сайдбар-переключатель пакетов, вкладки **Данные / Медиа / Визуализация / История изменений**, отслеживание изменений и сохранение через обычный POST-форму на Django-вью (`package_manifest_save`, переиспользует `package_admin_service.patch_manifest` + дописывает `field_changelog.json`).
- **Визуализация** — `static/ui/packages_viz.js`: SVG-оверлей keypoints/bbox/segments, карта глубины из `.npy` (палитра, режимы «рядом/наложение», проба под курсором), фильмстрип, ссылка в CVAT, экспорт PNG/JSON. Данные — из `datapipe_test/*` через `/ui/.../viz-data/` и `/ui/packages/depth/<file>`.

Серверная логика — `api/packages_ui.py` и `api/views_ui.py`.

## Статика

- `api/static/ui/admin.css` — общая тема
- `api/static/ui/packages.css`, `packages_viz.css` — стили пакетов
- `api/static/ui/packages_list.js`, `packages_workspace.js`, `packages_viz.js` — логика пакетов
- `api/static/ui/project_builder.js` — визуальный редактор конфига
- `api/static/ui/firebase_login.js` — вход клиента на странице логина
