# Firebase для Data Collector

Нужен, чтобы мобилка и админка логинились, а Django проверял токен на `/v1/*`.

**Одно правило:** везде один и тот же Firebase-проект (клиент, Web-конфиг Django, service account). Иначе логин ок, а API → **401**.

Связано: [`local-run-demo.ru.md`](local-run-demo.ru.md), [`../admin-panel/README.ru.md`](../admin-panel/README.ru.md).

---

## Быстрый путь: попросить агента

В Cursor откройте этот репозиторий и напишите:

```text
Настрой Firebase для Data Collector по скиллу firebase-data-collector.
Проект: <ваш-project-id> (или создай новый).
Package Android: com.example.data_collector
```

Агент сам пройдёт шаги ниже (MCP + правки файлов). Вам останется:

1. Войти в Google, если попросит (`firebase_login`).
2. Скачать **service account** JSON в Console (ключ нельзя выдать через MCP) и положить в `django_server/firebase-service-account.json`.
3. Создать тестового пользователя в Authentication → Users (или попросить агента подсказать куда кликать).

Скилл лежит в `.cursor/skills/firebase-data-collector/`.  
Firebase MCP уже есть в Cursor (плагин Firebase) — отдельно ставить не обязательно.

---

## Руками: 7 шагов

### 1. Проект в Firebase

1. Откройте [console.firebase.google.com](https://console.firebase.google.com/).
2. Создайте проект или выберите свой → скопируйте **Project ID**.

### 2. Приложения

В Project settings → Your apps добавьте (если ещё нет):

| Платформа | Что указать |
| --- | --- |
| Android | package = `com.example.data_collector` (см. `android/app/build.gradle.kts`) |
| Web | любое имя — нужно для логина в админке `/ui/` |
| iOS | только если реально собираете iOS |

Скачайте:

- Android → `google-services.json` → положите в `android/app/google-services.json`
- Web → скопируйте поля config (apiKey, appId, …)

### 3. Клиент Flutter

Обновите `lib/firebase_options.dart`: блоки **android** и **web** должны указывать на **ваш** Project ID и правильные appId (`:android:…` и `:web:…` — разные!).

Альтернатива: `dart run flutterfire_cli:flutterfire configure` и выбрать тот же проект.

После смены конфигов — **полный restart** приложения (не hot reload).

### 4. Включить Email/Password

1. Build → Authentication → Sign-in method → **Email/Password** → Enable.
2. Users → Add user → email и пароль для теста.
3. Settings → Authorized domains → должны быть `localhost` и `127.0.0.1`.

### 5. Ключ для Django (service account)

Без этого файла Django не проверяет токены → **401**.

1. Project settings → Service accounts → **Generate new private key**.
2. Сохраните как:

```text
django_server/firebase-service-account.json
```

Файл в `.gitignore` — **не коммитить**. В JSON поле `project_id` = ваш Project ID.

Другой путь: `$env:FIREBASE_SERVICE_ACCOUNT_PATH = "C:\path\to\key.json"` (PowerShell).

### 6. Web-конфиг Django + запуск

В `django_server/collector_site/settings.py` (или через env) те же Web-поля, что в `firebase_options.dart`:

| Env | Поле |
| --- | --- |
| `FIREBASE_WEB_API_KEY` | apiKey |
| `FIREBASE_WEB_AUTH_DOMAIN` | authDomain |
| `FIREBASE_WEB_PROJECT_ID` | projectId |
| `FIREBASE_WEB_STORAGE_BUCKET` | storageBucket |
| `FIREBASE_WEB_MESSAGING_SENDER_ID` | messagingSenderId |
| `FIREBASE_WEB_APP_ID` | appId |

Запуск (не ставьте `FIREBASE_AUTH_ENABLED=false`):

```powershell
cd django_server
python manage.py runserver 0.0.0.0:8000
```

Проверка: `GET /v1/projects` без заголовка → **401**; с Bearer (Firebase ID token) → **200**.

### 7. Права в админке + мобилка

1. `http://127.0.0.1:8000/ui/` → войти staff.
2. **Пользователи** → **Синхронизировать с Firebase**.
3. У тестового пользователя включить нужные **mobile_projects**.
4. Перелогин в приложении.

Мобилка:

```bash
flutter run -d <device> --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

| Устройство | API_BASE_URL |
| --- | --- |
| Android-эмулятор | `http://10.0.2.2:8000` |
| iOS-симулятор | `http://127.0.0.1:8000` |
| Телефон | `http://<IP_ПК>:8000` |

Войти тем же email/паролем, что в Firebase Users.

---

## Обход без Firebase (только быстрое демо API)

```powershell
$env:FIREBASE_AUTH_ENABLED = "false"
python manage.py runserver 0.0.0.0:8000
```

Тогда `/v1/*` не требует JWT. Для нормального логина вернитесь к шагам 5–7.

---

## Чек-лист

| # | Готово? |
| --- | --- |
| 1 | Один Project ID везде |
| 2 | `google-services.json` + `firebase_options` (android/web) |
| 3 | Email/Password + тестовый пользователь |
| 4 | `django_server/firebase-service-account.json` от того же проекта |
| 5 | `FIREBASE_WEB_*` = Web из `firebase_options` |
| 6 | Sync пользователей + `mobile_projects` |
| 7 | Flutter с `API_BASE_URL`, логин, проекты видны |

---

## Если не работает

| Симптом | Что сделать |
| --- | --- |
| **401** на `/v1/*` | Один project_id у клиента и SA; перезапуск Django; полный restart Flutter + новый логин |
| Firebase не стартует | `google-services.json`, package name, `firebase_options` |
| Логин ок, проектов нет | Админка → `mobile_projects`; перелогин |
| Админка не логинится | `FIREBASE_WEB_*`, Authorized domains |
| iOS/macOS «чужой» проект | В репо часто android/web = один проект, ios/macos = другой. Для демо достаточно android |

---

## Агенту: что делает MCP, что нет

| Можно через Firebase MCP | Только руками / файлы |
| --- | --- |
| Логин, список/создание проектов | Скачать private key (service account) |
| Создать Android/Web app | Положить SA JSON на диск |
| Выдать SDK-конфиг (`firebase_get_sdk_config`) | Создать пользователя в Auth (или Console) |
| Включить Email/Password (`firebase_update_environment`) | Выдать `mobile_projects` в Django-админке |

Подробный сценарий для агента: `.cursor/skills/firebase-data-collector/SKILL.md`.
