"""Профили протокола бонитировки из Git: collector/protocol/{profile_id}.json.

Привязка к формам — в самом профиле:
  { "id": "cow", "form_ids": ["cow", "cow_inference"], ... }
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .models import Project
from .project_git import GitProjectError, pull, repo_dir

PROTOCOL_REL_DIR = "collector/protocol"
_PROFILE_ID_RE = re.compile(r"^[a-z0-9_]+$")


def protocol_profile_rel_path(profile_id: str) -> str:
    return f"{PROTOCOL_REL_DIR}/{profile_id}.json"


def is_valid_profile_id(profile_id: str) -> bool:
    return bool(profile_id and _PROFILE_ID_RE.fullmatch(profile_id))


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise GitProjectError(f"Невалидный JSON в {path.name}: {e}", "invalid_json") from e
    if not isinstance(data, dict):
        raise GitProjectError(f"Корень {path.name} должен быть объектом.", "invalid_json")
    return data


def _protocol_dir(project_id: str) -> Path:
    return repo_dir(project_id) / PROTOCOL_REL_DIR


def list_protocol_profiles(
    project_id: str,
    *,
    fetch_remote: bool = False,
) -> list[dict[str, Any]]:
    """Все профили collector/protocol/*.json."""
    if fetch_remote:
        try:
            project = Project.objects.filter(project_id=project_id).first()
            if project is not None:
                pull(project)
        except GitProjectError:
            pass
    root = _protocol_dir(project_id)
    if not root.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json")):
        stem = path.stem
        if not is_valid_profile_id(stem):
            continue
        try:
            doc = _read_json(path)
        except GitProjectError:
            continue
        if not doc.get("id"):
            doc["id"] = stem
        out.append(doc)
    return out


def load_protocol_profile(
    project_id: str,
    profile_id: str,
    *,
    fetch_remote: bool = False,
) -> dict[str, Any] | None:
    """Загрузить collector/protocol/{id}.json. None если файла нет."""
    if not is_valid_profile_id(profile_id):
        return None
    if fetch_remote:
        try:
            project = Project.objects.filter(project_id=project_id).first()
            if project is not None:
                pull(project)
        except GitProjectError:
            pass
    path = repo_dir(project_id) / protocol_profile_rel_path(profile_id)
    if not path.is_file():
        return None
    doc = _read_json(path)
    if not doc.get("id"):
        doc["id"] = profile_id
    return doc


def resolve_protocol_profile_for_form(
    project_id: str,
    form_id: str,
    *,
    fetch_remote: bool = False,
) -> dict[str, Any] | None:
    """Найти профиль, у которого form_id входит в form_ids."""
    fid = (form_id or "").strip()
    if not fid:
        return None
    for profile in list_protocol_profiles(project_id, fetch_remote=fetch_remote):
        raw = profile.get("form_ids")
        if not isinstance(raw, list):
            continue
        ids = {str(x).strip() for x in raw if isinstance(x, str) and str(x).strip()}
        if fid in ids:
            return profile
    return None


def profile_field_catalog(profile: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """field_id → дескриптор поля из профиля (title/type/options)."""
    out: dict[str, dict[str, Any]] = {}
    raw = profile.get("fields")
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        fid = item.get("field_id")
        if not isinstance(fid, str) or not fid.strip():
            continue
        out[fid.strip()] = item
    return out


def profile_section_ids(profile: dict[str, Any], key: str) -> list[str]:
    raw = profile.get(key)
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, str):
            continue
        fid = item.strip()
        if not fid or fid in seen:
            continue
        seen.add(fid)
        out.append(fid)
    return out
