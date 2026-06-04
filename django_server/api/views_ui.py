"""Веб-интерфейс администрирования (проекты, конфиги, медиа, пакеты)."""

from __future__ import annotations

import json
import mimetypes
import re
from pathlib import Path
from uuid import uuid4

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
from .project_config_service import (
    bootstrap_new_project,
    create_credential,
    create_credential_generated,
    load_config_dict,
    save_config_to_git,
    seed_project_json,
    update_credential_private_key,
)
from .project_config_validate import validate_project_payload
from .project_git import (
    GitProjectError,
    delete_media_file,
    list_media_files,
    media_config_path,
    media_dir,
    normalize_git_remote,
    normalize_media_rel,
    pull,
    test_remote,
    write_media_file,
)
from .project_git import remove_cache as git_remove_cache
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


def _safe_rel_path(s: str) -> str | None:
    s = (s or "").strip().replace("\\", "/").strip("/")
    if not s or ".." in Path(s).parts:
        return None
    return s


def _sanitize_upload_basename(name: str) -> str:
    base = Path(str(name or "file")).name
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", base).strip("._") or "file"
    return s[:200]


def _allocate_auto_relative_path(project: Project, uploaded_filename: str) -> str:
    """Уникальный путь под `collector/media/uploads/…`."""
    safe = _sanitize_upload_basename(uploaded_filename)
    base = media_dir(project)
    for _ in range(4096):
        rel = f"uploads/{uuid4().hex[:12]}_{safe}".replace("\\", "/")
        sp = normalize_media_rel(rel)
        if sp and not (base / sp).exists():
            return sp
    return normalize_media_rel(f"uploads/{uuid4().hex}_{safe}") or f"uploads/{uuid4().hex}_file.bin"


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
        git_url = (request.POST.get("git_repo_url") or "").strip()
        private_key = (request.POST.get("private_key") or "").strip()
        generate_key = request.POST.get("generate_key") == "1"
        if not pid:
            messages.error(request, "Укажите project_id (как поле id в config.json).")
            return redirect("ui_project_new")
        if Project.objects.filter(project_id=pid).exists():
            messages.error(request, "Проект с таким id уже есть.")
            return redirect("ui_project_detail", project_id=pid)
        try:
            git_remote = normalize_git_remote(git_url)
        except GitProjectError as e:
            messages.error(request, e.message)
            return redirect("ui_project_new")
        try:
            if generate_key:
                cred, public_key, _ = create_credential_generated(label=f"{pid} deploy")
            else:
                cred = create_credential(label=f"{pid} deploy", private_key=private_key)
                public_key = cred.public_key
        except GitProjectError as e:
            messages.error(request, e.message)
            return redirect("ui_project_new")
        project = Project.objects.create(
            project_id=pid,
            name=name,
            git_remote=git_remote,
            git_default_ref=(request.POST.get("git_default_ref") or "main").strip() or "main",
            git_credential=cred,
        )
        seed = seed_project_json(pid, name)
        for w in bootstrap_new_project(project, seed=seed):
            messages.warning(request, w)
        if generate_key:
            messages.info(
                request,
                "Добавьте deploy key в GitHub (Settings → Deploy keys, с write access). "
                "Публичный ключ — на странице проекта.",
            )
        messages.success(request, f"Проект {pid} создан. Git: {git_remote}")
        request.session[f"git_public_key_{pid}"] = public_key
        return redirect("ui_project_detail", project_id=pid)
    return render(request, "ui/project_new.html", {})


@staff_only
def project_detail(request, project_id: str):
    project = get_object_or_404(Project, project_id=project_id)
    pkg_count = project.packages.count()
    public_key = request.session.pop(f"git_public_key_{project_id}", None) or project.git_credential.public_key
    return render(
        request,
        "ui/project_detail.html",
        {
            "project": project,
            "package_count": pkg_count,
            "is_staff": request.user.is_staff,
            "git_public_key": public_key,
        },
    )


@staff_only
@require_http_methods(["GET", "POST"])
def project_update_ssh_key(request, project_id: str):
    project = get_object_or_404(Project, project_id=project_id)
    public_key = request.session.pop(f"git_public_key_{project_id}", None) or project.git_credential.public_key
    if request.method == "POST":
        private_key = (request.POST.get("private_key") or "").strip()
        if not private_key:
            messages.error(request, "Вставьте приватный ключ OpenSSH.")
            return redirect("ui_project_update_ssh_key", project_id=project_id)
        try:
            public_key = update_credential_private_key(project.git_credential, private_key)
            request.session[f"git_public_key_{project_id}"] = public_key
            messages.success(
                request,
                "Приватный ключ обновлён. Если public key изменился — обновите Deploy key на GitHub.",
            )
        except GitProjectError as e:
            messages.error(request, e.message)
        return redirect("ui_project_update_ssh_key", project_id=project_id)
    return render(
        request,
        "ui/project_ssh.html",
        {"project": project, "git_public_key": public_key},
    )


