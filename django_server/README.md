# django_server

Монолит: мобильный API, staff UI и SPA пакетов (client-admin).

## Роли

| Роль | Вход | Где назначают проекты | UI |
|------|------|------------------------|-----|
| **Админ** | `/ui/login/` — логин без `@`, Django **staff** | — | Проекты, **Пользователи**, Пакеты |
| **Клиент** | `/ui/login/` — **email** + Firebase | Пользователи → галочки **Client-admin** | Пакеты |

Отдельных «веб-пользователей» Django нет — только Firebase + колонка Client-admin в таблице пользователей.

## Запуск

```bash
cd django_server
python manage.py migrate
python manage.py createsuperuser

cd frontend/packages && npm ci && npm run build
python manage.py runserver
```

- Вход (админ и клиент): http://127.0.0.1:8000/ui/login/
- Пакеты после входа: http://127.0.0.1:8000/ui/packages/
