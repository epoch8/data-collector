from __future__ import annotations

import json
import mimetypes
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.http import FileResponse, HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .models import PackageSession, Project, UploadedBlob
from .request_auth import forbid_if_no_project_access, project_ids_for_request
from .utils import collect_blob_refs, parse_json_body, validate_blob_logical_path, weak_etag


def _require_project(request, project_id: str) -> JsonResponse | None:
    return forbid_if_no_project_access(request, project_id, scope="mobile")


def _err(code: str, message: str, details=None):
    body = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return body


def health(_request):
    return HttpResponse("ok", content_type="text/plain")


@method_decorator(csrf_exempt, name="dispatch")
class ProjectsCatalogView(View):
    def get(self, request):
        qs = Project.objects.all().order_by("name")
        allowed = project_ids_for_request(request, scope="mobile")
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
        body = json.dumps({"projects": items}, separators=(",", ":"))
        etag = weak_etag(body)
        if request.headers.get("If-None-Match") == etag:
            return HttpResponse(status=304, headers={"ETag": etag})
        return HttpResponse(
            body,
            content_type="application/json; charset=utf-8",
            headers={"ETag": etag},
        )


@method_decorator(csrf_exempt, name="dispatch")
class ProjectConfigView(View):
    def get(self, request, project_id: str):
        denied = _require_project(request, project_id)
        if denied:
            return denied
        project = Project.objects.filter(project_id=project_id).first()
        if not project:
            return JsonResponse(
                _err("not_found", "Unknown project"),
                status=404,
            )
        body = project.raw_json
        etag = weak_etag(body)
        if request.headers.get("If-None-Match") == etag:
            return HttpResponse(status=304, headers={"ETag": etag})
        return HttpResponse(
            body,
            content_type="application/json; charset=utf-8",
            headers={"ETag": etag},
        )


@method_decorator(csrf_exempt, name="dispatch")
class PackageSessionCreateView(View):
    def post(self, request, project_id: str):
        denied = _require_project(request, project_id)
        if denied:
            return denied
        raw = request.body.decode("utf-8") if request.body else "{}"
        data, err = parse_json_body(raw)
        if err:
            return JsonResponse(_err("invalid_json", "Body must be JSON object"), status=400)
        package_id = (data or {}).get("package_id")
        if not package_id or not isinstance(package_id, str):
            return JsonResponse(
                _err("validation", "package_id required"),
                status=422,
            )
        project = Project.objects.get(project_id=project_id)
        session, created = PackageSession.objects.get_or_create(
            project=project,
            package_id=package_id,
            defaults={"phase": PackageSession.Phase.AWAITING_BLOBS},
        )
        uid = getattr(request, "firebase_uid", None) or ""
        email = getattr(request, "firebase_email", None) or ""
        if uid and not session.uploader_uid:
            session.uploader_uid = uid
            session.uploader_email = email
            session.save(update_fields=["uploader_uid", "uploader_email"])
        if session.phase == PackageSession.Phase.COMPLETED:
            return JsonResponse(
                _err(
                    "conflict",
                    "Package already completed",
                    {"package_id": package_id},
                ),
                status=409,
            )
        status = _session_status(session)
        return JsonResponse(
            {"package_id": package_id, "status": status},
            status=201 if created else 200,
        )


def _session_status(session: PackageSession) -> str:
    return {
        PackageSession.Phase.AWAITING_BLOBS: "awaiting_blobs",
        PackageSession.Phase.READY_TO_COMMIT: "ready_to_commit",
        PackageSession.Phase.COMPLETED: "completed",
        PackageSession.Phase.FAILED: "failed",
    }[session.phase]


@method_decorator(csrf_exempt, name="dispatch")
class PackageBlobPutView(View):
    def put(self, request, project_id: str, package_id: str, blob_path: str):
        denied = _require_project(request, project_id)
        if denied:
            return denied
        logical = blob_path.replace("\\", "/")
        if "%" in logical:
            from urllib.parse import unquote

            logical = unquote(logical)
        verr = validate_blob_logical_path(logical)
        if verr:
            return JsonResponse(
                _err("invalid_blob_path", verr, logical),
                status=422,
            )
        session = PackageSession.objects.filter(
            project__project_id=project_id,
            package_id=package_id,
        ).first()
        if not session:
            return JsonResponse(_err("not_found", "Start package session first"), status=404)
        if session.phase == PackageSession.Phase.COMPLETED:
            return JsonResponse(_err("conflict", "Package already completed"), status=409)
        if session.phase == PackageSession.Phase.FAILED:
            return JsonResponse(_err("conflict", "Package session failed"), status=409)
        if session.phase == PackageSession.Phase.READY_TO_COMMIT:
            session.manifest_json = ""
            session.phase = PackageSession.Phase.AWAITING_BLOBS
            session.save(update_fields=["manifest_json", "phase"])
        data = request.body or b""
        size = len(data)
        UploadedBlob.objects.filter(session=session, logical_path=logical).delete()
        blob = UploadedBlob(session=session, logical_path=logical, size_bytes=size)
        blob.file.save("body.bin", ContentFile(data), save=True)
        if session.phase != PackageSession.Phase.READY_TO_COMMIT:
            session.phase = PackageSession.Phase.AWAITING_BLOBS
            session.save(update_fields=["phase"])
        return JsonResponse({"path": logical, "size": size})


