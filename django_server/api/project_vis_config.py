"""Чтение и валидация collector/viz.json из Git-кэша проекта."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Project
from .project_git import GitProjectError, pull, repo_dir

VIS_CONFIG_REL_PATH = "collector/viz.json"
JOIN_KEY = "manifest_blob_key"

KNOWN_PLUGINS = frozenset({"keypoint_korovas", "depth_map", "yolo_detection"})
KNOWN_TABLES = frozenset(
    {"cow_keypoint_annotation", "cow_inference_result", "yolo_detection"},
)
KNOWN_PALETTES = frozenset({"gt", "inference", "yolo"})

PLUGIN_ALLOWED_TABLES: dict[str, frozenset[str]] = {
    "keypoint_korovas": frozenset({"cow_keypoint_annotation", "cow_inference_result"}),
    "depth_map": frozenset({"cow_inference_result"}),
    "yolo_detection": frozenset({"yolo_detection"}),
}

YOLO_LAYER_OPTION_KEYS = frozenset({"include_classes", "classes"})

_DEPRECATED_YOLO_KEYS = frozenset({"class_names", "class_colors"})


def _strip_json_line_comments(line: str) -> str:
    """Удаляет // комментарий вне строк JSON (для collector/viz.json)."""
    in_string = False
    escape = False
    quote = ""
    for i, ch in enumerate(line):
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch in ('"', "'"):
            if not in_string:
                in_string = True
                quote = ch
            elif quote == ch:
                in_string = False
                quote = ""
            continue
        if not in_string and ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
            return line[:i].rstrip()
    return line


def parse_vis_json_text(raw: str) -> dict[str, Any]:
    """JSON + построчные // комментарии."""
    cleaned = "\n".join(_strip_json_line_comments(ln) for ln in raw.splitlines())
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise GitProjectError(
            f"Корень {VIS_CONFIG_REL_PATH} должен быть объектом.",
            "invalid_vis_json",
        )
    return data


def _validate_yolo_layer_options(layer: dict[str, Any], lid: str, i: int, errs: list[str]) -> None:
    if layer.get("plugin") != "yolo_detection":
        return
    for dep in _DEPRECATED_YOLO_KEYS:
        if dep in layer:
            errs.append(
                f'layers[{i}] ({lid}): поле "{dep}" устарело — используйте только "classes".',
            )
    inc = layer.get("include_classes")
    if inc is not None:
        if not isinstance(inc, list) or not all(
            isinstance(x, int) and not isinstance(x, bool) for x in inc
        ):
            errs.append(f'layers[{i}] ({lid}): include_classes — массив int, напр. [0, 1].')
    classes = layer.get("classes")
    if classes is None:
        return
    if not isinstance(classes, dict) or not classes:
        errs.append(f'layers[{i}] ({lid}): classes — непустой объект {{"0": {{…}}}}.')
        return
    for k, v in classes.items():
        if not str(k).isdigit():
            errs.append(f'layers[{i}] ({lid}): classes — ключи "0", "1", … (id из YOLO .txt).')
            break
        if isinstance(v, str):
            if not v.strip():
                errs.append(f'layers[{i}] ({lid}): classes["{k}"] — непустая строка-имя.')
            continue
        if isinstance(v, dict):
            name = v.get("name") if isinstance(v.get("name"), str) else v.get("label")
            if not isinstance(name, str) or not name.strip():
                errs.append(f'layers[{i}] ({lid}): classes["{k}"].name — обязательно.')
            if v.get("color") is not None and not isinstance(v.get("color"), str):
                errs.append(f'layers[{i}] ({lid}): classes["{k}"].color — строка (#hex).')
            continue
        errs.append(
            f'layers[{i}] ({lid}): classes["{k}"] — строка или {{"name":"…","color":"#hex"}}.',
        )
        break


def layer_options_for_api(layer: dict[str, Any]) -> dict[str, Any]:
    """Опции слоя, которые UI передаёт в viz-data (плагин-специфичные)."""
    if layer.get("plugin") != "yolo_detection":
        return {}
    out: dict[str, Any] = {}
    for key in YOLO_LAYER_OPTION_KEYS:
        if key in layer:
            out[key] = layer[key]
    return out


