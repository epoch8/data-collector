# data_collector

Клиент для сбора данных (Flutter) + бэкенд Django с админкой.

## Структура репозитория

- **`django_server/`**: Django-проект и **админка**. Запускается отдельно от приложения (свой `manage.py`, миграции, `runserver`). Клиент ходит на API по URL, который задаёте при сборке Flutter.
- **Корень репозитория**: **Flutter-приложение** (`lib/`, `pubspec.yaml`, `android/`, `ios/` и т.д.). Точка входа: `lib/main.dart`.

## Как запустить

**Django** (из каталога `django_server/`): локально по умолчанию SQLite и файлы в `media/` (режим `local`). Установите зависимости, выполните миграции и поднимите сервер.

```bash
cd django_server
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Продакшен (PostgreSQL + GCS): в окружении задайте `POSTGRES_*` (или явно `DJANGO_ENV=production`); зависимости те же — `requirements.txt`.

Админка: `python manage.py createsuperuser`, в браузере откройте `http://127.0.0.1:8000/admin/`.

Развёрнутый сервер (тот же Django, что и API): базовый URL `https://data-collector-app.korovas.ml.epoch8.dev` — админка: `/admin/`, API как в спеках — с этого же хоста (без завершающего `/` в `API_BASE_URL`).

**Flutter** (из корня репозитория):

```bash
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

Для Android-эмулятора `10.0.2.2` это хост-ПК. На физическом устройстве подставьте IP машины, где запущен Django.

## Сборка и авторизация

- **Firebase** (Email/Password и т.п.): `lib/firebase_options.dart`, для Android ещё `android/app/google-services.json`. Обновить конфиг:

```bash
dart run flutterfire_cli:flutterfire configure
```

(подробности в комментариях в `firebase_options.dart`).

- **Django API:** при запуске/сборке передайте базовый URL без завершающего `/` (пример в блоке выше).
- Если на Django **не** включена проверка Firebase-токена, опционально:

```bash
flutter run --dart-define=API_BASE_URL=... --dart-define=API_BEARER_TOKEN=...
```

См. `lib/core/api/api_environment.dart`.

## Основные схемы и спеки (`specs/`)

| Файл | О чём |
|------|--------|
| [`specs/main-scheme/01-abstract-config-entities.drawio`](specs/main-scheme/01-abstract-config-entities.drawio) | Абстрактный конфиг: сущности и как из них **собираются проекты**. |
| [`specs/main-scheme/02-client-server-config-and-package.drawio`](specs/main-scheme/02-client-server-config-and-package.drawio) + [`specs/09-server-project-config-delivery.md`](specs/09-server-project-config-delivery.md) | Как конфиг **создаётся и доставляется** клиенту; как клиент **заполняет** данные по конфигу и что **ожидает сервер**. |
| [`specs/main-scheme/03_server_api.drawio`](specs/main-scheme/03_server_api.drawio) + [`specs/08-server-api-package-upload.md`](specs/08-server-api-package-upload.md) | **Загрузка пакета** на сервер (API и поток). |
| [`specs/main-scheme/04-auth-firebase-django.drawio`](specs/main-scheme/04-auth-firebase-django.drawio) | **Аутентификация:** Firebase на клиенте и связка с Django. |
| [`specs/main-scheme/05-admin-roles-access.drawio`](specs/main-scheme/05-admin-roles-access.drawio) | **Роли админки:** суперадмин (E8), админ проекта (хозяйства), сотрудник; границы доступа и иерархия назначения прав. |

Остальная документация по продукту и стеку лежит в `specs/*.md` (обзор, MVP, структура пакета и т.д.).
