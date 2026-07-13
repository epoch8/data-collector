#!/usr/bin/env python3
"""Полный read-only бэкап проекта data-collector (без Django).

Скачивает локально:
  - Postgres project DB (все таблицы public → JSONL + manifests.jsonl)
  - S3 prefix проекта (все объекты, зеркало ключей)
  - Git-репозиторий проекта (shallow clone → collector/config.json, media/, viz.json)

Безопасность:
  - Только чтение из Postgres (SELECT), S3 (ListObjects/GetObject), Git (clone)
  - Ничего не удаляет ни локально, ни в облаке
  - Пишет только в --output (создаёт новые файлы / пропускает существующие)

Пример:
  cd tools/project-backup
  pip install -r requirements.txt
  $env:DATABASE_URL = "postgresql+psycopg2://..."
  $env:AWS_PROFILE = "yandex"
  python backup_project.py backup \\
    --bucket dc-project-korovas \\
    --endpoint-url https://storage.yandexcloud.net \\
    --git-remote git@github.com:org/repo.git \\
    --output $env:USERPROFILE\\Desktop\\backup\\korovas
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import unquote, urlparse

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
except ImportError:
    boto3 = None  # type: ignore[assignment]
    BotoCoreError = ClientError = NoCredentialsError = Exception  # type: ignore[misc, assignment]

try:
    import psycopg2
    from psycopg2 import sql
except ImportError:
    psycopg2 = None  # type: ignore[assignment]
    sql = None  # type: ignore[assignment]


# ── helpers ──────────────────────────────────────────────────────────────────


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _uri_to_connect_kwargs(database_url: str) -> dict:
    raw = (database_url or "").strip()
    if raw.startswith("postgresql+psycopg2://"):
        raw = "postgresql://" + raw[len("postgresql+psycopg2://") :]
    elif raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://") :]

    parts = urlparse(raw)
    if parts.scheme not in ("postgresql",):
        raise ValueError("Ожидается postgresql:// или postgresql+psycopg2:// URI")

    dbname = (parts.path or "").lstrip("/")
    if not dbname:
        raise ValueError("В URI не указано имя базы")

    from urllib.parse import parse_qs

    qs = parse_qs(parts.query)
    sslmode = (qs.get("sslmode") or [""])[0]

    kwargs = {
        "host": parts.hostname,
        "port": parts.port or 5432,
        "dbname": dbname,
        "user": unquote(parts.username or ""),
        "password": unquote(parts.password or ""),
    }
    if sslmode:
        kwargs["sslmode"] = sslmode
    return kwargs


def normalize_prefix(prefix: str) -> str:
    p = (prefix or "").strip().replace("\\", "/")
    if p and not p.endswith("/"):
        p += "/"
    return p


def make_s3_client(args: argparse.Namespace):
    if boto3 is None:
        raise RuntimeError("Установите boto3: pip install boto3")

    endpoint = (
        (getattr(args, "endpoint_url", "") or "").strip()
        or os.environ.get("S3_ENDPOINT_URL", "")
        or os.environ.get("AWS_ENDPOINT_URL", "")
    )
    access_key = (
        (getattr(args, "access_key", "") or "").strip()
        or os.environ.get("AWS_ACCESS_KEY_ID", "")
        or os.environ.get("S3_KEY", "")
    )
    secret_key = (
        (getattr(args, "secret_key", "") or "").strip()
        or os.environ.get("AWS_SECRET_ACCESS_KEY", "")
        or os.environ.get("S3_SECRET", "")
    )
    region = (getattr(args, "region", "") or "").strip() or os.environ.get("AWS_DEFAULT_REGION", "")

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


def _validate_output_dir(output: Path) -> None:
    raw = str(output)
    if raw.startswith("s3://") or raw.startswith("gs://"):
        raise ValueError("OUTPUT должен быть локальной папкой, не URI облака")
    if output.exists() and not output.is_dir():
        raise ValueError(f"OUTPUT существует и не является папкой: {output}")


def _write_json(path: Path, data: Any, *, dry_run: bool) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ── Postgres backup ───────────────────────────────────────────────────────────


def _list_public_tables(conn) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
            """
        )
        return [row[0] for row in cur.fetchall()]


def _export_table_jsonl(conn, table: str, dest: Path, *, dry_run: bool) -> int:
    if dry_run:
        with conn.cursor() as cur:
            cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table)))
            row = cur.fetchone()
            return int(row[0]) if row else 0

    query = sql.SQL("SELECT row_to_json(t) FROM {} AS t").format(sql.Identifier(table))
    count = 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8") as f, conn.cursor() as cur:
        cur.execute(query)
        while True:
            rows = cur.fetchmany(500)
            if not rows:
                break
            for (row_json,) in rows:
                f.write(json.dumps(row_json, ensure_ascii=False) + "\n")
                count += 1
    return count


