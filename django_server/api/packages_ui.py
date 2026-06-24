"""Server-side helpers for the Django-rendered packages UI."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from . import project_packages as ppkg
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
                    "path": path.replace("\\", "/"),
                    "metadata": meta if isinstance(meta, dict) else None,
                },
            )
    return shots


def _nested_map(obj: Any) -> dict[str, Any] | None:
    if isinstance(obj, dict):
        return obj
    return None


def _shot_exif(meta: dict[str, Any] | None) -> dict[str, Any]:
    if not meta:
        return {}
    direct = _nested_map(meta.get("exif"))
    if direct:
        return direct
    sup = _nested_map(meta.get("camera_supplement"))
    if sup:
        return _nested_map(sup.get("exif")) or {}
    return {}


def _shot_frame_camera(meta: dict[str, Any] | None) -> dict[str, Any]:
    if not meta:
        return {}
    return _nested_map(meta.get("frame_camera")) or {}


def format_collected_at(value: Any) -> str | None:
    dt = _parse_dt(value)
    if not dt:
        return None
    local = dt.astimezone()
    return local.strftime("%d.%m.%Y %H:%M")


def shot_meta_summary(meta: dict[str, Any] | None) -> dict[str, str]:
    """Краткая мета для карточки снимка: основная строка + доп. детали."""
    if not meta:
        return {"primary": "", "secondary": "", "when": ""}
    fc = _shot_frame_camera(meta)
    primary_parts: list[str] = []
    w, h = fc.get("image_width_px"), fc.get("image_height_px")
    if w and h:
        primary_parts.append(f"{int(w)}×{int(h)}")
    focal = fc.get("focal_length_mm")
    if focal is not None:
        primary_parts.append(f"{_fmt_num(focal)} mm")
    elif fc.get("fx_px") is not None:
        primary_parts.append(f"fx {_fmt_num(fc['fx_px'])}")

    exif = _shot_exif(meta)
    secondary_parts: list[str] = []
    iso = exif.get("ISO") or exif.get("PhotographicSensitivity")
    if iso is not None:
        secondary_parts.append(f"ISO {iso}")
    exp = exif.get("ExposureTime") or exif.get("ShutterSpeedValue")
    if exp is not None:
        secondary_parts.append(str(exp))
    model = exif.get("Model") or exif.get("LensModel")
    if model:
        secondary_parts.append(str(model))

    when = format_collected_at(meta.get("collected_at")) or ""
    return {
        "primary": " · ".join(primary_parts),
        "secondary": " · ".join(secondary_parts),
        "when": when,
    }


def shot_meta_tags(meta: dict[str, Any] | None) -> list[str]:
    """Краткие метки для карточки снимка (разрешение, фокус, ISO, время)."""
    if not meta:
        return []
    tags: list[str] = []
    fc = _shot_frame_camera(meta)
    w, h = fc.get("image_width_px"), fc.get("image_height_px")
    if w and h:
        tags.append(f"{int(w)}×{int(h)}")
    focal = fc.get("focal_length_mm")
    if focal is not None:
        tags.append(f"{_fmt_num(focal)} mm")
    elif fc.get("fx_px") is not None:
        tags.append(f"fx {_fmt_num(fc['fx_px'])}")
    exif = _shot_exif(meta)
    iso = exif.get("ISO") or exif.get("PhotographicSensitivity")
    if iso is not None:
        tags.append(f"ISO {iso}")
    exp = exif.get("ExposureTime") or exif.get("ShutterSpeedValue")
    if exp is not None:
        tags.append(str(exp))
    collected = format_collected_at(meta.get("collected_at"))
    if collected:
        tags.append(collected)
    return tags


def _fmt_num(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.1f}".rstrip("0").rstrip(".")
    return str(value)


def build_media_sections(
    root: dict[str, Any],
    fields: list[dict[str, Any]],
    data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Секции вкладки «Медиа»: снимки camera_photo по шагам scroll_form."""
    by_id = {f["field_id"]: f for f in fields}
    used_paths: set[str] = set()
    sections: list[dict[str, Any]] = []

    flow = root.get("config", {}).get("flow") if isinstance(root.get("config"), dict) else None
    steps = (flow or {}).get("steps") or [] if isinstance(flow, dict) else []

    for step in steps:
        if not isinstance(step, dict) or step.get("screen") != "scroll_form":
            continue
        field_ids = step.get("field_ids") or []
        step_fields: list[dict[str, Any]] = []
        for fid in field_ids:
            f = by_id.get(fid)
            if not f or f.get("type") != "camera_photo":
                continue
            shots = []
            for sh in extract_form_shots(data.get(fid)):
                used_paths.add(sh["path"])
                shots.append(
                    {
                        "path": sh["path"],
                        "metadata": sh["metadata"],
                        "meta": shot_meta_summary(sh["metadata"]),
                    },
                )
            if not shots:
                continue
            step_fields.append(
                {
                    "field_id": fid,
                    "label": field_label(f),
                    "shots": shots,
                },
            )
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

    orphan_fields: list[dict[str, Any]] = []
    for f in fields:
        if f.get("type") != "camera_photo":
            continue
        fid = f["field_id"]
        if any(
            any(sf["field_id"] == fid for sf in sec["fields"])
            for sec in sections
        ):
            continue
        shots = []
        for sh in extract_form_shots(data.get(fid)):
            used_paths.add(sh["path"])
            shots.append(
                {
                    "path": sh["path"],
                    "metadata": sh["metadata"],
                    "meta": shot_meta_summary(sh["metadata"]),
                },
            )
        if shots:
            orphan_fields.append(
                {
                    "field_id": fid,
                    "label": field_label(f),
                    "shots": shots,
                },
            )
    if orphan_fields:
        sections.append({"id": "_other", "title": "Прочие поля", "fields": orphan_fields})

    return sections, used_paths


