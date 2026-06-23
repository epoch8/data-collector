# data_collector

Клиент для сбора данных (Flutter) + бэкенд Django с веб-админкой.

## Структура репозитория

- **`django_server/`** — API и **веб-админка** (`/ui/`). Свой `manage.py`, миграции, `runserver`. Подробнее: [`django_server/README.md`](django_server/README.md).
- **Корень** — Flutter-приложение (`lib/`, `pubspec.yaml`, `android/`, `ios/`, `web/`). Точка входа: `lib/main.dart`.
- **`test_dev/`** — Docker Compose (PostgreSQL + MinIO) для локальной проверки прод-подобных хранилищ. Подробнее: [`test_dev/README.md`](test_dev/README.md).

## Локальный запуск

### Django (простой режим)

По умолчанию **`local`**: каталог Django — SQLite, пакеты проектов — SQLite + файлы в `project_db/` и `project_media/`.

```bash
cd django_server
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

- Вход в админку: http://127.0.0.1:8000/ui/login/ (staff — галочка «Админ-доступ»)
- Django admin: http://127.0.0.1:8000/admin/

Конфиг проекта хранится в **Git-репозитории** (`collector/config.json`), не в БД — см. [`specs/git-backed-projects.md`](specs/git-backed-projects.md).

### Flutter (Android)

Из корня репозитория:

```bash
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

Для эмулятора `10.0.2.2` — хост-ПК. На физическом устройстве подставьте IP машины с Django.

### Flutter Web (опционально)

```bash
flutter run -d chrome --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

Отличия web/Android: [`docs/web-vs-android.md`](docs/web-vs-android.md).

### test_dev — имитация прод-хранилищ

Если нужно проверить **PostgreSQL + S3** (per-project `database_uri` / `storage_uri`) без облака:

```bash
cp test_dev/.env.example test_dev/.env
docker compose -f test_dev/docker-compose.yml up -d
```

Поднимутся Postgres (`localhost:55432`) и MinIO (`http://localhost:9000`). URI задаются в UI проекта («Изменить хранилище»); полная инструкция — в [`test_dev/README.md`](test_dev/README.md) и [`specs/project-storage-uris.md`](specs/project-storage-uris.md).

## Продакшен

**Каталог платформы** (Django): PostgreSQL + Google Cloud Storage. Задайте `POSTGRES_*` (или явно `DJANGO_ENV=production`); зависимости — `requirements.txt`.

**Данные проектов** (пакеты, медиа, pipeline) настраиваются **отдельно на каждый проект** через `database_uri` и `storage_uri` в UI. Если поля пустые — SQLite + локальная папка на сервере (часто смонтированный диск). В проде типично Postgres + `gs://` или `s3://`.

Развёрнутый инстанс: `https://data-collector-app.korovas.ml.epoch8.dev` — админка `/ui/`, API с того же хоста. В `API_BASE_URL` не добавляйте завершающий `/`.

Полезные переменные: `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, Firebase (`FIREBASE_SERVICE_ACCOUNT_PATH` или JSON в окружении).

## Сборка и авторизация

- **Firebase** (Email/Password): `lib/firebase_options.dart`, для Android — `android/app/google-services.json`. Обновить конфиг:

```bash
dart run flutterfire_cli:flutterfire configure
```

(подробности в комментариях в `firebase_options.dart`).

- **Django API:** при запуске/сборке передайте базовый URL без завершающего `/`.
- Если на Django **не** включена проверка Firebase-токена, опционально:

```bash
flutter run --dart-define=API_BASE_URL=... --dart-define=API_BEARER_TOKEN=...
```

См. `lib/core/api/api_environment.dart`.

## Основные схемы и спеки (`specs/`)

| Файл | О чём |
|------|--------|
| [`specs/01-overview.md`](specs/01-overview.md) | Обзор продукта и текущего scope |
| [`specs/02-data-models-schema.md`](specs/02-data-models-schema.md) | JSON-конфиг, Django/SQLAlchemy/Drift модели |
| [`specs/03-user-journey-screens.md`](specs/03-user-journey-screens.md) | Экраны Flutter и `/ui/` |
| [`specs/04-tech-stack-architecture.md`](specs/04-tech-stack-architecture.md) | Стек и структура репозитория |
| [`specs/06-upload-lifecycle.md`](specs/06-upload-lifecycle.md) | Жизненный цикл upload на устройстве |
| [`specs/07-package-payload-structure.md`](specs/07-package-payload-structure.md) | Структура пакета и camera metadata |
| [`specs/main-scheme/01-abstract-config-entities.drawio`](specs/main-scheme/01-abstract-config-entities.drawio) | Абстрактный конфиг: сущности и как из них **собираются проекты**. |
| [`specs/main-scheme/02-client-server-config-and-package.drawio`](specs/main-scheme/02-client-server-config-and-package.drawio) + [`specs/09-server-project-config-delivery.md`](specs/09-server-project-config-delivery.md) | Как конфиг **создаётся и доставляется** клиенту; как клиент **заполняет** данные по конфигу и что **ожидает сервер**. |
| [`specs/main-scheme/03_server_api.drawio`](specs/main-scheme/03_server_api.drawio) + [`specs/08-server-api-package-upload.md`](specs/08-server-api-package-upload.md) | **Загрузка пакета** на сервер (API и поток). |
| [`specs/main-scheme/04-auth-firebase-django.drawio`](specs/main-scheme/04-auth-firebase-django.drawio) | **Аутентификация:** Firebase на клиенте и связка с Django. |
| [`specs/main-scheme/05-admin-roles-access.drawio`](specs/main-scheme/05-admin-roles-access.drawio) | **Роли админки:** staff (E8), client-admin, сотрудник. |
| [`specs/git-backed-projects.md`](specs/git-backed-projects.md) | **Git-репозиторий** проекта: deploy key, `config.json`, синхронизация. |
| [`specs/project-storage-uris.md`](specs/project-storage-uris.md) | **Хранилища проекта:** `database_uri`, `storage_uri`, Postgres/S3/GCS. |
| [`specs/collector-vis-config.md`](specs/collector-vis-config.md) | **`collector/viz.json`** — визуализация pipeline в админке. |
| [`specs/config/09-project-json-builder-guide.md`](specs/config/09-project-json-builder-guide.md) | Гайд по сборке JSON проекта. |

Backlog: [`specs/todo`](specs/todo). Диаграммы `.drawio` — при ревизии сверять с `specs/main-scheme/todo.txt`.
