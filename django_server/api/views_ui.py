"""Веб-интерфейс администрирования (проекты, конфиги, медиа, пакеты)."""

from __future__ import annotations

import json
import mimetypes
import re
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.http import FileResponse, HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods, require_POST

from .firebase_user_sync import sync_collector_users_from_firebase
from .models import CollectorUser, PackageSession, Project, UploadedBlob
from .packages_spa_assets import packages_spa_assets, packages_spa_built
from .project_config_validate import validate_project_payload
from .ui_access import staff_only


def ui_logout(request):
    if request.user.is_authenticated:
        logout(request)
    return redirect("ui_login")


def _project_assets_dir(project_id: str) -> Path:
    return Path(settings.PROJECT_ASSETS_ROOT) / project_id


def _list_media_files(project_id: str) -> list[tuple[str, int]]:
    root = _project_assets_dir(project_id)
    if not root.is_dir():
        return []
    out: list[tuple[str, int]] = []
    for f in sorted(root.rglob("*")):
        if f.is_file():
            rel = str(f.relative_to(root)).replace("\\", "/")
            out.append((rel, f.stat().st_size))
    return out


def _safe_rel_path(s: str) -> str | None:
    s = (s or "").strip().replace("\\", "/").strip("/")
    if not s or ".." in Path(s).parts:
        return None
    return s


def _sanitize_upload_basename(name: str) -> str:
    base = Path(str(name or "file")).name
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", base).strip("._") or "file"
    return s[:200]


def _allocate_auto_relative_path(project_id: str, uploaded_filename: str) -> str:
    """Уникальный относительный путь: uploads/<короткий id>_<безопасное имя файла>."""
    safe = _sanitize_upload_basename(uploaded_filename)
    base = _project_assets_dir(project_id)
    for _ in range(4096):
        rel = f"uploads/{uuid4().hex[:12]}_{safe}".replace("\\", "/")
        sp = _safe_rel_path(rel)
        if sp and not (base / sp).exists():
            return sp
    return _safe_rel_path(f"uploads/{uuid4().hex}_{safe}") or f"uploads/{uuid4().hex}_file.bin"


def _seed_project_json(project_id: str, name: str) -> dict:
    """Минимальный валидный конфиг для нового проекта и при битом JSON в БД."""
    return {
        "id": project_id,
        "name": name or project_id,
        "version": "1",
        "config": {
            "fields": [
                {
                    "field_id": "demo_text",
                    "priority": 1,
                    "type": "text_input",
                    "title": "Пример текста",
                    "instructions": "Заполните поле",
                    "validation": {},
                },
            ],
            "flow": {
                "steps": [
                    {"id": "form1", "screen": "form", "field_ids": ["demo_text"]},
                ],
            },
            "ui": {},
        },
    }


def _next_config_version(project: Project, ver: str) -> str:
    if ver:
        return ver
    try:
        v = int(project.config_version)
        return str(v + 1)
    except ValueError:
        return project.config_version + "-1"


def _save_project_json(project: Project, project_id: str, data: dict, ver: str) -> list[str]:
    """Возвращает список ошибок валидации; пустой — сохранено."""
    data["id"] = project_id
    errs = validate_project_payload(data, project_id)
    if errs:
        return errs
    project.config_version = _next_config_version(project, ver.strip())
    project.raw_json = json.dumps(data, ensure_ascii=False, indent=2)
    project.name = (data.get("name") or project.name)[:512]
    project.save()
    return []


