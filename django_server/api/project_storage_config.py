"""Резолвер per-project хранилищ: database_uri (SQLAlchemy) и storage_uri (fsspec).

Источник истины — поля Project.database_uri / Project.storage_uri.
Если поле пустое — подставляется дефолт «как раньше»: SQLite-файл и папка на диске
сервера (PROJECT_DB_ROOT / PROJECT_MEDIA_ROOT). Дефолт не зависит от DJANGO_ENV.

См. specs/project-storage-uris.md.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit, urlunsplit

from django.conf import settings


@dataclass(frozen=True)
class StorageConfig:
    """Разрешённые URI проекта + удобные производные."""

    project_id: str
    database_uri: str
    storage_uri: str
    storage_options: dict = field(default_factory=dict)

    @property
    def storage_scheme(self) -> str:
        return urlsplit(self.storage_uri).scheme or "file"

    @property
    def is_local_storage(self) -> bool:
        return self.storage_scheme == "file"

    @property
    def is_sqlite(self) -> bool:
        return self.database_uri.startswith("sqlite:")


def _project_db_root() -> Path:
    return Path(getattr(settings, "PROJECT_DB_ROOT", settings.BASE_DIR / "project_db"))


def _project_media_root() -> Path:
    return Path(getattr(settings, "PROJECT_MEDIA_ROOT", settings.BASE_DIR / "project_media"))


def _path_to_file_uri(path: Path) -> str:
    """Path -> file:// URI с прямыми слэшами (Windows-safe), без trailing slash."""
    return path.resolve().as_uri()


def file_uri_to_path(file_uri: str) -> Path:
    """file:///... -> локальный Path. Windows: убираем ведущий слэш перед диском."""
    raw = urlsplit(file_uri).path
    # Windows: '/C:/Users/...' -> 'C:/Users/...'
    if len(raw) >= 3 and raw[0] == "/" and raw[2] == ":":
        raw = raw[1:]
    return Path(raw)


def default_database_uri(project_id: str) -> str:
    db_file = _project_db_root() / project_id / "project.sqlite3"
    # sqlite:/// + абсолютный путь. as_posix(), чтобы на Windows не было обратных слэшей.
    return "sqlite:///" + db_file.resolve().as_posix()


def default_storage_uri(project_id: str) -> str:
    root = _project_media_root() / project_id
    return _ensure_trailing_slash(_path_to_file_uri(root))


def _ensure_trailing_slash(uri: str) -> str:
    return uri if uri.endswith("/") else uri + "/"


def normalize_storage_uri(raw: str) -> str:
    """Привести пользовательский ввод к каноничному storage_uri.

    - голое имя бакета (`korovas-dc-x`) -> `gs://korovas-dc-x/`
    - `gs://bucket` / `s3://bucket/prefix` -> с trailing slash
    - локальный путь -> file:// URI
    """
    value = (raw or "").strip()
    if not value:
        return ""
    parts = urlsplit(value)
    scheme = parts.scheme.lower()
    if scheme in ("gs", "s3", "file", "abfs", "az", "http", "https"):
        return _ensure_trailing_slash(value)
    # Windows-путь с диском (C:\... или C:/...) — urlsplit увидит scheme="c".
    if len(scheme) == 1:
        return _ensure_trailing_slash(_path_to_file_uri(Path(value)))
    # Нет схемы: отличаем локальный путь от голого имени бакета.
    if "/" in value or "\\" in value or value.startswith("."):
        return _ensure_trailing_slash(_path_to_file_uri(Path(value)))
    # Голое имя -> GCS-бакет.
    return f"gs://{value.strip('/')}/"


def normalize_database_uri(raw: str) -> str:
    """Нормализация database_uri. Пустое -> пустое (резолвится в дефолт по проекту).

    `postgres://` приводим к каноничному `postgresql://` (SQLAlchemy 2.x).
    Остальные SQLAlchemy URL принимаем как есть.
    """
    value = (raw or "").strip()
    if not value:
        return ""
    parts = urlsplit(value)
    if parts.scheme.lower() == "postgres":
        return urlunsplit(("postgresql",) + parts[1:])
    return value


