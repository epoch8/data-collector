"""Чтение/запись конфига проекта из Git."""

from __future__ import annotations

import json
from typing import Any

from django.http import JsonResponse

from .models import GitCredential, Project
from .project_config_validate import validate_project_payload
from .project_git import (
    DEFAULT_FORM_ID,
    GitProjectError,
    generate_ssh_key_pair,
    normalize_git_remote,
    normalize_private_key,
    public_key_from_private,
    read_config_dict,
    read_config_file,
    seed_config_if_missing,
    test_remote,
    write_config_dict,
)
from .views import _err


def seed_project_json(project_id: str, name: str) -> dict[str, Any]:
    return {
        "id": project_id,
        "name": name or project_id,
        "version": "1",
        "config": {
            "fields": [
                {
                    "field_id": "demo_text",
                    "type": "text_input",
                    "title": "Пример текста",
                    "instructions": "Заполните поле",
                    "validation": {},
                },
            ],
            "flow": {
                "steps": [
                    {
                        "id": "form1",
                        "screen": "scroll_form",
                        "form_title": "Сбор данных",
                        "field_ids": ["demo_text"],
                    },
                    {"id": "review", "screen": "review"},
                ],
            },
            "ui": {},
        },
    }


def _options_for_builder(raw: Any) -> list[dict[str, str]]:
    """Варианты single_choice для SSR-редактора (список {value, label})."""
    if not isinstance(raw, list) or not raw:
        return [{"value": "", "label": ""}]
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in raw:
        if isinstance(item, str):
            value = item.strip()
            label = value
        elif isinstance(item, dict):
            value = str(item.get("value") or "").strip()
            label = str(item.get("label") or "").strip()
            if not value:
                value = label
            if not label:
                label = value
        else:
            continue
        if not value or value in seen:
            continue
        seen.add(value)
        out.append({"value": value, "label": label})
    return out or [{"value": "", "label": ""}]


