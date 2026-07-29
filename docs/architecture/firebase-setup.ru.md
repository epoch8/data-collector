# Firebase: настройка для Data Collector

Пошаговый гайд: один Firebase-проект → клиент (Flutter) → Django (проверка ID token) → пользователи в админке.

Подставьте **свои** значения вместо плейсхолдеров в `<угловых скобках>`.  
Места под скриншоты отмечены блоками `> 📷 …`.

Связанные документы: [`local-run-demo.ru.md`](local-run-demo.ru.md), [`../admin-panel/README.ru.md`](../admin-panel/README.ru.md).

---

## Зачем это нужно

| Компонент | Роль Firebase |
| --- | --- |
| Мобилка / Web | Email/Password → ID token |
| Django `/v1/*` | Проверяет token через Admin SDK (service account) |
| Админка `/ui/` | Web SDK (логин staff) + список пользователей из Firebase |

**Правило:** `project_id` у клиента, у Web-конфига Django и у service account JSON — **один и тот же** Firebase-проект. Иначе логин проходит, а API отвечает **401**.

---

## Плейсхолдеры

Заполните один раз и используйте ниже:

| Плейсхолдер | Откуда взять | Пример формата |
| --- | --- | --- |
| `<FIREBASE_PROJECT_ID>` | Firebase Console → Project settings → Project ID | `my-collector-dev` |
| `<ANDROID_PACKAGE>` | `applicationId` в `android/app/build.gradle(.kts)` | `com.example.data_collector` |
| `<IOS_BUNDLE_ID>` | Bundle ID в Xcode / `ios/…` | `com.example.dataCollector` |
| `<ANDROID_APP_ID>` | Console → Project settings → Your apps → Android | `1:123…:android:abc…` |
| `<WEB_APP_ID>` | Your apps → Web | `1:123…:web:def…` |
| `<IOS_APP_ID>` | Your apps → iOS (если есть) | `1:123…:ios:…` |
| `<API_KEY_ANDROID>` | `google-services.json` → `api_key.current_key` | `AIza…` |
| `<API_KEY_WEB>` | Web SDK config → `apiKey` | `AIza…` |
| `<MESSAGING_SENDER_ID>` | Project number / `messagingSenderId` | `123456789012` |
| `<STORAGE_BUCKET>` | обычно `<FIREBASE_PROJECT_ID>.firebasestorage.app` | `…firebasestorage.app` |
| `<AUTH_DOMAIN>` | обычно `<FIREBASE_PROJECT_ID>.firebaseapp.com` | `….firebaseapp.com` |
| `<DEMO_USER_EMAIL>` / `<DEMO_USER_PASSWORD>` | создаёте в Authentication → Users | — |
| `<PATH_TO_SA_JSON>` | скачанный private key | см. §4 |

---

## 1. Firebase-проект и приложения

