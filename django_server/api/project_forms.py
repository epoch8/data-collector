"""
Несколько форм в проекте (specs/10-project-multiple-forms.md).

Discovery:
1) collector/forms/{form_id}/config.json
2) legacy collector/config.json → form_id=default
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .models import Project
from .project_config_validate import validate_project_payload
from .project_git import (
    CONFIG_REL_PATH,
    DEFAULT_FORM_ID,
    FORMS_REL_DIR,
    GitProjectError,
    commit_text_files,
    pull,
    repo_dir,
)

_FORM_ID_RE = re.compile(r"^[a-z0-9_]+$")


def form_config_rel_path(form_id: str) -> str:
    return f"{FORMS_REL_DIR}/{form_id}/config.json"


def form_config_path(project: Project, form_id: str) -> Path:
    return repo_dir(project.project_id) / form_config_rel_path(form_id)


def is_valid_form_id(form_id: str) -> bool:
    return bool(form_id and _FORM_ID_RE.fullmatch(form_id))


def _read_json_file(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise GitProjectError(f"Невалидный JSON в {path.name}: {e}", "invalid_json") from e
    if not isinstance(data, dict):
        raise GitProjectError(f"Корень {path.name} должен быть объектом.", "invalid_json")
    return data


def _form_display_name(config: dict[str, Any], form_id: str) -> str:
    name = config.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return form_id


def _form_version(config: dict[str, Any]) -> str:
    ver = config.get("version")
    if isinstance(ver, str) and ver.strip():
        return ver.strip()
    return "1"


def list_form_ids_on_disk(project: Project) -> list[str]:
    """form_id на диске (без pull). default первым, остальные по алфавиту."""
    forms_root = repo_dir(project.project_id) / FORMS_REL_DIR
    found: list[str] = []
    if forms_root.is_dir():
        for child in forms_root.iterdir():
            if not child.is_dir():
                continue
            fid = child.name
            if not is_valid_form_id(fid):
                continue
            if (child / "config.json").is_file():
                found.append(fid)
    found.sort()
    if DEFAULT_FORM_ID in found:
        found.remove(DEFAULT_FORM_ID)
        found.insert(0, DEFAULT_FORM_ID)
    return found


def project_has_any_config(project: Project) -> bool:
    dest = repo_dir(project.project_id)
    if list_form_ids_on_disk(project):
        return True
    return (dest / CONFIG_REL_PATH).is_file()


def load_project_forms(
    project: Project,
    *,
    fetch_remote: bool = True,
    force_pull: bool = False,
) -> list[dict[str, Any]]:
    """
    Список форм: [{form_id, name, version, config}, ...].
    config — полный project JSON формы.
    """
    if fetch_remote:
        pull(project, force=force_pull)

    forms: list[dict[str, Any]] = []
    for form_id in list_form_ids_on_disk(project):
        path = form_config_path(project, form_id)
        data = _read_json_file(path)
        forms.append(
            {
                "form_id": form_id,
                "name": _form_display_name(data, form_id),
                "version": _form_version(data),
                "config": data,
            },
        )

    if forms:
        return forms

    legacy = repo_dir(project.project_id) / CONFIG_REL_PATH
    if legacy.is_file():
        data = _read_json_file(legacy)
        return [
            {
                "form_id": DEFAULT_FORM_ID,
                "name": _form_display_name(data, DEFAULT_FORM_ID),
                "version": _form_version(data),
                "config": data,
            },
        ]

    raise GitProjectError(
        f"В репозитории нет форм ({FORMS_REL_DIR}/*/config.json) "
        f"и нет legacy {CONFIG_REL_PATH}.",
        "config_missing",
    )


def forms_summary(project: Project, *, fetch_remote: bool = True) -> list[dict[str, str]]:
    forms = load_project_forms(project, fetch_remote=fetch_remote)
    return [
        {
            "form_id": f["form_id"],
            "name": f["name"],
            "version": f["version"],
        }
        for f in forms
    ]


def get_form_config(
    project: Project,
    form_id: str,
    *,
    fetch_remote: bool = True,
) -> dict[str, Any]:
    forms = load_project_forms(project, fetch_remote=fetch_remote)
    for f in forms:
        if f["form_id"] == form_id:
            return f["config"]
    raise GitProjectError(f'Неизвестная форма "{form_id}".', "unknown_form_id")


def get_default_form_config(project: Project, *, fetch_remote: bool = True) -> dict[str, Any]:
    forms = load_project_forms(project, fetch_remote=fetch_remote)
    for f in forms:
        if f["form_id"] == DEFAULT_FORM_ID:
            return f["config"]
    return forms[0]["config"]


def write_form_config_dict(
    project: Project,
    form_id: str,
    data: dict[str, Any],
    *,
    commit_message: str | None = None,
) -> str:
    """Записать forms/{form_id}/config.json. Для default также обновляет legacy config.json."""
    if not is_valid_form_id(form_id):
        raise GitProjectError(
            f'Некорректный form_id "{form_id}". Допустимо: [a-z0-9_]+.',
            "invalid_form_id",
        )
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    files = {form_config_rel_path(form_id): text}
    if form_id == DEFAULT_FORM_ID:
        files[CONFIG_REL_PATH] = text
    return commit_text_files(
        project,
        files,
        commit_message=commit_message or f"config: update form {form_id} from data-collector admin",
    )


def validate_form_exists(
    project: Project,
    form_id: str | None,
    *,
    fetch_remote: bool = True,
) -> str:
    """Нормализует form_id; пустой → default. Бросает GitProjectError если нет такой формы."""
    fid = (form_id or "").strip() or DEFAULT_FORM_ID
    if not is_valid_form_id(fid):
        raise GitProjectError(f'Некорректный form_id "{fid}".', "invalid_form_id")
    forms = load_project_forms(project, fetch_remote=fetch_remote)
    ids = {f["form_id"] for f in forms}
    if fid not in ids:
        raise GitProjectError(f'Неизвестная форма "{fid}".', "unknown_form_id")
    return fid


def normalize_manifest_form_id(manifest: dict[str, Any]) -> str:
    """form_id из манифеста; пустой/отсутствует → default."""
    raw = manifest.get("form_id")
    if raw is None or raw == "":
        return DEFAULT_FORM_ID
    if not isinstance(raw, str) or not is_valid_form_id(raw):
        raise GitProjectError(
            f'Некорректный form_id в манифесте: {raw!r}.',
            "invalid_form_id",
        )
    return raw


def validate_form_payload(data: dict[str, Any], project_id: str, form_id: str) -> list[str]:
    errs = validate_project_payload(data, project_id)
    if not is_valid_form_id(form_id):
        errs.append(f'Некорректный form_id "{form_id}".')
    return errs