def storage_uri_from_legacy_bucket(media_bucket: str) -> str:
    """Конверсия старого Project.media_bucket -> storage_uri (gs://)."""
    bucket = (media_bucket or "").strip().strip("/")
    if not bucket:
        return ""
    return f"gs://{bucket}/"


def postgres_db_name(project_id: str) -> str:
    """Имя Postgres-базы для проекта (db-per-project): proj_krs_label, proj_yolo, …"""
    import re

    safe = re.sub(r"[^\w]+", "_", (project_id or "").strip().lower()).strip("_")
    return f"proj_{safe}" if safe else "proj_unknown"


def build_postgres_database_uri(
    project_id: str,
    *,
    host: str = "localhost",
    port: int = 55432,
    user: str = "collector",
    password: str = "collector",
) -> str:
    dbname = postgres_db_name(project_id)
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"


def build_s3_storage_uri(
    project_id: str,
    *,
    bucket: str = "dc-packages",
) -> str:
    prefix = (project_id or "").strip().strip("/")
    return f"s3://{bucket.strip('/')}/{prefix}/"


def default_s3_storage_options(
    *,
    endpoint_url: str = "http://localhost:9000",
    key: str = "minioadmin",
    secret: str = "minioadmin",
) -> dict:
    return {"endpoint_url": endpoint_url, "key": key, "secret": secret}


def decode_storage_options(encrypted: str) -> dict:
    """Расшифровать JSON storage_options. Пусто/ошибка -> {}."""
    raw = (encrypted or "").strip()
    if not raw:
        return {}
    try:
        from .git_credential_crypto import decrypt_private_key

        data = json.loads(decrypt_private_key(raw))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def encode_storage_options(options: dict) -> str:
    """Зашифровать JSON storage_options. Пустой dict -> ''."""
    clean = {k: v for k, v in (options or {}).items() if v not in (None, "")}
    if not clean:
        return ""
    from .git_credential_crypto import encrypt_private_key

    return encrypt_private_key(json.dumps(clean, ensure_ascii=False))


def resolve(project) -> StorageConfig:
    """Собрать эффективную конфигурацию хранилища для проекта (с дефолтами)."""
    project_id = project.project_id
    db_uri = (getattr(project, "database_uri", "") or "").strip()
    st_uri = (getattr(project, "storage_uri", "") or "").strip()
    if not st_uri:
        legacy = storage_uri_from_legacy_bucket(getattr(project, "media_bucket", ""))
        st_uri = legacy or default_storage_uri(project_id)
    if not db_uri:
        db_uri = default_database_uri(project_id)
    options = decode_storage_options(getattr(project, "storage_options_encrypted", ""))
    return StorageConfig(
        project_id=project_id,
        database_uri=db_uri,
        storage_uri=st_uri,
        storage_options=options,
    )


def resolve_by_id(project_id: str) -> StorageConfig:
    """Как resolve(), но грузит Project по id. Нет проекта -> чистые дефолты."""
    from .models import Project

    project = Project.objects.filter(project_id=project_id).first()
    if project is None:
        return StorageConfig(
            project_id=project_id,
            database_uri=default_database_uri(project_id),
            storage_uri=default_storage_uri(project_id),
            storage_options={},
        )
    return resolve(project)


def sqlite_path_from_uri(database_uri: str) -> Path | None:
    """Вернуть путь к файлу для sqlite URI; None для не-sqlite.

    SQLAlchemy-конвенции:
      sqlite:///rel.db        -> rel.db (относительный)
      sqlite:////abs/path.db  -> /abs/path.db (unix абсолютный)
      sqlite:///C:/path.db    -> C:/path.db (windows абсолютный)
    """
    scheme = urlsplit(database_uri).scheme.lower()
    if not scheme.startswith("sqlite"):
        return None
    marker = "sqlite:///"
    idx = database_uri.find(marker)
    if idx == -1:
        return None
    rest = database_uri[idx + len(marker):]
    return Path(rest)