@method_decorator(csrf_exempt, name="dispatch")
class PackageManifestPutView(View):
    def put(self, request, project_id: str, package_id: str):
        denied = _require_project(request, project_id)
        if denied:
            return denied
        session = PackageSession.objects.filter(
            project__project_id=project_id,
            package_id=package_id,
        ).first()
        if not session:
            return JsonResponse(_err("not_found", "Start package session first"), status=404)
        if session.phase == PackageSession.Phase.COMPLETED:
            return JsonResponse(
                {"status": "completed", "package_id": package_id},
                status=200,
            )
        raw = request.body.decode("utf-8") if request.body else ""
        manifest, err = parse_json_body(raw)
        if err:
            return JsonResponse(_err("invalid_json", "Manifest must be JSON"), status=400)
        assert manifest is not None
        url_pid = manifest.get("project_id")
        if not url_pid:
            return JsonResponse(
                _err(
                    "validation",
                    "project_id required in manifest",
                    {"field": "project_id"},
                ),
                status=422,
            )
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
                _err("missing_blobs", "Manifest references blobs not uploaded yet", missing),
                status=422,
            )
        uid = getattr(request, "firebase_uid", None) or ""
        email = getattr(request, "firebase_email", None) or ""
        if uid:
            manifest["submitted_by"] = {
                "firebase_uid": uid,
                "email": email,
            }
        session.manifest_json = json.dumps(
            manifest,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        session.phase = PackageSession.Phase.READY_TO_COMMIT
        session.save(update_fields=["manifest_json", "phase"])
        return JsonResponse({"status": "ready_to_commit", "package_id": package_id})


@method_decorator(csrf_exempt, name="dispatch")
class PackageCommitView(View):
    def post(self, request, project_id: str, package_id: str):
        denied = _require_project(request, project_id)
        if denied:
            return denied
        session = PackageSession.objects.filter(
            project__project_id=project_id,
            package_id=package_id,
        ).first()
        if not session:
            return JsonResponse(_err("not_found", "Package not found"), status=404)
        with transaction.atomic():
            session = PackageSession.objects.select_for_update().get(pk=session.pk)
            if session.phase == PackageSession.Phase.COMPLETED:
                return JsonResponse(
                    {
                        "status": "completed",
                        "package_id": package_id,
                        "idempotent": True,
                    },
                    status=200,
                )
            if session.phase != PackageSession.Phase.READY_TO_COMMIT or not session.manifest_json:
                return JsonResponse(
                    _err("invalid_phase", "Manifest not accepted; call PUT manifest first"),
                    status=409,
                )
            session.phase = PackageSession.Phase.COMPLETED
            session.save(update_fields=["phase"])
        return JsonResponse({"status": "completed", "package_id": package_id})


@method_decorator(csrf_exempt, name="dispatch")
class PackageDetailView(View):
    """GET статус; DELETE отмена черновика (спека 08 §11.5–11.6)."""

    def get(self, request, project_id: str, package_id: str):
        denied = _require_project(request, project_id)
        if denied:
            return denied
        session = PackageSession.objects.filter(
            project__project_id=project_id,
            package_id=package_id,
        ).first()
        if not session:
            return JsonResponse(_err("not_found", "Package not found"), status=404)
        blobs = sorted(session.blobs.values_list("logical_path", flat=True))
        return JsonResponse(
            {
                "package_id": package_id,
                "status": _session_status(session),
                "blobs": blobs,
            },
        )

    def delete(self, request, project_id: str, package_id: str):
        denied = _require_project(request, project_id)
        if denied:
            return denied
        session = PackageSession.objects.filter(
            project__project_id=project_id,
            package_id=package_id,
        ).first()
        if not session:
            return JsonResponse(_err("not_found", "Package not found"), status=404)
        if session.phase == PackageSession.Phase.COMPLETED:
            return JsonResponse(_err("conflict", "Cannot delete completed package"), status=409)
        session.delete()
        return HttpResponse(status=204)


@method_decorator(csrf_exempt, name="dispatch")
class ProjectAssetGetView(View):
    """GET файла примера для конфига: путь относительно `assets/<slug>/` на репо → project_assets/<project_id>/."""

    def get(self, request, project_id: str, asset_path: str):
        denied = _require_project(request, project_id)
        if denied:
            return denied
        rel = (asset_path or "").replace("\\", "/").strip("/")
        if not rel or ".." in Path(rel).parts:
            return JsonResponse(_err("invalid_path", rel), status=422)
        base = Path(settings.PROJECT_ASSETS_ROOT) / project_id
        target = (base / rel).resolve()
        base_res = base.resolve()
        try:
            target.relative_to(base_res)
        except ValueError:
            return JsonResponse(_err("invalid_path", rel), status=422)
        if not target.is_file():
            return JsonResponse(_err("not_found", "Asset not found"), status=404)
        ctype, _ = mimetypes.guess_type(str(target))
        return FileResponse(
            open(target, "rb"),
            content_type=ctype or "application/octet-stream",
        )