def _export_manifests_jsonl(conn, dest: Path, *, dry_run: bool) -> int:
    """Совместимость с tools/photo-export (manifests.jsonl)."""
    where = """
        manifest_json IS NOT NULL
          AND manifest_json <> ''
    """
    if dry_run:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM package_session WHERE {where}")
            row = cur.fetchone()
            return int(row[0]) if row else 0

    sql_text = f"""
        SELECT package_id, phase, manifest_json
        FROM package_session
        WHERE {where}
        ORDER BY created_at
    """
    count = 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    with conn.cursor() as cur:
        cur.execute(sql_text)
        with dest.open("w", encoding="utf-8") as f:
            for package_id, pkg_phase, manifest_json in cur:
                try:
                    manifest = json.loads(manifest_json)
                except json.JSONDecodeError:
                    continue
                line = json.dumps(
                    {
                        "package_id": package_id,
                        "phase": pkg_phase,
                        "manifest": manifest,
                    },
                    ensure_ascii=False,
                )
                f.write(line + "\n")
                count += 1
    return count


def backup_postgres(
    connect_kwargs: dict,
    output_dir: Path,
    *,
    dry_run: bool,
) -> dict[str, Any]:
    if psycopg2 is None or sql is None:
        raise RuntimeError("Установите psycopg2-binary: pip install psycopg2-binary")

    pg_dir = output_dir / "postgres"
    tables_info: dict[str, int] = {}
    manifests_count = 0

    with psycopg2.connect(**connect_kwargs) as conn:
        conn.set_session(readonly=True, autocommit=True)
        tables = _list_public_tables(conn)
        for table in tables:
            dest = pg_dir / f"{table}.jsonl"
            tables_info[table] = _export_table_jsonl(conn, table, dest, dry_run=dry_run)
        if "package_session" in tables:
            manifests_count = _export_manifests_jsonl(
                conn,
                output_dir / "manifests.jsonl",
                dry_run=dry_run,
            )

    return {
        "tables": tables_info,
        "table_count": len(tables_info),
        "row_count_total": sum(tables_info.values()),
        "manifests_jsonl_rows": manifests_count,
        "directory": str(pg_dir),
    }


# ── S3 backup ─────────────────────────────────────────────────────────────────


def _local_path_for_s3_key(prefix: str, key: str, s3_root: Path) -> Path:
    rel = key
    if prefix and key.startswith(prefix):
        rel = key[len(prefix) :]
    rel = rel.lstrip("/")
    return s3_root / rel.replace("/", os.sep)


def backup_s3(
    client,
    bucket: str,
    prefix: str,
    output_dir: Path,
    *,
    dry_run: bool,
    skip_existing: bool,
) -> dict[str, Any]:
    prefix = normalize_prefix(prefix)
    s3_root = output_dir / "s3"
    listed = downloaded = skipped = errors = 0
    total_bytes = 0

    paginator = client.get_paginator("list_objects_v2")
    try:
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents") or []:
                key = obj["Key"]
                if key.endswith("/"):
                    continue
                listed += 1
                local_path = _local_path_for_s3_key(prefix, key, s3_root)
                size = int(obj.get("Size") or 0)

                if skip_existing and local_path.is_file():
                    skipped += 1
                    total_bytes += size
                    continue

                if dry_run:
                    downloaded += 1
                    total_bytes += size
                    continue

                local_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    client.download_file(bucket, key, str(local_path))
                    downloaded += 1
                    total_bytes += size
                except (ClientError, BotoCoreError, OSError) as exc:
                    errors += 1
                    print(f"S3 skip {key}: {exc}", file=sys.stderr)
    except NoCredentialsError:
        raise RuntimeError(
            "Нет S3 credentials. Задайте AWS_PROFILE или AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY."
        ) from None
    except (ClientError, BotoCoreError) as exc:
        raise RuntimeError(f"S3 list error: {exc}") from exc

    return {
        "bucket": bucket,
        "prefix": prefix,
        "objects_listed": listed,
        "objects_downloaded": downloaded,
        "objects_skipped_existing": skipped,
        "errors": errors,
        "bytes": total_bytes,
        "directory": str(s3_root),
    }


# ── Git backup ────────────────────────────────────────────────────────────────


