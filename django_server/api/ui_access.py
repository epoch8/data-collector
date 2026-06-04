"""Доступ к /ui: staff — Django session; клиенты — Firebase (сессия после входа)."""

from __future__ import annotations

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect

from .models import CollectorUser


def staff_only(view_func):
    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            return HttpResponseForbidden("Только для администраторов (staff)")
        return view_func(request, *args, **kwargs)

    return _wrapped


def get_ui_collector(request) -> CollectorUser | None:
    return getattr(request, "collector_user", None)


def is_ui_staff(request) -> bool:
    return request.user.is_authenticated and request.user.is_staff


def allowed_package_project_ids(request) -> set[str] | None:
    """None = все проекты (staff); иначе только Client-admin."""
    if is_ui_staff(request):
        return None
    cu = get_ui_collector(request)
    if cu is None:
        return set()
    return set(cu.admin_projects.values_list("project_id", flat=True))


def packages_ui_required(view_func):
    """Пакеты: staff или Firebase-клиент с назначенными проектами."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if is_ui_staff(request):
            return view_func(request, *args, **kwargs)
        cu = get_ui_collector(request)
        if cu is not None and cu.admin_projects.exists():
            return view_func(request, *args, **kwargs)
        if not request.user.is_authenticated and cu is None:
            from django.urls import reverse

            login_url = reverse("ui_login")
            next_path = request.get_full_path()
            return redirect(f"{login_url}?next={next_path}")
        return HttpResponseForbidden(
            "Нет доступа к пакетам. Назначьте проекты в разделе «Пользователи» (Client-admin).",
        )

    return _wrapped


def ui_login_redirect_target(request) -> str:
    if is_ui_staff(request):
        return "/ui/projects/"
    if get_ui_collector(request) is not None:
        return "/ui/packages/"
    return "/ui/login/"


def ui_logout_clear_collector_session(request) -> None:
    request.session.pop("ui_collector_pk", None)
