# Local run demo — пошаговая инструкция

Локальный прогон: **Git-репо с конфигом** → **Django** → **Postgres + MinIO** → привязка к проекту → проверка.

Подходит как приложение к слайду про хранилища / пайплайн. Подробности: `[test_dev/README.ru.md](../../test_dev/README.ru.md)`, `[specs/git-backed-projects.ru.md](../../specs/git-backed-projects.ru.md)`, `[specs/project-storage-uris.ru.md](../../specs/project-storage-uris.ru.md)`.

В примере ниже `project_id` = `demo-local`. Подставьте свой.

---

## 0. Что должно быть установлено

- Docker Desktop (или Docker Engine + Compose)
- Python 3.11+, git, ssh-keygen в PATH
- Аккаунт GitHub (или другой Git-хостинг с Deploy keys)

Клон репозитория data-collector:

```bash
cd path/to/data-collector
```

---



## 1. Создать Git-репозиторий проекта

Конфиг живёт **не в Django DB**, а в отдельном репо: **1 репозиторий = 1 проект**.

### 1.1. Создать пустой репо на GitHub

Например: `https://github.com/<org>/demo-local.git`  
SSH URL понадобится такой: `git@github.com:<org>/demo-local.git`

### 1.2. Заполнить структуру (локально)

```bash
mkdir demo-local && cd demo-local
git init -b main

mkdir -p collector/media
```

Минимальный `collector/config.json` (поле `id` = `project_id` в Django):

```json
{
  "id": "demo-local",
  "name": "Local Demo",
  "version": "1.0",
  "config": {
    "fields": [
      {
        "field_id": "note",
        "type": "text_input",
        "title": "Заметка",
        "validation": { "required": true }
      }
    ],
    "flow": {
      "steps": [
        {
          "id": "main",
          "screen": "scroll_form",
          "form_title": "Форма",
          "field_ids": ["note"]
        },
        { "id": "check", "screen": "review" }
      ]
    }
  }
}
```

Опционально для webhook после commit пакета — `collector/pipeline.json`:

```json
{
  "version": 1,
  "on_commit": {
    "enabled": true,
    "url": "http://localhost:18080/api/run-with-labels",
    "method": "POST",
    "headers": { "Content-Type": "application/json" },
    "body": { "labels": [["stage", "packages"]] },
    "timeout_seconds": 10
  }
}
```

Закоммитить и запушить:

```bash
git add collector
git commit -m "Initial collector config"
git remote add origin git@github.com:<org>/demo-local.git
git push -u origin main
cd ..
```

---



## 2. Поднять Django (админка + API)

```bash
cd django_server
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
# 0.0.0.0 — чтобы до эмулятора/телефона достучаться с другого интерфейса
python manage.py runserver 0.0.0.0:8000
```

