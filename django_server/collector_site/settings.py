import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Режим развёртывания:
#   local      — SQLite + файлы в media/ (как до prod-деплоя)
#   production — PostgreSQL + Google Cloud Storage (k8s / Docker)
# Явно: DJANGO_ENV=local | production
# По умолчанию: production, если задан POSTGRES_HOST; иначе local.
_django_env = os.environ.get("DJANGO_ENV", "").strip().lower()
if _django_env == "production":
    DJANGO_ENV = "production"
elif _django_env == "local":
    DJANGO_ENV = "local"
elif os.environ.get("POSTGRES_HOST", "").strip():
    DJANGO_ENV = "production"
else:
    DJANGO_ENV = "local"

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "dev-only-change-in-production-not-for-production-use",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

# Для HTTPS за пределами localhost (админка / формы): через запятую, со схемой.
# Пример: DJANGO_CSRF_TRUSTED_ORIGINS=https://data-collector-app.korovas.ml.epoch8.dev
_csrf = os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").strip()
CSRF_TRUSTED_ORIGINS = [x.strip() for x in _csrf.split(",") if x.strip()]

APPEND_SLASH = False

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "api",
]
if DJANGO_ENV == "production":
    INSTALLED_APPS.append("storages")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "api.middleware.UiCollectorSessionMiddleware",
    "api.middleware.ApiV1AuthMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "collector_site.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "api.ui_context.ui_template_context",
            ],
        },
    },
]

WSGI_APPLICATION = "collector_site.wsgi.application"

if DJANGO_ENV == "production":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql_psycopg2",
            "NAME": os.environ.get("POSTGRES_DB"),
            "USER": os.environ.get("POSTGRES_USER"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD"),
            "HOST": os.environ.get("POSTGRES_HOST"),
            "PORT": os.environ.get("PGPORT"),
        }
    }
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
            "OPTIONS": {
                "bucket_name": os.environ.get("GS_STORAGE", "korovas-dc-prod"),
            },
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS: list = []

LOGIN_URL = "/ui/login/"
LOGIN_REDIRECT_URL = "/ui/"

MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

PROJECT_GIT_CACHE_ROOT = Path(
    os.environ.get("PROJECT_GIT_CACHE_ROOT", str(BASE_DIR / "project_git_cache")),
)
# Минимальный интервал между git fetch для одного проекта (секунды). Снижает лаг UI пакетов.
PROJECT_GIT_PULL_MIN_INTERVAL_SEC = int(os.environ.get("PROJECT_GIT_PULL_MIN_INTERVAL_SEC", "300"))

# Per-project SQLite: inference / GT (pipeline.sqlite3 в PROJECT_DB_ROOT/<project_id>/).
PROJECT_DB_ROOT = Path(os.environ.get("PROJECT_DB_ROOT", str(BASE_DIR / "project_db")))
PACKAGE_FIELD_CHANGELOG_PATH = Path(
    os.environ.get(
        "PACKAGE_FIELD_CHANGELOG_PATH",
        str(BASE_DIR / "data" / "field_changelog.json"),
    ),
)

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

API_BEARER_TOKEN = os.environ.get("API_BEARER_TOKEN", "").strip() or None

# Новому CollectorUser (первый запрос / sync Firebase) выдаётся доступ к этому project_id
# в mobile_projects, если проект есть в БД. admin_projects назначаются вручную в админке.
DEFAULT_COLLECTOR_PROJECT_ID = (
    os.environ.get("DEFAULT_COLLECTOR_PROJECT_ID", "").strip() or "simple-photo-2026"
)

# Firebase Admin SDK: проверка ID token (/v1/*) и синхронизация пользователей.
# 1) Переменная FIREBASE_SERVICE_ACCOUNT_PATH — путь к JSON сервисного аккаунта
# 2) Или положите файл firebase-service-account.json в папку django_server/ (не коммитить)
# 3) Или FIREBASE_SERVICE_ACCOUNT_JSON — весь JSON одной строкой
# 4) Или GOOGLE_APPLICATION_CREDENTIALS — путь к JSON (как в документации Google Cloud)
_firebase_sa_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH", "").strip()
_firebase_sa_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
_local_sa = BASE_DIR / "firebase-service-account.json"
if _firebase_sa_path:
    FIREBASE_SERVICE_ACCOUNT_PATH = _firebase_sa_path