def backup_git(
    git_remote: str,
    git_ref: str,
    output_dir: Path,
    *,
    dry_run: bool,
) -> dict[str, Any]:
    git_remote = (git_remote or "").strip()
    git_ref = (git_ref or "main").strip() or "main"
    if not git_remote:
        return {"skipped": True, "reason": "git_remote not set"}

    if shutil.which("git") is None:
        return {"skipped": True, "reason": "git not found in PATH"}

    dest = output_dir / "git-repo"
    if dest.exists():
        return {
            "skipped": True,
            "reason": f"destination already exists: {dest}",
            "hint": "Удалите папку вручную или укажите другой --output",
            "directory": str(dest),
        }

    if dry_run:
        return {
            "skipped": False,
            "dry_run": True,
            "remote": git_remote,
            "ref": git_ref,
            "directory": str(dest),
        }

    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "git",
        "clone",
        "--depth",
        "1",
        "--branch",
        git_ref,
        "--single-branch",
        git_remote,
        str(dest),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        err = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(f"git clone failed: {err or exc}") from exc

    collector = dest / "collector"
    files_found = []
    for rel in ("config.json", "viz.json"):
        p = collector / rel
        if p.is_file():
            files_found.append(f"collector/{rel}")
    media_dir = collector / "media"
    media_count = sum(1 for p in media_dir.rglob("*") if p.is_file()) if media_dir.is_dir() else 0

    return {
        "skipped": False,
        "remote": git_remote,
        "ref": git_ref,
        "directory": str(dest),
        "collector_files": files_found,
        "collector_media_files": media_count,
    }


# ── CLI ───────────────────────────────────────────────────────────────────────


def _add_s3_auth_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--endpoint-url",
        default="",
        help="S3 endpoint (Yandex/MinIO), напр. https://storage.yandexcloud.net",
    )
    parser.add_argument("--access-key", default="", help="S3 access key")
    parser.add_argument("--secret-key", default="", help="S3 secret key")
    parser.add_argument("--region", default="", help="AWS region (опционально)")


