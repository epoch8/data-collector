"""Per-project package blob storage: local folder (dev) or dedicated GCS bucket (prod)."""

from __future__ import annotations

import mimetypes
import shutil
from pathlib import Path
from typing import BinaryIO, Iterator

from django.conf import settings
from django.http import FileResponse, StreamingHttpResponse


def media_root(project_id: str) -> Path:
    return Path(settings.PROJECT_MEDIA_ROOT) / project_id


def storage_rel_path(package_id: str, logical_path: str) -> str:
    rel = logical_path.replace("\\", "/").lstrip("/")
    return f"packages/{package_id}/{rel}"


def local_abs_path(project_id: str, storage_path: str) -> Path:
    return media_root(project_id) / storage_path


def bucket_name(project_id: str, project_media_bucket: str = "") -> str:
    explicit = (project_media_bucket or "").strip()
    if explicit:
        return explicit
    tmpl = getattr(settings, "PROJECT_MEDIA_BUCKET_TEMPLATE", "korovas-dc-{project_id}")
    return tmpl.format(project_id=project_id)


def _use_gcs() -> bool:
    return getattr(settings, "DJANGO_ENV", "") == "production"


def _gcs_client():
    from google.cloud import storage

    return storage.Client()


def write_blob(
    project_id: str,
    package_id: str,
    logical_path: str,
    data: bytes,
    *,
    media_bucket: str = "",
) -> str:
    rel = storage_rel_path(package_id, logical_path)
    if _use_gcs():
        bucket = bucket_name(project_id, media_bucket)
        client = _gcs_client()
        client.bucket(bucket).blob(rel).upload_from_string(data)
    else:
        path = local_abs_path(project_id, rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return rel


def delete_blob_file(
    project_id: str,
    storage_path: str,
    *,
    media_bucket: str = "",
) -> None:
    if _use_gcs():
        bucket = bucket_name(project_id, media_bucket)
        client = _gcs_client()
        blob = client.bucket(bucket).blob(storage_path)
        if blob.exists():
            blob.delete()
        return
    path = local_abs_path(project_id, storage_path)
    path.unlink(missing_ok=True)


def remove_package_media(
    project_id: str,
    package_id: str,
    *,
    media_bucket: str = "",
) -> None:
    prefix = f"packages/{package_id}/"
    if _use_gcs():
        bucket = bucket_name(project_id, media_bucket)
        client = _gcs_client()
        blobs = client.list_blobs(bucket, prefix=prefix)
        for blob in blobs:
            blob.delete()
        return
    root = media_root(project_id) / "packages" / package_id
    shutil.rmtree(root, ignore_errors=True)


def remove_project_media(project_id: str, *, media_bucket: str = "") -> None:
    if _use_gcs():
        bucket = bucket_name(project_id, media_bucket)
        client = _gcs_client()
        blobs = list(client.list_blobs(bucket))
        if blobs:
            bucket_obj = client.bucket(bucket)
            bucket_obj.delete_blobs(blobs)
        return
    shutil.rmtree(media_root(project_id), ignore_errors=True)


def open_blob_path(
    project_id: str,
    storage_path: str,
    *,
    media_bucket: str = "",
) -> Path | None:
    """Local filesystem path for FileResponse; None if missing or GCS."""
    if _use_gcs():
        return None
    path = local_abs_path(project_id, storage_path)
    return path if path.is_file() else None


def read_blob_head(
    project_id: str,
    storage_path: str,
    *,
    media_bucket: str = "",
    max_bytes: int = 256 * 1024,
) -> bytes | None:
    if _use_gcs():
        bucket = bucket_name(project_id, media_bucket)
        client = _gcs_client()
        blob = client.bucket(bucket).blob(storage_path)
        if not blob.exists():
            return None
        return blob.download_as_bytes(start=0, end=max_bytes - 1)
    path = local_abs_path(project_id, storage_path)
    if not path.is_file():
        return None
    with path.open("rb") as f:
        return f.read(max_bytes)


def _gcs_stream(storage_path: str, bucket: str) -> Iterator[bytes]:
    client = _gcs_client()
    blob = client.bucket(bucket).blob(storage_path)
    with blob.open("rb") as f:
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

    if _use_gcs():
        bucket = bucket_name(project_id, media_bucket)
        client = _gcs_client()
        blob = client.bucket(bucket).blob(storage_path)
        if not blob.exists():
            return None
        resp = StreamingHttpResponse(
            _gcs_stream(storage_path, bucket),
            content_type=content_type,
        )
        resp["Content-Disposition"] = disposition
        return resp

    path = local_abs_path(project_id, storage_path)
    if not path.is_file():
        return None
    resp = FileResponse(path.open("rb"), content_type=content_type)
    resp["Content-Disposition"] = disposition
    return resp
