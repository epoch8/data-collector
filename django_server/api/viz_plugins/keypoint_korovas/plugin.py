"""Плагин keypoint_korovas — GT / inference keypoints."""

from __future__ import annotations

from typing import Any

from api import project_db as pdb

PLUGIN_ID = "keypoint_korovas"
ALLOWED_TABLES = frozenset({"cow_keypoint_annotation", "cow_inference_result"})
REQUIRES_PALETTE = True


def validate_layer(layer: dict[str, Any], layer_id: str, index: int) -> list[str]:
    return []


def layer_options_for_api(layer: dict[str, Any]) -> dict[str, Any]:
    return {}


def fetch(project_id: str, package_id: str, table: str) -> list[dict[str, Any]]:
    if table == "cow_keypoint_annotation":
        return pdb.list_gt(project_id, package_id)
    if table == "cow_inference_result":
        return pdb.list_inference(project_id, package_id)
    return []
