from __future__ import annotations

import json
import mimetypes

from django.http import FileResponse, HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .models import Project
from . import project_packages as ppkg
from .request_auth import forbid_if_no_project_access, project_ids_for_request
from .utils import collect_blob_refs, parse_json_body, validate_blob_logical_path, weak_etag


def _require_project(request, project_id: str) -> JsonResponse | None:
    return forbid_if_no_project_access(request, project_id, scope="mobile")


def _media_bucket(project_id: str) -> str:
    project = Project.objects.filter(project_id=project_id).only("media_bucket").first()
    return (project.media_bucket if project else "") or ""


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
                "config_version": p.config_version_label,
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
        from .project_config_service import load_config_body

        body, sha, err = load_config_body(project_id)
        if err is not None:
            return err
        etag = sha or weak_etag(body or "")
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
        if not Project.objects.filter(project_id=project_id).exists():
            return JsonResponse(_err("not_found", "Unknown project"), status=404)
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
        session, created = ppkg.get_or_create_session(project_id, package_id)
        uid = getattr(request, "firebase_uid", None) or ""
        email = getattr(request, "firebase_email", None) or ""
        if uid and not session.uploader_uid:
            ppkg.update_uploader(project_id, package_id, uid=uid, email=email)
            session = ppkg.get_session(project_id, package_id) or session
        if session.phase == ppkg.Phase.COMPLETED:
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


def _session_status(session: ppkg.PackageSession) -> str:
    return session.phase


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
        session = ppkg.get_session(project_id, package_id)
        if not session:
            return JsonResponse(_err("not_found", "Start package session first"), status=404)
        if session.phase == ppkg.Phase.COMPLETED:
            return JsonResponse(_err("conflict", "Package already completed"), status=409)
        if session.phase == ppkg.Phase.FAILED:
            return JsonResponse(_err("conflict", "Package session failed"), status=409)
        if session.phase == ppkg.Phase.READY_TO_COMMIT:
            ppkg.reset_manifest_phase(project_id, package_id)
        data = request.body or b""
        ppkg.put_blob(
            project_id,
            package_id,
            logical,
            data,
            media_bucket=_media_bucket(project_id),
        )
        return JsonResponse({"path": logical, "size": len(data)})


@method_decorator(csrf_exempt, name="dispatch")
class PackageManifestPutView(View):
    def put(self, request, project_id: str, package_id: str):
        denied = _require_project(request, project_id)
        if denied:
            return denied
        session = ppkg.get_session(project_id, package_id)
        if not session:
            return JsonResponse(_err("not_found", "Start package session first"), status=404)
        if session.phase == ppkg.Phase.COMPLETED:
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
        uploaded = set(ppkg.list_blob_paths(project_id, package_id))
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
        manifest_json = json.dumps(
            manifest,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        ppkg.save_manifest(project_id, package_id, manifest_json)
        return JsonResponse({"status": "ready_to_commit", "package_id": package_id})


@method_decorator(csrf_exempt, name="dispatch")
class PackageCommitView(View):
    def post(self, request, project_id: str, package_id: str):
        denied = _require_project(request, project_id)
        if denied:
            return denied
        session = ppkg.get_session(project_id, package_id)
        if not session:
            return JsonResponse(_err("not_found", "Package not found"), status=404)
        try:
            committed = ppkg.commit_session(project_id, package_id)
        except ValueError:
            return JsonResponse(
                _err("invalid_phase", "Manifest not accepted; call PUT manifest first"),
                status=409,
            )
        if not committed:
            return JsonResponse(
                {
                    "status": "completed",
                    "package_id": package_id,
                    "idempotent": True,
                },
                status=200,
            )
        # Первый успешный commit — дёргаем настроенную в config.on_commit ручку.
        # Best-effort: ошибки логируются внутри и не влияют на ответ клиенту.
        from .package_callback_service import dispatch_on_commit

        dispatch_on_commit(project_id, package_id)
        return JsonResponse({"status": "completed", "package_id": package_id})


@method_decorator(csrf_exempt, name="dispatch")
class PackageDetailView(View):
    """GET статус; DELETE отмена черновика (спека 08 §11.5–11.6)."""

    def get(self, request, project_id: str, package_id: str):
        denied = _require_project(request, project_id)
        if denied:
            return denied
        session = ppkg.get_session(project_id, package_id)
        if not session:
            return JsonResponse(_err("not_found", "Package not found"), status=404)
        blobs = sorted(ppkg.list_blob_paths(project_id, package_id))
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
        session = ppkg.get_session(project_id, package_id)
        if not session:
            return JsonResponse(_err("not_found", "Package not found"), status=404)
        if session.phase == ppkg.Phase.COMPLETED:
            return JsonResponse(_err("conflict", "Cannot delete completed package"), status=409)
        ppkg.delete_session(project_id, package_id, media_bucket=_media_bucket(project_id))
        return HttpResponse(status=204)


@method_decorator(csrf_exempt, name="dispatch")
class ProjectAssetGetView(View):
    """GET медиа инструкций: `collector/media/…` в git-кэше проекта."""

    def get(self, request, project_id: str, asset_path: str):
        denied = _require_project(request, project_id)
        if denied:
            return denied
        from .project_git import resolve_media_file

        target = resolve_media_file(project_id, asset_path)
        if target is None:
            return JsonResponse(_err("not_found", "Asset not found"), status=404)
        ctype, _ = mimetypes.guess_type(str(target))
        return FileResponse(
            open(target, "rb"),
            content_type=ctype or "application/octet-stream",
        )
