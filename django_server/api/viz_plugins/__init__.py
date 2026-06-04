"""Реестр плагинов визуализации: по одной папке на plugin id."""

from __future__ import annotations

from typing import Any

from .cvat_link import plugin as cvat_link_plugin
from .depth_map import plugin as depth_map_plugin
from .keypoint_korovas import plugin as keypoint_korovas_plugin
from .yolo_detection import plugin as yolo_detection_plugin

_PLUGINS = (
    yolo_detection_plugin,
    depth_map_plugin,
    cvat_link_plugin,
    keypoint_korovas_plugin,
)

REGISTRY: dict[str, Any] = {p.PLUGIN_ID: p for p in _PLUGINS}

KNOWN_PLUGINS = frozenset(REGISTRY.keys())

KNOWN_TABLES = frozenset().union(*(p.ALLOWED_TABLES for p in _PLUGINS))

PLUGIN_ALLOWED_TABLES: dict[str, frozenset[str]] = {
    pid: p.ALLOWED_TABLES for pid, p in REGISTRY.items()
}

KNOWN_PALETTES = frozenset({"gt", "inference", "yolo"})


def get_plugin(plugin_id: str) -> Any | None:
    return REGISTRY.get(plugin_id)


def validate_layer_options(layer: dict[str, Any], layer_id: str, index: int) -> list[str]:
    plugin_id = layer.get("plugin")
    mod = get_plugin(str(plugin_id)) if isinstance(plugin_id, str) else None
    if mod is None:
        return []
    return mod.validate_layer(layer, layer_id, index)


def layer_options_for_api(layer: dict[str, Any]) -> dict[str, Any]:
    plugin_id = layer.get("plugin")
    mod = get_plugin(str(plugin_id)) if isinstance(plugin_id, str) else None
    if mod is None:
        return {}
    return mod.layer_options_for_api(layer)


def fetch_table(project_id: str, package_id: str, table: str, plugin_id: str) -> list[dict[str, Any]]:
    mod = get_plugin(plugin_id)
    if mod is None:
        return []
    return mod.fetch(project_id, package_id, table)
