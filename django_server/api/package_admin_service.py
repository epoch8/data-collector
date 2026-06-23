"""Shared package admin logic for /ui/api/v1 and Django views."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import unquote

from django.http import HttpResponseForbidden, JsonResponse

from . import project_media as pm
from . import project_packages as ppkg
from .models import Project
from .utils import collect_blob_refs, parse_json_body
from .views import _err


def _media_bucket(project: Project | None) -> str:
    return (project.media_bucket if project else "") or ""


def parse_manifest(session: ppkg.PackageSession) -> dict | None:
    return session.manifest_dict


def has_pipeline_flag(manifest: dict | None, key: str) -> bool:
    if not manifest:
        return False
    pr = manifest.get("pipeline_results")
    if not isinstance(pr, dict):
        return False
    return key in pr and pr[key] is not None


def searchable_field_ids(project: Project, cfg_root: dict | None = None) -> set[str]:
    if cfg_root is None:
        from .project_config_service import load_config_dict

        cfg_root, err = load_config_dict(project.project_id)
        if err or not cfg_root:
            return set()
    fields = (cfg_root.get("config") or {}).get("fields") or []
    ids: set[str] = set()
    for f in fields:
        if not isinstance(f, dict):
            continue
        fid = f.get("field_id")
        ftype = f.get("type")
        if isinstance(fid, str) and ftype in ("text_input", "datetime"):
            ids.add(fid)
    return ids


def data_fields_for_search(
    manifest: dict | None,
    field_ids: set[str],
) -> dict[str, str | int | float | bool | None]:
    if not manifest or not field_ids:
        return {}
    data = manifest.get("data")
    if not isinstance(data, dict):
        return {}
    out: dict[str, str | int | float | bool | None] = {}
    for fid in field_ids:
        v = data.get(fid)
        if v is None:
            out[fid] = None
        elif isinstance(v, (str, int, float, bool)):
            out[fid] = v
    return out


def list_projects(*, allowed: set[str] | None) -> list[dict[str, Any]]:
    qs = Project.objects.all().order_by("name")
    if allowed is not None:
        qs = qs.filter(project_id__in=allowed)
    return [
        {
            "project_id": p.project_id,
            "name": p.name,
            "config_version": p.config_version_label,
            "updated_at": p.updated_at.isoformat(),
        }
        for p in qs
    ]


def get_project_config(project_id: str) -> tuple[dict | None, JsonResponse | None]:
    from .project_config_service import load_config_dict

    return load_config_dict(project_id)


def list_package_summaries(
    project_id: str,
    *,
    phase: str = "",
    limit: int = 500,
) -> tuple[list[dict[str, Any]] | None, JsonResponse | None]:
    """Список пакетов без разбора manifest_json (сайдбар workspace)."""
    if not Project.objects.filter(project_id=project_id).exists():
        return None, JsonResponse(_err("not_found", "Unknown project"), status=404)

    sessions = ppkg.list_sessions(project_id, phase=phase, limit=limit)
    return [
        {
            "package_id": s.package_id,
            "project_id": project_id,
            "phase": s.phase,
            "created_at": s.created_at,
            "uploader_email": s.uploader_email or "",
        }
        for s in sessions
    ], None


def list_packages(
    project_id: str,
    *,
    phase: str,
    preview_prefix: str,
    search_field_ids: set[str] | None = None,
) -> tuple[list[dict[str, Any]] | None, JsonResponse | None]:
    project = Project.objects.filter(project_id=project_id).first()
    if not project:
        return None, JsonResponse(_err("not_found", "Unknown project"), status=404)

    searchable = (
        search_field_ids
        if search_field_ids is not None
        else searchable_field_ids(project)
    )
    sessions = ppkg.list_sessions(project_id, phase=phase, limit=500)

    items = []
    for s in sessions:
        manifest = parse_manifest(s)
        items.append(
            {
                "package_id": s.package_id,
                "project_id": project_id,
                "phase": s.phase,
                "created_at": s.created_at,
                "uploader_email": s.uploader_email or "",
                "has_inference": has_pipeline_flag(manifest, "inference"),
                "has_cvat": has_pipeline_flag(manifest, "cvat"),
                "data_fields": data_fields_for_search(manifest, searchable),
            },
        )
    return items, None


def get_workspace(
    project_id: str,
    package_id: str,
    *,
    preview_prefix: str,
) -> tuple[dict[str, Any] | None, JsonResponse | None]:
    project = Project.objects.filter(project_id=project_id).first()
    if not project:
        return None, JsonResponse(_err("not_found", "Unknown project"), status=404)

    session = ppkg.get_session(project_id, package_id)
    if not session:
        return None, JsonResponse(_err("not_found", "Package not found"), status=404)

    manifest = parse_manifest(session)
    if manifest is None:
        return None, JsonResponse(_err("not_found", "Manifest not loaded"), status=404)

    project_config, cfg_err = get_project_config(project_id)
    if cfg_err is not None:
        return None, cfg_err
    if project_config is None:
        return None, JsonResponse(_err("invalid_config", "Project config unavailable"), status=500)

    blobs = [
        {
            "blob_id": b.id,
            "logical_path": b.logical_path,
            "size_bytes": b.size_bytes,
            "preview_url": ppkg.blob_preview_url(
                project_id, package_id, b.logical_path, prefix=preview_prefix,
            ),
        }
        for b in ppkg.list_blobs(project_id, package_id)
    ]

    return {
        "session": {
            "package_id": session.package_id,
            "project_id": project_id,
            "phase": session.phase,
            "created_at": session.created_at,
            "uploader_email": session.uploader_email or "",
            "has_inference": has_pipeline_flag(manifest, "inference"),
            "has_cvat": has_pipeline_flag(manifest, "cvat"),
        },
        "manifest": manifest,
        "blobs": blobs,
        "project_config": project_config,
    }, None


def patch_manifest(
    project_id: str,
    package_id: str,
    raw_body: str,
) -> JsonResponse | None:
    session = ppkg.get_session(project_id, package_id)
    if not session:
        return JsonResponse(_err("not_found", "Package not found"), status=404)

    if session.phase != ppkg.Phase.COMPLETED:
        return JsonResponse(
            _err("invalid_phase", "Only completed packages can be edited from admin"),
            status=409,
        )

    manifest, err = parse_json_body(raw_body)
    if err:
        return JsonResponse(_err("invalid_json", "Manifest must be JSON object"), status=400)
    assert manifest is not None

    url_pid = manifest.get("project_id")
    if url_pid != project_id:
        return JsonResponse(
            _err(
                "project_id_mismatch",
                "Manifest project_id must match URL",
                {"expected": project_id, "actual": url_pid},
            ),
            status=422,
        )

    refs: set[str] = set()
    collect_blob_refs(manifest, refs)
    uploaded = set(ppkg.list_blob_paths(project_id, package_id))
    missing = sorted(refs - uploaded)
    if missing:
        return JsonResponse(
            _err("missing_blobs", "Manifest references blobs not in package", missing),
            status=422,
        )

    existing = parse_manifest(session) or {}
    submitted_by = existing.get("submitted_by")
    if isinstance(submitted_by, dict):
        manifest["submitted_by"] = submitted_by

    manifest_json = json.dumps(
        manifest,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    ppkg.update_manifest(project_id, package_id, manifest_json)
    return JsonResponse({"ok": True, "package_id": package_id})


def blob_preview_response(
    project_id: str,
    package_id: str,
    logical_path: str,
) -> JsonResponse | HttpResponseForbidden:
    logical = unquote((logical_path or "").replace("\\", "/"))
    project = Project.objects.filter(project_id=project_id).first()
    bucket = _media_bucket(project)
    blob = ppkg.get_blob_by_path(project_id, package_id, logical)
    if not blob:
        return JsonResponse(_err("not_found", "Blob not found"), status=404)
    resp = pm.blob_file_response(
        project_id,
        blob.storage_path,
        blob.logical_path,
        media_bucket=bucket,
    )
    if resp is None:
        return HttpResponseForbidden("No file")
    return resp
