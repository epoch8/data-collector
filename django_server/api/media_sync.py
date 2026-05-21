"""Копирование статики проекта из репозитория Flutter → project_assets."""

from __future__ import annotations

import shutil
from pathlib import Path

from django.conf import settings


def sync_project_media_from_repo(repo_root: Path, project_id: str) -> None:
    """Копирует из `repo/assets/...` в project_assets/<project_id>/ (пути как после `assets/`)."""
    dest_root = Path(settings.PROJECT_ASSETS_ROOT) / project_id
    dest_root.mkdir(parents=True, exist_ok=True)
    slug = project_id.split("-", 1)[0] if "-" in project_id else project_id
    assets_root = repo_root / "assets"
    if not assets_root.is_dir():
        return
    sources = [
        assets_root / slug,
        assets_root / "old" / slug,
    ]
    for src in sources:
        if not src.is_dir():
            continue
        for f in src.rglob("*"):
            if not f.is_file():
                continue
            try:
                rel_under_assets = f.relative_to(assets_root)
            except ValueError:
                continue
            parts = rel_under_assets.parts
            if len(parts) >= 3 and parts[0] == "old" and parts[1] == slug:
                rel_under_assets = Path(*parts[1:])
            out = dest_root / rel_under_assets
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, out)
