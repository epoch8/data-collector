# Развёртывание Flutter Web (коллектор)


## Что получается на выходе

После `flutter build web` каталог **`build/web/`** — обычный **статический сайт** (HTML, JS, WASM, ассеты). Его раздаёт nginx, CDN, объектное хранилище с публичным URL или любой другой static host. Отдельного «Flutter-сервера» для продакшена не нужно.

## Сборка

Из **корня репозитория** (рядом с `pubspec.yaml`):

```bash
flutter pub get
flutter build web --release --dart-define=API_BASE_URL=https://ваш-api.example.com
```

- **`API_BASE_URL`** — базовый URL Django админки


Подробнее: `lib/core/api/api_environment.dart`, общий контекст — `README.md`.

## Раздача файлов

1. Скопируйте содержимое **`build/web/`** на хост (или задеплойте артефакт пайплайна).
2. Настройте **SPA-поведение**: запросы к несуществующим путям (кроме реальных файлов) отдавайте **`index.html`**, иначе прямой заход по URL или обновление страницы дадут 404.
3. Предпочтительно **HTTPS** (Firebase и современные браузеры).

## Django и CORS

Браузер шлёт запросы с **origin** вашего web-приложения. В **`django_server/collector_site/settings.py`** CORS настроен через `django-cors-headers`.

- В **продакшене** (`DEBUG=False`) в regex по умолчанию попадают только `localhost` / `127.0.0.1` с любым портом. **Origin продакшен-приложения** нужно явно разрешить переменной окружения:

  **`DJANGO_CORS_ALLOWED_ORIGINS`** — список через запятую, например:

  `https://collector.example.com,https://www.collector.example.com`

- После смены origin пересобирать Flutter **не обязательно**, если не меняли `API_BASE_URL`.

## Firebase

Конфиг клиента: `lib/firebase_options.dart` (и при необходимости шаги из `README.md` / `flutterfire configure`). Для web-логина в консоли Firebase должны быть разрешены **домен приложения** (Authorized domains), с которого открывают собранный сайт.

## Связанные заметки

Отличия web от APK (файлы, камера, сеть): **`docs/web-vs-android.md`**.
