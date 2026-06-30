#!/usr/bin/env python3
"""Helpers for bilingual docs: *.md (EN) + *.ru.md (RU) with language switchers."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Main docs to keep in sync (relative to repo root).
DOC_PATHS = [
    "README.md",
    "django_server/README.md",
    "test_dev/README.md",
    "examples/README.md",
    "examples/cow-keypoints/README.md",
    "legacy/README.md",
    "docs/admin-panel/README.md",
    "docs/mobile-app/README.md",
    "docs/deploy-flutter-web.md",
    "docs/web-vs-android.md",
    "docs/i18n.md",
    "specs/01-overview.md",
    "specs/02-data-models-schema.md",
    "specs/03-user-journey-screens.md",
    "specs/04-tech-stack-architecture.md",
    "specs/05-stage-1-mvp.md",
    "specs/06-upload-lifecycle.md",
    "specs/07-package-payload-structure.md",
    "specs/08-server-api-package-upload.md",
    "specs/09-server-project-config-delivery.md",
    "specs/git-backed-projects.md",
    "specs/project-storage-uris.md",
    "specs/collector-vis-config.md",
    "specs/config/09-project-json-builder-guide.md",
    "specs/config/json-driven-collection-ui.md",
]

SWITCHER_RE = re.compile(
    r"^> \*\*Language / Язык:\*\*.*\n\n",
    re.MULTILINE,
)


def en_ru_names(path: Path) -> tuple[Path, Path]:
    """README.md -> (README.md, README.ru.md); foo.md -> (foo.md, foo.ru.md)."""
    if path.name == "README.md":
        ru = path.with_name("README.ru.md")
    else:
        ru = path.with_suffix(".ru.md")
    return path, ru


def switcher(en_name: str, ru_name: str, *, active: str) -> str:
    if active == "en":
        en_part = "**English**"
        ru_part = f"[Русский]({ru_name})"
    else:
        en_part = f"[English]({en_name})"
        ru_part = "**Русский**"
    return f"> **Language / Язык:** {en_part} · {ru_part}\n\n"


def strip_switcher(text: str) -> str:
    return SWITCHER_RE.sub("", text, count=1)


def ensure_ru_copy(rel: str) -> None:
    """Copy current .md to .ru.md if .ru.md missing (bootstrap Russian archive)."""
    en_path, ru_path = en_ru_names(ROOT / rel)
    if not en_path.is_file():
        print(f"skip missing: {rel}")
        return
    if ru_path.is_file():
        print(f"exists: {ru_path.relative_to(ROOT)}")
        return
    ru_path.write_text(en_path.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"copied -> {ru_path.relative_to(ROOT)}")


def add_switchers(rel: str) -> None:
    en_path, ru_path = en_ru_names(ROOT / rel)
    en_file = en_path.name
    ru_file = ru_path.name
    for path, active in ((en_path, "en"), (ru_path, "ru")):
        if not path.is_file():
            continue
        body = strip_switcher(path.read_text(encoding="utf-8"))
        path.write_text(switcher(en_file, ru_file, active=active) + body, encoding="utf-8")
        print(f"switcher ({active}): {path.relative_to(ROOT)}")


def main() -> None:
    cmd = (sys.argv[1:] or ["help"])[0]
    if cmd == "bootstrap-ru":
        for rel in DOC_PATHS:
            ensure_ru_copy(rel)
    elif cmd == "switchers":
        for rel in DOC_PATHS:
            add_switchers(rel)
    else:
        print("Usage: python scripts/i18n_docs.py [bootstrap-ru|switchers]")


if __name__ == "__main__":
    main()
