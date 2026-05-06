import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

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
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "api.middleware.ApiV1AuthMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
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
            ],
        },
    },
]

WSGI_APPLICATION = "collector_site.wsgi.application"

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
LOGIN_REDIRECT_URL = "/ui/projects/"

MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

PROJECT_ASSETS_ROOT = Path(os.environ.get("PROJECT_ASSETS_ROOT", str(BASE_DIR / "project_assets")))

STATIC_URL = "static/"

API_BEARER_TOKEN = os.environ.get("API_BEARER_TOKEN", "").strip() or None

# Новому CollectorUser (первый запрос / sync Firebase) выдаётся доступ к этому project_id, если он есть в БД.
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

ASSETS_CONFIG_ROOT = Path(
    os.environ.get(
        "ASSETS_CONFIG_ROOT",
        str(BASE_DIR.parent / "assets" / "config"),
    )
)

DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800
FILE_UPLOAD_MAX_MEMORY_SIZE = 2621440