def cmd_backup(args: argparse.Namespace) -> int:
    output_dir = Path(args.output).expanduser().resolve()
    dry_run = bool(args.dry_run)
    skip_existing = bool(args.skip_existing)

    try:
        _validate_output_dir(output_dir)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1

    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "backup_type": "data-collector-project-full",
        "created_at": _utc_now_iso(),
        "dry_run": dry_run,
        "output": str(output_dir),
        "read_only": True,
        "sections": {},
    }

    print("=== data-collector project backup (read-only) ===")
    print(f"Output: {output_dir}")
    if dry_run:
        print("DRY RUN — удалённых операций не будет\n")

    # Postgres
    if not args.skip_postgres:
        database_url = (args.database_url or os.environ.get("DATABASE_URL", "")).strip()
        if not database_url:
            print("Postgres: пропуск (нет --database-url / DATABASE_URL)", file=sys.stderr)
            manifest["sections"]["postgres"] = {"skipped": True, "reason": "no DATABASE_URL"}
        else:
            print("Postgres: экспорт таблиц…")
            try:
                connect_kwargs = _uri_to_connect_kwargs(database_url)
                pg_result = backup_postgres(connect_kwargs, output_dir, dry_run=dry_run)
                manifest["sections"]["postgres"] = pg_result
                print(
                    f"  таблиц: {pg_result['table_count']}, "
                    f"строк: {pg_result['row_count_total']}, "
                    f"manifests.jsonl: {pg_result['manifests_jsonl_rows']}"
                )
            except Exception as exc:
                print(f"Postgres ERROR: {exc}", file=sys.stderr)
                manifest["sections"]["postgres"] = {"error": str(exc)}
                if not args.continue_on_error:
                    return 1
    else:
        manifest["sections"]["postgres"] = {"skipped": True, "reason": "--skip-postgres"}
        print("Postgres: пропуск (--skip-postgres)")

    # S3
    if not args.skip_s3:
        bucket = (args.bucket or os.environ.get("S3_BUCKET", "")).strip()
        if not bucket:
            print("S3: пропуск (нет --bucket / S3_BUCKET)", file=sys.stderr)
            manifest["sections"]["s3"] = {"skipped": True, "reason": "no bucket"}
        else:
            prefix = args.prefix if args.prefix is not None else os.environ.get("S3_PREFIX", "")
            print(f"S3: скачивание s3://{bucket}/{normalize_prefix(prefix)}…")
            try:
                client = make_s3_client(args)
                s3_result = backup_s3(
                    client,
                    bucket,
                    prefix,
                    output_dir,
                    dry_run=dry_run,
                    skip_existing=skip_existing,
                )
                manifest["sections"]["s3"] = s3_result
                print(
                    f"  объектов: {s3_result['objects_listed']}, "
                    f"скачано: {s3_result['objects_downloaded']}, "
                    f"пропущено (уже есть): {s3_result['objects_skipped_existing']}, "
                    f"ошибок: {s3_result['errors']}"
                )
            except Exception as exc:
                print(f"S3 ERROR: {exc}", file=sys.stderr)
                manifest["sections"]["s3"] = {"error": str(exc)}
                if not args.continue_on_error:
                    return 1
    else:
        manifest["sections"]["s3"] = {"skipped": True, "reason": "--skip-s3"}
        print("S3: пропуск (--skip-s3)")

    # Git
    if not args.skip_git:
        git_remote = (args.git_remote or os.environ.get("GIT_REMOTE", "")).strip()
        git_ref = (args.git_ref or os.environ.get("GIT_REF", "main")).strip() or "main"
        print(f"Git: clone {git_remote or '(не задан)'}…")
        try:
            git_result = backup_git(git_remote, git_ref, output_dir, dry_run=dry_run)
            manifest["sections"]["git"] = git_result
            if git_result.get("skipped"):
                print(f"  пропуск: {git_result.get('reason', 'unknown')}")
            else:
                print(f"  → {git_result.get('directory')}")
        except Exception as exc:
            print(f"Git ERROR: {exc}", file=sys.stderr)
            manifest["sections"]["git"] = {"error": str(exc)}
            if not args.continue_on_error:
                return 1
    else:
        manifest["sections"]["git"] = {"skipped": True, "reason": "--skip-git"}
        print("Git: пропуск (--skip-git)")

    manifest_path = output_dir / "backup_manifest.json"
    _write_json(manifest_path, manifest, dry_run=dry_run)
    print(f"\nМанифест: {manifest_path}")
    print("Готово. Удалённых данных не затронуто.")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    backup_dir = Path(args.backup).expanduser().resolve()
    manifest_path = backup_dir / "backup_manifest.json"
    if not manifest_path.is_file():
        print(f"Нет {manifest_path}", file=sys.stderr)
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    print(f"Backup from: {manifest.get('created_at')}")
    print(f"Output: {manifest.get('output')}")

    ok = True
    for section, info in (manifest.get("sections") or {}).items():
        if not isinstance(info, dict):
            continue
        if info.get("error"):
            print(f"  {section}: ERROR — {info['error']}")
            ok = False
            continue
        if info.get("skipped"):
            print(f"  {section}: skipped ({info.get('reason', '')})")
            continue
        if section == "postgres":
            pg_dir = backup_dir / "postgres"
            missing = [
                t
                for t, _ in (info.get("tables") or {}).items()
                if not (pg_dir / f"{t}.jsonl").is_file()
            ]
            if missing:
                print(f"  postgres: отсутствуют файлы таблиц: {', '.join(missing)}")
                ok = False
            else:
                print(f"  postgres: OK ({info.get('table_count', 0)} таблиц)")
        elif section == "s3":
            s3_dir = backup_dir / "s3"
            n_files = sum(1 for p in s3_dir.rglob("*") if p.is_file()) if s3_dir.is_dir() else 0
            print(f"  s3: {n_files} локальных файлов (ожидалось скачать ~{info.get('objects_downloaded', '?')})")
        elif section == "git":
            git_dir = Path(info.get("directory") or backup_dir / "git-repo")
            cfg = git_dir / "collector" / "config.json"
            if git_dir.is_dir() and cfg.is_file():
                print(f"  git: OK ({cfg})")
            elif info.get("dry_run"):
                print("  git: dry-run only")
            else:
                print(f"  git: нет collector/config.json в {git_dir}")
                ok = False

    manifests = backup_dir / "manifests.jsonl"
    if manifests.is_file():
        lines = sum(1 for ln in manifests.read_text(encoding="utf-8").splitlines() if ln.strip())
        print(f"  manifests.jsonl: {lines} строк")
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Полный read-only бэкап проекта (Postgres + S3 + Git)",
    )
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("backup", help="Скачать бэкап в локальную папку")
    b.add_argument(
        "-o",
        "--output",
        default=os.environ.get("OUTPUT_DIR", "backup"),
        help="Локальная папка бэкапа",
    )
    b.add_argument("--database-url", default="", help="Postgres URI (или env DATABASE_URL)")
    b.add_argument("--bucket", default="", help="S3 bucket (или env S3_BUCKET)")
    b.add_argument("--prefix", default=None, help="Префикс в бакете (или env S3_PREFIX)")
    b.add_argument("--git-remote", default="", help="SSH/HTTPS URL репо (или env GIT_REMOTE)")
    b.add_argument("--git-ref", default="", help="Ветка Git (default main)")
    b.add_argument("--dry-run", action="store_true", help="Только план, без записи файлов")
    b.add_argument(
        "--skip-existing",
        action="store_true",
        help="S3: не перекачивать уже существующие локальные файлы",
    )
    b.add_argument("--skip-postgres", action="store_true")
    b.add_argument("--skip-s3", action="store_true")
    b.add_argument("--skip-git", action="store_true")
    b.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Продолжить при ошибке одной из секций",
    )
    _add_s3_auth_args(b)
    b.set_defaults(func=cmd_backup)

    v = sub.add_parser("verify", help="Проверить локальный бэкап по backup_manifest.json")
    v.add_argument("backup", help="Папка с бэкапом")
    v.set_defaults(func=cmd_verify)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
