"""Веб-интерфейс администрирования (проекты, конфиги, медиа, пакеты)."""

from __future__ import annotations

import json
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
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import check_for_language, gettext as _
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods, require_POST

from . import package_admin_service as pas
from . import packages_ui as pui
from . import project_storage_config as psc
from .firebase_user_sync import sync_collector_users_from_firebase
from . import project_packages as ppkg
from .models import CollectorUser, Project


def _storage_form_context(project: Project | None = None) -> dict:
    """Контекст для include ui/_project_storage_fields.html."""
    if project is None:
        return {}
    cfg = psc.resolve(project)
    db_user, has_db_password = psc.database_credentials_for_ui(project)
    db_stored = (project.database_uri or "").strip()
    return {
        "storage_uri_value": project.storage_uri,
        "database_uri_value": psc.strip_database_credentials(db_stored) if db_stored else "",
        "effective_storage_uri": cfg.storage_uri,
        "effective_database_uri": psc.mask_database_uri(cfg.database_uri),
        "s3_endpoint_url": cfg.storage_options.get("endpoint_url", ""),
        "s3_key": cfg.storage_options.get("key", ""),
        "has_s3_secret": bool(cfg.storage_options.get("secret")),
        "db_user": db_user,
        "has_db_password": has_db_password,
    }


def _provision_project_database(request, project) -> None:
    if not (project.database_uri or "").strip() and not (
        project.database_options_encrypted or ""
    ).strip():
        return
    ok, msg = psc.ensure_project_database(project)
    if ok:
        messages.info(request, msg)
    else:
        messages.warning(request, _("БД проекта: {msg}").format(msg=msg))


