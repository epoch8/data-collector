# client-admin (перенесён)

Исходники и сборка SPA пакетов перенесены в монолит:

**[`django_server/frontend/packages/`](../django_server/frontend/packages/)**

- Сборка: `cd django_server/frontend/packages && npm ci && npm run build` → `django_server/api/static/packages/`
- UI: [`/ui/packages/`](../django_server/api/urls_ui.py) внутри Django
- API: [`/ui/api/v1/`](../django_server/api/urls_ui_api.py) (Django session + CSRF)

Корневая папка `client-admin/` сохранена для совместимости ссылок в документации; разработка ведётся в `django_server/frontend/packages`.
