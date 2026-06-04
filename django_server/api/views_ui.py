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
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    HttpResponseForbidden,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods, require_POST

from . import package_admin_service as pas
from . import packages_ui as pui
from .firebase_user_sync import sync_collector_users_from_firebase
from .models import CollectorUser, PackageSession, Project, UploadedBlob
from .project_config_validate import validate_project_payload
from .ui_access import (
    allowed_package_project_ids,
    get_ui_collector,
    is_ui_staff,
    packages_ui_required,
    staff_only,
    ui_logout_clear_collector_session,
)


def ui_logout(request):
    if request.user.is_authenticated:
        logout(request)
    ui_logout_clear_collector_session(request)
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
    if is_ui_staff(request):
        return redirect("ui_project_list")
    if get_ui_collector(request) is not None:
        return redirect("ui_package_list")
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


def _package_projects_queryset(request):
    allowed = allowed_package_project_ids(request)
    qs = Project.objects.all().order_by("name")
    if allowed is not None:
        qs = qs.filter(project_id__in=allowed)
    return qs


def _forbid_package_project(request, project_id: str) -> HttpResponseForbidden | None:
    allowed = allowed_package_project_ids(request)
    if allowed is not None and project_id not in allowed:
        return HttpResponseForbidden("Нет доступа к этому проекту.")
    return None


def _ui_verifier_email(request) -> str:
    if request.user.is_authenticated and request.user.email:
        return request.user.email
    cu = get_ui_collector(request)
    if cu is not None and cu.email:
        return cu.email
    if request.user.is_authenticated:
        return request.user.username
    return ""


def _select_project(request, projects: list[Project]):
    """Возвращает (project, project_id) или (None, '') и при запрете — HttpResponseForbidden."""
    project_id = (request.GET.get("project") or "").strip()
    if project_id:
        denied = _forbid_package_project(request, project_id)
        if denied is not None:
            return None, "", denied
        selected = next((p for p in projects if p.project_id == project_id), None)
        if selected is not None:
            return selected, project_id, None
    if projects:
        return projects[0], projects[0].project_id, None
    return None, "", None


@packages_ui_required
def package_list(request):
    projects = list(_package_projects_queryset(request))
    selected, project_id, denied = _select_project(request, projects)
    if denied is not None:
        return denied

    phase = (request.GET.get("phase") or "completed").strip()
    mode = (request.GET.get("mode") or "field").strip()
    field_id = (request.GET.get("field") or "").strip()
    text = (request.GET.get("q") or "").strip()
    date = (request.GET.get("date") or "").strip()

    fields: list = []
    search_fields: list = []
    rows: list = []
    phase_chips: list = []
    selected_field = None
    total = 0

    if selected is not None:
        root = pui.config_root(selected)
        fields = pui.config_fields(root)
        search_fields = pui.searchable_fields(fields)
        if mode == "field" and not field_id and search_fields:
            field_id = search_fields[0]["field_id"]
        selected_field = next((f for f in search_fields if f["field_id"] == field_id), None)

        items, _err = pas.list_packages(project_id, phase="", preview_prefix="/ui/api/v1")
        items = items or []
        total = len(items)
        phase_chips = [
            {"id": p, "label": ("Все" if p == "all" else pui.phase_label(p)), "active": p == phase}
            for p in pui.phase_options(items)
        ]
        filtered = pui.filter_packages(
            items, fields, phase=phase, mode=mode, field_id=field_id, text=text, date=date,
        )
        for it in filtered:
            data_fields = it.get("data_fields") or {}
            rows.append(
                {
                    "package_id": it["package_id"],
                    "short_id": pui.short_package_id(it["package_id"]),
                    "phase": it["phase"],
                    "phase_label": pui.phase_label(it["phase"]),
                    "created_at": it["created_at"],
                    "uploader_email": it.get("uploader_email") or "",
                    "field_value": data_fields.get(field_id) if field_id else None,
                    "url": reverse("ui_package_workspace", args=[project_id, it["package_id"]]),
                },
            )

    show_field_column = bool(mode == "field" and selected_field)
    is_datetime = bool(selected_field and selected_field.get("type") == "datetime")

    return render(
        request,
        "ui/packages/list.html",
        {
            "is_staff": is_ui_staff(request),
            "projects": projects,
            "project_id": project_id,
            "selected_project": selected,
            "search_fields": search_fields,
            "selected_field": selected_field,
            "show_field_column": show_field_column,
            "is_datetime_field": is_datetime,
            "phase_chips": phase_chips,
            "rows": rows,
            "total": total,
            "f_phase": phase,
            "f_mode": mode,
            "f_field": field_id,
            "f_q": text,
            "f_date": date,
        },
    )


