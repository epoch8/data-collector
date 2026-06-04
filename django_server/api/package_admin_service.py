"""Shared package admin logic for /ui/api/v1 and Django views."""

from __future__ import annotations

import json
import mimetypes
from pathlib import Path
from typing import Any

from django.http import FileResponse, HttpResponseForbidden, JsonResponse

from .models import PackageSession, Project, UploadedBlob
from .utils import collect_blob_refs, parse_json_body
from .views import _err


def blob_preview_url(project_id: str, package_id: str, blob_pk: int, *, prefix: str) -> str:
    base = prefix.rstrip("/")
    return (
        f"{base}/projects/{project_id}/packages/{package_id}"
        f"/blobs/{blob_pk}/preview"
    )


def parse_manifest(session: PackageSession) -> dict | None:
    raw = (session.manifest_json or "").strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


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

    qs = PackageSession.objects.filter(project__project_id=project_id).order_by("-created_at")
    if phase:
        qs = qs.filter(phase=phase)
    return [
        {
            "package_id": s.package_id,
            "project_id": project_id,
            "phase": s.phase,
            "created_at": s.created_at.isoformat(),
            "uploader_email": s.uploader_email or "",
        }
        for s in qs[:limit]
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
    qs = PackageSession.objects.filter(project__project_id=project_id).order_by("-created_at")
    if phase:
        qs = qs.filter(phase=phase)
    qs = qs[:500]

    items = []
    for s in qs:
        manifest = parse_manifest(s)
        items.append(
            {
                "package_id": s.package_id,
                "project_id": project_id,
                "phase": s.phase,
                "created_at": s.created_at.isoformat(),
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

    session = PackageSession.objects.filter(
        project__project_id=project_id,
        package_id=package_id,
    ).first()
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
            "blob_id": b.pk,
            "logical_path": b.logical_path,
            "size_bytes": b.size_bytes,
            "preview_url": blob_preview_url(project_id, package_id, b.pk, prefix=preview_prefix),
        }
        for b in session.blobs.all().order_by("logical_path")
    ]

    return {
        "session": {
            "package_id": session.package_id,
            "project_id": project_id,
            "phase": session.phase,
            "created_at": session.created_at.isoformat(),
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
    session = PackageSession.objects.filter(
        project__project_id=project_id,
        package_id=package_id,
    ).first()
    if not session:
        return JsonResponse(_err("not_found", "Package not found"), status=404)

    if session.phase != PackageSession.Phase.COMPLETED:
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
    uploaded = set(session.blobs.values_list("logical_path", flat=True))
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

    session.manifest_json = json.dumps(
        manifest,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    session.save(update_fields=["manifest_json"])
    return JsonResponse({"ok": True, "package_id": package_id})


def blob_preview_response(
    project_id: str,
    package_id: str,
    blob_pk: int,
) -> FileResponse | JsonResponse | HttpResponseForbidden:
    blob = UploadedBlob.objects.filter(
        pk=blob_pk,
        session__project__project_id=project_id,
        session__package_id=package_id,
    ).first()
    if not blob:
        return JsonResponse(_err("not_found", "Blob not found"), status=404)
    if not blob.file:
        return HttpResponseForbidden("No file")
    ctype, _ = mimetypes.guess_type(blob.logical_path)
    resp = FileResponse(blob.file.open("rb"), content_type=ctype or "application/octet-stream")
    resp["Content-Disposition"] = f'inline; filename="{Path(blob.logical_path).name}"'
    return resp
