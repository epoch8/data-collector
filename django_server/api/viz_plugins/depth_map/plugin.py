"""Плагин depth_map — путь к .npy в пакете (таблица depth_map)."""

from __future__ import annotations

from typing import Any

from api import project_db as pdb

PLUGIN_ID = "depth_map"
ALLOWED_TABLES = frozenset({"depth_map"})
REQUIRES_PALETTE = False


def validate_layer(layer: dict[str, Any], layer_id: str, index: int) -> list[str]:
    return []


def layer_options_for_api(layer: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(layer.get("unit"), str):
        out["unit"] = layer["unit"]
    return out


def fetch(project_id: str, package_id: str, table: str) -> list[dict[str, Any]]:
    if table != "depth_map":
        return []
    return pdb.list_depth_map(project_id, package_id)