def _enrich_blob(project_id, package_id, blob, form_blob_paths):
    path = blob["logical_path"]
    return {
        "blob_id": blob["blob_id"],
        "logical_path": path,
        "file_name": pui.blob_file_name(path),
        "size_bytes": blob["size_bytes"],
        "is_image": pui.is_image_path(path),
        "in_form": path in form_blob_paths,
        "url": reverse("ui_package_blob_download", args=[project_id, package_id, blob["blob_id"]]),
    }


def _build_data_sections(sections, data, editable):
    out = []
    for sec in sections:
        sfields = []
        for f in sec["fields"]:
            fid = f["field_id"]
            value = data.get(fid)
            sfields.append(
                {
                    "field_id": fid,
                    "label": pui.field_label(f),
                    "type": f.get("type"),
                    "hint": pui.field_hint(f),
                    "required": pui.field_required(f),
                    "value": "" if value is None else value,
                    "editable": editable and f.get("type") == "text_input",
                },
            )
        out.append({"id": sec["id"], "title": sec["title"], "fields": sfields})
    return out


@packages_ui_required
def package_workspace(request, project_id: str, package_id: str):
    denied = _forbid_package_project(request, project_id)
    if denied is not None:
        return denied

    body, err = pas.get_workspace(project_id, package_id, preview_prefix="/ui/api/v1")
    if err is not None:
        raise Http404("Package not found")

    session = body["session"]
    manifest = body["manifest"]
    config = body["project_config"]
    data = manifest.get("data") if isinstance(manifest.get("data"), dict) else {}

    fields = pui.config_fields(config)
    sections = pui.build_flow_sections(config, fields)
    is_editable = session["phase"] == PackageSession.Phase.COMPLETED
    data_sections = _build_data_sections(sections, data, is_editable)

    form_blob_paths = pui.collect_form_blob_paths(data)
    blobs = [_enrich_blob(project_id, package_id, b, form_blob_paths) for b in body["blobs"]]

    entries = pui.read_changelog(project_id, package_id)
    has_viz = pui.has_visualisation(project_id, package_id)
    blob_map = {b["logical_path"]: b["url"] for b in blobs}

    # Sidebar: все пакеты проекта
    side_items, _ = pas.list_packages(project_id, phase="", preview_prefix="/ui/api/v1")
    sidebar = [
        {
            "package_id": it["package_id"],
            "short_id": pui.short_package_id(it["package_id"]),
            "phase": it["phase"],
            "phase_label": pui.phase_label(it["phase"]),
            "uploader_email": it.get("uploader_email") or "",
            "created_at": it["created_at"],
            "active": it["package_id"] == package_id,
            "url": reverse("ui_package_workspace", args=[project_id, it["package_id"]]),
        }
        for it in (side_items or [])
    ]

    project_name = (config.get("name") if isinstance(config, dict) else None) or project_id

    return render(
        request,
        "ui/packages/workspace.html",
        {
            "is_staff": is_ui_staff(request),
            "project_id": project_id,
            "project_name": project_name,
            "package_id": package_id,
            "short_package_id": pui.short_package_id(package_id),
            "session": session,
            "phase_label": pui.phase_label(session["phase"]),
            "is_editable": is_editable,
            "data_sections": data_sections,
            "blobs": blobs,
            "blob_count": len(blobs),
            "entries": entries,
            "has_viz": has_viz,
            "blob_map_json": json.dumps(blob_map, ensure_ascii=False),
            "sidebar": sidebar,
            "list_url": reverse("ui_package_list") + f"?project={project_id}",
            "save_url": reverse("ui_package_manifest_save", args=[project_id, package_id]),
            "viz_data_url": reverse("ui_package_viz_data", args=[project_id, package_id]),
            "verifier_email": _ui_verifier_email(request),
        },
    )