1. Откройте [Firebase Console](https://console.firebase.google.com/).
2. Создайте проект или выберите существующий → запомните `<FIREBASE_PROJECT_ID>`.

> 📷 Project overview / Project settings — Project ID и Project number

3. Зарегистрируйте приложения (если ещё нет):

| Платформа | Что указать |
| --- | --- |
| **Android** | Package name = `<ANDROID_PACKAGE>` |
| **Web** | любое display name (нужен для админки `/ui/login/`) |
| **iOS** (опционально) | Bundle ID = `<IOS_BUNDLE_ID>` |

> 📷 Add app → Android / Web — форма регистрации

4. Скачайте или выгрузите SDK-конфиги:

```bash
npx -y firebase-tools@latest login
npx -y firebase-tools@latest use <FIREBASE_PROJECT_ID>

# Android → файл в репозитории
npx -y firebase-tools@latest apps:sdkconfig ANDROID <ANDROID_APP_ID> \
  > android/app/google-services.json

# Web → скопировать поля в firebase_options + Django (ниже)
npx -y firebase-tools@latest apps:sdkconfig WEB <WEB_APP_ID>

# iOS (если нужно)
npx -y firebase-tools@latest apps:sdkconfig IOS <IOS_APP_ID> \
  > ios/Runner/GoogleService-Info.plist
```

> 📷 Project settings → Your apps — список App ID

В корне репозитория можно зафиксировать активный проект:

```json
// .firebaserc
{
  "projects": {
    "default": "<FIREBASE_PROJECT_ID>"
  }
}
```

---

## 2. Клиент Flutter

### 2.1. Android

Файл: `android/app/google-services.json`  
Проверьте:

- `project_info.project_id` = `<FIREBASE_PROJECT_ID>`
- `client[].android_client_info.package_name` = `<ANDROID_PACKAGE>`

> 📷 (опц.) фрагмент `google-services.json` с `project_id` и `package_name`

### 2.2. `lib/firebase_options.dart`

Платформы **android** и **web** должны указывать на тот же `<FIREBASE_PROJECT_ID>`:

```dart
static const FirebaseOptions android = FirebaseOptions(
  apiKey: '<API_KEY_ANDROID>',
  appId: '<ANDROID_APP_ID>',
  messagingSenderId: '<MESSAGING_SENDER_ID>',
  projectId: '<FIREBASE_PROJECT_ID>',
  authDomain: '<AUTH_DOMAIN>',
  storageBucket: '<STORAGE_BUCKET>',
);

static const FirebaseOptions web = FirebaseOptions(
  apiKey: '<API_KEY_WEB>',
  appId: '<WEB_APP_ID>',
  messagingSenderId: '<MESSAGING_SENDER_ID>',
  projectId: '<FIREBASE_PROJECT_ID>',
  authDomain: '<AUTH_DOMAIN>',
  storageBucket: '<STORAGE_BUCKET>',
);
```

iOS/macOS — по необходимости, после регистрации iOS-приложения.

Альтернатива: `dart run flutterfire_cli:flutterfire configure` и выбор того же проекта.

После смены конфигов — **полный restart** приложения (не hot reload).

---

## 3. Authentication в Console

1. **Build → Authentication → Sign-in method** → включить **Email/Password**.

> 📷 Sign-in method — Email/Password Enabled

2. **Users → Add user** → `<DEMO_USER_EMAIL>` / `<DEMO_USER_PASSWORD>`  
   Этот же логин используете в мобилке.

> 📷 Users — созданный пользователь

3. **Authentication → Settings → Authorized domains**  
   Для локальной админки должны быть `localhost` и `127.0.0.1` (и ваш прод-домен, если есть).

> 📷 Authorized domains

---

## 4. Service account для Django

Без ключа Admin SDK Django не проверяет ID token → **401** на `/v1/*`.

1. ⚙️ **Project settings → Service accounts**.
2. **Generate new private key** → скачать JSON.

> 📷 Service accounts — Generate new private key

3. Положить файл (путь по умолчанию в коде; файл в `.gitignore` — **не коммитить**):

```text
django_server/firebase-service-account.json
```

или указать путь:

```powershell
# PowerShell
$env:FIREBASE_SERVICE_ACCOUNT_PATH = "<PATH_TO_SA_JSON>"
```

```bash
# macOS / Linux
export FIREBASE_SERVICE_ACCOUNT_PATH="<PATH_TO_SA_JSON>"
```

В JSON поле `"project_id"` должно быть **`<FIREBASE_PROJECT_ID>`** — тот же, что у клиента.

Другие варианты: `FIREBASE_SERVICE_ACCOUNT_JSON` (весь JSON строкой) или `GOOGLE_APPLICATION_CREDENTIALS`.

---

## 5. Django: Web SDK и запуск с auth

### 5.1. `FIREBASE_WEB_CONFIG`

В `django_server/collector_site/settings.py` (или через env) — те же значения, что Web в `firebase_options.dart`:

| Ключ | Значение |
| --- | --- |
| `apiKey` | `<API_KEY_WEB>` |
| `authDomain` | `<AUTH_DOMAIN>` |
| `projectId` | `<FIREBASE_PROJECT_ID>` |
| `storageBucket` | `<STORAGE_BUCKET>` |
| `messagingSenderId` | `<MESSAGING_SENDER_ID>` |
| `appId` | `<WEB_APP_ID>` |

Переменные окружения (если не хотите править defaults в коде):  
`FIREBASE_WEB_API_KEY`, `FIREBASE_WEB_AUTH_DOMAIN`, `FIREBASE_WEB_PROJECT_ID`, `FIREBASE_WEB_STORAGE_BUCKET`, `FIREBASE_WEB_MESSAGING_SENDER_ID`, `FIREBASE_WEB_APP_ID`.

### 5.2. Запуск с проверкой токенов

При наличии `firebase-service-account.json` auth обычно включается сам.  
Не задавайте `FIREBASE_AUTH_ENABLED=false` и не ставьте `API_BEARER_TOKEN` для этого сценария.

```powershell
Remove-Item Env:FIREBASE_AUTH_ENABLED -ErrorAction SilentlyContinue
Remove-Item Env:API_BEARER_TOKEN -ErrorAction SilentlyContinue
cd django_server
python manage.py runserver 0.0.0.0:8000
```

```bash
unset FIREBASE_AUTH_ENABLED
unset API_BEARER_TOKEN
cd django_server
python manage.py runserver 0.0.0.0:8000
```

Ожидание: `GET /v1/projects` **без** `Authorization` → **401**; с валидным Bearer (ID token) → **200**.

Переменные читаются при старте процесса — после смены SA/флагов нужен перезапуск `runserver`.

---

## 6. Пользователи и доступ к проектам

1. Откройте админку: `http://127.0.0.1:8000/ui/` (staff).
2. Раздел **Пользователи** → **Синхронизировать с Firebase**.
3. У нужного пользователя выдайте **mobile_projects** (проекты, которые видит мобилка).
4. После смены прав — **перелогин** в приложении.

> 📷 Пользователи → Sync → галочки mobile_projects

Подробнее про роли: [`../admin-panel/README.ru.md`](../admin-panel/README.ru.md).

---

## 7. Запуск мобилки

| Устройство | `API_BASE_URL` |
| --- | --- |
| Android-эмулятор | `http://10.0.2.2:<PORT>` |
| iOS-симулятор | `http://127.0.0.1:<PORT>` |
| Физический телефон | `http://<IP_ПК>:<PORT>` |

```bash
flutter pub get
flutter run -d <device_id> \
  --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

Войти: `<DEMO_USER_EMAIL>` / `<DEMO_USER_PASSWORD>`.

> 📷 Экран логина приложения

---

## 8. Обход без Firebase Auth (только для быстрого демо)

Если service account ещё нет и нужно просто проверить API:

```powershell
$env:FIREBASE_AUTH_ENABLED = "false"
python manage.py runserver 0.0.0.0:8000
```

```bash
export FIREBASE_AUTH_ENABLED=false
python manage.py runserver 0.0.0.0:8000
```

Тогда `/v1/*` не требует Firebase JWT. Для нормальной связки с логином вернитесь к §4–§5.

Полный локальный пайплайн (Git, Postgres, MinIO): [`local-run-demo.ru.md`](local-run-demo.ru.md).

---

## Чек-лист

| # | Шаг | Ок |
| --- | --- | --- |
| 1 | Один `<FIREBASE_PROJECT_ID>` везде | ☐ |
| 2 | Android/Web apps зарегистрированы, SDK-конфиги на месте | ☐ |
| 3 | Email/Password включён, демо-пользователь создан | ☐ |
| 4 | `firebase-service-account.json` от того же project_id | ☐ |
| 5 | `FIREBASE_WEB_CONFIG` = Web из `firebase_options` | ☐ |
| 6 | `runserver` без `FIREBASE_AUTH_ENABLED=false` | ☐ |
| 7 | Sync пользователей + `mobile_projects` | ☐ |
| 8 | Flutter с `API_BASE_URL`, логин, каталог проектов виден | ☐ |

---

## Если не работает

| Симптом | Что проверить |
| --- | --- |
| **401** на `/v1/*` | SA и клиент — один project_id; перезапуск Django; полный restart Flutter + повторный логин |
| Firebase не инициализируется | `google-services.json` / `firebase_options` / package name |
| Логин ок, проектов нет | Админка → **mobile_projects**; Git sync проекта на сервере |
| Админка не логинится (Web) | `FIREBASE_WEB_CONFIG`, Authorized domains (`localhost`) |
| Токен «чужого» проекта | Не смешивать два Firebase-проекта в клиенте и SA |

---

## Куда класть скриншоты

Рекомендуемая папка: `docs/architecture/img/firebase/`  
Вставляйте под блоками `> 📷 …`, например:

```markdown
![Project ID](img/firebase/01-project-settings.png)
```
