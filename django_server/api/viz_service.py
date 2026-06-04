"""Данные визуализации: Git vis config + project SQLite."""

from __future__ import annotations

from typing import Any

from .models import Project
from .project_vis_config import load_vis_config
from .viz_plugins import fetch_table, layer_options_for_api


def _fetch_layer_records(
    project_id: str,
    package_id: str,
    layer: dict[str, Any],
) -> list[dict[str, Any]]:
    table = layer.get("table")
    plugin = layer.get("plugin")
    if not isinstance(table, str) or not isinstance(plugin, str):
        return []
    return fetch_table(project_id, package_id, table, plugin)


def package_has_visualisation(project_id: str, package_id: str) -> bool:
    project = Project.objects.filter(project_id=project_id).first()
    if not project or not project.git_remote:
        return False
    try:
        vis = load_vis_config(project, fetch_remote=False)
    except Exception:
        return False
    if not vis:
        return False
    for layer in vis.get("layers") or []:
        if not isinstance(layer, dict):
            continue
        if _fetch_layer_records(project_id, package_id, layer):
            return True
    return False


def build_package_viz_payload(
    project_id: str,
    package_id: str,
) -> dict[str, Any] | None:
    project = Project.objects.filter(project_id=project_id).first()
    if not project:
        return None
    try:
        vis = load_vis_config(project, fetch_remote=False)
    except Exception:
        vis = None
    if not vis:
        try:
            vis = load_vis_config(project, fetch_remote=True)
        except Exception:
            return None
    if not vis:
        return None

    layers_meta = []
    data: dict[str, list[dict[str, Any]]] = {}
    has_any = False

    for layer in vis.get("layers") or []:
        if not isinstance(layer, dict):
            continue
        lid = layer.get("id")
        table = layer.get("table")
        if not isinstance(lid, str) or not isinstance(table, str):
            continue
        records = _fetch_layer_records(project_id, package_id, layer)
        if records:
            has_any = True
        data[lid] = records
        meta: dict[str, Any] = {
            "id": lid,
            "label": layer.get("label") or lid,
            "plugin": layer.get("plugin"),
            "table": table,
            "palette": layer.get("palette"),
            "default_visible": bool(layer.get("default_visible")),
        }
        meta.update(layer_options_for_api(layer))
        layers_meta.append(meta)

    if not has_any:
        return None

    return {
        "version": vis.get("version", 1),
        "join_key": vis.get("join_key", "manifest_blob_key"),
        "layers": layers_meta,
        "data": data,
    }
