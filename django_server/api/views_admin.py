"""SPA API для client-admin (Firebase): deprecated for web; use /ui/api/v1 with session."""

from __future__ import annotations

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from . import package_admin_service as pas
from .request_auth import forbid_if_no_project_access, project_ids_for_request

ADMIN_API_PREFIX = "/admin-api/v1"
PREVIEW_PREFIX = ADMIN_API_PREFIX


@method_decorator(csrf_exempt, name="dispatch")
class AdminProjectsListView(View):
    def get(self, request):
        allowed = project_ids_for_request(request, scope="admin")
        items = pas.list_projects(allowed=allowed)
        return JsonResponse({"projects": items})


@method_decorator(csrf_exempt, name="dispatch")
class AdminProjectConfigView(View):
    def get(self, request, project_id: str):
        denied = forbid_if_no_project_access(request, project_id, scope="admin")
        if denied is not None:
            return denied
        body, err = pas.get_project_config(project_id)
        if err is not None:
            return err
        return JsonResponse(body)


@method_decorator(csrf_exempt, name="dispatch")
class AdminPackageListView(View):
    def get(self, request, project_id: str):
        denied = forbid_if_no_project_access(request, project_id, scope="admin")
        if denied is not None:
            return denied
        phase = (request.GET.get("phase") or "").strip()
        items, err = pas.list_packages(project_id, phase=phase, preview_prefix=PREVIEW_PREFIX)
        if err is not None:
            return err
        return JsonResponse(items, safe=False)


@method_decorator(csrf_exempt, name="dispatch")
class AdminPackageWorkspaceView(View):
    def get(self, request, project_id: str, package_id: str):
        denied = forbid_if_no_project_access(request, project_id, scope="admin")
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


@method_decorator(csrf_exempt, name="dispatch")
class AdminPackageManifestPatchView(View):
    def patch(self, request, project_id: str, package_id: str):
        denied = forbid_if_no_project_access(request, project_id, scope="admin")
        if denied is not None:
            return denied
        raw = request.body.decode("utf-8") if request.body else ""
        return pas.patch_manifest(project_id, package_id, raw)


@method_decorator(csrf_exempt, name="dispatch")
class AdminBlobPreviewView(View):
    def get(self, request, project_id: str, package_id: str, blob_pk: int):
        denied = forbid_if_no_project_access(request, project_id, scope="admin")
        if denied is not None:
            return denied
        return pas.blob_preview_response(project_id, package_id, blob_pk)
