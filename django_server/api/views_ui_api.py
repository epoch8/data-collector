"""Session JSON API for packages UI (/ui/api/v1)."""

from __future__ import annotations

import json

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie

from . import package_admin_service as pas
from . import packages_ui as pui
from .models import PackageSession
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
        items, err = pas.list_packages(
            project_id,
            phase=phase,
            preview_prefix=PREVIEW_PREFIX,
        )
        if err is not None:
            return err
        return JsonResponse(items, safe=False)


class UiPackageWorkspaceView(View):
    def get(self, request, project_id: str, package_id: str):
        denied = ui_api_forbid_if_no_project(request, project_id)
        if denied is not None:
            return denied
        body, err = pas.get_workspace(project_id, package_id, preview_prefix=PREVIEW_PREFIX)
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


class UiFieldChangelogView(View):
    def get(self, request):
        denied = ui_api_forbid_if_unauthenticated(request)
        if denied is not None:
            return denied
        package_id = (request.GET.get("package_id") or "").strip()
        project_id = (request.GET.get("project_id") or "").strip()
        if project_id:
            denied_p = ui_api_forbid_if_no_project(request, project_id)
            if denied_p is not None:
                return denied_p
        entries = pui.list_changelog_entries(
            project_id=project_id,
            package_id=package_id,
        )
        return JsonResponse({"entries": entries})

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
        session = PackageSession.objects.filter(
            project__project_id=project_id,
            package_id=package_id,
        ).first()
        if session is None:
            return JsonResponse({"error": "not_found"}, status=404)
        verifier = (body.get("verifier_email") or request.user.email or "").strip()
        count = pui.append_changelog(session, reason, verifier, changes)
        if count == 0:
            return JsonResponse({"error": "no_valid_changes"}, status=400)
        return JsonResponse({"ok": True, "entries_count": count})
