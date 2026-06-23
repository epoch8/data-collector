"""Плагин yolo_detection — bbox из таблицы yolo_detection."""

from __future__ import annotations

from typing import Any

from api import project_db as pdb

PLUGIN_ID = "yolo_detection"
ALLOWED_TABLES = frozenset({"yolo_detection"})
REQUIRES_PALETTE = True

_DEPRECATED_KEYS = frozenset({"class_names", "class_colors"})
_OPTION_KEYS = frozenset({"include_classes", "classes"})


def validate_layer(layer: dict[str, Any], layer_id: str, index: int) -> list[str]:
    errs: list[str] = []
    for dep in _DEPRECATED_KEYS:
        if dep in layer:
            errs.append(
                f'layers[{index}] ({layer_id}): поле "{dep}" устарело — используйте "classes".',
            )
    inc = layer.get("include_classes")
    if inc is not None:
        if not isinstance(inc, list) or not all(
            isinstance(x, int) and not isinstance(x, bool) for x in inc
        ):
            errs.append(f'layers[{index}] ({layer_id}): include_classes — массив int.')
    classes = layer.get("classes")
    if classes is None:
        return errs
    if not isinstance(classes, dict) or not classes:
        errs.append(f'layers[{index}] ({layer_id}): classes — непустой объект.')
        return errs
    for k, v in classes.items():
        if not str(k).isdigit():
            errs.append(f'layers[{index}] ({layer_id}): classes — ключи "0", "1", …')
            break
        if isinstance(v, str):
            if not v.strip():
                errs.append(f'layers[{index}] ({layer_id}): classes["{k}"] — непустая строка.')
            continue
        if isinstance(v, dict):
            name = v.get("name") if isinstance(v.get("name"), str) else v.get("label")
            if not isinstance(name, str) or not name.strip():
                errs.append(f'layers[{index}] ({layer_id}): classes["{k}"].name — обязательно.')
            if v.get("color") is not None and not isinstance(v.get("color"), str):
                errs.append(f'layers[{index}] ({layer_id}): classes["{k}"].color — #hex строка.')
            continue
        errs.append(f'layers[{index}] ({layer_id}): classes["{k}"] — строка или {{"name","color"}}.')
        break
    return errs


def layer_options_for_api(layer: dict[str, Any]) -> dict[str, Any]:
    return {k: layer[k] for k in _OPTION_KEYS if k in layer}


def fetch(project_id: str, package_id: str, table: str) -> list[dict[str, Any]]:
    if table != "yolo_detection":
        return []
    return pdb.list_yolo_detection(project_id, package_id)
