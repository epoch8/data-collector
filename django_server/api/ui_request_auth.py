"""Firebase и Django session (staff) для /ui/api/v1."""

from __future__ import annotations

from django.http import JsonResponse

from .models import CollectorUser, Project
from .views import _err


def _firebase_collector(request) -> CollectorUser | None:
    return getattr(request, "collector_user", None)


def ui_api_principal(request) -> tuple[str, str, set[str] | None] | None:
    """
    (role, email, allowed_project_ids).
    staff: allowed=None (все проекты).
    client (Firebase): только admin_projects.
    """
    if request.user.is_authenticated and request.user.is_staff:
        return ("staff", request.user.email or request.user.username, None)

    cu = _firebase_collector(request)
    if cu is not None:
        allowed = set(cu.admin_projects.values_list("project_id", flat=True))
        if not allowed:
            return None
        return ("client", cu.email or cu.firebase_uid, allowed)

    return None


def ui_api_forbid_if_unauthenticated(request) -> JsonResponse | None:
    if ui_api_principal(request) is not None:
        return None
    if _firebase_collector(request) is not None:
        return JsonResponse(
            _err("forbidden", "No projects in Client-admin — assign in Users"),
            status=403,
        )
    if not request.user.is_authenticated:
        return JsonResponse(_err("unauthorized", "Firebase login or staff session required"), status=401)
    return JsonResponse(_err("forbidden", "Staff or Firebase client with Client-admin projects required"), status=403)


def ui_api_forbid_if_no_project(request, project_id: str) -> JsonResponse | None:
    denied = ui_api_forbid_if_unauthenticated(request)
    if denied is not None:
        return denied
    if not Project.objects.filter(project_id=project_id).exists():
        return JsonResponse(_err("not_found", "Unknown project"), status=404)
    principal = ui_api_principal(request)
    assert principal is not None
    _role, _email, allowed = principal
    if allowed is not None and project_id not in allowed:
        return JsonResponse(_err("forbidden", "No access to this project"), status=403)
    return None


def allowed_project_ids_for_request(request) -> set[str] | None:
    principal = ui_api_principal(request)
    if principal is None:
        return set()
    return principal[2]