elif _local_sa.is_file():
    FIREBASE_SERVICE_ACCOUNT_PATH = str(_local_sa.resolve())
else:
    FIREBASE_SERVICE_ACCOUNT_PATH = None

_firebase_flag = os.environ.get("FIREBASE_AUTH_ENABLED", "").strip().lower()
_firebase_has_credentials = bool(
    FIREBASE_SERVICE_ACCOUNT_PATH
    or _firebase_sa_json
    or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
)
if _firebase_flag in ("0", "false", "no", "off"):
    FIREBASE_AUTH_ENABLED = False
elif _firebase_flag in ("1", "true", "yes", "on"):
    FIREBASE_AUTH_ENABLED = True
else:
    FIREBASE_AUTH_ENABLED = _firebase_has_credentials

# Проверка ID token (Admin SDK): отзыв токенов — опционально (часто ломает dev без сети к Google).
FIREBASE_CHECK_REVOKED = os.environ.get("FIREBASE_CHECK_REVOKED", "").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
FIREBASE_CLOCK_SKEW_SECONDS = int(os.environ.get("FIREBASE_CLOCK_SKEW_SECONDS", "60"))

# Firebase Web SDK (вход клиента на /ui/login/) — тот же проект, что ios в lib/firebase_options.dart.
FIREBASE_WEB_CONFIG = {
    "apiKey": os.environ.get("FIREBASE_WEB_API_KEY", "AIzaSyCGtNxCn-rs7Gd3LEbG754GimCxz1yOi7c"),
    "authDomain": os.environ.get(
        "FIREBASE_WEB_AUTH_DOMAIN",
        "data-collector-dev-e8.firebaseapp.com",
    ),
    "projectId": os.environ.get("FIREBASE_WEB_PROJECT_ID", "data-collector-dev-e8"),
    "storageBucket": os.environ.get(
        "FIREBASE_WEB_STORAGE_BUCKET",
        "data-collector-dev-e8.firebasestorage.app",
    ),
    "messagingSenderId": os.environ.get("FIREBASE_WEB_MESSAGING_SENDER_ID", "181572319604"),
    # Зарегистрируйте Web-приложение в Firebase Console → App ID с суффиксом :web:
    "appId": os.environ.get(
        "FIREBASE_WEB_APP_ID",
        "1:181572319604:ios:0000000000000000000000",
    ),
}

ASSETS_CONFIG_ROOT = Path(
    os.environ.get(
        "ASSETS_CONFIG_ROOT",
        str(BASE_DIR.parent / "assets" / "config"),
    )
)

DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800
FILE_UPLOAD_MAX_MEMORY_SIZE = 2621440

# --- CORS (Flutter Web / браузер) ---
# Дополнительные точные origin через запятую, например:
# DJANGO_CORS_ALLOWED_ORIGINS=https://app.example.com,http://127.0.0.1:3000
_cors_origins = os.environ.get("DJANGO_CORS_ALLOWED_ORIGINS", "").strip()
CORS_ALLOWED_ORIGINS = [x.strip() for x in _cors_origins.split(",") if x.strip()]

# Локальный Flutter Web: порт меняется при каждом flutter run — разрешаем localhost / 127.0.0.1 с любым портом.
# При DEBUG — ещё и частные LAN-адреса (телефон в той же Wi‑Fi: http://<IP_ПК>:<порт_приложения>).
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^http://localhost:\d+$",
    r"^http://127\.0\.0\.1:\d+$",
]
if DEBUG:
    CORS_ALLOWED_ORIGIN_REGEXES += [
        r"^http://192\.168\.\d{1,3}\.\d{1,3}:\d+$",
        r"^http://10\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+$",
        r"^http://172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}:\d+$",
    ]

# Явные методы и заголовки для preflight (Authorization шлёт браузер с Firebase).
CORS_ALLOW_METHODS = (
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
)
CORS_ALLOW_HEADERS = (
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
)

# Не требуем cookie для API; при необходимости кук можно включить и настроить CORS_ALLOW_CREDENTIALS.
CORS_ALLOW_CREDENTIALS = False

# Same-origin /ui SPA uses session cookies (not CORS).
SESSION_COOKIE_SAMESITE = "Lax"
