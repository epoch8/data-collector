"""Resolve Vite build assets for embedded packages SPA."""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings


def packages_spa_built() -> bool:
    manifest = Path(settings.PACKAGES_SPA_MANIFEST)
    return manifest.is_file()


def packages_spa_assets() -> dict[str, str | None]:
    """
    Returns {js, css} static paths relative to STATIC_URL (e.g. packages/assets/index-xxx.js).
    """
    manifest_path = Path(settings.PACKAGES_SPA_MANIFEST)
    if not manifest_path.is_file():
        return {"js": None, "css": None, "built": False}

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"js": None, "css": None, "built": False}

    entry = manifest.get("index.html")
    if entry is None:
        for key, val in manifest.items():
            if isinstance(val, dict) and val.get("isEntry"):
                entry = val
                break
    if not isinstance(entry, dict):
        return {"js": None, "css": None, "built": False}

    js_file = entry.get("file")
    css_files = entry.get("css") or []
    css_file = css_files[0] if css_files else None

    def _static_path(rel: str | None) -> str | None:
        if not rel:
            return None
        return f"packages/{rel}".replace("\\", "/")

    return {
        "js": _static_path(js_file),
        "css": _static_path(css_file),
        "built": True,
    }
