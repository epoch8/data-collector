"""Данные визуализации: Git vis config + project SQLite."""

from __future__ import annotations

from typing import Any

from .models import Project
from .project_vis_config import load_vis_config


def _fetch_table(project_id: str, package_id: str, table: str) -> list[dict[str, Any]]:
    from . import project_db as pdb

    if table == "cow_keypoint_annotation":
        return pdb.list_gt(project_id, package_id)
    if table == "cow_inference_result":
        return pdb.list_inference(project_id, package_id)
    return []


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
        table = layer.get("table")
        if not isinstance(table, str):
            continue
        if _fetch_table(project_id, package_id, table):
            return True
    return False


def build_package_viz_payload(
    project_id: str,
    package_id: str,
) -> dict[str, Any] | None:
    project = Project.objects.filter(project_id=project_id).first()
    if not project:
        return None
    vis = load_vis_config(project, fetch_remote=True)
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
        records = _fetch_table(project_id, package_id, table)
        if records:
            has_any = True
        data[lid] = records
        layers_meta.append(
            {
                "id": lid,
                "label": layer.get("label") or lid,
                "plugin": layer.get("plugin"),
                "table": table,
                "palette": layer.get("palette"),
                "default_visible": bool(layer.get("default_visible")),
            },
        )

    if not has_any:
        return None

    return {
        "version": vis.get("version", 1),
        "join_key": vis.get("join_key", "manifest_blob_key"),
        "layers": layers_meta,
        "data": data,
    }
