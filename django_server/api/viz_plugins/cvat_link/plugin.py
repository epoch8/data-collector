"""Плагин cvat_link — ссылка на задачу CVAT по кадру (таблица cvat_link)."""

from __future__ import annotations

from typing import Any

from api import project_db as pdb

PLUGIN_ID = "cvat_link"
ALLOWED_TABLES = frozenset({"cvat_link"})
REQUIRES_PALETTE = False


def validate_layer(layer: dict[str, Any], layer_id: str, index: int) -> list[str]:
    return []


def layer_options_for_api(layer: dict[str, Any]) -> dict[str, Any]:
    return {}


def fetch(project_id: str, package_id: str, table: str) -> list[dict[str, Any]]:
    if table != "cvat_link":
        return []
    return pdb.list_cvat_link(project_id, package_id)
