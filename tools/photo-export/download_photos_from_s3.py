#!/usr/bin/env python3
"""Выгрузка фото из S3 в папки {animal_id}/{pose}/{file}.

Отдельный скрипт — без Django. Использует AWS credentials из окружения
(aws sso login / aws configure / переменные AWS_*).

Два шага:
  1. list   — посмотреть, что лежит в бакете (после aws login)
  2. download — скачать по индексу манифестов + config проекта

Зависимости:
  pip install boto3

Примеры:
  # Шаг 1: разведка бакета
  cd tools/photo-export
  python download_photos_from_s3.py list --bucket dc-project-korovas

  # Шаг 3: скачивание (нужен manifests.jsonl — см. export_manifests.py)
  python download_photos_from_s3.py download \\
    --bucket dc-project-korovas \\
    --manifests manifests.jsonl \\
    --output %USERPROFILE%\\Desktop\\export\\korovas \\
    --dry-run
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
except ImportError:
    print("Установите boto3: pip install boto3", file=sys.stderr)
    sys.exit(1)

_ANIMAL_FIELD_FALLBACKS = (
    "cow_identifier",
    "animal_id",
    "animalId",
    "subject_id",
    "cow_name",
)
_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")


# ── helpers (без Django) ─────────────────────────────────────────────────────


def sanitize_dir_name(value: str, *, max_len: int = 80) -> str:
    raw = (value or "").strip()
    if not raw:
        return "_unknown"
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", raw)
    safe = re.sub(r"\s+", " ", safe).strip().strip(".")
    if not safe:
        return "_unknown"
    if len(safe) > max_len:
        safe = safe[:max_len].rstrip(". ")
    return safe


def field_label(field: dict[str, Any]) -> str:
    return field.get("title") or field.get("field_id") or ""


def is_image_path(path: str) -> bool:
    return path.lower().endswith(_IMAGE_EXTS)


def extract_form_shots(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, dict):
        return []
    shots = []
    for path, meta in value.items():
        if isinstance(path, str) and path.startswith("blobs/"):
            shots.append(
                {
                    "path": path.replace("\\", "/"),
                    "metadata": meta if isinstance(meta, dict) else None,
                },
            )
    return shots


def load_config(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"config должен быть JSON-объектом: {path}")
    return data


def resolve_animal_field_id(config_root: dict[str, Any], explicit: str) -> str:
    if explicit:
        return explicit.strip()
    flow = (config_root.get("config") or {}).get("flow") or {}
    for step in flow.get("steps") or []:
        if not isinstance(step, dict):
            continue
        fid = (step.get("cow_id_field_id") or "").strip()
        if fid:
            return fid
    fields = (config_root.get("config") or {}).get("fields") or []
    field_ids = {
        f.get("field_id")
        for f in fields
        if isinstance(f, dict) and isinstance(f.get("field_id"), str)
    }
    for candidate in _ANIMAL_FIELD_FALLBACKS:
        if candidate in field_ids:
            return candidate
    return ""


def camera_photo_fields(config_root: dict[str, Any]) -> list[dict[str, Any]]:
    fields = (config_root.get("config") or {}).get("fields") or []
    by_id = {
        f["field_id"]: f
        for f in fields
        if isinstance(f, dict) and isinstance(f.get("field_id"), str)
    }
    ordered: list[dict[str, Any]] = []
    seen: set[str] = set()

    flow = (config_root.get("config") or {}).get("flow") or {}
    for step in flow.get("steps") or []:
        if not isinstance(step, dict) or step.get("screen") != "scroll_form":
            continue
        for fid in step.get("field_ids") or []:
            f = by_id.get(fid)
            if not f or f.get("type") != "camera_photo" or fid in seen:
                continue
            ordered.append(f)
            seen.add(fid)

    for f in fields:
        if (
            isinstance(f, dict)
            and f.get("type") == "camera_photo"
            and f.get("field_id") not in seen
        ):
            ordered.append(f)
    return ordered


def pose_folder_name(index: int, field: dict[str, Any]) -> str:
    fid = field.get("field_id") or f"pose_{index}"
    title = field_label(field)
    short_title = sanitize_dir_name(title, max_len=48)
    if short_title and short_title != fid:
        return f"{index:02d}_{fid}_{short_title}"
    return f"{index:02d}_{fid}"


def animal_id_from_manifest(
    manifest: dict[str, Any],
    animal_field_id: str,
    package_id: str,
) -> str:
    data = manifest.get("data")
    if not isinstance(data, dict):
        return package_id
    if animal_field_id:
        value = data.get(animal_field_id)
        if value is not None and str(value).strip():
            return str(value).strip()
    for candidate in _ANIMAL_FIELD_FALLBACKS:
        value = data.get(candidate)
        if value is not None and str(value).strip():
            return str(value).strip()
    return package_id


def unique_dest_path(dest_dir: Path, file_name: str, package_id: str) -> Path:
    candidate = dest_dir / file_name
    if not candidate.exists():
        return candidate
    stem = Path(file_name).stem
    suffix = Path(file_name).suffix
    short_pkg = package_id[:8]
    alt = dest_dir / f"{stem}__{short_pkg}{suffix}"
    if not alt.exists():
        return alt
    n = 2
    while True:
        alt = dest_dir / f"{stem}__{short_pkg}_{n}{suffix}"
        if not alt.exists():
            return alt
        n += 1


def normalize_prefix(prefix: str) -> str:
    p = (prefix or "").strip().replace("\\", "/")
    if p and not p.endswith("/"):
        p += "/"
    return p


def s3_key(prefix: str, package_id: str, blob_path: str) -> str:
    """blob_path = blobs/img_001.jpg → {prefix}packages/{uuid}/blobs/img_001.jpg"""
    rel = blob_path.replace("\\", "/").lstrip("/")
    if not rel.startswith("blobs/"):
        rel = f"blobs/{rel}"
    return f"{prefix}packages/{package_id}/{rel}"


def iter_manifests(path: Path) -> Iterator[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return
    # JSON array
    if text.startswith("["):
        items = json.loads(text)
        if not isinstance(items, list):
            raise ValueError("manifests JSON array expected")
        for item in items:
            if isinstance(item, dict):
                yield item
        return
    # JSONL
    for line_no, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"manifests.jsonl:{line_no}: {exc}") from exc
        if isinstance(item, dict):
            yield item


def manifest_body(row: dict[str, Any]) -> dict[str, Any] | None:
    raw = row.get("manifest")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None
    if "data" in row and isinstance(row.get("data"), dict):
        return row
    return None


# ── S3 ───────────────────────────────────────────────────────────────────────


def _add_s3_auth_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--endpoint-url",
        default="",
        help="S3 endpoint (MinIO/Yandex/…), напр. https://storage.yandexcloud.net",
    )
    parser.add_argument(
        "--access-key",
        default="",
        help="S3 access key (или env AWS_ACCESS_KEY_ID / S3_KEY)",
    )
    parser.add_argument(
        "--secret-key",
        default="",
        help="S3 secret (или env AWS_SECRET_ACCESS_KEY / S3_SECRET)",
    )
    parser.add_argument("--region", default="", help="AWS region (опционально)")


def make_s3_client(args: argparse.Namespace):
    endpoint = (
        (args.endpoint_url or "").strip()
        or os.environ.get("S3_ENDPOINT_URL", "")
        or os.environ.get("AWS_ENDPOINT_URL", "")
    )
    access_key = (
        (args.access_key or "").strip()
        or os.environ.get("AWS_ACCESS_KEY_ID", "")
        or os.environ.get("S3_KEY", "")
    )
    secret_key = (
        (args.secret_key or "").strip()
        or os.environ.get("AWS_SECRET_ACCESS_KEY", "")
        or os.environ.get("S3_SECRET", "")
    )
    region = (args.region or "").strip() or os.environ.get("AWS_DEFAULT_REGION", "")

    kwargs: dict[str, Any] = {}
    if region:
        kwargs["region_name"] = region
    if endpoint:
        kwargs["endpoint_url"] = endpoint
    if access_key:
        kwargs["aws_access_key_id"] = access_key
    if secret_key:
        kwargs["aws_secret_access_key"] = secret_key

    return boto3.client("s3", **kwargs)


def cmd_list(args: argparse.Namespace) -> int:
    prefix = normalize_prefix(args.prefix)
    client = make_s3_client(args)

    endpoint = (args.endpoint_url or "").strip() or "(default AWS)"
    print(f"Endpoint: {endpoint}")
    print(f"Bucket: s3://{args.bucket}/{prefix}")
    print("Listing (первые объекты)…\n")

    paginator = client.get_paginator("list_objects_v2")
    total = 0
    packages: Counter[str] = Counter()
    sample_keys: list[str] = []

    try:
        for page in paginator.paginate(Bucket=args.bucket, Prefix=prefix):
            for obj in page.get("Contents") or []:
                key = obj["Key"]
                total += 1
                if len(sample_keys) < 20:
                    sample_keys.append(key)
                # packages/{uuid}/blobs/...
                parts = key[len(prefix):].split("/")
                if len(parts) >= 2 and parts[0] == "packages":
                    packages[parts[1]] += 1
                if args.limit and total >= args.limit:
                    break
            if args.limit and total >= args.limit:
                break
    except NoCredentialsError:
        print(
            "Нет S3 credentials. Передайте --access-key/--secret-key "
            "или задайте AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY.",
            file=sys.stderr,
        )
        return 1
    except (ClientError, BotoCoreError) as exc:
        print(f"S3 error: {exc}", file=sys.stderr)
        return 1

    print(f"Всего объектов: {total}" + (f" (лимит {args.limit})" if args.limit else ""))
    print(f"Уникальных package_id: {len(packages)}")
    if packages:
        top = packages.most_common(5)
        print("Примеры package_id (число файлов):")
        for pkg_id, n in top:
            print(f"  {pkg_id}  ({n} files)")
    print("\nПримеры ключей:")
    for key in sample_keys:
        print(f"  s3://{args.bucket}/{key}")

    if total == 0:
        print(
            "\nПусто. Проверьте --bucket и --prefix "
            "(prefix = папка проекта внутри бакета, как в storage_uri).",
            file=sys.stderr,
        )
        return 1
    return 0


def pose_fields_for_package(
    data: dict[str, Any],
    config_pose_fields: list[dict[str, Any]],
    *,
    auto_fields: bool,
) -> list[dict[str, Any]]:
    """Поля с фото для пакета: из config (если есть совпадения) или авто из manifest.data."""
    if config_pose_fields and not auto_fields:
        matched = [
            f
            for f in config_pose_fields
            if extract_form_shots(data.get(f.get("field_id") or ""))
        ]
        if matched:
            return matched

    discovered: list[dict[str, Any]] = []
    for fid in sorted(data):
        if extract_form_shots(data.get(fid)):
            discovered.append({"field_id": fid, "title": fid})
    return discovered


def cmd_download(args: argparse.Namespace) -> int:
    prefix = normalize_prefix(args.prefix)
    output_dir = Path(args.output).expanduser().resolve()
    manifests_path = Path(args.manifests).expanduser()
    config_path = (args.config or "").strip()
    auto_fields = bool(args.auto_fields) or not config_path

    if not manifests_path.is_file():
        print(f"Нет файла манифестов: {manifests_path}", file=sys.stderr)
        print("См. export_manifests.py — как выгрузить из Postgres.", file=sys.stderr)
        return 1

    config_root: dict[str, Any] = {}
    config_pose_fields: list[dict[str, Any]] = []
    if config_path:
        cfg_file = Path(config_path).expanduser()
        if not cfg_file.is_file():
            print(f"Нет config: {cfg_file}", file=sys.stderr)
            return 1
        config_root = load_config(cfg_file)
        config_pose_fields = camera_photo_fields(config_root)

    animal_field_id = (args.animal_field or "").strip()
    if not animal_field_id:
        animal_field_id = resolve_animal_field_id(config_root, "") or (
            "cow_name" if auto_fields else "cow_identifier"
        )
    if auto_fields:
        print("Ракурсы: авто из manifest.data (поля с blobs/*)")
    elif not config_pose_fields:
        print("В config нет полей camera_photo — включён авто-режим", file=sys.stderr)
        auto_fields = True

    client = make_s3_client(args)
    dry_run = bool(args.dry_run)
    skip_existing = bool(args.skip_existing)
    images_only = not bool(args.all_blobs)
    phase_filter = "" if args.all_phases else (args.phase or "").strip()

    rows_out: list[dict[str, str]] = []
    downloaded = skipped = missing = errors = 0

    print(f"Bucket: s3://{args.bucket}/{prefix}")
    ep = (args.endpoint_url or "").strip() or os.environ.get("S3_ENDPOINT_URL", "") or "(default)"
    print(f"Endpoint: {ep}")
    print(f"Output: {output_dir}")
    print(f"Animal field: {animal_field_id or '(auto)'}")
    print(f"Manifests: {manifests_path}")
    if dry_run:
        print("DRY RUN\n")

    if not dry_run:
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            print(
                f"Не удалось создать папку выгрузки: {output_dir}\n"
                f"  ({exc})\n"
                "Проверьте, что диск существует (D: может отсутствовать). "
                "Попробуйте, например:\n"
                f"  --output {Path.home() / 'Desktop' / 'export' / 'korovas'}",
                file=sys.stderr,
            )
            return 1

    for row in iter_manifests(manifests_path):
        package_id = (row.get("package_id") or "").strip()
        if not package_id:
            continue
        phase = (row.get("phase") or "").strip()
        if phase_filter and phase != phase_filter:
            continue

        manifest = manifest_body(row)
        if not manifest:
            print(f"skip {package_id}: нет manifest", file=sys.stderr)
            continue

        animal_id = animal_id_from_manifest(manifest, animal_field_id, package_id)
        animal_dir = sanitize_dir_name(animal_id)
        data = manifest.get("data")
        if not isinstance(data, dict):
            data = {}

        pose_fields = pose_fields_for_package(
            data,
            config_pose_fields,
            auto_fields=auto_fields,
        )
        if not pose_fields:
            print(f"skip {package_id}: нет фото в manifest.data", file=sys.stderr)
            continue

        for pose_idx, field in enumerate(pose_fields, start=1):
            fid = field.get("field_id") or ""
            pose_dir = pose_folder_name(pose_idx, field)
            for shot in extract_form_shots(data.get(fid)):
                blob_path = shot["path"]
                logical = blob_path.removeprefix("blobs/")
                if images_only and not is_image_path(logical):
                    continue

                file_name = Path(logical.replace("\\", "/")).name or "blob"
                dest_dir = output_dir / animal_dir / pose_dir
                dest_path = unique_dest_path(dest_dir, file_name, package_id)
                key = s3_key(prefix, package_id, blob_path)

                rec = {
                    "animal_id": animal_id,
                    "pose_index": str(pose_idx),
                    "pose_field_id": fid,
                    "pose_folder": pose_dir,
                    "package_id": package_id,
                    "s3_key": key,
                    "local_path": str(dest_path.relative_to(output_dir)),
                    "status": "",
                }

                if skip_existing and dest_path.exists():
                    rec["status"] = "skipped_exists"
                    skipped += 1
                    rows_out.append(rec)
                    continue

                if dry_run:
                    rec["status"] = "planned"
                    print(dest_path)
                    rows_out.append(rec)
                    continue

                try:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    client.download_file(args.bucket, key, str(dest_path))
                    rec["status"] = "ok"
                    downloaded += 1
                    print(dest_path)
                except ClientError as exc:
                    code = exc.response.get("Error", {}).get("Code", "")
                    rec["status"] = f"error:{code}"
                    if code in ("404", "NoSuchKey"):
                        missing += 1
                        print(f"  NOT FOUND s3://{args.bucket}/{key}", file=sys.stderr)
                    else:
                        errors += 1
                        print(f"  ERROR {key}: {exc}", file=sys.stderr)
                except (BotoCoreError, OSError) as exc:
                    rec["status"] = f"error:{exc}"
                    errors += 1
                    print(f"  ERROR {key}: {exc}", file=sys.stderr)
                rows_out.append(rec)

    if not dry_run and rows_out:
        index_path = Path(args.index_csv) if args.index_csv else output_dir / "_export_index.csv"
        index_path.parent.mkdir(parents=True, exist_ok=True)
        with index_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "animal_id", "pose_index", "pose_field_id", "pose_folder",
                    "package_id", "s3_key", "local_path", "status",
                ],
            )
            writer.writeheader()
            writer.writerows(rows_out)
        print(f"\nИндекс: {index_path}")

    print(
        f"\nГотово: скачано={downloaded}, пропущено={skipped}, "
        f"нет в S3={missing}, ошибок={errors}"
        + (" (dry-run)" if dry_run else ""),
    )
    return 0 if errors == 0 else 1


# ── CLI ──────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="S3 -> папки по животным и ракурсам (standalone, boto3)",
    )
    sub = p.add_subparsers(dest="command", required=True)

    pl = sub.add_parser("list", help="Шаг 1: посмотреть содержимое бакета")
    pl.add_argument("--bucket", required=True, help="Имя S3-бакета")
    pl.add_argument(
        "--prefix",
        default="",
        help="Префикс внутри бакета (как в storage_uri проекта, напр. korovas-2026/)",
    )
    _add_s3_auth_args(pl)
    pl.add_argument("--limit", type=int, default=500, help="Макс. объектов для листинга")
    pl.set_defaults(func=cmd_list)

    pd = sub.add_parser("download", help="Шаг 2: скачать фото по манифестам")
    pd.add_argument("--bucket", required=True)
    pd.add_argument("--prefix", default="")
    _add_s3_auth_args(pd)
    pd.add_argument(
        "--manifests",
        required=True,
        help="manifests.jsonl — одна строка JSON на пакет (см. export_manifests.sql)",
    )
    pd.add_argument(
        "--config",
        default="",
        help="config.json проекта (опционально; без него — авто по manifest.data)",
    )
    pd.add_argument(
        "--auto-fields",
        action="store_true",
        help="Ракурсы из manifest.data (photo_top, photo_profile_left, …), игнор config",
    )
    pd.add_argument("--output", required=True, help="Локальная папка выгрузки")
    pd.add_argument(
        "--animal-field",
        default="",
        help="Папка животного: cow_name (кличка/имя), cow_identifier (ID) и т.д.",
    )
    pd.add_argument("--phase", default="completed", help="Только пакеты с этой фазой")
    pd.add_argument(
        "--all-phases",
        action="store_true",
        help="Скачать все фазы из manifests.jsonl (игнор --phase)",
    )
    pd.add_argument("--all-blobs", action="store_true", help="Не только изображения")
    pd.add_argument("--skip-existing", action="store_true")
    pd.add_argument("--index-csv", default="")
    pd.add_argument("--dry-run", action="store_true")
    pd.set_defaults(func=cmd_download)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
