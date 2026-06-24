"""Per-project DB (пакеты + pipeline) через SQLAlchemy: SQLite (dev) или Postgres (prod).

Бэкенд выбирается по Project.database_uri (см. project_storage_config). Схема —
SQLAlchemy MetaData + create_all (идемпотентно, как прежний CREATE IF NOT EXISTS).

Публичный API (connect/insert_*/list_*/…) сохранён. connect() отдаёт тонкую обёртку
над SQLAlchemy Connection, понимающую тот же `?`-плейсхолдер и доступ к строкам
по индексу и по имени (как sqlite3.Row).
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    event,
    inspect,
)
from sqlalchemy.pool import NullPool

from . import project_storage_config as psc

metadata = MetaData()

package_session = Table(
    "package_session",
    metadata,
    Column("package_id", Text, primary_key=True),
    # project_id — для разделения проектов, когда несколько проектов делят одну БД.
    # Nullable ради совместимости со старыми БД (бэкфилл из manifest при инициализации).
    Column("project_id", Text, index=True),
    Column("phase", Text, nullable=False),
    Column("manifest_json", Text, nullable=False),
    Column("failure_reason", Text, nullable=False),
    Column("uploader_uid", Text, nullable=False),
    Column("uploader_email", Text, nullable=False),
    Column("created_at", Text, nullable=False),
)

uploaded_blob = Table(
    "uploaded_blob",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("package_id", Text, nullable=False, index=True),
    Column("logical_path", Text, nullable=False),
    Column("size_bytes", Integer, nullable=False),
    Column("sha256", Text, nullable=False),
    Column("storage_path", Text, nullable=False),
    Column("created_at", Text, nullable=False),
    UniqueConstraint("package_id", "logical_path", name="uq_blob_pkg_logical"),
)

package_field_change = Table(
    "package_field_change",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("package_id", Text, nullable=False, index=True),
    Column("field_id", Text, nullable=False),
    Column("before_value", Text),
    Column("after_value", Text),
    Column("reason", Text, nullable=False),
    Column("verifier_email", Text, nullable=False),
    Column("changed_at", Text, nullable=False),
)

cow_keypoint_annotation = Table(
    "cow_keypoint_annotation",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("package_id", Text, nullable=False, index=True),
    Column("manifest_blob_key", Text, nullable=False),
    Column("cvat_link", Text, nullable=False),
    Column("image_width", Integer, nullable=False),
    Column("image_height", Integer, nullable=False),
    Column("annotation_json", Text, nullable=False),
    Column("created_at", Text, nullable=False),
    UniqueConstraint("package_id", "manifest_blob_key", name="uq_gt_pkg_key"),
)

cow_inference_result = Table(
    "cow_inference_result",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("package_id", Text, nullable=False, index=True),
    Column("manifest_blob_key", Text, nullable=False),
    Column("source_export", Text, nullable=False),
    Column("image_width", Integer, nullable=False),
    Column("image_height", Integer, nullable=False),
    Column("inference_json", Text, nullable=False),
    Column("depth_blob_key", Text),
    Column("depth_format", Text, nullable=False),
    Column("depth_unit", Text, nullable=False),
    Column("depth_width", Integer),
    Column("depth_height", Integer),
    Column("created_at", Text, nullable=False),
    UniqueConstraint("package_id", "manifest_blob_key", name="uq_inf_pkg_key"),
)

yolo_detection = Table(
    "yolo_detection",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("package_id", Text, nullable=False, index=True),
    Column("manifest_blob_key", Text, nullable=False),
    Column("image_width", Integer, nullable=False),
    Column("image_height", Integer, nullable=False),
    Column("detections_json", Text, nullable=False),
    Column("source_label", Text, nullable=False),
    Column("created_at", Text, nullable=False),
    UniqueConstraint("package_id", "manifest_blob_key", name="uq_yolo_pkg_key"),
)

depth_map = Table(
    "depth_map",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("package_id", Text, nullable=False, index=True),
    Column("manifest_blob_key", Text, nullable=False),
    Column("depth_path", Text, nullable=False),
    Column("format", Text, nullable=False),
    Column("unit", Text, nullable=False),
    Column("width", Integer),
    Column("height", Integer),
    Column("source_label", Text, nullable=False),
    Column("created_at", Text, nullable=False),
    UniqueConstraint("package_id", "manifest_blob_key", name="uq_depth_pkg_key"),
)

cvat_link = Table(
    "cvat_link",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("package_id", Text, nullable=False, index=True),
    Column("manifest_blob_key", Text, nullable=False),
    Column("url", Text, nullable=False),
    Column("label", Text, nullable=False),
    Column("created_at", Text, nullable=False),
    UniqueConstraint("package_id", "manifest_blob_key", name="uq_cvat_pkg_key"),
)


def _now() -> str:
    return timezone.now().isoformat()


# --- Engine management -------------------------------------------------------

_engines: dict = {}
_initialized: set = set()


def _sqlite_on_connect(dbapi_conn, _rec) -> None:
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA busy_timeout=30000")
    cur.close()


def _prepare_sqlite(uri: str) -> None:
    path = psc.sqlite_path_from_uri(uri)
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    legacy = path.parent / "pipeline.sqlite3"
    if not path.exists() and legacy.is_file():
        legacy.rename(path)


def _project_id_from_manifest(manifest_json: Any) -> str:
    raw = (manifest_json or "").strip() if isinstance(manifest_json, str) else ""
    if not raw:
        return ""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return ""
    if isinstance(data, dict):
        pid = data.get("project_id")
        if isinstance(pid, str):
            return pid.strip()
    return ""


def _ensure_package_session_project_id(engine) -> None:
    """Добавить колонку project_id в старые БД и заполнить её из manifest_json.

    Нужно для разделения проектов в общей БД: create_all не меняет существующие
    таблицы, поэтому колонку добавляем вручную (ALTER) и делаем разовый бэкфилл.
    """
    try:
        cols = {c["name"] for c in inspect(engine).get_columns("package_session")}
    except Exception:
        return
    if "project_id" not in cols:
        with engine.begin() as conn:
            conn.exec_driver_sql("ALTER TABLE package_session ADD COLUMN project_id TEXT")
    is_pg = engine.dialect.name != "sqlite"
    ph = "%s" if is_pg else "?"
    with engine.begin() as conn:
        rows = conn.exec_driver_sql(
            "SELECT package_id, manifest_json FROM package_session "
            "WHERE project_id IS NULL OR project_id = ''",
        ).fetchall()
        for row in rows:
            pid = _project_id_from_manifest(row[1])
            if not pid:
                continue
            conn.exec_driver_sql(
                f"UPDATE package_session SET project_id = {ph} WHERE package_id = {ph}",
                (pid, row[0]),
            )


def get_engine_for_uri(uri: str):
    engine = _engines.get(uri)
    if engine is None:
        if uri.startswith("sqlite"):
            _prepare_sqlite(uri)
            engine = create_engine(
                uri,
                future=True,
                poolclass=NullPool,
                connect_args={"check_same_thread": False, "timeout": 30},
            )
            event.listen(engine, "connect", _sqlite_on_connect)
        else:
            engine = create_engine(uri, future=True, pool_pre_ping=True)
        _engines[uri] = engine
    if uri not in _initialized:
        metadata.create_all(engine)
        _ensure_package_session_project_id(engine)
        _initialized.add(uri)
    return engine


def _engine_for_project(project_id: str):
    uri = psc.resolve_by_id(project_id).database_uri
    return get_engine_for_uri(uri)


class _Row:
    """Доступ к строке и по индексу (row[0]), и по имени (row['col']) — как sqlite3.Row."""

    __slots__ = ("_t", "_m")

    def __init__(self, sa_row):
        self._t = sa_row
        self._m = sa_row._mapping

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._t[key]
        return self._m[key]

    def __contains__(self, key):
        return key in self._m

    def get(self, key, default=None):
        return self._m.get(key, default)

    def keys(self):
        return list(self._m.keys())


class _Result:
    def __init__(self, res):
        self._res = res

    def fetchone(self):
        row = self._res.fetchone()
        return None if row is None else _Row(row)

    def fetchall(self):
        return [_Row(r) for r in self._res.fetchall()]

    @property
    def rowcount(self):
        return self._res.rowcount

    @property
    def lastrowid(self):
        return self._res.lastrowid


class _Conn:
    """Тонкая обёртка над SQLAlchemy Connection с qmark-SQL (как sqlite3)."""

    def __init__(self, sa_conn):
        self._c = sa_conn
        self._pg = sa_conn.dialect.name != "sqlite"

    def execute(self, sql: str, params=()):
        if self._pg:
            sql = sql.replace("?", "%s")
        if params:
            res = self._c.exec_driver_sql(sql, tuple(params))
        else:
            res = self._c.exec_driver_sql(sql)
        return _Result(res)


def project_db_root() -> Path:
    return Path(getattr(settings, "PROJECT_DB_ROOT", settings.BASE_DIR / "project_db"))


def db_path(project_id: str) -> Path | None:
    """Путь к sqlite-файлу проекта (None, если БД не sqlite)."""
    uri = psc.resolve_by_id(project_id).database_uri
    if uri.startswith("sqlite"):
        _prepare_sqlite(uri)
    return psc.sqlite_path_from_uri(uri)


def remove_project_db(project_id: str, *, database_uri: str | None = None) -> None:
    uri = database_uri
    if uri is None:
        uri = psc.resolve_by_id(project_id).database_uri
    psc.drop_database_uri(uri)


@contextmanager
def connect(project_id: str) -> Iterator[_Conn]:
    engine = _engine_for_project(project_id)
    with engine.begin() as sa_conn:
        yield _Conn(sa_conn)


def ensure_schema(project_id: str) -> None:
    """Создать схему для проекта (идемпотентно)."""
    _engine_for_project(project_id)


def package_has_pipeline_data(project_id: str, package_id: str) -> bool:
    with connect(project_id) as conn:
        gt = conn.execute(
            "SELECT 1 FROM cow_keypoint_annotation WHERE package_id = ? LIMIT 1",
            (package_id,),
        ).fetchone()
        if gt:
            return True
        inf = conn.execute(
            "SELECT 1 FROM cow_inference_result WHERE package_id = ? LIMIT 1",
            (package_id,),
        ).fetchone()
        if inf:
            return True
        for tbl in ("yolo_detection", "depth_map", "cvat_link"):
            hit = conn.execute(
                f"SELECT 1 FROM {tbl} WHERE package_id = ? LIMIT 1",
                (package_id,),
            ).fetchone()
            if hit:
                return True
        return False


PIPELINE_TABLES = (
    "cow_keypoint_annotation",
    "cow_inference_result",
    "yolo_detection",
    "depth_map",
    "cvat_link",
)


def rebind_pipeline_package_id(
    project_id: str,
    old_package_id: str,
    new_package_id: str,
) -> dict[str, int]:
    """Перенести pipeline-строки со старого package_id на новый (manifest_blob_key без изменений)."""
    if old_package_id == new_package_id:
        return {}
    counts: dict[str, int] = {}
    with connect(project_id) as conn:
        for tbl in PIPELINE_TABLES:
            cur = conn.execute(
                f"UPDATE {tbl} SET package_id = ? WHERE package_id = ?",
                (new_package_id, old_package_id),
            )
            if cur.rowcount:
                counts[tbl] = cur.rowcount
    return counts


def delete_package_pipeline_data(project_id: str, package_id: str) -> None:
    with connect(project_id) as conn:
        conn.execute(
            "DELETE FROM cow_keypoint_annotation WHERE package_id = ?",
            (package_id,),
        )
        conn.execute(
            "DELETE FROM cow_inference_result WHERE package_id = ?",
            (package_id,),
        )
        conn.execute(
            "DELETE FROM yolo_detection WHERE package_id = ?",
            (package_id,),
        )
        conn.execute(
            "DELETE FROM depth_map WHERE package_id = ?",
            (package_id,),
        )
        conn.execute(
            "DELETE FROM cvat_link WHERE package_id = ?",
            (package_id,),
        )


def insert_depth_map(
    project_id: str,
    *,
    package_id: str,
    manifest_blob_key: str,
    depth_path: str,
    image_size: dict[str, Any] | None = None,
    fmt: str = "npy",
    unit: str = "m",
    width: int | None = None,
    height: int | None = None,
    source_label: str = "",
) -> None:
    if width is None:
        width = int((image_size or {}).get("width") or 0) or None
    if height is None:
        height = int((image_size or {}).get("height") or 0) or None
    with connect(project_id) as conn:
        conn.execute(
            """
            INSERT INTO depth_map (
                package_id, manifest_blob_key, depth_path,
                format, unit, width, height, source_label, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(package_id, manifest_blob_key) DO UPDATE SET
                depth_path = excluded.depth_path,
                format = excluded.format,
                unit = excluded.unit,
                width = excluded.width,
                height = excluded.height,
                source_label = excluded.source_label
            """,
            (
                package_id,
                manifest_blob_key,
                depth_path,
                fmt,
                unit,
                width,
                height,
                source_label,
                _now(),
            ),
        )


def insert_cvat_link(
    project_id: str,
    *,
    package_id: str,
    manifest_blob_key: str,
    url: str,
    label: str = "",
) -> None:
    with connect(project_id) as conn:
        conn.execute(
            """
            INSERT INTO cvat_link (
                package_id, manifest_blob_key, url, label, created_at
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(package_id, manifest_blob_key) DO UPDATE SET
                url = excluded.url,
                label = excluded.label
            """,
            (package_id, manifest_blob_key, url, label, _now()),
        )


def insert_yolo_detection(
    project_id: str,
    *,
    package_id: str,
    manifest_blob_key: str,
    image_size: dict[str, Any],
    boxes: list[dict[str, Any]],
    source_label: str = "",
) -> None:
    with connect(project_id) as conn:
        conn.execute(
            """
            INSERT INTO yolo_detection (
                package_id, manifest_blob_key,
                image_width, image_height, detections_json, source_label, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(package_id, manifest_blob_key) DO UPDATE SET
                image_width = excluded.image_width,
                image_height = excluded.image_height,
                detections_json = excluded.detections_json,
                source_label = excluded.source_label
            """,
            (
                package_id,
                manifest_blob_key,
                int(image_size.get("width") or 0),
                int(image_size.get("height") or 0),
                json.dumps({"boxes": boxes}, ensure_ascii=False),
                source_label,
                _now(),
            ),
        )


def insert_gt(
    project_id: str,
    *,
    package_id: str,
    manifest_blob_key: str,
    image_size: dict[str, Any],
    annotation: dict[str, Any],
) -> None:
    with connect(project_id) as conn:
        conn.execute(
            """
            INSERT INTO cow_keypoint_annotation (
                package_id, manifest_blob_key, cvat_link,
                image_width, image_height, annotation_json, created_at
            ) VALUES (?, ?, '', ?, ?, ?, ?)
            ON CONFLICT(package_id, manifest_blob_key) DO UPDATE SET
                image_width = excluded.image_width,
                image_height = excluded.image_height,
                annotation_json = excluded.annotation_json
            """,
            (
                package_id,
                manifest_blob_key,
                int(image_size.get("width") or 0),
                int(image_size.get("height") or 0),
                json.dumps(annotation, ensure_ascii=False),
                _now(),
            ),
        )


def insert_inference(
    project_id: str,
    *,
    package_id: str,
    manifest_blob_key: str,
    source_export: str,
    image_size: dict[str, Any],
    inference: dict[str, Any],
) -> None:
    with connect(project_id) as conn:
        conn.execute(
            """
            INSERT INTO cow_inference_result (
                package_id, manifest_blob_key, source_export,
                image_width, image_height, inference_json,
                depth_blob_key, depth_format, depth_unit,
                depth_width, depth_height, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, NULL, 'npy', 'm', NULL, NULL, ?)
            ON CONFLICT(package_id, manifest_blob_key) DO UPDATE SET
                source_export = excluded.source_export,
                image_width = excluded.image_width,
                image_height = excluded.image_height,
                inference_json = excluded.inference_json
            """,
            (
                package_id,
                manifest_blob_key,
                source_export,
                int(image_size.get("width") or 0),
                int(image_size.get("height") or 0),
                json.dumps(inference, ensure_ascii=False),
                _now(),
            ),
        )


def _row_to_gt(row: sqlite3.Row) -> dict[str, Any]:
    ann = json.loads(row["annotation_json"])
    return {
        "package_id": row["package_id"],
        "project_id": "",  # filled by caller
        "manifest_blob_key": row["manifest_blob_key"],
        "image_size": {"width": row["image_width"], "height": row["image_height"]},
        "annotation": ann,
    }


def _depth_url(project_id: str, package_id: str, logical_path: str) -> str:
    return reverse(
        "ui_package_depth_blob",
        kwargs={
            "project_id": project_id,
            "package_id": package_id,
            "logical_path": logical_path,
        },
    )


def _row_to_inference(
    row: sqlite3.Row,
    *,
    project_id: str,
    package_id: str,
) -> dict[str, Any]:
    inf = json.loads(row["inference_json"])
    out: dict[str, Any] = {
        "package_id": row["package_id"],
        "project_id": project_id,
        "manifest_blob_key": row["manifest_blob_key"],
        "source_export": row["source_export"],
        "image_size": {"width": row["image_width"], "height": row["image_height"]},
        "inference": inf,
    }
    return out


def list_gt(project_id: str, package_id: str) -> list[dict[str, Any]]:
    with connect(project_id) as conn:
        rows = conn.execute(
            """
            SELECT * FROM cow_keypoint_annotation
            WHERE package_id = ?
            ORDER BY manifest_blob_key
            """,
            (package_id,),
        ).fetchall()
    out = []
    for row in rows:
        rec = _row_to_gt(row)
        rec["project_id"] = project_id
        out.append(rec)
    return out


def _row_to_yolo(row: sqlite3.Row) -> dict[str, Any]:
    det = json.loads(row["detections_json"])
    if not isinstance(det, dict):
        det = {"boxes": []}
    return {
        "package_id": row["package_id"],
        "manifest_blob_key": row["manifest_blob_key"],
        "image_size": {"width": row["image_width"], "height": row["image_height"]},
        "detections": det,
        "source_label": row["source_label"] or "",
    }


def list_yolo_detection(project_id: str, package_id: str) -> list[dict[str, Any]]:
    with connect(project_id) as conn:
        rows = conn.execute(
            """
            SELECT * FROM yolo_detection
            WHERE package_id = ?
            ORDER BY manifest_blob_key
            """,
            (package_id,),
        ).fetchall()
    return [_row_to_yolo(row) for row in rows]


def _row_to_depth(
    row: sqlite3.Row,
    *,
    project_id: str,
    package_id: str,
) -> dict[str, Any]:
    path = row["depth_path"]
    dm: dict[str, Any] = {
        "format": row["format"] or "npy",
        "unit": row["unit"] or "m",
        "asset_path": path,
        "depth_path": path,
        "depth_url": _depth_url(project_id, package_id, path),
    }
    if row["width"]:
        dm["width"] = row["width"]
    if row["height"]:
        dm["height"] = row["height"]
    return {
        "package_id": row["package_id"],
        "manifest_blob_key": row["manifest_blob_key"],
        "image_size": {"width": row["width"] or 0, "height": row["height"] or 0},
        "depth_map": dm,
        "source_label": row["source_label"] or "",
    }


def list_depth_map(project_id: str, package_id: str) -> list[dict[str, Any]]:
    with connect(project_id) as conn:
        rows = conn.execute(
            """
            SELECT * FROM depth_map
            WHERE package_id = ?
            ORDER BY manifest_blob_key
            """,
            (package_id,),
        ).fetchall()
    return [_row_to_depth(row, project_id=project_id, package_id=package_id) for row in rows]


def _row_to_cvat(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "package_id": row["package_id"],
        "manifest_blob_key": row["manifest_blob_key"],
        "cvat_link": row["url"],
        "label": row["label"] or "",
    }


def list_cvat_link(project_id: str, package_id: str) -> list[dict[str, Any]]:
    with connect(project_id) as conn:
        rows = conn.execute(
            """
            SELECT * FROM cvat_link
            WHERE package_id = ?
            ORDER BY manifest_blob_key
            """,
            (package_id,),
        ).fetchall()
    return [_row_to_cvat(row) for row in rows]


def list_inference(project_id: str, package_id: str) -> list[dict[str, Any]]:
    with connect(project_id) as conn:
        rows = conn.execute(
            """
            SELECT * FROM cow_inference_result
            WHERE package_id = ?
            ORDER BY manifest_blob_key
            """,
            (package_id,),
        ).fetchall()
    return [_row_to_inference(row, project_id=project_id, package_id=package_id) for row in rows]