def vis_config_path(project: Project) -> Path:
    return repo_dir(project.project_id) / VIS_CONFIG_REL_PATH


def read_vis_config_raw(
    project: Project,
    *,
    fetch_remote: bool = True,
    force_pull: bool = False,
) -> str | None:
    if fetch_remote:
        pull(project, force=force_pull)
    path = vis_config_path(project)
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def read_vis_config_dict(
    project: Project,
    *,
    fetch_remote: bool = True,
    force_pull: bool = False,
) -> dict[str, Any] | None:
    raw = read_vis_config_raw(project, fetch_remote=fetch_remote, force_pull=force_pull)
    if raw is None:
        return None
    try:
        return parse_vis_json_text(raw)
    except json.JSONDecodeError as e:
        raise GitProjectError(
            f"Невалидный JSON в {VIS_CONFIG_REL_PATH}: {e}",
            "invalid_vis_json",
        ) from e


def validate_vis_config(data: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if data.get("version") != 1:
        errs.append("version должен быть 1.")
    jk = data.get("join_key")
    if jk is not None and jk != JOIN_KEY:
        errs.append(f'join_key должен быть "{JOIN_KEY}" или опущен.')
    layers = data.get("layers")
    if not isinstance(layers, list) or not layers:
        errs.append("layers должен быть непустым массивом.")
        return errs
    seen_ids: set[str] = set()
    for i, layer in enumerate(layers):
        if not isinstance(layer, dict):
            errs.append(f"layers[{i}]: должен быть объектом.")
            continue
        lid = layer.get("id")
        if not isinstance(lid, str) or not lid.strip():
            errs.append(f"layers[{i}]: нужен непустой id.")
            continue
        if lid in seen_ids:
            errs.append(f'Дублируется id слоя "{lid}".')
        seen_ids.add(lid)
        plugin = layer.get("plugin")
        if plugin not in KNOWN_PLUGINS:
            errs.append(
                f'layers[{i}] ({lid}): неизвестный plugin "{plugin}". '
                f"Допустимо: {sorted(KNOWN_PLUGINS)}.",
            )
            continue
        table = layer.get("table")
        if table not in KNOWN_TABLES:
            errs.append(
                f'layers[{i}] ({lid}): неизвестная table "{table}". '
                f"Допустимо: {sorted(KNOWN_TABLES)}.",
            )
            continue
        allowed = PLUGIN_ALLOWED_TABLES.get(str(plugin), frozenset())
        if table not in allowed:
            errs.append(
                f'layers[{i}] ({lid}): plugin "{plugin}" не поддерживает table "{table}".',
            )
        if plugin in ("keypoint_korovas", "yolo_detection"):
            pal = layer.get("palette")
            if pal not in KNOWN_PALETTES:
                errs.append(
                    f'layers[{i}] ({lid}): для {plugin} нужен palette '
                    f"gt|inference|yolo.",
                )
        label = layer.get("label")
        if not isinstance(label, str) or not label.strip():
            errs.append(f"layers[{i}] ({lid}): нужен label.")
        dv = layer.get("default_visible")
        if dv is not None and not isinstance(dv, bool):
            errs.append(f"layers[{i}] ({lid}): default_visible должен быть boolean.")
        _validate_yolo_layer_options(layer, lid, i, errs)
    return errs


def load_vis_config(
    project: Project,
    *,
    fetch_remote: bool = True,
    force_pull: bool = False,
) -> dict[str, Any] | None:
    """Валидный конфиг визуализации или None, если файла нет."""
    data = read_vis_config_dict(
        project,
        fetch_remote=fetch_remote,
        force_pull=force_pull,
    )
    if data is None:
        return None
    errs = validate_vis_config(data)
    if errs:
        raise GitProjectError(
            f"{VIS_CONFIG_REL_PATH}: " + "; ".join(errs),
            "invalid_vis_config",
        )
    if data.get("join_key") is None:
        data = {**data, "join_key": JOIN_KEY}
    return data
