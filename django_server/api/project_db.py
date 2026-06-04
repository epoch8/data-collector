"""Per-project SQLite: GT annotations and inference (pipeline tables)."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from django.conf import settings
from django.urls import reverse

_SCHEMA_VERSION = 1

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cow_keypoint_annotation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    package_id TEXT NOT NULL,
    manifest_blob_key TEXT NOT NULL,
    cvat_link TEXT NOT NULL DEFAULT '',
    image_width INTEGER NOT NULL,
    image_height INTEGER NOT NULL,
    annotation_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(package_id, manifest_blob_key)
);

CREATE TABLE IF NOT EXISTS cow_inference_result (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    package_id TEXT NOT NULL,
    manifest_blob_key TEXT NOT NULL,
    source_export TEXT NOT NULL DEFAULT '',
    image_width INTEGER NOT NULL,
    image_height INTEGER NOT NULL,
    inference_json TEXT NOT NULL,
    depth_blob_key TEXT,
    depth_format TEXT NOT NULL DEFAULT 'npy',
    depth_unit TEXT NOT NULL DEFAULT 'm',
    depth_width INTEGER,
    depth_height INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(package_id, manifest_blob_key)
);

CREATE INDEX IF NOT EXISTS idx_gt_pkg ON cow_keypoint_annotation(package_id);
CREATE INDEX IF NOT EXISTS idx_inf_pkg ON cow_inference_result(package_id);

CREATE TABLE IF NOT EXISTS yolo_detection (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    package_id TEXT NOT NULL,
    manifest_blob_key TEXT NOT NULL,
    image_width INTEGER NOT NULL,
    image_height INTEGER NOT NULL,
    detections_json TEXT NOT NULL,
    source_label TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(package_id, manifest_blob_key)
);

CREATE INDEX IF NOT EXISTS idx_yolo_pkg ON yolo_detection(package_id);
"""


def project_db_root() -> Path:
    return Path(getattr(settings, "PROJECT_DB_ROOT", settings.BASE_DIR / "project_db"))


def db_path(project_id: str) -> Path:
    root = project_db_root() / project_id
    root.mkdir(parents=True, exist_ok=True)
    return root / "pipeline.sqlite3"


@contextmanager
def connect(project_id: str) -> Iterator[sqlite3.Connection]:
    path = db_path(project_id)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        ensure_schema(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA_SQL)
    row = conn.execute(
        "SELECT value FROM schema_meta WHERE key = 'version'",
    ).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO schema_meta(key, value) VALUES ('version', ?)",
            (str(_SCHEMA_VERSION),),
        )


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
        yolo = conn.execute(
            "SELECT 1 FROM yolo_detection WHERE package_id = ? LIMIT 1",
            (package_id,),
        ).fetchone()
        return yolo is not None


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
                image_width, image_height, detections_json, source_label
            ) VALUES (?, ?, ?, ?, ?, ?)
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
            ),
        )


def insert_gt(
    project_id: str,
    *,
    package_id: str,
    manifest_blob_key: str,
    cvat_link: str,
    image_size: dict[str, Any],
    annotation: dict[str, Any],
) -> None:
    with connect(project_id) as conn:
        conn.execute(
            """
            INSERT INTO cow_keypoint_annotation (
                package_id, manifest_blob_key, cvat_link,
                image_width, image_height, annotation_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(package_id, manifest_blob_key) DO UPDATE SET
                cvat_link = excluded.cvat_link,
                image_width = excluded.image_width,
                image_height = excluded.image_height,
                annotation_json = excluded.annotation_json
            """,
            (
                package_id,
                manifest_blob_key,
                cvat_link,
                int(image_size.get("width") or 0),
                int(image_size.get("height") or 0),
                json.dumps(annotation, ensure_ascii=False),
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
    depth_blob_key: str | None = None,
    depth_format: str = "npy",
    depth_unit: str = "m",
    depth_width: int | None = None,
    depth_height: int | None = None,
) -> None:
    with connect(project_id) as conn:
        conn.execute(
            """
            INSERT INTO cow_inference_result (
                package_id, manifest_blob_key, source_export,
                image_width, image_height, inference_json,
                depth_blob_key, depth_format, depth_unit,
                depth_width, depth_height
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(package_id, manifest_blob_key) DO UPDATE SET
                source_export = excluded.source_export,
                image_width = excluded.image_width,
                image_height = excluded.image_height,
                inference_json = excluded.inference_json,
                depth_blob_key = excluded.depth_blob_key,
                depth_format = excluded.depth_format,
                depth_unit = excluded.depth_unit,
                depth_width = excluded.depth_width,
                depth_height = excluded.depth_height
            """,
            (
                package_id,
                manifest_blob_key,
                source_export,
                int(image_size.get("width") or 0),
                int(image_size.get("height") or 0),
                json.dumps(inference, ensure_ascii=False),
                depth_blob_key,
                depth_format,
                depth_unit,
                depth_width,
                depth_height,
            ),
        )


def _row_to_gt(row: sqlite3.Row) -> dict[str, Any]:
    ann = json.loads(row["annotation_json"])
    return {
        "package_id": row["package_id"],
        "project_id": "",  # filled by caller
        "manifest_blob_key": row["manifest_blob_key"],
        "cvat_link": row["cvat_link"],
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
    depth_key = row["depth_blob_key"]
    if depth_key:
        dm: dict[str, Any] = {
            "format": row["depth_format"] or "npy",
            "unit": row["depth_unit"] or "m",
            "asset_path": depth_key,
            "depth_url": _depth_url(project_id, package_id, depth_key),
        }
        if row["depth_width"]:
            dm["width"] = row["depth_width"]
        if row["depth_height"]:
            dm["height"] = row["depth_height"]
        out["depth_map"] = dm
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