def _coerce_value(original, new_text: str):
    """text_input: если исходное значение было числом и ввод числовой — храним число."""
    if isinstance(original, bool):
        return new_text
    if isinstance(original, (int, float)) and not isinstance(original, bool):
        try:
            if new_text.strip() == "":
                return ""
            if "." in new_text or "e" in new_text.lower():
                return float(new_text)
            return int(new_text)
        except ValueError:
            return new_text
    return new_text


@packages_ui_required
@require_POST
def package_manifest_save(request, project_id: str, package_id: str):
    denied = _forbid_package_project(request, project_id)
    if denied is not None:
        return denied

    body, err = pas.get_workspace(project_id, package_id, preview_prefix="/ui/api/v1")
    if err is not None:
        raise Http404("Package not found")

    session = body["session"]
    if session["phase"] != PackageSession.Phase.COMPLETED:
        messages.error(request, "Редактировать можно только пакеты в статусе «Завершён».")
        return redirect("ui_package_workspace", project_id=project_id, package_id=package_id)

    manifest = body["manifest"]
    config = body["project_config"]
    data = dict(manifest.get("data") or {})

    editable_ids = [
        f["field_id"]
        for f in pui.config_fields(config)
        if f.get("type") == "text_input"
    ]

    changes = []
    for fid in editable_ids:
        posted = request.POST.get(f"data__{fid}")
        if posted is None:
            continue
        before = data.get(fid)
        after = _coerce_value(before, posted)
        if json.dumps(before, ensure_ascii=False, sort_keys=True) != json.dumps(
            after, ensure_ascii=False, sort_keys=True,
        ):
            changes.append({"field_id": fid, "before": before, "after": after})
            data[fid] = after

    if not changes:
        messages.info(request, "Изменений нет.")
        return redirect("ui_package_workspace", project_id=project_id, package_id=package_id)

    reason = (request.POST.get("reason") or "").strip()
    if not reason:
        messages.error(request, "Укажите причину корректировки.")
        return redirect("ui_package_workspace", project_id=project_id, package_id=package_id)

    manifest["data"] = data
    manifest["project_id"] = project_id
    patch_resp = pas.patch_manifest(
        project_id, package_id, json.dumps(manifest, ensure_ascii=False),
    )
    if patch_resp.status_code != 200:
        try:
            detail = json.loads(patch_resp.content.decode("utf-8"))
            msg = detail.get("error", {}).get("message", "Ошибка сохранения")
        except (json.JSONDecodeError, AttributeError):
            msg = "Ошибка сохранения"
        messages.error(request, f"Не удалось сохранить: {msg}")
        return redirect("ui_package_workspace", project_id=project_id, package_id=package_id)

    pui.append_changelog(
        project_id, package_id, reason, _ui_verifier_email(request), changes,
    )
    messages.success(request, f"Сохранено. Изменено полей: {len(changes)}.")
    return redirect("ui_package_workspace", project_id=project_id, package_id=package_id)


@packages_ui_required
def package_viz_data(request, project_id: str, package_id: str):
    denied = _forbid_package_project(request, project_id)
    if denied is not None:
        return denied
    return JsonResponse(
        {
            "gt": pui.gt_annotations_for_package(project_id, package_id),
            "inference": pui.inference_for_package(project_id, package_id),
        },
    )


@packages_ui_required
def package_depth_npy(request, filename: str):
    safe = Path(filename).name
    if not safe.endswith(".npy"):
        raise Http404("Not found")
    path = pui.datapipe_dir() / safe
    if not path.is_file():
        raise Http404("Not found")
    return FileResponse(path.open("rb"), content_type="application/octet-stream")


@packages_ui_required
def package_blob_download(request, project_id: str, package_id: str, blob_pk: int):
    denied = _forbid_package_project(request, project_id)
    if denied is not None:
        return denied
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
