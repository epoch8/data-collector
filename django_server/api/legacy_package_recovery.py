"""Восстановление пакетов из db.sqlite3 (после DROP TABLE) и media/pkg/."""

from __future__ import annotations

import json
import re
from pathlib import Path

from django.conf import settings

from .utils import collect_blob_refs


def legacy_filename_to_logical(filename: str) -> str | None:
    if not filename.endswith("_body.bin"):
        return None
    lid = filename[:-9]
    if not lid.startswith("blobs__"):
        return None
    rest = lid[7:]
    m = re.match(r"^(img_\d+)(?:_[A-Za-z0-9]{5,8})?(\.\w+)$", rest)
    if m:
        rest = m.group(1) + m.group(2)
    elif re.match(r"^img_\d+\.\w+$", rest):
        pass
    else:
        m2 = re.match(r"^(.+?)(?:_[A-Za-z0-9]{5,8})(\.\w+)$", rest)
        if m2:
            rest = m2.group(1) + m2.group(2)
    return f"blobs/{rest}"


def build_legacy_session_index(pkg_root: Path | None = None) -> dict[str, dict[str, Path]]:
    root = pkg_root or (Path(settings.MEDIA_ROOT) / "pkg")
    index: dict[str, dict[str, Path]] = {}
    if not root.is_dir():
        return index
    for session_dir in root.iterdir():
        if not session_dir.is_dir():
            continue
        files: dict[str, Path] = {}
        for f in session_dir.iterdir():
            if not f.is_file():
                continue
            logical = legacy_filename_to_logical(f.name)
            if logical:
                files[logical] = f
        if files:
            index[session_dir.name] = files
    return index


def extract_manifests_from_db(db_path: Path) -> list[dict]:
    text = db_path.read_bytes().decode("utf-8", errors="ignore")
    manifests: list[dict] = []
    patterns = (
        r'\{"package_id"\s*:\s*"([^"]+)"\s*,\s*"project_id"\s*:\s*"([^"]+)"',
        r'\{"project_id"\s*:\s*"([^"]+)"[^}]{0,80}"package_id"\s*:\s*"([^"]+)"',
    )
    for pat in patterns:
        for m in re.finditer(pat, text):
            start = m.start()
            depth = 0
            end = None
            for i in range(start, min(start + 300000, len(text))):
                c = text[i]
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            if end is None:
                continue
            try:
                obj = json.loads(text[start:end])
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and obj.get("project_id") and obj.get("package_id"):
                manifests.append(obj)

    seen: set[tuple[str, str]] = set()
    unique: list[dict] = []
    for m in manifests:
        key = (str(m["project_id"]), str(m["package_id"]))
        if key in seen:
            continue
        seen.add(key)
        unique.append(m)
    return unique


def guess_phase(db_text: str, package_id: str) -> str:
    idx = db_text.find(package_id)
    if idx < 0:
        return "completed"
    window = db_text[idx : idx + 200]
    for phase in ("completed", "ready_to_commit", "awaiting_blobs", "failed"):
        if phase in window:
            return phase
    return "completed"


def guess_uploader(db_text: str, package_id: str) -> tuple[str, str]:
    idx = db_text.find(package_id)
    if idx < 0:
        return "", ""
    window = db_text[max(0, idx - 400) : idx + 400]
    email_m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", window)
    uid_m = re.search(r"[A-Za-z0-9]{20,40}", window)
    return (uid_m.group(0) if uid_m else "", email_m.group(0) if email_m else "")


def session_hints_from_db(db_text: str, package_id: str) -> list[str]:
    """session_id из остатков UploadedBlob (pkg/{id}/blobs__…) рядом с package_id в db."""
    idx = db_text.find(package_id)
    if idx < 0:
        return []
    window = db_text[max(0, idx - 3000) : idx + 8000]
    return list(dict.fromkeys(re.findall(r"pkg/(\d+)/blobs__", window)))


def find_session_for_manifest(
    manifest: dict,
    index: dict[str, dict[str, Path]],
    *,
    db_text: str = "",
    used_sessions: set[str] | None = None,
) -> str | None:
    used = used_sessions or set()
    refs: set[str] = set()
    collect_blob_refs(manifest, refs)
    package_id = str(manifest.get("package_id") or "")

    candidates: list[str] = []
    if db_text and package_id:
        for sid in session_hints_from_db(db_text, package_id):
            if sid in index and sid not in used:
                candidates.append(sid)

    def score(sid: str) -> int:
        files = index.get(sid, {})
        if not refs:
            return len(files)
        return len(refs & set(files.keys()))

    def fits(sid: str) -> bool:
        files = index.get(sid, {})
        if not refs:
            return bool(files)
        return refs.issubset(set(files.keys()))

    for sid in candidates:
        if fits(sid):
            return sid

    best_sid: str | None = None
    best_score = -1
    for sid, files in index.items():
        if sid in used or not files:
            continue
        if refs and not refs.issubset(set(files.keys())):
            continue
        sc = score(sid)
        if sc > best_score:
            best_score = sc
            best_sid = sid
    return best_sid if best_score > 0 else None
