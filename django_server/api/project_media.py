"""Per-project package blob storage через fsspec (file:// | s3:// | gs://).

Бэкенд и креды берутся из Project.storage_uri / storage_options (см.
project_storage_config). Параметр media_bucket оставлен для обратной
совместимости вызовов и больше не влияет на выбор бэкенда.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Iterator

from django.http import FileResponse, StreamingHttpResponse

from . import project_storage_config as psc


def storage_rel_path(package_id: str, logical_path: str) -> str:
    rel = logical_path.replace("\\", "/").lstrip("/")
    return f"packages/{package_id}/{rel}"


def _fs_and_path(project_id: str, storage_path: str):
    cfg = psc.resolve_by_id(project_id)
    fs = psc.filesystem_for(cfg)
    return fs, psc.object_path(cfg, storage_path), cfg


def write_blob(
    project_id: str,
    package_id: str,
    logical_path: str,
    data: bytes,
    *,
    media_bucket: str = "",
) -> str:
    rel = storage_rel_path(package_id, logical_path)
    fs, abs_path, cfg = _fs_and_path(project_id, rel)
    if cfg.is_local_storage:
        Path(abs_path).parent.mkdir(parents=True, exist_ok=True)
    else:
        parent = abs_path.rsplit("/", 1)[0]
        try:
            fs.makedirs(parent, exist_ok=True)
        except (NotImplementedError, FileExistsError):
            pass
    with fs.open(abs_path, "wb") as f:
        f.write(data)
    return rel


def delete_blob_file(
    project_id: str,
    storage_path: str,
    *,
    media_bucket: str = "",
) -> None:
    fs, abs_path, _ = _fs_and_path(project_id, storage_path)
    try:
        if fs.exists(abs_path):
            fs.rm_file(abs_path)
    except (FileNotFoundError, AttributeError):
        try:
            fs.rm(abs_path)
        except FileNotFoundError:
            pass


def remove_package_media(
    project_id: str,
    package_id: str,
    *,
    media_bucket: str = "",
) -> None:
    fs, abs_path, _ = _fs_and_path(project_id, f"packages/{package_id}")
    try:
        if fs.exists(abs_path):
            fs.rm(abs_path, recursive=True)
    except FileNotFoundError:
        pass


def remove_project_media(
    project_id: str,
    *,
    media_bucket: str = "",
    config: psc.StorageConfig | None = None,
) -> None:
    cfg = config or psc.resolve_by_id(project_id)
    fs = psc.filesystem_for(cfg)
    root = psc.object_root(cfg)
    try:
        if fs.exists(root):
            fs.rm(root, recursive=True)
    except FileNotFoundError:
        pass


def open_blob_path(
    project_id: str,
    storage_path: str,
    *,
    media_bucket: str = "",
) -> Path | None:
    """Локальный путь для FileResponse; None если не локальное хранилище или нет файла."""
    cfg = psc.resolve_by_id(project_id)
    if not cfg.is_local_storage:
        return None
    path = Path(psc.object_path(cfg, storage_path))
    return path if path.is_file() else None


def read_blob_head(
    project_id: str,
    storage_path: str,
    *,
    media_bucket: str = "",
    max_bytes: int = 256 * 1024,
) -> bytes | None:
    fs, abs_path, _ = _fs_and_path(project_id, storage_path)
    if not fs.exists(abs_path):
        return None
    with fs.open(abs_path, "rb") as f:
        return f.read(max_bytes)


def _fs_stream(fs, abs_path: str) -> Iterator[bytes]:
    with fs.open(abs_path, "rb") as f:
        while True:
            chunk = f.read(1024 * 64)
            if not chunk:
                break
            yield chunk


def blob_file_response(
    project_id: str,
    storage_path: str,
    logical_path: str,
    *,
    media_bucket: str = "",
) -> FileResponse | StreamingHttpResponse | None:
    ctype, _ = mimetypes.guess_type(logical_path)
    content_type = ctype or "application/octet-stream"
    filename = Path(logical_path.replace("\\", "/")).name
    disposition = f'inline; filename="{filename}"'

    cfg = psc.resolve_by_id(project_id)
    fs = psc.filesystem_for(cfg)
    abs_path = psc.object_path(cfg, storage_path)

    if cfg.is_local_storage:
        path = Path(abs_path)
        if not path.is_file():
            return None
        resp = FileResponse(path.open("rb"), content_type=content_type)
        resp["Content-Disposition"] = disposition
        return resp

    if not fs.exists(abs_path):
        return None
    resp = StreamingHttpResponse(_fs_stream(fs, abs_path), content_type=content_type)
    resp["Content-Disposition"] = disposition
    return resp
