from __future__ import annotations

import hashlib
import json
import re
from typing import Any


def weak_etag(payload: str | bytes) -> str:
    h = hashlib.sha256(
        payload if isinstance(payload, bytes) else payload.encode("utf-8"),
    ).hexdigest()
    return f'W/"{h[:32]}"'


def collect_blob_refs(obj: Any, out: set[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str):
                s = k.replace("\\", "/")
                if s.startswith("blobs/"):
                    out.add(s)
            collect_blob_refs(v, out)
    elif isinstance(obj, list):
        for v in obj:
            collect_blob_refs(v, out)
    elif isinstance(obj, str):
        s = obj.replace("\\", "/")
        if s.startswith("blobs/"):
            out.add(s)


def validate_blob_logical_path(path: str) -> str | None:
    """Возвращает ошибку или None если путь безопасен."""
    norm = path.replace("\\", "/")
    if ".." in norm or norm.startswith("/"):
        return "invalid_blob_path"
    if not re.match(r"^blobs/[^/].*", norm):
        return "blob_path_must_start_with_blobs_slash"
    return None


def parse_json_body(raw: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None, "invalid_json"
    if not isinstance(data, dict):
        return None, "expected_object"
    return data, None