def ui_home(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("ui_project_list")
    return redirect("ui_login")


@staff_only
def project_list(request):
    return render(
        request,
        "ui/project_list.html",
        {
            "projects": Project.objects.all().order_by("name"),
            "is_staff": True,
        },
    )


@staff_only
@require_http_methods(["GET", "POST"])
def project_new(request):
    if request.method == "POST":
        pid = (request.POST.get("project_id") or "").strip()
        name = (request.POST.get("name") or "").strip() or pid
        if not pid:
            messages.error(request, "Укажите project_id (как поле id в JSON).")
            return redirect("ui_project_new")
        if Project.objects.filter(project_id=pid).exists():
            messages.error(request, "Проект с таким id уже есть.")
            return redirect("ui_project_detail", project_id=pid)
        seed = _seed_project_json(pid, name)
        body = {
            "id": pid,
            "name": name,
            "version": seed["version"],
            "config": seed["config"],
        }
        Project.objects.create(
            project_id=pid,
            name=name,
            config_version="1",
            raw_json=json.dumps(body, ensure_ascii=False, indent=2),
        )
        _project_assets_dir(pid).mkdir(parents=True, exist_ok=True)
        messages.success(request, f"Проект {pid} создан.")
        return redirect("ui_project_detail", project_id=pid)
    return render(request, "ui/project_new.html", {})


@staff_only
def project_detail(request, project_id: str):
    project = get_object_or_404(Project, project_id=project_id)
    media = _list_media_files(project_id)
    pkg_count = project.packages.count()
    return render(
        request,
        "ui/project_detail.html",
        {
            "project": project,
            "media_files": media,
            "package_count": pkg_count,
            "is_staff": request.user.is_staff,
        },
    )


@staff_only
@require_http_methods(["GET", "POST"])
def project_config(request, project_id: str):
    project = get_object_or_404(Project, project_id=project_id)
    if request.method == "POST":
        raw = request.POST.get("raw_json", "")
        ver = (request.POST.get("config_version") or "").strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            messages.error(request, f"Невалидный JSON: {e}")
            return redirect("ui_project_config", project_id=project_id)
        errs = _save_project_json(project, project_id, data, ver)
        if errs:
            for e in errs:
                messages.error(request, e)
            try:
                pretty = json.dumps(json.loads(raw), ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                pretty = raw
            return render(
                request,
                "ui/project_config.html",
                {
                    "project": project,
                    "pretty_json": pretty,
                    "validation_errors": errs,
                    "read_only": False,
                },
            )
        messages.success(request, "Конфиг сохранён, версия обновлена.")
        return redirect("ui_project_detail", project_id=project_id)
    try:
        pretty = json.dumps(json.loads(project.raw_json), ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        pretty = project.raw_json
    return render(
        request,
        "ui/project_config.html",
        {
            "project": project,
            "pretty_json": pretty,
            "validation_errors": None,
            "read_only": False,
        },
    )


@ensure_csrf_cookie
@staff_only
@require_http_methods(["GET", "POST"])
def project_config_builder(request, project_id: str):
    """Визуальный редактор + превью; сохраняет тот же JSON, что и raw-редактор."""
    project = get_object_or_404(Project, project_id=project_id)
    if request.method == "POST":
        raw = request.POST.get("raw_json", "")
        ver = (request.POST.get("config_version") or "").strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            messages.error(request, f"Невалидный JSON: {e}")
            return redirect("ui_project_config_builder", project_id=project_id)
        errs = _save_project_json(project, project_id, data, ver)
        if errs:
            for e in errs:
                messages.error(request, e)
            try:
                initial_data = json.loads(raw)
            except json.JSONDecodeError:
                initial_data = _seed_project_json(project.project_id, project.name)
            try:
                pretty = json.dumps(json.loads(project.raw_json), ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                pretty = project.raw_json
            return render(
                request,
                "ui/project_config_builder.html",
                {
                    "project": project,
                    "initial_data": initial_data,
                    "pretty_json": pretty,
                    "validation_errors": errs,
                    "config_version": ver or project.config_version,
                },
            )
        messages.success(request, "Конфиг сохранён, версия обновлена.")
        return redirect("ui_project_detail", project_id=project_id)
    try:
        initial_data = json.loads(project.raw_json)
        pretty = json.dumps(initial_data, ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        initial_data = _seed_project_json(project.project_id, project.name)
        pretty = json.dumps(initial_data, ensure_ascii=False, indent=2)
    return render(
        request,
        "ui/project_config_builder.html",
        {
            "project": project,
            "initial_data": initial_data,
            "pretty_json": pretty,
            "config_version": project.config_version,
        },
    )


@staff_only
@require_POST
def project_config_validate_api(request, project_id: str):
    """POST JSON тела проекта — ответ { ok, errors } без сохранения."""
    try:
        data = json.loads(request.body.decode())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "errors": ["Тело запроса не является JSON."]}, status=400)
    errs = validate_project_payload(data, project_id)
    return JsonResponse({"ok": not bool(errs), "errors": errs})


@staff_only
@require_http_methods(["GET", "POST"])
def project_media(request, project_id: str):
    project = get_object_or_404(Project, project_id=project_id)
    if request.method == "POST":
        if "delete" in request.POST:
            rel = _safe_rel_path(request.POST.get("rel_path", ""))
            if not rel:
                messages.error(request, "Некорректный путь.")
            else:
                target = (_project_assets_dir(project_id) / rel).resolve()
                base = _project_assets_dir(project_id).resolve()
                try:
                    target.relative_to(base)
                except ValueError:
                    messages.error(request, "Некорректный путь.")
                else:
                    if target.is_file():
                        target.unlink()
                        messages.success(request, f"Удалено: {rel}")
                    else:
                        messages.warning(request, "Файл не найден.")
            return redirect("ui_project_media", project_id=project_id)
        f = request.FILES.get("file")
        if not f:
            msg = "Выберите файл для загрузки."
            if request.POST.get("respond") == "json":
                return JsonResponse({"ok": False, "error": msg}, status=400)
            messages.error(request, msg)
            return redirect("ui_project_media", project_id=project_id)
        rel = _allocate_auto_relative_path(project_id, f.name)
        dest = _project_assets_dir(project_id) / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("wb") as out:
            for chunk in f.chunks():
                out.write(chunk)
        messages.success(request, f"Сохранено: {rel}")
        if request.POST.get("respond") == "json":
            return JsonResponse({"ok": True, "relative_path": rel})
        return redirect("ui_project_media", project_id=project_id)
    if request.GET.get("format") == "json":
        rows = _list_media_files(project_id)
        files = [
            {"relative_path": rel, "size": size, "asset_path": f"assets/{rel}" if rel else ""}
            for rel, size in rows
        ]
        return JsonResponse({"files": files})
    return render(
        request,
        "ui/project_media.html",
        {"project": project, "media_files": _list_media_files(project_id)},
    )


@staff_only
@require_POST
def project_delete(request, project_id: str):
    project = get_object_or_404(Project, project_id=project_id)
    if request.POST.get("confirm") != project_id:
        messages.error(request, "Введите подтверждение: id проекта в поле confirm.")
        return redirect("ui_project_detail", project_id=project_id)
    project.delete()
    messages.success(request, "Проект удалён.")
    return redirect("ui_project_list")


@ensure_csrf_cookie
def packages_spa(request, subpath: str = ""):
    assets = packages_spa_assets()
    if not packages_spa_built():
        return render(
            request,
            "ui/packages_spa_missing.html",
            status=503,
        )
    return render(
        request,
        "ui/packages_app.html",
        {
            "spa_js": assets.get("js"),
            "spa_css": assets.get("css"),
        },
    )


@staff_only
def collector_user_list(request):
    users = CollectorUser.objects.prefetch_related("mobile_projects", "admin_projects").order_by(
        "email", "firebase_uid"
    )
    return render(request, "ui/collector_user_list.html", {"collector_users": users})


@staff_only
@require_POST
def collector_user_sync_firebase(request):
    try:
        r = sync_collector_users_from_firebase()
        messages.success(
            request,
            f"Firebase: импортировано пользователей из консоли — {r.total_firebase} "
            f"(новых записей {r.created}, обновлён email {r.updated_email}).",
        )
    except Exception as e:
        messages.error(request, str(e))
    return redirect("ui_collector_user_list")


@staff_only
@require_http_methods(["GET", "POST"])
def collector_user_detail(request, pk: int):
    cu = get_object_or_404(
        CollectorUser.objects.prefetch_related("mobile_projects", "admin_projects"),
        pk=pk,
    )
    all_projects = list(Project.objects.all().order_by("name"))
    if request.method == "POST":
        mobile_ids = request.POST.getlist("mobile_projects")
        admin_ids = request.POST.getlist("admin_projects")
        mobile_allowed = set(
            Project.objects.filter(project_id__in=mobile_ids).values_list("project_id", flat=True)
        )
        admin_allowed = set(
            Project.objects.filter(project_id__in=admin_ids).values_list("project_id", flat=True)
        )
        cu.mobile_projects.set(Project.objects.filter(project_id__in=mobile_allowed))
        cu.admin_projects.set(Project.objects.filter(project_id__in=admin_allowed))
        messages.success(request, "Права доступа сохранены.")
        return redirect("ui_collector_user_detail", pk=cu.pk)
    selected_mobile = list(cu.mobile_projects.values_list("project_id", flat=True))
    selected_admin = list(cu.admin_projects.values_list("project_id", flat=True))
    return render(
        request,
        "ui/collector_user_detail.html",
        {
            "collector_user": cu,
            "all_projects": all_projects,
            "selected_mobile_project_ids": selected_mobile,
            "selected_admin_project_ids": selected_admin,
        },
    )
