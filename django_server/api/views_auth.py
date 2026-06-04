from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.views import LoginView
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie

from .packages_spa_assets import packages_spa_assets, packages_spa_built
from .ui_access import ui_login_redirect_target


@ensure_csrf_cookie
def ui_login_page(request):
    """Единая страница входа (React): клиент Firebase + админ Django."""
    if request.user.is_authenticated and request.user.is_staff:
        redirect_to = request.GET.get("next") or ui_login_redirect_target(request.user)
        return redirect(redirect_to)
    if request.user.is_authenticated:
        logout(request)

    assets = packages_spa_assets()
    if not packages_spa_built():
        return render(request, "ui/packages_spa_missing.html", status=503)
    return render(
        request,
        "ui/login_app.html",
        {
            "spa_js": assets.get("js"),
            "spa_css": assets.get("css"),
        },
    )


@csrf_protect
@require_POST
def ui_staff_login_api(request):
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
    redirect_to = request.POST.get("next") or ui_login_redirect_target(user)
    return JsonResponse({"redirect": redirect_to})


class UiLoginView(LoginView):
    """POST-совместимость для старых форм; GET — ui_login_page."""

    template_name = "ui/login.html"

    def get(self, request, *args, **kwargs):
        return ui_login_page(request)

    def form_valid(self, form):
        response = super().form_valid(form)
        if not self.request.user.is_staff:
            logout(self.request)
            return redirect("ui_login")
        return response

    def get_success_url(self) -> str:
        redirect_to = self.get_redirect_url()
        if redirect_to:
            return redirect_to
        return ui_login_redirect_target(self.request.user)
