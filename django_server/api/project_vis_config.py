"""Чтение и валидация collector/viz.json из Git-кэша проекта."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Project
from .project_git import GitProjectError, pull, repo_dir

VIS_CONFIG_REL_PATH = "collector/viz.json"
JOIN_KEY = "manifest_blob_key"

KNOWN_PLUGINS = frozenset({"keypoint_korovas", "depth_map"})
KNOWN_TABLES = frozenset({"cow_keypoint_annotation", "cow_inference_result"})
KNOWN_PALETTES = frozenset({"gt", "inference"})

PLUGIN_ALLOWED_TABLES: dict[str, frozenset[str]] = {
    "keypoint_korovas": frozenset({"cow_keypoint_annotation", "cow_inference_result"}),
    "depth_map": frozenset({"cow_inference_result"}),
}


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
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise GitProjectError(
            f"Невалидный JSON в {VIS_CONFIG_REL_PATH}: {e}",
            "invalid_vis_json",
        ) from e
    if not isinstance(data, dict):
        raise GitProjectError(
            f"Корень {VIS_CONFIG_REL_PATH} должен быть объектом.",
            "invalid_vis_json",
        )
    return data


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
        if plugin == "keypoint_korovas":
            pal = layer.get("palette")
            if pal not in KNOWN_PALETTES:
                errs.append(
                    f'layers[{i}] ({lid}): для keypoint_korovas нужен palette gt|inference.',
                )
        label = layer.get("label")
        if not isinstance(label, str) or not label.strip():
            errs.append(f"layers[{i}] ({lid}): нужен label.")
        dv = layer.get("default_visible")
        if dv is not None and not isinstance(dv, bool):
            errs.append(f"layers[{i}] ({lid}): default_visible должен быть boolean.")
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