def attach_blobs_to_media_sections(
    sections: list[dict[str, Any]],
    blobs_by_path: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for sec in sections:
        fields = []
        for fld in sec["fields"]:
            shots = []
            for sh in fld["shots"]:
                blob = blobs_by_path.get(sh["path"])
                if blob:
                    shots.append({**sh, **blob})
            if shots:
                fields.append({**fld, "shots": shots})
        if fields:
            out.append({**sec, "fields": fields})
    return out


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


def has_visualisation(project_id: str, package_id: str) -> bool:
    from .viz_service import package_has_visualisation

    return package_has_visualisation(project_id, package_id)


def _changelog_entry_dict(project_id: str, row: ppkg.FieldChange) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "package_id": row.package_id,
        "field_id": row.field_id,
        "before": row.before_value,
        "after": row.after_value,
        "reason": row.reason,
        "verifier_email": row.verifier_email,
        "changed_at": row.changed_at,
    }


def list_changelog_entries(
    *,
    project_id: str = "",
    package_id: str = "",
) -> list[dict[str, Any]]:
    if project_id:
        rows = ppkg.list_field_changes(project_id, package_id=package_id)
        return [_changelog_entry_dict(project_id, row) for row in rows]

    out: list[dict[str, Any]] = []
    for project in Project.objects.all().order_by("name"):
        rows = ppkg.list_field_changes(project.project_id, package_id=package_id)
        out.extend(_changelog_entry_dict(project.project_id, row) for row in rows)
    out.sort(key=lambda e: e["changed_at"], reverse=True)
    return out


def read_changelog(project_id: str, package_id: str) -> list[dict[str, Any]]:
    return list_changelog_entries(project_id=project_id, package_id=package_id)


def append_changelog(
    project_id: str,
    package_id: str,
    reason: str,
    verifier_email: str,
    changes: list[dict[str, Any]],
) -> int:
    return ppkg.append_field_changes(
        project_id,
        package_id,
        reason,
        verifier_email,
        changes,
    )