@staff_only
@require_http_methods(["GET", "POST"])
def project_git_settings(request, project_id: str):
    project = get_object_or_404(Project, project_id=project_id)
    if request.method == "POST":
        git_url = (request.POST.get("git_repo_url") or "").strip()
        git_ref = (request.POST.get("git_default_ref") or "main").strip() or "main"
        if not git_url:
            messages.error(request, "Укажите URL репозитория GitHub.")
            return redirect("ui_project_git_settings", project_id=project_id)
        try:
            git_remote = normalize_git_remote(git_url)
        except GitProjectError as e:
            messages.error(request, e.message)
            return redirect("ui_project_git_settings", project_id=project_id)
        changed = project.git_remote != git_remote or project.git_default_ref != git_ref
        project.git_remote = git_remote
        project.git_default_ref = git_ref
        if changed:
            project.last_synced_sha = ""
            project.last_synced_at = None
            project.sync_error = ""
            project.save(
                update_fields=[
                    "git_remote",
                    "git_default_ref",
                    "last_synced_sha",
                    "last_synced_at",
                    "sync_error",
                    "updated_at",
                ]
            )
            git_remove_cache(project_id)
        else:
            project.save(update_fields=["git_remote", "git_default_ref", "updated_at"])
            messages.info(request, "Настройки Git не изменились.")
            return redirect("ui_project_detail", project_id=project_id)
        try:
            test_remote(project)
            pull(project, force=True)
            messages.success(
                request,
                f"Git обновлён: {git_remote}, ветка {git_ref}. Кэш пересоздан.",
            )
        except GitProjectError as e:
            messages.warning(
                request,
                f"Настройки сохранены, но подключение не удалось: {e.message}",
            )
        return redirect("ui_project_detail", project_id=project_id)
    return render(
        request,
        "ui/project_git_settings.html",
        {
            "project": project,
            "git_repo_url": project.git_remote,
            "git_default_ref": project.git_default_ref,
        },
    )


@staff_only
@require_POST
def project_git_sync(request, project_id: str):
    project = get_object_or_404(Project, project_id=project_id)
    try:
        test_remote(project)
        pull(project, force=True)
        seed = seed_project_json(project.project_id, project.name)
        bootstrap_new_project(project, seed=seed, try_seed_push=True)
        messages.success(request, "Git: подключение OK, репозиторий обновлён.")
    except GitProjectError as e:
        messages.error(request, f"Git: {e.message}")
    return redirect("ui_project_detail", project_id=project_id)


