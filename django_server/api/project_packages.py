"""Package sessions, blobs and changelog in per-project SQLite."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import quote

from django.utils import timezone

from . import project_db as pdb
from . import project_media as pm
from . import project_storage_config as psc


class Phase:
    AWAITING_BLOBS = "awaiting_blobs"
    READY_TO_COMMIT = "ready_to_commit"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PackageSession:
    package_id: str
    phase: str
    manifest_json: str
    failure_reason: str
    uploader_uid: str
    uploader_email: str
    created_at: str

    @property
    def manifest_dict(self) -> dict[str, Any] | None:
        raw = (self.manifest_json or "").strip()
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None


@dataclass
class UploadedBlob:
    id: int
    package_id: str
    logical_path: str
    size_bytes: int
    sha256: str
    storage_path: str
    created_at: str


@dataclass
class FieldChange:
    id: int
    package_id: str
    field_id: str
    before_value: Any
    after_value: Any
    reason: str
    verifier_email: str
    changed_at: str


def _now_iso() -> str:
    return timezone.now().isoformat()


def _parse_json_value(raw: str | None) -> Any:
    if raw is None or raw == "":
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _row_to_session(row: sqlite3.Row) -> PackageSession:
    return PackageSession(
        package_id=row["package_id"],
        phase=row["phase"],
        manifest_json=row["manifest_json"] or "",
        failure_reason=row["failure_reason"] or "",
        uploader_uid=row["uploader_uid"] or "",
        uploader_email=row["uploader_email"] or "",
        created_at=row["created_at"] or "",
    )


def _row_to_blob(row: sqlite3.Row) -> UploadedBlob:
    return UploadedBlob(
        id=int(row["id"]),
        package_id=row["package_id"],
        logical_path=row["logical_path"],
        size_bytes=int(row["size_bytes"] or 0),
        sha256=row["sha256"] or "",
        storage_path=row["storage_path"],
        created_at=row["created_at"] or "",
    )


def _row_to_change(row: sqlite3.Row) -> FieldChange:
    return FieldChange(
        id=int(row["id"]),
        package_id=row["package_id"],
        field_id=row["field_id"],
        before_value=_parse_json_value(row["before_value"]),
        after_value=_parse_json_value(row["after_value"]),
        reason=row["reason"] or "",
        verifier_email=row["verifier_email"] or "",
        changed_at=row["changed_at"] or "",
    )


def get_session(project_id: str, package_id: str) -> PackageSession | None:
    with pdb.connect(project_id) as conn:
        row = conn.execute(
            "SELECT * FROM package_session WHERE package_id = ?",
            (package_id,),
        ).fetchone()
    return _row_to_session(row) if row else None


def get_or_create_session(
    project_id: str,
    package_id: str,
    *,
    phase: str = Phase.AWAITING_BLOBS,
) -> tuple[PackageSession, bool]:
    with pdb.connect(project_id) as conn:
        row = conn.execute(
            "SELECT * FROM package_session WHERE package_id = ?",
            (package_id,),
        ).fetchone()
        if row:
            return _row_to_session(row), False
        now = _now_iso()
        conn.execute(
            """
            INSERT INTO package_session (
                package_id, phase, manifest_json, failure_reason,
                uploader_uid, uploader_email, created_at
            ) VALUES (?, ?, '', '', '', '', ?)
            """,
            (package_id, phase, now),
        )
        row = conn.execute(
            "SELECT * FROM package_session WHERE package_id = ?",
            (package_id,),
        ).fetchone()
        assert row is not None
        return _row_to_session(row), True


def update_uploader(
    project_id: str,
    package_id: str,
    *,
    uid: str,
    email: str,
) -> None:
    with pdb.connect(project_id) as conn:
        conn.execute(
            """
            UPDATE package_session
            SET uploader_uid = ?, uploader_email = ?
            WHERE package_id = ? AND (uploader_uid IS NULL OR uploader_uid = '')
            """,
            (uid, email, package_id),
        )


def list_sessions(
    project_id: str,
    *,
    phase: str = "",
    limit: int = 500,
) -> list[PackageSession]:
    with pdb.connect(project_id) as conn:
        if phase:
            rows = conn.execute(
                """
                SELECT * FROM package_session
                WHERE phase = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (phase, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM package_session
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return [_row_to_session(r) for r in rows]


def list_blobs(project_id: str, package_id: str) -> list[UploadedBlob]:
    with pdb.connect(project_id) as conn:
        rows = conn.execute(
            """
            SELECT * FROM uploaded_blob
            WHERE package_id = ?
            ORDER BY logical_path
            """,
            (package_id,),
        ).fetchall()
    return [_row_to_blob(r) for r in rows]


def list_blob_paths(project_id: str, package_id: str) -> list[str]:
    return [b.logical_path for b in list_blobs(project_id, package_id)]


def get_blob_by_id(project_id: str, package_id: str, blob_id: int) -> UploadedBlob | None:
    with pdb.connect(project_id) as conn:
        row = conn.execute(
            """
            SELECT * FROM uploaded_blob
            WHERE package_id = ? AND id = ?
            """,
            (package_id, blob_id),
        ).fetchone()
    return _row_to_blob(row) if row else None


def get_blob_by_path(project_id: str, package_id: str, logical_path: str) -> UploadedBlob | None:
    with pdb.connect(project_id) as conn:
        row = conn.execute(
            """
            SELECT * FROM uploaded_blob
            WHERE package_id = ? AND logical_path = ?
            """,
            (package_id, logical_path),
        ).fetchone()
    return _row_to_blob(row) if row else None


def put_blob(
    project_id: str,
    package_id: str,
    logical_path: str,
    data: bytes,
    *,
    media_bucket: str = "",
) -> UploadedBlob:
    logical = logical_path.replace("\\", "/")
    sha = hashlib.sha256(data).hexdigest()
    storage_path = pm.write_blob(
        project_id, package_id, logical, data, media_bucket=media_bucket,
    )
    now = _now_iso()
    with pdb.connect(project_id) as conn:
        old = conn.execute(
            """
            SELECT storage_path FROM uploaded_blob
            WHERE package_id = ? AND logical_path = ?
            """,
            (package_id, logical),
        ).fetchone()
        if old and old["storage_path"] != storage_path:
            pm.delete_blob_file(project_id, old["storage_path"], media_bucket=media_bucket)
        conn.execute(
            "DELETE FROM uploaded_blob WHERE package_id = ? AND logical_path = ?",
            (package_id, logical),
        )
        conn.execute(
            """
            INSERT INTO uploaded_blob (
                package_id, logical_path, size_bytes, sha256, storage_path, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (package_id, logical, len(data), sha, storage_path, now),
        )
        row = conn.execute(
            """
            SELECT * FROM uploaded_blob
            WHERE package_id = ? AND logical_path = ?
            """,
            (package_id, logical),
        ).fetchone()
        assert row is not None
        return _row_to_blob(row)


def reset_manifest_phase(project_id: str, package_id: str) -> None:
    with pdb.connect(project_id) as conn:
        conn.execute(
            """
            UPDATE package_session
            SET manifest_json = '', phase = ?
            WHERE package_id = ?
            """,
            (Phase.AWAITING_BLOBS, package_id),
        )


def save_manifest(project_id: str, package_id: str, manifest_json: str) -> None:
    with pdb.connect(project_id) as conn:
        conn.execute(
            """
            UPDATE package_session
            SET manifest_json = ?, phase = ?
            WHERE package_id = ?
            """,
            (manifest_json, Phase.READY_TO_COMMIT, package_id),
        )


def update_manifest(project_id: str, package_id: str, manifest_json: str) -> None:
    with pdb.connect(project_id) as conn:
        conn.execute(
            "UPDATE package_session SET manifest_json = ? WHERE package_id = ?",
            (manifest_json, package_id),
        )


def commit_session(project_id: str, package_id: str) -> bool:
    """Returns True if newly committed, False if already completed."""
    with pdb.connect(project_id) as conn:
        row = conn.execute(
            "SELECT phase, manifest_json FROM package_session WHERE package_id = ?",
            (package_id,),
        ).fetchone()
        if not row:
            raise LookupError("package_not_found")
        if row["phase"] == Phase.COMPLETED:
            return False
        if row["phase"] != Phase.READY_TO_COMMIT or not (row["manifest_json"] or "").strip():
            raise ValueError("not_ready_to_commit")
        conn.execute(
            "UPDATE package_session SET phase = ? WHERE package_id = ?",
            (Phase.COMPLETED, package_id),
        )
        return True


def delete_session(
    project_id: str,
    package_id: str,
    *,
    media_bucket: str = "",
    keep_pipeline: bool = False,
) -> bool:
    session = get_session(project_id, package_id)
    if not session:
        return False
    blobs = list_blobs(project_id, package_id)
    for blob in blobs:
        pm.delete_blob_file(project_id, blob.storage_path, media_bucket=media_bucket)
    pm.remove_package_media(project_id, package_id, media_bucket=media_bucket)
    if not keep_pipeline:
        pdb.delete_package_pipeline_data(project_id, package_id)
    with pdb.connect(project_id) as conn:
        conn.execute("DELETE FROM package_field_change WHERE package_id = ?", (package_id,))
        conn.execute("DELETE FROM uploaded_blob WHERE package_id = ?", (package_id,))
        conn.execute("DELETE FROM package_session WHERE package_id = ?", (package_id,))
    return True


def purge_all_packages(
    project_id: str,
    *,
    media_bucket: str = "",
    keep_pipeline: bool = True,
) -> int:
    """Удалить все package_session + blobs + media; pipeline-таблицы опционально сохранить."""
    sessions = list_sessions(project_id, limit=10000)
    removed = 0
    for session in sessions:
        if delete_session(
            project_id,
            session.package_id,
            media_bucket=media_bucket,
            keep_pipeline=keep_pipeline,
        ):
            removed += 1
    return removed


def blob_preview_url(
    project_id: str,
    package_id: str,
    logical_path: str,
    *,
    prefix: str,
) -> str:
    base = prefix.rstrip("/")
    encoded = quote(logical_path.replace("\\", "/"), safe="")
    return (
        f"{base}/projects/{project_id}/packages/{package_id}"
        f"/blobs/{encoded}/preview"
    )


def list_field_changes(
    project_id: str,
    *,
    package_id: str = "",
    limit: int = 500,
) -> list[FieldChange]:
    with pdb.connect(project_id) as conn:
        if package_id:
            rows = conn.execute(
                """
                SELECT * FROM package_field_change
                WHERE package_id = ?
                ORDER BY changed_at DESC
                LIMIT ?
                """,
                (package_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM package_field_change
                ORDER BY changed_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return [_row_to_change(r) for r in rows]


def append_field_changes(
    project_id: str,
    package_id: str,
    reason: str,
    verifier_email: str,
    changes: list[dict[str, Any]],
) -> int:
    now = _now_iso()
    rows = 0
    with pdb.connect(project_id) as conn:
        for change in changes:
            field_id = change.get("field_id")
            if not field_id:
                continue
            conn.execute(
                """
                INSERT INTO package_field_change (
                    package_id, field_id, before_value, after_value,
                    reason, verifier_email, changed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    package_id,
                    str(field_id),
                    json.dumps(change.get("before"), ensure_ascii=False),
                    json.dumps(change.get("after"), ensure_ascii=False),
                    reason,
                    verifier_email,
                    now,
                ),
            )
            rows += 1
    return rows


def remove_project_packages(
    project_id: str,
    *,
    media_bucket: str = "",
    config: psc.StorageConfig | None = None,
) -> None:
    cfg = config or psc.resolve_by_id(project_id)
    pm.remove_project_media(project_id, media_bucket=media_bucket, config=cfg)
    pdb.remove_project_db(project_id, database_uri=cfg.database_uri)