def prepare_builder_ssr_steps(initial_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Шаги сценария для SSR в визуальном редакторе (логика совпадает с loadModel в project_builder.js)."""
    cfg = (initial_data or {}).get("config") or {}
    fields_raw = cfg.get("fields") or []
    by_id: dict[str, dict[str, Any]] = {}
    for f in fields_raw:
        if isinstance(f, dict) and isinstance(f.get("field_id"), str):
            by_id[f["field_id"]] = f

    raw_steps = ((cfg.get("flow") or {}).get("steps")) or []
    steps: list[dict[str, Any]] = []
    used_ids: set[str] = set()

    for st in raw_steps:
        if not isinstance(st, dict):
            continue
        screen = str(st.get("screen", "scroll_form")).lower().replace("-", "_")
        if screen == "review":
            steps.append(
                {
                    "kind": "review",
                    "id": st.get("id") or "review",
                    "form_title": st.get("form_title") or "",
                },
            )
            continue
        field_items: list[dict[str, Any]] = []
        for fid in st.get("field_ids") or []:
            if not isinstance(fid, str) or fid in used_ids:
                continue
            f = by_id.get(fid)
            if not f:
                continue
            used_ids.add(fid)
            validation = f.get("validation") if isinstance(f.get("validation"), dict) else {}
            field_items.append(
                {
                    "field_id": fid,
                    "type": f.get("type") or "text_input",
                    "title": f.get("title") or "",
                    "instructions": f.get("instructions") or "",
                    "required": validation.get("required") is True,
                    "options": _options_for_builder(f.get("options")),
                },
            )
        steps.append(
            {
                "kind": "scroll_form",
                "id": st.get("id") or "",
                "form_title": st.get("form_title") or "",
                "cow_id_hints": st.get("cow_id_hints") is True,
                "cow_id_field_id": st.get("cow_id_field_id") or "",
                "fields": field_items,
            },
        )

    orphan = [by_id[fid] for fid in by_id if fid not in used_ids]
    first_scroll = next((s for s in steps if s["kind"] == "scroll_form"), None)
    if first_scroll is None:
        first_scroll = {
            "kind": "scroll_form",
            "id": "form1",
            "form_title": "",
            "cow_id_hints": False,
            "cow_id_field_id": "",
            "fields": [],
        }
        steps.insert(0, first_scroll)
    for f in orphan:
        validation = f.get("validation") if isinstance(f.get("validation"), dict) else {}
        first_scroll["fields"].append(
            {
                "field_id": f.get("field_id") or "",
                "type": f.get("type") or "text_input",
                "title": f.get("title") or "",
                "instructions": f.get("instructions") or "",
                "required": validation.get("required") is True,
                "options": _options_for_builder(f.get("options")),
            },
        )

    reviews = [s for s in steps if s["kind"] == "review"]
    non_review = [s for s in steps if s["kind"] != "review"]
    review = reviews[0] if reviews else {"kind": "review", "id": "review", "form_title": ""}
    ordered = non_review + [review]
    scroll_n = 0
    for st in ordered:
        if st["kind"] == "scroll_form":
            scroll_n += 1
            st["scroll_ordinal"] = scroll_n
    return ordered


def create_credential(*, label: str, private_key: str) -> GitCredential:
    if not (private_key or "").strip():
        raise GitProjectError("Укажите приватный SSH-ключ или сгенерируйте пару.", "missing_key")
    from .git_credential_crypto import encrypt_private_key

    normalized = normalize_private_key(private_key)
    try:
        public_key = public_key_from_private(normalized)
    except GitProjectError:
        raise
    except Exception as e:
        raise GitProjectError(f"Не удалось прочитать публичный ключ: {e}", "invalid_key") from e
    return GitCredential.objects.create(
        label=label,
        public_key=public_key,
        private_key_encrypted=encrypt_private_key(normalized),
    )


def update_credential_private_key(credential: GitCredential, private_key: str) -> str:
    """Обновить приватный ключ; возвращает public key."""
    from .git_credential_crypto import encrypt_private_key

    normalized = normalize_private_key(private_key)
    public_key = public_key_from_private(normalized)
    credential.public_key = public_key
    credential.private_key_encrypted = encrypt_private_key(normalized)
    credential.save(update_fields=["public_key", "private_key_encrypted"])
    return public_key


def create_credential_generated(*, label: str) -> tuple[GitCredential, str, str]:
    private_key, public_key = generate_ssh_key_pair()
    from .git_credential_crypto import encrypt_private_key

    cred = GitCredential.objects.create(
        label=label,
        public_key=public_key,
        private_key_encrypted=encrypt_private_key(private_key),
    )
    return cred, public_key, private_key


def git_error_response(exc: GitProjectError, *, status: int = 502) -> JsonResponse:
    return JsonResponse(
        _err(exc.code, exc.message),
        status=status,
    )


def load_config_dict(project_id: str) -> tuple[dict[str, Any] | None, JsonResponse | None]:
    project = Project.objects.filter(project_id=project_id).select_related("git_credential").first()
    if not project:
        return None, JsonResponse(_err("not_found", "Unknown project"), status=404)
    if not project.git_remote:
        return None, JsonResponse(_err("git_not_configured", "Project has no Git remote"), status=503)
    try:
        return read_config_dict(project, fetch_remote=True, force_pull=False), None
    except GitProjectError as e:
        return None, git_error_response(e)


def load_config_body(project_id: str) -> tuple[str | None, str | None, JsonResponse | None]:
    """Тело JSON для API и ETag (sha)."""
    project = Project.objects.filter(project_id=project_id).select_related("git_credential").first()
    if not project:
        return None, None, JsonResponse(_err("not_found", "Unknown project"), status=404)
    try:
        raw = read_config_file(project, fetch_remote=True, force_pull=False)
        project.refresh_from_db(fields=["last_synced_sha"])
        return raw, project.last_synced_sha or None, None
    except GitProjectError as e:
        return None, None, git_error_response(e)


def save_config_to_git(
    project: Project,
    project_id: str,
    data: dict[str, Any],
    *,
    form_id: str = DEFAULT_FORM_ID,
    commit_message: str | None = None,
    update_project_name: bool = False,
) -> list[str]:
    """Сохранить config формы в Git. Root name — имя формы, не имя проекта в каталоге."""
    from .project_forms import is_valid_form_id, write_form_config_dict

    data["id"] = project_id
    fid = (form_id or DEFAULT_FORM_ID).strip() or DEFAULT_FORM_ID
    if not is_valid_form_id(fid):
        return [f'Некорректный form_id "{fid}". Допустимо: [a-z0-9_]+.']
    errs = validate_project_payload(data, project_id)
    if errs:
        return errs
    try:
        msg = commit_message or f"config: update form {fid} from data-collector admin"
        write_form_config_dict(project, fid, data, commit_message=msg)
        if update_project_name and fid == DEFAULT_FORM_ID:
            name = (data.get("name") or project.name)[:512]
            if name != project.name:
                project.name = name
                project.save(update_fields=["name", "updated_at"])
    except GitProjectError as e:
        return [e.message]
    return []


def load_form_config_dict(
    project_id: str,
    form_id: str = DEFAULT_FORM_ID,
) -> tuple[dict[str, Any] | None, JsonResponse | None]:
    project = Project.objects.filter(project_id=project_id).select_related("git_credential").first()
    if not project:
        return None, JsonResponse(_err("not_found", "Unknown project"), status=404)
    if not project.git_remote:
        return None, JsonResponse(_err("git_not_configured", "Project has no Git remote"), status=503)
    from .project_forms import get_form_config

    try:
        return get_form_config(project, form_id, fetch_remote=True), None
    except GitProjectError as e:
        return None, git_error_response(e, status=404 if e.code in ("unknown_form_id", "config_missing") else 502)


def list_forms_for_admin(project: Project) -> list[dict[str, str]]:
    from .project_forms import forms_summary

    try:
        return forms_summary(project, fetch_remote=True)
    except GitProjectError:
        return []


def create_project_form(
    project: Project,
    form_id: str,
    name: str,
    *,
    copy_from: str = DEFAULT_FORM_ID,
) -> list[str]:
    """Создать forms/{form_id}/config.json (копия другой формы или пустой seed)."""
    import copy

    from .project_forms import (
        is_valid_form_id,
        list_form_ids_on_disk,
        load_project_forms,
        write_form_config_dict,
    )

    fid = (form_id or "").strip()
    if not is_valid_form_id(fid):
        return ['Некорректный form_id. Допустимо: латиница, цифры и «_».']
    display = (name or "").strip() or fid
    try:
        existing_forms = load_project_forms(project, fetch_remote=True)
    except GitProjectError:
        existing_forms = []
    existing = {f["form_id"] for f in existing_forms}
    if fid in existing:
        return [f'Форма «{fid}» уже существует.']

    # Только legacy config.json: перенести в forms/default, иначе после
    # появления forms/{new} discovery перестанет отдавать default.
    if not list_form_ids_on_disk(project) and existing_forms:
        legacy_default = next(
            (f for f in existing_forms if f["form_id"] == DEFAULT_FORM_ID),
            existing_forms[0],
        )
        try:
            write_form_config_dict(
                project,
                DEFAULT_FORM_ID,
                copy.deepcopy(legacy_default["config"]),
                commit_message="config: migrate legacy config to forms/default",
            )
        except GitProjectError as e:
            return [f"Не удалось перенести default в forms/: {e.message}"]

    seed: dict[str, Any] | None = None
    src = (copy_from or "").strip()
    if src and src != "_empty":
        try:
            forms = load_project_forms(project, fetch_remote=False)
            for f in forms:
                if f["form_id"] == src:
                    seed = copy.deepcopy(f["config"])
                    break
        except GitProjectError:
            seed = None
    if seed is None:
        seed = seed_project_json(project.project_id, display)
    seed["id"] = project.project_id
    seed["name"] = display
    if not isinstance(seed.get("version"), str) or not str(seed.get("version")).strip():
        seed["version"] = "1"
    try:
        write_form_config_dict(
            project,
            fid,
            seed,
            commit_message=f"config: create form {fid} from data-collector admin",
        )
    except GitProjectError as e:
        return [e.message]
    return []


def bootstrap_new_project(
    project: Project,
    *,
    seed: dict[str, Any],
    try_seed_push: bool = True,
) -> list[str]:
    """Проверка доступа и при необходимости seed commit. Возвращает предупреждения (не фатальные)."""
    warnings: list[str] = []
    try:
        test_remote(project)
    except GitProjectError as e:
        warnings.append(
            f"Подключение к Git пока не работает: {e.message}. "
            "Добавьте deploy key на GitHub и нажмите «Проверить Git»."
        )
        project.sync_error = e.message[:2000]
        project.save(update_fields=["sync_error", "updated_at"])
        return warnings
    if not try_seed_push:
        return warnings
    try:
        seed_config_if_missing(project, seed)
    except GitProjectError as e:
        warnings.append(f"Не удалось записать начальный config.json: {e.message}")
    return warnings
