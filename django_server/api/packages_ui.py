"""Server-side helpers for the Django-rendered packages UI (ex client-admin)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from django.conf import settings

from .models import Project

# ── Phases ──────────────────────────────────────────────────────────────────

PHASE_LABELS: dict[str, str] = {
    "completed": "Завершён",
    "awaiting_blobs": "Ожидает файлы",
    "ready_to_commit": "Готов к commit",
    "failed": "Ошибка",
    "uploading": "Загрузка",
}


def phase_label(phase: str) -> str:
    return PHASE_LABELS.get(phase, phase)


def phase_options(items: list[dict[str, Any]]) -> list[str]:
    """['all', 'completed', ...прочие фазы, что встречаются]."""
    present = {it.get("phase") for it in items if it.get("phase")}
    rest = sorted(p for p in present if p != "completed")
    return ["all", "completed", *rest]


# ── Config / fields ───────────────────────────────────────────────────────────

DATA_TAB_TYPES = ("text_input", "datetime")


def config_root(project: Project) -> dict[str, Any]:
    from .project_config_service import load_config_dict

    root, err = load_config_dict(project.project_id)
    if err or not root:
        return {}
    return root


def config_fields(root: dict[str, Any]) -> list[dict[str, Any]]:
    fields = (root.get("config") or {}).get("fields") or []
    return [f for f in fields if isinstance(f, dict) and f.get("field_id")]


def is_data_tab_field(field: dict[str, Any]) -> bool:
    return field.get("type") in DATA_TAB_TYPES


def searchable_fields(fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [f for f in fields if is_data_tab_field(f)]


def field_label(field: dict[str, Any]) -> str:
    return field.get("title") or field.get("field_id") or ""


def field_required(field: dict[str, Any]) -> bool:
    validation = field.get("validation")
    if isinstance(validation, dict):
        return bool(validation.get("required"))
    return False


def field_hint(field: dict[str, Any]) -> str:
    return (field.get("instructions") or "").strip()


def build_flow_sections(
    root: dict[str, Any],
    fields: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Секции вкладки «Данные» из config.flow.steps (только scroll_form)."""
    by_id = {f["field_id"]: f for f in fields}
    used: set[str] = set()
    sections: list[dict[str, Any]] = []

    flow = root.get("config", {}).get("flow") if isinstance(root.get("config"), dict) else None
    steps = (flow or {}).get("steps") or [] if isinstance(flow, dict) else []

    for step in steps:
        if not isinstance(step, dict):
            continue
        if step.get("screen") != "scroll_form":
            continue
        field_ids = step.get("field_ids") or []
        if not field_ids:
            continue
        step_fields: list[dict[str, Any]] = []
        for fid in field_ids:
            f = by_id.get(fid)
            if not f or not is_data_tab_field(f):
                continue
            step_fields.append(f)
            used.add(fid)
        if not step_fields:
            continue
        title = (step.get("form_title") or "").strip() or step.get("id") or "Форма"
        sections.append(
            {
                "id": step.get("id") or "-".join(field_ids),
                "title": title,
                "fields": step_fields,
            },
        )

    orphan = [f for f in fields if is_data_tab_field(f) and f["field_id"] not in used]
    if orphan:
        sections.append({"id": "_other", "title": "Прочее", "fields": orphan})

    if not sections:
        all_fields = [f for f in fields if is_data_tab_field(f)]
        if all_fields:
            sections.append({"id": "_all", "title": "Данные", "fields": all_fields})

    return sections


# ── Blob references in manifest.data ────────────────────────────────────────

def collect_form_blob_paths(data: Any) -> set[str]:
    out: set[str] = set()

    def walk(obj: Any) -> None:
        if isinstance(obj, str):
            if obj.startswith("blobs/"):
                out.add(obj.replace("\\", "/"))
        elif isinstance(obj, list):
            for v in obj:
                walk(v)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                key = str(k).replace("\\", "/")
                if key.startswith("blobs/"):
                    out.add(key)
                walk(v)

    walk(data)
    return out