@staff_only
@require_http_methods(["GET", "POST"])
def project_config(request, project_id: str):
    project = get_object_or_404(Project, project_id=project_id)
    if request.method == "POST":
        raw = request.POST.get("raw_json", "")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            messages.error(request, f"Невалидный JSON: {e}")
            return redirect("ui_project_config", project_id=project_id)
        errs = save_config_to_git(project, project_id, data)
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
        messages.success(request, "Конфиг закоммичен и отправлен в Git.")
        return redirect("ui_project_detail", project_id=project_id)
    data, err = load_config_dict(project_id)
    if err is not None:
        try:
            body = json.loads(err.content.decode())
            msg = body.get("error", {}).get("message", "Ошибка загрузки конфига из Git")
        except (json.JSONDecodeError, AttributeError):
            msg = "Ошибка загрузки конфига из Git"
        messages.error(request, msg)
        pretty = json.dumps(seed_project_json(project_id, project.name), ensure_ascii=False, indent=2)
    else:
        pretty = json.dumps(data, ensure_ascii=False, indent=2)
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
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            messages.error(request, f"Невалидный JSON: {e}")
            return redirect("ui_project_config_builder", project_id=project_id)
        errs = save_config_to_git(project, project_id, data)
        if errs:
            for e in errs:
                messages.error(request, e)
            try:
                initial_data = json.loads(raw)
            except json.JSONDecodeError:
                initial_data = seed_project_json(project.project_id, project.name)
            return render(
                request,
                "ui/project_config_builder.html",
                {
                    "project": project,
                    "initial_data": initial_data,
                    "pretty_json": json.dumps(initial_data, ensure_ascii=False, indent=2),
                    "validation_errors": errs,
                },
            )
        messages.success(request, "Конфиг закоммичен и отправлен в Git.")
        return redirect("ui_project_detail", project_id=project_id)
    data, err = load_config_dict(project_id)
    if err is not None or not data:
        initial_data = seed_project_json(project.project_id, project.name)
    else:
        initial_data = data
    pretty = json.dumps(initial_data, ensure_ascii=False, indent=2)
    return render(
        request,
        "ui/project_config_builder.html",
        {
            "project": project,
            "initial_data": initial_data,
            "pretty_json": pretty,
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
            rel = normalize_media_rel(request.POST.get("rel_path", ""))
            if not rel:
                messages.error(request, "Некорректный путь.")
            else:
                try:
                    delete_media_file(project, rel)
                    messages.success(request, f"Удалено из Git: {media_config_path(rel)}")
                except GitProjectError as e:
                    messages.error(request, e.message)
            return redirect("ui_project_media", project_id=project_id)
        f = request.FILES.get("file")
        if not f:
            msg = "Выберите файл для загрузки."
            if request.POST.get("respond") == "json":
                return JsonResponse({"ok": False, "error": msg}, status=400)
            messages.error(request, msg)
            return redirect("ui_project_media", project_id=project_id)
        rel = _allocate_auto_relative_path(project, f.name)
        data = b"".join(chunk for chunk in f.chunks())
        try:
            write_media_file(project, rel, data)
        except GitProjectError as e:
            if request.POST.get("respond") == "json":
                return JsonResponse({"ok": False, "error": e.message}, status=400)
            messages.error(request, e.message)
            return redirect("ui_project_media", project_id=project_id)
        cfg_path = media_config_path(rel)
        messages.success(request, f"Закоммичено в Git: {cfg_path}")
        if request.POST.get("respond") == "json":
            return JsonResponse(
                {
                    "ok": True,
                    "relative_path": rel,
                    "config_path": cfg_path,
                    "asset_path": cfg_path,
                }
            )
        return redirect("ui_project_media", project_id=project_id)
    try:
        pull(project, force=False)
    except GitProjectError:
        pass
    rows = list_media_files(project)
    if request.GET.get("format") == "json":
        files = [
            {
                "relative_path": rel,
                "size": size,
                "config_path": media_config_path(rel),
                "asset_path": media_config_path(rel),
            }
            for rel, size in rows
        ]
        return JsonResponse({"files": files})
    return render(
        request,
        "ui/project_media.html",
        {"project": project, "media_files": rows},
    )


@staff_only
@require_POST
def project_delete(request, project_id: str):
    project = get_object_or_404(Project, project_id=project_id)
    if request.POST.get("confirm") != project_id:
        messages.error(request, "Введите подтверждение: id проекта в поле confirm.")
        return redirect("ui_project_detail", project_id=project_id)
    cred = project.git_credential
    cred_pk = cred.pk
    project.delete()
    git_remove_cache(project_id)
    if not Project.objects.filter(git_credential_id=cred_pk).exists():
        cred.delete()
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


def package_list_legacy_redirect(request):
    """Старый URL React SPA: /ui/packages/list → /ui/packages/."""
    url = reverse("ui_package_list")
    if request.GET:
        url = f"{url}?{request.GET.urlencode()}"
    return redirect(url)


@packages_ui_required
def package_workspace_legacy_redirect(request, project_id: str, package_id: str):
    """Старый URL React SPA: /ui/packages/projects/…/packages/… → workspace."""
    return redirect("ui_package_workspace", project_id=project_id, package_id=package_id)


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

        search_ids = {f["field_id"] for f in search_fields}
        items, _err = pas.list_packages(
            project_id,
            phase="",
            preview_prefix="/ui/api/v1",
            search_field_ids=search_ids,
        )
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

    # Sidebar: без manifest_json — только колонки сессии
    side_items, _ = pas.list_package_summaries(project_id)
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
    from .project_git import GitProjectError
    from .viz_service import build_package_viz_payload

    try:
        payload = build_package_viz_payload(project_id, package_id)
    except GitProjectError as e:
        return JsonResponse({"error": e.message, "code": e.code}, status=502)
    if payload is None:
        return JsonResponse(
            {"error": "Нет collector/viz.json или данных pipeline для пакета."},
            status=404,
        )
    return JsonResponse(payload)


@packages_ui_required
def package_depth_npy(request, filename: str):
    """Legacy: .npy из datapipe_test/ (демо korovas-2026)."""
    safe = Path(filename).name
    if not safe.endswith(".npy"):
        raise Http404("Not found")
    path = pui.datapipe_dir() / safe
    if not path.is_file():
        raise Http404("Not found")
    return FileResponse(path.open("rb"), content_type="application/octet-stream")


@packages_ui_required
def package_depth_blob(request, project_id: str, package_id: str, logical_path: str):
    """Карта глубины из blob пакета (рядом с фото в media/pkg/…)."""
    denied = _forbid_package_project(request, project_id)
    if denied is not None:
        return denied
    rel = (logical_path or "").replace("\\", "/").strip("/")
    if not rel.endswith(".npy") or ".." in Path(rel).parts:
        raise Http404("Not found")
    blob = UploadedBlob.objects.filter(
        session__project__project_id=project_id,
        session__package_id=package_id,
        logical_path=rel,
    ).first()
    if not blob or not blob.file:
        raise Http404("Not found")
    return FileResponse(blob.file.open("rb"), content_type="application/octet-stream")


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