from .project_config_service import (
    bootstrap_new_project,
    create_credential,
    create_credential_generated,
    load_config_dict,
    prepare_builder_ssr_steps,
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


def ui_set_language(request):
    """Переключает язык интерфейса /ui через cookie (тумблер RU/EN в шапке)."""
    lang = (request.GET.get("lang") or "").strip()
    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER") or "/ui/"
    if not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = "/ui/"
    response = redirect(next_url)
    if lang in dict(settings.LANGUAGES) and check_for_language(lang):
        response.set_cookie(
            settings.LANGUAGE_COOKIE_NAME,
            lang,
            max_age=settings.LANGUAGE_COOKIE_AGE,
            path=settings.LANGUAGE_COOKIE_PATH,
            domain=settings.LANGUAGE_COOKIE_DOMAIN,
            samesite=settings.LANGUAGE_COOKIE_SAMESITE,
        )
    return response


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
            messages.error(request, _("Укажите project_id (как поле id в config.json)."))
            return redirect("ui_project_new")
        if Project.objects.filter(project_id=pid).exists():
            messages.error(request, _("Проект с таким id уже есть."))
            return redirect("ui_project_detail", project_id=pid)
        try:
            git_remote = normalize_git_remote(git_url)
        except GitProjectError as e:
            messages.error(request, e.message)
            return redirect("ui_project_new")
        try:
            if generate_key:
                cred, public_key, _unused = create_credential_generated(label=f"{pid} deploy")
            else:
                cred = create_credential(label=f"{pid} deploy", private_key=private_key)
                public_key = cred.public_key
        except GitProjectError as e:
            messages.error(request, e.message)
            return redirect("ui_project_new")
        storage_uri, database_uri, st_enc, db_enc = psc.save_storage_from_post(request.POST)
        project = Project.objects.create(
            project_id=pid,
            name=name,
            git_remote=git_remote,
            git_default_ref=(request.POST.get("git_default_ref") or "main").strip() or "main",
            git_credential=cred,
            storage_uri=storage_uri,
            database_uri=database_uri,
            storage_options_encrypted=st_enc,
            database_options_encrypted=db_enc,
        )
        _provision_project_database(request, project)
        seed = seed_project_json(pid, name)
        for w in bootstrap_new_project(project, seed=seed):
            messages.warning(request, w)
        if generate_key:
            messages.info(
                request,
                _(
                    "Добавьте deploy key в GitHub (Settings → Deploy keys, с write access). "
                    "Публичный ключ — на странице проекта."
                ),
            )
        messages.success(
            request,
            _("Проект {pid} создан. Git: {git}").format(pid=pid, git=git_remote),
        )
        request.session[f"git_public_key_{pid}"] = public_key
        return redirect("ui_project_detail", project_id=pid)
    return render(request, "ui/project_new.html", {})


@staff_only
def project_detail(request, project_id: str):
    project = get_object_or_404(Project, project_id=project_id)
    package_count = 0
    project_db_error = ""
    try:
        package_count = len(ppkg.list_sessions(project.project_id))
    except Exception:
        project_db_error = _(
            "БД проекта недоступна. Проверьте настройки хранилища "
            "или нажмите «Проверить хранилище»."
        )
    public_key = request.session.pop(f"git_public_key_{project_id}", None) or project.git_credential.public_key
    cfg = psc.resolve(project)
    return render(
        request,
        "ui/project_detail.html",
        {
            "project": project,
            "package_count": package_count,
            "project_db_error": project_db_error,
            "is_staff": request.user.is_staff,
            "git_public_key": public_key,
            "effective_storage_uri": cfg.storage_uri,
            "effective_database_uri": psc.mask_database_uri(cfg.database_uri),
            "storage_is_default": not (project.storage_uri or "").strip(),
            "database_is_default": not (project.database_uri or "").strip()
            and not (project.database_options_encrypted or "").strip(),
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
            messages.error(request, _("Вставьте приватный ключ OpenSSH."))
            return redirect("ui_project_update_ssh_key", project_id=project_id)
        try:
            public_key = update_credential_private_key(project.git_credential, private_key)
            request.session[f"git_public_key_{project_id}"] = public_key
            messages.success(
                request,
                _("Приватный ключ обновлён. Если public key изменился — обновите Deploy key на GitHub."),
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
            messages.error(request, _("Укажите URL репозитория GitHub."))
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
            messages.info(request, _("Настройки Git не изменились."))
            return redirect("ui_project_detail", project_id=project_id)
        try:
            test_remote(project)
            pull(project, force=True)
            messages.success(
                request,
                _("Git обновлён: {remote}, ветка {ref}. Кэш пересоздан.").format(
                    remote=git_remote, ref=git_ref,
                ),
            )
        except GitProjectError as e:
            messages.warning(
                request,
                _("Настройки сохранены, но подключение не удалось: {error}").format(
                    error=e.message,
                ),
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
        messages.success(request, _("Git: подключение OK, репозиторий обновлён."))
    except GitProjectError as e:
        messages.error(request, _("Git: {error}").format(error=e.message))
    return redirect("ui_project_detail", project_id=project_id)


@staff_only
@require_http_methods(["GET", "POST"])
def project_storage_settings(request, project_id: str):
    project = get_object_or_404(Project, project_id=project_id)
    if request.method == "POST":
        existing_st = psc.decode_storage_options(project.storage_options_encrypted)
        existing_db = psc.decode_database_options(project.database_options_encrypted)
        storage_uri, database_uri, st_enc, db_enc = psc.save_storage_from_post(
            request.POST,
            existing_storage=existing_st,
            existing_db=existing_db,
        )
        project.storage_uri = storage_uri
        project.database_uri = database_uri
        project.storage_options_encrypted = st_enc
        project.database_options_encrypted = db_enc
        project.save(
            update_fields=[
                "storage_uri",
                "database_uri",
                "storage_options_encrypted",
                "database_options_encrypted",
                "updated_at",
            ]
        )
        _provision_project_database(request, project)
        messages.success(request, _("Настройки хранилища сохранены."))
        return redirect("ui_project_detail", project_id=project_id)
    return render(
        request,
        "ui/project_storage_settings.html",
        {"project": project, **_storage_form_context(project)},
    )


@staff_only
@require_POST
def project_storage_check(request, project_id: str):
    project = get_object_or_404(Project, project_id=project_id)
    cfg = psc.resolve(project)
    try:
        for note in psc.check_storage(cfg):
            messages.info(request, note)
        messages.success(request, _("Хранилище: проверка завершена."))
    except Exception as e:  # noqa: BLE001 — показываем причину пользователю
        messages.error(request, _("Хранилище: ошибка подключения — {error}").format(error=e))
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
            messages.error(request, _("Невалидный JSON: {error}").format(error=e))
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
        messages.success(request, _("Конфиг закоммичен и отправлен в Git."))
        return redirect("ui_project_detail", project_id=project_id)
    data, err = load_config_dict(project_id)
    if err is not None:
        try:
            body = json.loads(err.content.decode())
            msg = body.get("error", {}).get("message", _("Ошибка загрузки конфига из Git"))
        except (json.JSONDecodeError, AttributeError):
            msg = _("Ошибка загрузки конфига из Git")
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

    def _builder_context(project: Project, initial_data: dict, **extra):
        return {
            "project": project,
            "initial_data": initial_data,
            "pretty_json": json.dumps(initial_data, ensure_ascii=False, indent=2),
            "builder_ssr_steps": prepare_builder_ssr_steps(initial_data),
            **extra,
        }

    project = get_object_or_404(Project, project_id=project_id)
    if request.method == "POST":
        raw = request.POST.get("raw_json", "")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            messages.error(request, _("Невалидный JSON: {error}").format(error=e))
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
                _builder_context(project, initial_data, validation_errors=errs),
            )
        messages.success(request, _("Конфиг закоммичен и отправлен в Git."))
        return redirect("ui_project_detail", project_id=project_id)
    data, err = load_config_dict(project_id)
    if err is not None or not data:
        initial_data = seed_project_json(project.project_id, project.name)
    else:
        initial_data = data
    return render(
        request,
        "ui/project_config_builder.html",
        _builder_context(project, initial_data),
    )


@staff_only
@require_POST
def project_config_validate_api(request, project_id: str):
    """POST JSON тела проекта — ответ { ok, errors } без сохранения."""
    try:
        data = json.loads(request.body.decode())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "errors": [_("Тело запроса не является JSON.")]}, status=400)
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
                messages.error(request, _("Некорректный путь."))
            else:
                try:
                    delete_media_file(project, rel)
                    messages.success(
                        request,
                        _("Удалено из Git: {path}").format(path=media_config_path(rel)),
                    )
                except GitProjectError as e:
                    messages.error(request, e.message)
            return redirect("ui_project_media", project_id=project_id)
        f = request.FILES.get("file")
        if not f:
            msg = _("Выберите файл для загрузки.")
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
        messages.success(request, _("Закоммичено в Git: {path}").format(path=cfg_path))
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
        messages.error(request, _("Введите подтверждение: id проекта в поле confirm."))
        return redirect("ui_project_detail", project_id=project_id)
    cred = project.git_credential
    cred_pk = cred.pk
    project.delete()
    git_remove_cache(project_id)
    if not Project.objects.filter(git_credential_id=cred_pk).exists():
        cred.delete()
    messages.success(request, _("Проект удалён."))
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
        return HttpResponseForbidden(_("Нет доступа к этому проекту."))
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
            {"id": p, "label": (_("Все") if p == "all" else pui.phase_label(p)), "active": p == phase}
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


def _enrich_blob(project_id, package_id, blob, form_blob_paths, *, field_id="", field_label=""):
    path = blob["logical_path"]
    return {
        "blob_id": blob["blob_id"],
        "logical_path": path,
        "file_name": pui.blob_file_name(path),
        "size_bytes": blob["size_bytes"],
        "is_image": pui.is_image_path(path),
        "in_form": path in form_blob_paths,
        "field_id": field_id,
        "field_label": field_label,
        "url": reverse(
            "ui_package_blob_download",
            args=[project_id, package_id, path],
        ),
    }


def _build_media_context(project_id, package_id, config, fields, data, raw_blobs):
    form_blob_paths = pui.collect_form_blob_paths(data)
    media_sections, used_paths = pui.build_media_sections(config, fields, data)
    blobs_by_path = {}
    for b in raw_blobs:
        path = b["logical_path"]
        blobs_by_path[path] = _enrich_blob(
            project_id, package_id, b, form_blob_paths,
        )
    media_sections = pui.attach_blobs_to_media_sections(media_sections, blobs_by_path)
    orphan_blobs = [
        blobs_by_path[path]
        for path in sorted(blobs_by_path)
        if path not in used_paths
    ]
    all_blobs = list(blobs_by_path.values())
    return media_sections, orphan_blobs, all_blobs, form_blob_paths


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
    is_editable = session["phase"] == ppkg.Phase.COMPLETED
    data_sections = _build_data_sections(sections, data, is_editable)

    form_blob_paths = pui.collect_form_blob_paths(data)
    media_sections, orphan_blobs, blobs, _ = _build_media_context(
        project_id, package_id, config, fields, data, body["blobs"],
    )

    entries = pui.read_changelog(project_id, package_id)
    has_viz = pui.has_visualisation(project_id, package_id)
    blob_map = {b["logical_path"]: b["url"] for b in blobs}
    manifest_json = json.dumps(manifest, ensure_ascii=False, indent=2)

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
            "media_sections": media_sections,
            "orphan_blobs": orphan_blobs,
            "blobs": blobs,
            "blob_count": len(blobs),
            "manifest_json": manifest_json,
            "entries": entries,
            "has_viz": has_viz,
            "blob_map_json": json.dumps(blob_map, ensure_ascii=False),
            "sidebar": sidebar,
            "list_url": reverse("ui_package_list") + f"?project={project_id}",
            "save_url": reverse("ui_package_manifest_save", args=[project_id, package_id]),
            "delete_url": reverse("ui_package_delete", args=[project_id, package_id]),
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
    if session["phase"] != ppkg.Phase.COMPLETED:
        messages.error(request, _("Редактировать можно только пакеты в статусе «Завершён»."))
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
        messages.info(request, _("Изменений нет."))
        return redirect("ui_package_workspace", project_id=project_id, package_id=package_id)

    reason = (request.POST.get("reason") or "").strip()
    if not reason:
        messages.error(request, _("Укажите причину корректировки."))
        return redirect("ui_package_workspace", project_id=project_id, package_id=package_id)

    manifest["data"] = data
    manifest["project_id"] = project_id
    if ppkg.get_session(project_id, package_id) is None:
        raise Http404("Package not found")

    patch_resp = pas.patch_manifest(
        project_id, package_id, json.dumps(manifest, ensure_ascii=False),
    )
    if patch_resp.status_code != 200:
        try:
            detail = json.loads(patch_resp.content.decode("utf-8"))
            msg = detail.get("error", {}).get("message", _("Ошибка сохранения"))
        except (json.JSONDecodeError, AttributeError):
            msg = _("Ошибка сохранения")
        messages.error(request, _("Не удалось сохранить: {msg}").format(msg=msg))
        return redirect("ui_package_workspace", project_id=project_id, package_id=package_id)

    pui.append_changelog(
        project_id, package_id, reason, _ui_verifier_email(request), changes,
    )
    messages.success(request, _("Сохранено. Изменено полей: {n}.").format(n=len(changes)))
    return redirect("ui_package_workspace", project_id=project_id, package_id=package_id)


@packages_ui_required
@require_POST
def package_delete(request, project_id: str, package_id: str):
    denied = _forbid_package_project(request, project_id)
    if denied is not None:
        return denied

    project = Project.objects.filter(project_id=project_id).first()
    if not project:
        raise Http404("Project not found")

    session = ppkg.get_session(project_id, package_id)
    if not session:
        messages.error(request, _("Пакет не найден."))
        return redirect(reverse("ui_package_list") + f"?project={project_id}")

    if request.POST.get("confirm") != "yes":
        messages.error(request, _("Подтвердите удаление."))
        return redirect("ui_package_workspace", project_id=project_id, package_id=package_id)

    ppkg.delete_session(
        project_id,
        package_id,
        media_bucket=(project.media_bucket or ""),
    )
    messages.success(
        request,
        _("Пакет {pid} удалён.").format(pid=pui.short_package_id(package_id)),
    )
    return redirect(reverse("ui_package_list") + f"?project={project_id}")


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
            {"error": _("Нет collector/viz.json или данных pipeline для пакета.")},
            status=404,
        )
    return JsonResponse(payload)


@packages_ui_required
def package_depth_blob(request, project_id: str, package_id: str, logical_path: str):
    """Карта глубины из blob пакета (project_media/…)."""
    denied = _forbid_package_project(request, project_id)
    if denied is not None:
        return denied
    rel = (logical_path or "").replace("\\", "/").strip("/")
    if not rel.endswith(".npy") or ".." in Path(rel).parts:
        raise Http404("Not found")
    project = Project.objects.filter(project_id=project_id).first()
    blob = ppkg.get_blob_by_path(project_id, package_id, rel)
    if not blob:
        raise Http404("Not found")
    from . import project_media as pm

    resp = pm.blob_file_response(
        project_id,
        blob.storage_path,
        blob.logical_path,
        media_bucket=(project.media_bucket if project else "") or "",
    )
    if resp is None:
        raise Http404("Not found")
    return resp


@packages_ui_required
def package_blob_download(request, project_id: str, package_id: str, logical_path: str):
    denied = _forbid_package_project(request, project_id)
    if denied is not None:
        return denied
    logical = (logical_path or "").replace("\\", "/")
    blob = ppkg.get_blob_by_path(project_id, package_id, logical)
    if not blob:
        raise Http404("Not found")
    project = Project.objects.filter(project_id=project_id).first()
    from . import project_media as pm

    resp = pm.blob_file_response(
        project_id,
        blob.storage_path,
        blob.logical_path,
        media_bucket=(project.media_bucket if project else "") or "",
    )
    if resp is None:
        return HttpResponseForbidden(_("Нет файла"))
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
            _(
                "Firebase: импортировано пользователей из консоли — {total} "
                "(новых записей {created}, обновлён email {updated})."
            ).format(
                total=r.total_firebase,
                created=r.created,
                updated=r.updated_email,
            ),
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
        messages.success(request, _("Права доступа сохранены."))
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
