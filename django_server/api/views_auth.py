import json

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.views import LoginView
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .collector_user_defaults import assign_default_collector_project
from .firebase_verify import firebase_auth_enabled, verify_id_token
from .models import CollectorUser
from .ui_access import (
    get_ui_collector,
    is_ui_staff,
    ui_login_redirect_target,
    ui_logout_clear_collector_session,
)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class UiLoginView(LoginView):
    """Вход staff: логин/пароль Django. Клиент: Firebase (см. login.html + firebase_login.js)."""

    template_name = "ui/login.html"
    redirect_authenticated_user = True

    def get_success_url(self) -> str:
        redirect_to = self.get_redirect_url()
        if redirect_to:
            return redirect_to
        return ui_login_redirect_target(self.request)

    def dispatch(self, request, *args, **kwargs):
        if is_ui_staff(request):
            redirect_to = request.GET.get("next") or ui_login_redirect_target(request)
            return redirect(redirect_to)
        if get_ui_collector(request) is not None:
            redirect_to = request.GET.get("next") or ui_login_redirect_target(request)
            return redirect(redirect_to)
        if request.user.is_authenticated and not request.user.is_staff:
            logout(request)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        if not self.request.user.is_staff:
            logout(self.request)
            return redirect("ui_login")
        ui_logout_clear_collector_session(self.request)
        return response


@csrf_protect
@require_POST
def ui_firebase_login(request):
    """Клиент: POST { id_token } → Django session (ui_collector_pk)."""
    if not firebase_auth_enabled():
        return JsonResponse({"detail": "Firebase отключён на сервере."}, status=503)
    try:
        body = json.loads(request.body.decode("utf-8") if request.body else "{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Невалидный JSON."}, status=400)
    raw = (body.get("id_token") or "").strip()
    if not raw:
        return JsonResponse({"detail": "Нужен id_token."}, status=400)
    try:
        claims = verify_id_token(raw)
    except Exception:
        return JsonResponse({"detail": "Неверный или просроченный токен Firebase."}, status=401)
    uid = claims.get("uid") or claims.get("sub")
    if not uid:
        return JsonResponse({"detail": "В токене нет uid."}, status=401)
    email = (claims.get("email") or "").strip()
    cu, created = CollectorUser.objects.get_or_create(
        firebase_uid=uid,
        defaults={"email": email},
    )
    if email and cu.email != email:
        cu.email = email
        cu.save(update_fields=["email"])
    if created:
        assign_default_collector_project(cu)
    if not cu.admin_projects.exists():
        return JsonResponse(
            {
                "detail": "Нет доступа к проектам: отметьте Client-admin в «Пользователи» для этого email.",
            },
            status=403,
        )
    logout(request)
    request.session["ui_collector_pk"] = cu.pk
    redirect_to = (body.get("next") or "").strip() or ui_login_redirect_target(request)
    return JsonResponse({"redirect": redirect_to})


@csrf_protect
@require_POST
def ui_staff_login_api(request):
    """AJAX staff login (опционально)."""
    username = (request.POST.get("username") or "").strip()
    password = request.POST.get("password") or ""
    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"detail": "Неверный логин или пароль."}, status=401)
    if not user.is_staff:
        return JsonResponse(
            {"detail": "Нужен аккаунт администратора (staff)."},
            status=403,
        )
    login(request, user)
    ui_logout_clear_collector_session(request)
    redirect_to = request.POST.get("next") or ui_login_redirect_target(request)
    return JsonResponse({"redirect": redirect_to})
