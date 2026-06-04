"""Session JSON API for embedded packages SPA (/ui/api/v1)."""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie

from . import package_admin_service as pas
from .ui_request_auth import (
    allowed_project_ids_for_request,
    ui_api_forbid_if_no_project,
    ui_api_forbid_if_unauthenticated,
    ui_api_principal,
)

UI_API_PREFIX = "/ui/api/v1"
PREVIEW_PREFIX = UI_API_PREFIX


@method_decorator(ensure_csrf_cookie, name="dispatch")
class UiMeView(View):
    def get(self, request):
        denied = ui_api_forbid_if_unauthenticated(request)
        if denied is not None:
            return denied
        principal = ui_api_principal(request)
        assert principal is not None
        role, email, allowed = principal
        username = request.user.username if request.user.is_authenticated else email
        return JsonResponse(
            {
                "role": role,
                "email": email,
                "username": username,
                "project_ids": None if allowed is None else sorted(allowed),
            },
        )


class UiProjectsListView(View):
    def get(self, request):
        denied = ui_api_forbid_if_unauthenticated(request)
        if denied is not None:
            return denied
        items = pas.list_projects(allowed=allowed_project_ids_for_request(request))
        return JsonResponse({"projects": items})


class UiProjectConfigView(View):
    def get(self, request, project_id: str):
        denied = ui_api_forbid_if_no_project(request, project_id)
        if denied is not None:
            return denied
        body, err = pas.get_project_config(project_id)
        if err is not None:
            return err
        return JsonResponse(body)


class UiPackageListView(View):
    def get(self, request, project_id: str):
        denied = ui_api_forbid_if_no_project(request, project_id)
        if denied is not None:
            return denied
        phase = (request.GET.get("phase") or "").strip()
        items, err = pas.list_packages(project_id, phase=phase, preview_prefix=PREVIEW_PREFIX)
        if err is not None:
            return err
        return JsonResponse(items, safe=False)


class UiPackageWorkspaceView(View):
    def get(self, request, project_id: str, package_id: str):
        denied = ui_api_forbid_if_no_project(request, project_id)
        if denied is not None:
            return denied
        body, err = pas.get_workspace(
            project_id,
            package_id,
            preview_prefix=PREVIEW_PREFIX,
        )
        if err is not None:
            return err
        return JsonResponse(body)


class UiPackageManifestPatchView(View):
    def patch(self, request, project_id: str, package_id: str):
        denied = ui_api_forbid_if_no_project(request, project_id)
        if denied is not None:
            return denied
        raw = request.body.decode("utf-8") if request.body else ""
        return pas.patch_manifest(project_id, package_id, raw)


class UiBlobPreviewView(View):
    def get(self, request, project_id: str, package_id: str, blob_pk: int):
        denied = ui_api_forbid_if_no_project(request, project_id)
        if denied is not None:
            return denied
        return pas.blob_preview_response(project_id, package_id, blob_pk)


def _changelog_path() -> Path:
    return Path(settings.BASE_DIR).parent / "datapipe_test" / "field_changelog.json"


class UiFieldChangelogView(View):
    def get(self, request):
        denied = ui_api_forbid_if_unauthenticated(request)
        if denied is not None:
            return denied
        package_id = (request.GET.get("package_id") or "").strip()
        project_id = (request.GET.get("project_id") or "").strip()
        path = _changelog_path()
        if not path.is_file():
            return JsonResponse({"entries": []})
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"entries": []})
        if not isinstance(data, list):
            return JsonResponse({"entries": []})
        filtered = []
        for item in data:
            if not isinstance(item, dict):
                continue
            if package_id and item.get("package_id") != package_id:
                continue
            if project_id and item.get("project_id") != project_id:
                continue
            if project_id:
                denied_p = ui_api_forbid_if_no_project(request, project_id)
                if denied_p is not None:
                    return denied_p
            filtered.append(item)
        return JsonResponse({"entries": filtered})

    def post(self, request):
        denied = ui_api_forbid_if_unauthenticated(request)
        if denied is not None:
            return denied
        try:
            body = json.loads(request.body.decode("utf-8") if request.body else "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "invalid_payload"}, status=400)
        reason = (body.get("reason") or "").strip()
        project_id = (body.get("project_id") or "").strip()
        package_id = (body.get("package_id") or "").strip()
        changes = body.get("changes")
        if not reason or not project_id or not package_id or not isinstance(changes, list) or not changes:
            return JsonResponse({"error": "invalid_payload"}, status=400)
        denied_p = ui_api_forbid_if_no_project(request, project_id)
        if denied_p is not None:
            return denied_p
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        verifier = (body.get("verifier_email") or request.user.email or "").strip()
        normalized = []
        for change in changes:
            if not isinstance(change, dict):
                continue
            fid = (change.get("field_id") or "").strip()
            if not fid:
                continue
            normalized.append(
                {
                    "project_id": project_id,
                    "package_id": package_id,
                    "field_id": fid,
                    "before": change.get("before"),
                    "after": change.get("after"),
                    "reason": reason,
                    "verifier_email": verifier,
                    "changed_at": now,
                },
            )
        if not normalized:
            return JsonResponse({"error": "no_valid_changes"}, status=400)
        path = _changelog_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        existing: list = []
        if path.is_file():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(raw, list):
                    existing = raw
            except json.JSONDecodeError:
                existing = []
        existing.extend(normalized)
        path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
        return JsonResponse({"ok": True, "entries_count": len(normalized)})
