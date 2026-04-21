"""Веб-интерфейс администрирования (проекты, конфиги, медиа, пакеты)."""

from __future__ import annotations

import json
import mimetypes
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import FileResponse, HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods, require_POST

from .models import PackageSession, Project, UploadedBlob
from .project_config_validate import validate_project_payload

staff_only = user_passes_test(lambda u: u.is_authenticated and u.is_staff)


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


@staff_only
@login_required
def ui_home(request):
    return redirect("ui_project_list")


@staff_only
@login_required
def project_list(request):
    return render(
        request,
        "ui/project_list.html",
        {"projects": Project.objects.all().order_by("name")},
    )


@staff_only
@login_required
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
@login_required
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
        },
    )


@staff_only
@login_required
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
                {"project": project, "pretty_json": pretty, "validation_errors": errs},
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
        {"project": project, "pretty_json": pretty, "validation_errors": None},
    )


@ensure_csrf_cookie
@staff_only
@login_required
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
@login_required
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
@login_required
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
        rel = _safe_rel_path(request.POST.get("relative_path", ""))
        if not f or not rel:
            messages.error(request, "Нужны файл и относительный путь (например korovas/example.jpg).")
            return redirect("ui_project_media", project_id=project_id)
        dest = _project_assets_dir(project_id) / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("wb") as out:
            for chunk in f.chunks():
                out.write(chunk)
        messages.success(request, f"Сохранено: {rel}")
        return redirect("ui_project_media", project_id=project_id)
    return render(
        request,
        "ui/project_media.html",
        {"project": project, "media_files": _list_media_files(project_id)},
    )


@staff_only
@login_required
@require_POST
def project_delete(request, project_id: str):
    project = get_object_or_404(Project, project_id=project_id)
    if request.POST.get("confirm") != project_id:
        messages.error(request, "Введите подтверждение: id проекта в поле confirm.")
        return redirect("ui_project_detail", project_id=project_id)
    project.delete()
    messages.success(request, "Проект удалён.")
    return redirect("ui_project_list")


@staff_only
@login_required
def package_list(request):
    qs = PackageSession.objects.select_related("project").order_by("-created_at")
    filter_project = (request.GET.get("project") or "").strip()
    if filter_project:
        qs = qs.filter(project__project_id=filter_project)
    qs = qs[:500]
    return render(
        request,
        "ui/package_list.html",
        {
            "sessions": qs,
            "filter_project": filter_project,
            "projects": Project.objects.all().order_by("name"),
        },
    )


@staff_only
@login_required
def package_detail(request, project_id: str, package_id: str):
    session = get_object_or_404(
        PackageSession,
        project__project_id=project_id,
        package_id=package_id,
    )
    blobs = list(session.blobs.all().order_by("logical_path"))
    manifest_pretty = ""
    if session.manifest_json:
        try:
            manifest_pretty = json.dumps(
                json.loads(session.manifest_json),
                ensure_ascii=False,
                indent=2,
            )
        except json.JSONDecodeError:
            manifest_pretty = session.manifest_json
    return render(
        request,
        "ui/package_detail.html",
        {
            "session": session,
            "blobs": blobs,
            "manifest_pretty": manifest_pretty,
        },
    )


@staff_only
@login_required
def package_blob_download(request, project_id: str, package_id: str, blob_pk: int):
    blob = get_object_or_404(
        UploadedBlob,
        pk=blob_pk,
        session__project__project_id=project_id,
        session__package_id=package_id,
    )
    if not blob.file:
        return HttpResponseForbidden("Нет файла")
    ctype, _ = mimetypes.guess_type(blob.logical_path)
    resp = FileResponse(blob.file.open("rb"), content_type=ctype or "application/octet-stream")
    resp["Content-Disposition"] = f'inline; filename="{Path(blob.logical_path).name}"'
    return resp