Открыть: [http://127.0.0.1:8000/ui/login/](http://127.0.0.1:8000/ui/login/)  
Войти как **staff** (галочка Admin access, логин без `@`).

Auth для мобилки/API: см. отдельный гайд `[firebase-setup.ru.md](firebase-setup.ru.md)`  
(или быстрый обход без проверки токенов — §8 ниже).

---



## 3. Создать проект в админке и привязать Git

1. Открыть [http://127.0.0.1:8000/ui/projects/](http://127.0.0.1:8000/ui/projects/)
2. **Новый проект**:
  - **project_id** = `demo-local` (как `id` в `config.json`)
  - **Название** = `Local Demo`
  - **Git-репозиторий** = `git@github.com:<org>/demo-local.git`
  - **Ветка** = `main`
  - **SSH-ключ** = «Сгенерировать на сервере»
  - Блок хранилища пока можно **оставить пустым**
3. Нажать **Создать проект**



### 3.1. Deploy key → GitHub

1. На карточке проекта открыть **SSH-ключ** → скопировать **публичный** ключ.
2. GitHub → репозиторий `demo-local` → **Settings → Deploy keys → Add deploy key**:
  - вставить публичный ключ
  - включить **Allow write access**
3. Вернуться в админку → **Проверить Git**
  Ожидание: sync OK, появляется/обновляется `collector/config.json`.

Без write-ключа сервер не сможет сохранять правки конфига из UI.

---



## 4. Поднять локальные хранилища (Postgres + MinIO)

Из **корня** data-collector:

```bash
cp test_dev/.env.example test_dev/.env
docker compose -f test_dev/docker-compose.yml up -d
```


| Сервис           | Адрес                    | Логин / пароль              |
| ---------------- | ------------------------ | --------------------------- |
| PostgreSQL       | `localhost:55432`        | `collector` / `collector`   |
| MinIO API (S3)   | `http://localhost:9000`  | `minioadmin` / `minioadmin` |
| MinIO Console    | `http://localhost:9001`  | `minioadmin` / `minioadmin` |
| Webhook-приёмник | `http://localhost:18080` | —                           |


При старте создаётся бакет `dc-packages`.

Проверка:

```bash
curl http://localhost:18080/health
# {"status":"ok"}
```

Остановка позже:

```bash
docker compose -f test_dev/docker-compose.yml down        # данные сохранить
docker compose -f test_dev/docker-compose.yml down -v     # снести тома
```

---



## 5. Создать БД проекта в Postgres

Отдельная база на проект:

```bash
docker compose -f test_dev/docker-compose.yml exec postgres createdb -U collector proj_demo_local
```

---



## 6. Привязать хранилища к проекту в UI

Карточка проекта `demo-local` → **Хранилище данных** / **Изменить хранилище**.

### Медиа (blobs) — MinIO


| Поле         | Значение                       |
| ------------ | ------------------------------ |
| storage_uri  | `s3://dc-packages/demo-local/` |
| endpoint_url | `http://localhost:9000`        |
| access key   | `minioadmin`                   |
| secret key   | `minioadmin`                   |


Trailing slash у `storage_uri` обязателен.

### БД проекта — Postgres


| Поле         | Значение                                                |
| ------------ | ------------------------------------------------------- |
| database_uri | `postgresql+psycopg2://localhost:55432/proj_demo_local` |
| user         | `collector`                                             |
| password     | `collector`                                             |


(Если UI принимает URI с логином целиком — можно  
`postgresql+psycopg2://collector:collector@localhost:55432/proj_demo_local`.)

### Проверка

Кнопка **Проверить хранилище**.

Ожидание:

- `DB … OK`
- `Storage (s3) … OK`

Если были данные в дефолтном SQLite/папке и нужно перенести:

```bash
cd django_server
python manage.py migrate_project_storage --project-id=demo-local --dry-run
python manage.py migrate_project_storage --project-id=demo-local
```

---



## 7. (Опционально) Webhook после commit пакета

Если в Git лежит `collector/pipeline.json` с `on_commit.url` на `http://localhost:18080/...`:

1. **Проверить Git** ещё раз (подтянуть `pipeline.json`).
2. Снять пакет в мобилке / загрузить → **commit**.
3. Смотреть вызовы:

```bash
curl http://localhost:18080/requests
docker compose -f test_dev/docker-compose.yml logs -f acceptance
```

Ручная имитация:

```bash
curl -X POST http://localhost:18080/api/run-with-labels \
  -H 'Content-Type: application/json' \
  -d '{"labels":[["stage","packages"]]}'
```

---



## 8. Запуск на мобилке



### 8.1. Auth

Полная настройка Firebase (проект, SDK-конфиги, service account, пользователи, чек-лист):  
→ `[firebase-setup.ru.md](firebase-setup.ru.md)`

Краткий обход без проверки токенов на API (если SA ещё нет):

```powershell
$env:FIREBASE_AUTH_ENABLED = "false"
# не задавайте API_BEARER_TOKEN
python manage.py runserver 0.0.0.0:8000
```

```bash
export FIREBASE_AUTH_ENABLED=false
python manage.py runserver 0.0.0.0:8000
```

```bash
curl http://127.0.0.1:8000/v1/projects
# при выключенном auth — 200 без Authorization
```



### 8.2. URL API для клиента


| Куда ставите приложение          | `API_BASE_URL`               |
| -------------------------------- | ---------------------------- |
| Android-эмулятор                 | `http://10.0.2.2:8000`       |
| iOS-симулятор                    | `http://127.0.0.1:8000`      |
| Физический телефон (та же Wi‑Fi) | `http://<IP_вашего_ПК>:8000` |


Узнать IP ПК (Windows): `ipconfig` → IPv4.

### 8.3. Flutter

```bash
flutter pub get
flutter devices
flutter run -d emulator-5554 --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

С Firebase Auth (§8.1 гайд) — войти email/паролем тестового пользователя.  
После смены `google-services.json` / SA — полный restart приложения.

### 8.4. Сценарий в приложении

1. Вкладка **Проект** → выбрать `demo-local` (или проект с выданным `mobile_projects`).
2. Пройти форму → сохранить пакет.
3. Вкладка **Сервер** → загрузить пакет.
4. Админка: [http://127.0.0.1:8000/ui/packages/](http://127.0.0.1:8000/ui/packages/) → пакет виден.
5. (Опц.) webhook: `curl http://localhost:18080/requests`.



### 8.5. APK (опционально)

```bash
flutter build apk --release --dart-define=API_BASE_URL=http://192.168.1.10:8000
```

---



## 9. Чек-лист «демо готово»


| #   | Шаг                                                                                                  | Ок  |
| --- | ---------------------------------------------------------------------------------------------------- | --- |
| 1   | Репо с `collector/config.json` запушен                                                               | ☐   |
| 2   | Django `runserver 0.0.0.0:8000`, staff-логин                                                         | ☐   |
| 3   | Проект создан, deploy key с write, **Проверить Git** OK                                              | ☐   |
| 4   | `docker compose … up -d` (Postgres + MinIO)                                                          | ☐   |
| 5   | БД `proj_demo_local` создана                                                                         | ☐   |
| 6   | В UI прописаны `database_uri` + `s3://…` + креды MinIO                                               | ☐   |
| 7   | **Проверить хранилище** → DB OK, Storage OK                                                          | ☐   |
| 8   | Auth: чек-лист из `[firebase-setup.ru.md](firebase-setup.ru.md)` *или* `FIREBASE_AUTH_ENABLED=false` | ☐   |
| 9   | Flutter с `API_BASE_URL`, пакет ушёл с «Сервер»                                                      | ☐   |
| 10  | Пакет виден в `/ui/packages/`                                                                        | ☐   |
| 11  | (Опц.) webhook виден в `/requests` после commit                                                      | ☐   |


---



## Куда смотреть, если не работает


| Симптом                                    | Что проверить                                                                                                         |
| ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| Git sync error / `couldn't find remote ref main` | На remote нет ветки `main`: запушьте `main` или в карточке проекта укажите реальную ветку (`master` и т.п.). Deploy key + **write access**, SSH URL `git@…` |
| Storage не OK                              | MinIO запущен, бакет `dc-packages`, endpoint `http://localhost:9000`, trailing `/`                                    |
| DB не OK                                   | База `proj_demo_local` создана, порт `55432`, user/password `collector`                                               |
| Webhook тишина                             | Есть ли `collector/pipeline.json`, `enabled: true`, acceptance на `:18080`                                            |
| Мобилка не видит API                       | `runserver 0.0.0.0:8000`, верный `API_BASE_URL` (эмулятор = `10.0.2.2`), firewall, одна Wi‑Fi                         |
| Auth / **401** / нет проектов после логина | `[firebase-setup.ru.md](firebase-setup.ru.md)` → раздел «Если не работает»                                            |
| Sync error / **502**                       | Git одного проекта сломан (`Permission denied (publickey)`). Починить deploy key или не использовать сломанный проект |


---



## Ссылки

- `[local-run-korovas-datapipe.ru.md](local-run-korovas-datapipe.ru.md)` — следующий шаг: пакеты → Datapipe → CVAT (скилл агента)
- `[firebase-setup.ru.md](firebase-setup.ru.md)` — Firebase: клиент, SA, Django, пользователи
- `[test_dev/README.ru.md](../../test_dev/README.ru.md)` — compose и URI
- `[docs/admin-panel/README.ru.md](../admin-panel/README.ru.md)` — создание проекта в UI
- `[docs/mobile-app/README.ru.md](../mobile-app/README.ru.md)` — путь оператора в приложении
- `[specs/git-backed-projects.ru.md](../../specs/git-backed-projects.ru.md)`
- `[specs/project-storage-uris.ru.md](../../specs/project-storage-uris.ru.md)`