def extract_form_shots(value: Any) -> list[dict[str, Any]]:
    """camera_photo поле: пути blobs/* внутри manifest.data[field_id]."""
    if not isinstance(value, dict):
        return []
    shots = []
    for path, meta in value.items():
        if isinstance(path, str) and path.startswith("blobs/"):
            shots.append(
                {
                    "path": path,
                    "metadata": meta if isinstance(meta, dict) else None,
                },
            )
    return shots


# ── List filtering ────────────────────────────────────────────────────────────

def _parse_dt(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value / 1000 if value > 1e11 else value, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        raw = value.strip()
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return None
    return None


def _local_date_key(value: Any) -> str | None:
    dt = _parse_dt(value)
    if not dt:
        return None
    return dt.strftime("%Y-%m-%d")


def filter_packages(
    items: list[dict[str, Any]],
    fields: list[dict[str, Any]],
    *,
    phase: str,
    mode: str,
    field_id: str,
    text: str,
    date: str,
) -> list[dict[str, Any]]:
    result = items if phase == "all" else [p for p in items if p.get("phase") == phase]

    selected = next((f for f in fields if f.get("field_id") == field_id), None)
    is_datetime = bool(selected and selected.get("type") == "datetime")

    if mode == "field" and field_id:
        if is_datetime:
            if date:
                result = [
                    p
                    for p in result
                    if _local_date_key((p.get("data_fields") or {}).get(field_id)) == date
                ]
        else:
            q = (text or "").strip().lower()
            if q:
                result = [
                    p
                    for p in result
                    if q in str((p.get("data_fields") or {}).get(field_id) or "").lower()
                ]
        return result

    q = (text or "").strip().lower()
    if not q:
        return result
    return [
        p
        for p in result
        if q in (p.get("package_id") or "").lower()
        or q in (p.get("uploader_email") or "").lower()
    ]


# ── Misc formatting ─────────────────────────────────────────────────────────

def short_package_id(pid: str) -> str:
    return f"{pid[:8]}…" if len(pid) > 12 else pid


def blob_file_name(path: str) -> str:
    parts = path.replace("\\", "/").split("/")
    return parts[-1] or path


IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")


def is_image_path(path: str) -> bool:
    return path.lower().endswith(IMAGE_EXTS)


# ── datapipe_test mock data (visualisation) + field changelog ────────────────

def datapipe_dir() -> Path:
    return Path(settings.BASE_DIR).parent / "datapipe_test"


def _load_records(filename: str) -> list[dict[str, Any]]:
    path = datapipe_dir() / filename
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    records = data.get("records") if isinstance(data, dict) else None
    return records if isinstance(records, list) else []


def has_visualisation(project_id: str, package_id: str) -> bool:
    from .viz_service import package_has_visualisation

    return package_has_visualisation(project_id, package_id)


def changelog_path() -> Path:
    return datapipe_dir() / "field_changelog.json"


def read_changelog(project_id: str, package_id: str) -> list[dict[str, Any]]:
    path = changelog_path()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    entries = [
        e
        for e in data
        if isinstance(e, dict)
        and e.get("project_id") == project_id
        and e.get("package_id") == package_id
    ]
    entries.sort(key=lambda e: str(e.get("changed_at") or ""), reverse=True)
    return entries


def append_changelog(
    project_id: str,
    package_id: str,
    reason: str,
    verifier_email: str,
    changes: list[dict[str, Any]],
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    normalized = [
        {
            "project_id": project_id,
            "package_id": package_id,
            "field_id": c["field_id"],
            "before": c.get("before"),
            "after": c.get("after"),
            "reason": reason,
            "verifier_email": verifier_email,
            "changed_at": now,
        }
        for c in changes
        if c.get("field_id")
    ]
    if not normalized:
        return 0
    path = changelog_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: list = []
    if path.is_file():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                existing = raw
        except (json.JSONDecodeError, OSError):
            existing = []
    existing.extend(normalized)
    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(normalized)