def filesystem_for(config: StorageConfig):
    """fsspec-файловая система для storage_uri проекта (с креды из storage_options)."""
    import fsspec

    scheme = config.storage_scheme
    opts = dict(config.storage_options or {})
    if scheme == "file":
        return fsspec.filesystem("file")
    if scheme == "s3":
        s3opts: dict = {}
        endpoint = opts.pop("endpoint_url", "") or opts.pop("endpoint", "")
        if "key" in opts:
            s3opts["key"] = opts.pop("key")
        if "secret" in opts:
            s3opts["secret"] = opts.pop("secret")
        if "token" in opts:
            s3opts["token"] = opts.pop("token")
        client_kwargs = opts.pop("client_kwargs", {}) or {}
        if endpoint:
            client_kwargs["endpoint_url"] = endpoint
        if client_kwargs:
            s3opts["client_kwargs"] = client_kwargs
        s3opts.update(opts)
        return fsspec.filesystem("s3", **s3opts)
    return fsspec.filesystem(scheme, **opts)


def object_root(config: StorageConfig) -> str:
    """Корень внутри ФС: локальный абсолютный путь или 'bucket/prefix' для s3/gs."""
    if config.is_local_storage:
        return str(file_uri_to_path(config.storage_uri))
    parts = urlsplit(config.storage_uri)
    return f"{parts.netloc}{parts.path}".rstrip("/")


def object_path(config: StorageConfig, rel_path: str) -> str:
    """Полный путь объекта внутри ФС для fs.open()/fs.exists()."""
    rel = rel_path.replace("\\", "/").lstrip("/")
    root = object_root(config)
    if config.is_local_storage:
        return str(Path(root) / rel)
    return f"{root}/{rel}" if root else rel


def check_storage(config: StorageConfig) -> list[str]:
    """Проверить доступность хранилища. Возвращает список строк-результатов.

    Бросает исключение только на жёстких ошибках подключения; «мягкие» проблемы
    (нет опционального бэкенда) возвращаются как предупреждения в списке.
    """
    notes: list[str] = []
    notes.append(_check_database(config))
    notes.append(_check_blob_storage(config))
    return notes


def _check_database(config: StorageConfig) -> str:
    if config.is_sqlite:
        path = sqlite_path_from_uri(config.database_uri)
        if path is None:
            return f"DB: не удалось разобрать sqlite URI: {config.database_uri}"
        path.parent.mkdir(parents=True, exist_ok=True)
        import sqlite3

        conn = sqlite3.connect(path)
        try:
            conn.execute("SELECT 1")
        finally:
            conn.close()
        return f"DB (SQLite): OK — {path}"
    # Postgres / прочее: пробуем через SQLAlchemy.
    try:
        from sqlalchemy import create_engine, text
    except ImportError:
        return "DB: SQLAlchemy не установлен — проверьте requirements.txt"
    engine = create_engine(config.database_uri)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    finally:
        engine.dispose()
    return f"DB ({urlsplit(config.database_uri).scheme}): OK"


def _check_blob_storage(config: StorageConfig) -> str:
    if config.is_local_storage:
        path = file_uri_to_path(config.storage_uri)
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".storage_check"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return f"Storage (file): OK — {path}"
    scheme = config.storage_scheme
    try:
        import fsspec  # noqa: F401
    except ImportError:
        return "Storage: fsspec не установлен — проверьте requirements.txt"
    try:
        fs = filesystem_for(config)
    except ImportError:
        return (
            f"Storage ({scheme}): не установлен бэкенд "
            f"({'gcsfs' if scheme == 'gs' else 's3fs'})"
        )
    # Write/delete-пробник: надёжнее ls по префиксу (пустой префикс у s3/gs
    # бросает FileNotFoundError, хотя бакет доступен).
    probe = object_path(config, ".storage_check")
    with fs.open(probe, "wb") as f:
        f.write(b"ok")
    try:
        fs.rm_file(probe)
    except (FileNotFoundError, AttributeError):
        try:
            fs.rm(probe)
        except FileNotFoundError:
            pass
    return f"Storage ({scheme}): OK — {config.storage_uri}"


def storage_join(storage_uri: str, rel_path: str) -> str:
    """Полный URI объекта внутри storage_uri."""
    base = _ensure_trailing_slash(storage_uri)
    rel = rel_path.replace("\\", "/").lstrip("/")
    parts = urlsplit(base)
    new_path = str(PurePosixPath(parts.path) / rel)
    if parts.path.startswith("/") and not new_path.startswith("/"):
        new_path = "/" + new_path
    return urlunsplit((parts.scheme, parts.netloc, new_path, "", ""))
