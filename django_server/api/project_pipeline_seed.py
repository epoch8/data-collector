"""Dev-заглушки pipeline: datapipe_test → project SQLite + *_depth.npy в пакете.

Включается только при PROJECT_PIPELINE_MOCK_SEED=1 (см. maybe_seed_on_commit после commit).
Мобильное приложение depth не отправляет — файлы появляются только из этого сида.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.files.base import ContentFile
from . import project_db as pdb
from .models import PackageSession, UploadedBlob
from .packages_ui import datapipe_dir, is_image_path

logger = logging.getLogger(__name__)

_MOCK_GT = "mock_datapipe_annotations.json"
_MOCK_INF = "mock_datapipe_inference.json"


def _records_by_blob_key(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for r in records:
        key = r.get("manifest_blob_key")
        if isinstance(key, str) and key:
            out[key] = r
    return out


def mock_seed_enabled() -> bool:
    return getattr(settings, "PROJECT_PIPELINE_MOCK_SEED", True)


def _load_mock_records(filename: str) -> list[dict[str, Any]]:
    path = datapipe_dir() / filename
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    records = data.get("records") if isinstance(data, dict) else None
    return [r for r in records if isinstance(r, dict)] if isinstance(records, list) else []


def _template_gt_records() -> list[dict[str, Any]]:
    return _load_mock_records(_MOCK_GT)


def _template_inf_records() -> list[dict[str, Any]]:
    return _load_mock_records(_MOCK_INF)


def _depth_npy_path(template: dict[str, Any]) -> Path | None:
    dm = template.get("depth_map")
    if not isinstance(dm, dict):
        return None
    asset = (dm.get("asset_path") or "").strip()
    if not asset:
        return None
    name = Path(asset.replace("\\", "/")).name
    path = datapipe_dir() / name
    return path if path.is_file() else None


def _depth_logical_for_image(image_logical: str) -> str:
    p = Path(image_logical.replace("\\", "/"))
    stem = p.stem
    parent = p.parent.as_posix()
    name = f"{stem}_depth.npy"
    return f"{parent}/{name}" if parent and parent != "." else name


def _attach_depth_blob(
    session: PackageSession,
    *,
    image_logical: str,
    template: dict[str, Any],
) -> str | None:
    npy_path = _depth_npy_path(template)
    if npy_path is None:
        return None
    logical = _depth_logical_for_image(image_logical)
    if session.blobs.filter(logical_path=logical).exists():
        return logical
    data = npy_path.read_bytes()
    dm = template.get("depth_map") if isinstance(template.get("depth_map"), dict) else {}
    UploadedBlob.objects.create(
        session=session,
        logical_path=logical,
        size_bytes=len(data),
        file=ContentFile(data, name=Path(logical).name),
    )
    return logical


def seed_package_pipeline(
    session: PackageSession,
    *,
    force: bool = False,
) -> dict[str, int]:
    """
    Копирует шаблоны datapipe_test на кадры пакета (по порядку JPG/PNG).
    Возвращает счётчики {gt, inference, depth_blobs}.
    """
    project_id = session.project.project_id
    package_id = session.package_id
    if not force and pdb.package_has_pipeline_data(project_id, package_id):
        return {"gt": 0, "inference": 0, "depth_blobs": 0, "skipped": 1}

    gt_by_key = _records_by_blob_key(_template_gt_records())
    inf_by_key = _records_by_blob_key(_template_inf_records())
    if not gt_by_key and not inf_by_key:
        logger.warning("No datapipe_test mock templates for seed")
        return {"gt": 0, "inference": 0, "depth_blobs": 0, "skipped": 0}

    images = sorted(
        [b for b in session.blobs.all() if is_image_path(b.logical_path)],
        key=lambda b: b.logical_path,
    )
    if not images:
        return {"gt": 0, "inference": 0, "depth_blobs": 0, "skipped": 0}

    if force:
        pdb.delete_package_pipeline_data(project_id, package_id)
        session.blobs.filter(logical_path__endswith="_depth.npy").delete()

    gt_n = inf_n = depth_n = 0
    for blob in images:
        key = blob.logical_path

        gt_t = gt_by_key.get(key)
        if gt_t:
            ann = gt_t.get("annotation") if isinstance(gt_t.get("annotation"), dict) else {}
            pdb.insert_gt(
                project_id,
                package_id=package_id,
                manifest_blob_key=key,
                cvat_link=str(gt_t.get("cvat_link") or ""),
                image_size=gt_t.get("image_size") if isinstance(gt_t.get("image_size"), dict) else {},
                annotation=ann,
            )
            gt_n += 1

        inf_t = inf_by_key.get(key)
        if inf_t:
            inf_body = inf_t.get("inference") if isinstance(inf_t.get("inference"), dict) else {}
            dm = inf_t.get("depth_map") if isinstance(inf_t.get("depth_map"), dict) else {}
            depth_key = _attach_depth_blob(session, image_logical=key, template=inf_t)
            if depth_key:
                depth_n += 1
            pdb.insert_inference(
                project_id,
                package_id=package_id,
                manifest_blob_key=key,
                source_export=str(inf_t.get("source_export") or ""),
                image_size=inf_t.get("image_size") if isinstance(inf_t.get("image_size"), dict) else {},
                inference=inf_body,
                depth_blob_key=depth_key,
                depth_format=str(dm.get("format") or "npy"),
                depth_unit=str(dm.get("unit") or "m"),
                depth_width=int(dm["width"]) if dm.get("width") else None,
                depth_height=int(dm["height"]) if dm.get("height") else None,
            )
            inf_n += 1

    return {"gt": gt_n, "inference": inf_n, "depth_blobs": depth_n, "skipped": 0}


def maybe_seed_on_commit(session: PackageSession) -> None:
    if not mock_seed_enabled():
        return
    if session.phase != PackageSession.Phase.COMPLETED:
        return
    try:
        stats = seed_package_pipeline(session)
        if stats.get("gt") or stats.get("inference"):
            logger.info(
                "Pipeline mock seed %s/%s: %s",
                session.project.project_id,
                session.package_id,
                stats,
            )
    except Exception:
        logger.exception(
            "Pipeline mock seed failed for %s/%s",
            session.project.project_id,
            session.package_id,
        )
