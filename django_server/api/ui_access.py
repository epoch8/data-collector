"""Доступ к /ui: staff — Django session; клиенты — Firebase (вход на /ui/login/)."""

from __future__ import annotations

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden


def staff_only(view_func):
    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            return HttpResponseForbidden("Только для администраторов (staff)")
        return view_func(request, *args, **kwargs)

    return _wrapped


def ui_login_redirect_target(user) -> str:
    return "/ui/projects/"
