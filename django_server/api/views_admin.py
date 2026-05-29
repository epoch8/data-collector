"""SPA API для client-admin: та же Firebase-авторизация и доступ к проектам, что и /v1/*."""

from __future__ import annotations

import json
import mimetypes
from pathlib import Path

from django.http import FileResponse, HttpResponseForbidden, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .models import PackageSession, Project, UploadedBlob
from .request_auth import forbid_if_no_project_access, project_ids_for_request
from .utils import collect_blob_refs, parse_json_body
from .views import _err


def _blob_preview_url(project_id: str, package_id: str, blob_pk: int) -> str:
    return (
        f"/admin-api/v1/projects/{project_id}/packages/{package_id}"
        f"/blobs/{blob_pk}/preview"
    )


def _parse_manifest(session: PackageSession) -> dict | None:
    raw = (session.manifest_json or "").strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _has_pipeline_flag(manifest: dict | None, key: str) -> bool:
    if not manifest:
        return False
    pr = manifest.get("pipeline_results")
    if not isinstance(pr, dict):
        return False
    return key in pr and pr[key] is not None


def _searchable_field_ids(project: Project) -> set[str]:
    try:
        cfg_root = json.loads(project.raw_json)
    except json.JSONDecodeError:
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


def _data_fields_for_search(manifest: dict | None, field_ids: set[str]) -> dict[str, str | int | float | bool | None]:
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


@method_decorator(csrf_exempt, name="dispatch")
class AdminProjectsListView(View):
    def get(self, request):
        qs = Project.objects.all().order_by("name")
        allowed = project_ids_for_request(request)
        if allowed is not None:
            qs = qs.filter(project_id__in=allowed)
        rows = list(qs)
        items = [
            {
                "project_id": p.project_id,
                "name": p.name,
                "config_version": p.config_version,
                "updated_at": p.updated_at.isoformat(),
            }
            for p in rows
        ]
        return JsonResponse({"projects": items})


@method_decorator(csrf_exempt, name="dispatch")
class AdminProjectConfigView(View):
    def get(self, request, project_id: str):
        denied = forbid_if_no_project_access(request, project_id)
        if denied is not None:
            return denied
        project = Project.objects.filter(project_id=project_id).first()
        if not project:
            return JsonResponse(_err("not_found", "Unknown project"), status=404)
        try:
            body = json.loads(project.raw_json)
        except json.JSONDecodeError:
            return JsonResponse(_err("invalid_config", "Project config is not valid JSON"), status=500)
        return JsonResponse(body)


@method_decorator(csrf_exempt, name="dispatch")
class AdminPackageListView(View):
    def get(self, request, project_id: str):
        denied = forbid_if_no_project_access(request, project_id)
        if denied is not None:
            return denied
        project = Project.objects.filter(project_id=project_id).first()
        if not project:
            return JsonResponse(_err("not_found", "Unknown project"), status=404)

        searchable = _searchable_field_ids(project)
        qs = PackageSession.objects.filter(project__project_id=project_id).order_by("-created_at")
        phase = (request.GET.get("phase") or "").strip()
        if phase:
            qs = qs.filter(phase=phase)
        qs = qs[:500]

        items = []
        for s in qs:
            manifest = _parse_manifest(s)
            items.append(
                {
                    "package_id": s.package_id,
                    "project_id": project_id,
                    "phase": s.phase,
                    "created_at": s.created_at.isoformat(),
                    "uploader_email": s.uploader_email or "",
                    "has_inference": _has_pipeline_flag(manifest, "inference"),
                    "has_cvat": _has_pipeline_flag(manifest, "cvat"),
                    "data_fields": _data_fields_for_search(manifest, searchable),
                },
            )
        return JsonResponse(items, safe=False)


@method_decorator(csrf_exempt, name="dispatch")
class AdminPackageWorkspaceView(View):
    def get(self, request, project_id: str, package_id: str):
        denied = forbid_if_no_project_access(request, project_id)
        if denied is not None:
            return denied
        project = Project.objects.filter(project_id=project_id).first()
        if not project:
            return JsonResponse(_err("not_found", "Unknown project"), status=404)

        session = PackageSession.objects.filter(
            project__project_id=project_id,
            package_id=package_id,
        ).first()
        if not session:
            return JsonResponse(_err("not_found", "Package not found"), status=404)

        manifest = _parse_manifest(session)
        if manifest is None:
            return JsonResponse(_err("not_found", "Manifest not loaded"), status=404)

        try:
            project_config = json.loads(project.raw_json)
        except json.JSONDecodeError:
            return JsonResponse(_err("invalid_config", "Project config is not valid JSON"), status=500)

        blobs_qs = session.blobs.all().order_by("logical_path")
        blobs = [
            {
                "blob_id": b.pk,
                "logical_path": b.logical_path,
                "size_bytes": b.size_bytes,
                "preview_url": _blob_preview_url(project_id, package_id, b.pk),
            }
            for b in blobs_qs
        ]

        return JsonResponse(
            {
                "session": {
                    "package_id": session.package_id,
                    "project_id": project_id,
                    "phase": session.phase,
                    "created_at": session.created_at.isoformat(),
                    "uploader_email": session.uploader_email or "",
                    "has_inference": _has_pipeline_flag(manifest, "inference"),
                    "has_cvat": _has_pipeline_flag(manifest, "cvat"),
                },
                "manifest": manifest,
                "blobs": blobs,
                "project_config": project_config,
            },
        )


@method_decorator(csrf_exempt, name="dispatch")
class AdminPackageManifestPatchView(View):
    def patch(self, request, project_id: str, package_id: str):
        denied = forbid_if_no_project_access(request, project_id)
        if denied is not None:
            return denied
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

        raw = request.body.decode("utf-8") if request.body else ""
        manifest, err = parse_json_body(raw)
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

        existing = _parse_manifest(session) or {}
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


@method_decorator(csrf_exempt, name="dispatch")
class AdminBlobPreviewView(View):
    def get(self, request, project_id: str, package_id: str, blob_pk: int):
        denied = forbid_if_no_project_access(request, project_id)
        if denied is not None:
            return denied
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
