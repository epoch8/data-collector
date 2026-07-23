#!/usr/bin/env python3
"""Восстановить бэкап project-backup в локальные Postgres + MinIO (test_dev).

Читает локальную папку бэкапа (postgres/*.jsonl + s3/**) и заливает в цель.
По умолчанию цель - test_dev: Postgres :55432 и MinIO :9000.

Безопасность:
  - Пишет только в --database-url / --bucket из аргументов или TARGET_* env
  - По умолчанию отказывается писать в non-localhost / облачные endpoint'ы
  - --wipe чистит таблицы цели перед заливкой (нужен --yes)
  - Ничего не трогает в исходном бэкапе

Пример (PowerShell):
  docker compose -f test_dev/docker-compose.yml up -d
  cd tools\\project-backup
  pip install -r requirements.txt
  python restore_project.py restore `
    --backup $env:USERPROFILE\\Desktop\\backup\\korovas `
    --database-url postgresql://collector:collector@localhost:55432/proj_korovas `
    --bucket dc-packages `
    --endpoint-url http://localhost:9000 `
    --access-key minioadmin `
    --secret-key minioadmin `
    --wipe --yes
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:
    boto3 = None  # type: ignore[assignment]
    BotoCoreError = ClientError = Exception  # type: ignore[misc, assignment]

try:
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extras import execute_values
except ImportError:
    psycopg2 = None  # type: ignore[assignment]
    sql = None  # type: ignore[assignment]
    execute_values = None  # type: ignore[assignment]


# Порядок заливки (сначала сессии, потом зависимые по смыслу таблицы).
TABLE_ORDER = [
    "package_session",
    "uploaded_blob",
    "package_field_change",
    "cow_keypoint_annotation",
    "cow_inference_result",
    "yolo_detection",
    "depth_map",
    "cvat_link",
]

# DDL совпадает с django_server/api/project_db.py (SQLAlchemy create_all).
TABLE_DDL: dict[str, str] = {
    "package_session": """
        CREATE TABLE IF NOT EXISTS package_session (
            package_id TEXT PRIMARY KEY,
            project_id TEXT,
            phase TEXT NOT NULL,
            manifest_json TEXT NOT NULL,
            failure_reason TEXT NOT NULL,
            uploader_uid TEXT NOT NULL,
            uploader_email TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """,
    "uploaded_blob": """
        CREATE TABLE IF NOT EXISTS uploaded_blob (
            id SERIAL PRIMARY KEY,
            package_id TEXT NOT NULL,
            logical_path TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            sha256 TEXT NOT NULL,
            storage_path TEXT NOT NULL,
            created_at TEXT NOT NULL,
            CONSTRAINT uq_blob_pkg_logical UNIQUE (package_id, logical_path)
        )
    """,
    "package_field_change": """
        CREATE TABLE IF NOT EXISTS package_field_change (
            id SERIAL PRIMARY KEY,
            package_id TEXT NOT NULL,
            field_id TEXT NOT NULL,
            before_value TEXT,
            after_value TEXT,
            reason TEXT NOT NULL,
            verifier_email TEXT NOT NULL,
            changed_at TEXT NOT NULL
        )
    """,
    "cow_keypoint_annotation": """
        CREATE TABLE IF NOT EXISTS cow_keypoint_annotation (
            id SERIAL PRIMARY KEY,
            package_id TEXT NOT NULL,
            manifest_blob_key TEXT NOT NULL,
            cvat_link TEXT NOT NULL,
            image_width INTEGER NOT NULL,
            image_height INTEGER NOT NULL,
            annotation_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            CONSTRAINT uq_gt_pkg_key UNIQUE (package_id, manifest_blob_key)
        )
    """,
    "cow_inference_result": """
        CREATE TABLE IF NOT EXISTS cow_inference_result (
            id SERIAL PRIMARY KEY,
            package_id TEXT NOT NULL,
            manifest_blob_key TEXT NOT NULL,
            source_export TEXT NOT NULL,
            image_width INTEGER NOT NULL,
            image_height INTEGER NOT NULL,
            inference_json TEXT NOT NULL,
            depth_blob_key TEXT,
            depth_format TEXT NOT NULL,
            depth_unit TEXT NOT NULL,
            depth_width INTEGER,
            depth_height INTEGER,
            created_at TEXT NOT NULL,
            CONSTRAINT uq_inf_pkg_key UNIQUE (package_id, manifest_blob_key)
        )
    """,
    "yolo_detection": """
        CREATE TABLE IF NOT EXISTS yolo_detection (
            id SERIAL PRIMARY KEY,
            package_id TEXT NOT NULL,
            manifest_blob_key TEXT NOT NULL,
            image_width INTEGER NOT NULL,
            image_height INTEGER NOT NULL,
            detections_json TEXT NOT NULL,
            source_label TEXT NOT NULL,
            created_at TEXT NOT NULL,
            CONSTRAINT uq_yolo_pkg_key UNIQUE (package_id, manifest_blob_key)
        )
    """,
    "depth_map": """
        CREATE TABLE IF NOT EXISTS depth_map (
            id SERIAL PRIMARY KEY,
            package_id TEXT NOT NULL,
            manifest_blob_key TEXT NOT NULL,
            depth_path TEXT NOT NULL,
            format TEXT NOT NULL,
            unit TEXT NOT NULL,
            width INTEGER,
            height INTEGER,
            source_label TEXT NOT NULL,
            created_at TEXT NOT NULL,
            CONSTRAINT uq_depth_pkg_key UNIQUE (package_id, manifest_blob_key)
        )
    """,
    "cvat_link": """
        CREATE TABLE IF NOT EXISTS cvat_link (
            id SERIAL PRIMARY KEY,
            package_id TEXT NOT NULL,
            manifest_blob_key TEXT NOT NULL,
            url TEXT NOT NULL,
            label TEXT NOT NULL,
            created_at TEXT NOT NULL,
            CONSTRAINT uq_cvat_pkg_key UNIQUE (package_id, manifest_blob_key)
        )
    """,
}

CLOUD_MARKERS = (
    "yandexcloud",
    "amazonaws.com",
    "storage.googleapis.com",
    "googleapis.com",
    "blob.core.windows.net",
)


# ── helpers ──────────────────────────────────────────────────────────────────


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
        or os.environ.get("TARGET_S3_ENDPOINT_URL", "")
        or os.environ.get("S3_ENDPOINT_URL", "")
        or os.environ.get("AWS_ENDPOINT_URL", "")
    )
    access_key = (
        (getattr(args, "access_key", "") or "").strip()
        or os.environ.get("TARGET_S3_KEY", "")
        or os.environ.get("AWS_ACCESS_KEY_ID", "")
        or os.environ.get("S3_KEY", "")
    )
    secret_key = (
        (getattr(args, "secret_key", "") or "").strip()
        or os.environ.get("TARGET_S3_SECRET", "")
        or os.environ.get("AWS_SECRET_ACCESS_KEY", "")
        or os.environ.get("S3_SECRET", "")
    )
    region = (
        (getattr(args, "region", "") or "").strip()
        or os.environ.get("AWS_DEFAULT_REGION", "")
        or "us-east-1"
    )

    kwargs: dict[str, Any] = {"region_name": region}
    if endpoint:
        kwargs["endpoint_url"] = endpoint
    if access_key:
        kwargs["aws_access_key_id"] = access_key
    if secret_key:
        kwargs["aws_secret_access_key"] = secret_key
    return boto3.client("s3", **kwargs), endpoint


def _is_local_host(host: str | None) -> bool:
    h = (host or "").strip().lower()
    return h in {"localhost", "127.0.0.1", "::1", "host.docker.internal"}


def assert_safe_targets(
    database_url: str,
    endpoint_url: str,
    *,
    allow_remote: bool,
) -> None:
    """Не дать случайно залить прод."""
    if allow_remote:
        return

    problems: list[str] = []
    if database_url:
        kw = _uri_to_connect_kwargs(database_url)
        if not _is_local_host(kw.get("host")):
            problems.append(f"Postgres host не localhost: {kw.get('host')}")

    ep = (endpoint_url or "").strip().lower()
    if ep:
        for marker in CLOUD_MARKERS:
            if marker in ep:
                problems.append(f"S3 endpoint похож на облако: {endpoint_url}")
                break
        parsed = urlparse(ep if "://" in ep else f"http://{ep}")
        if parsed.hostname and not _is_local_host(parsed.hostname):
            problems.append(f"S3 host не localhost: {parsed.hostname}")

    if problems:
        raise SystemExit(
            "Отказ: цель не похожа на локальный test_dev.\n"
            + "\n".join(f"  - {p}" for p in problems)
            + "\nЕсли уверены - добавьте --allow-remote."
        )


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"{path.name}:{line_no}: невалидный JSON: {e}") from e
            if not isinstance(obj, dict):
                raise ValueError(f"{path.name}:{line_no}: ожидался объект JSON")
            rows.append(obj)
    return rows


# ── Postgres ─────────────────────────────────────────────────────────────────


def ensure_database(database_url: str, *, dry_run: bool) -> None:
    """CREATE DATABASE при необходимости (подключаемся к maintenance DB)."""
    if psycopg2 is None or sql is None:
        raise RuntimeError("Установите psycopg2-binary")

    kw = _uri_to_connect_kwargs(database_url)
    dbname = kw["dbname"]
    admin = dict(kw)
    # Подключаемся к служебной БД из docker-compose (POSTGRES_DB=collector).
    admin["dbname"] = os.environ.get("TARGET_PG_ADMIN_DB", "collector")

    print(f"Postgres: проверка БД {dbname!r} на {admin['host']}:{admin['port']}...")
    if dry_run:
        print("  (dry-run) CREATE DATABASE пропущен")
        return

    conn = psycopg2.connect(**admin)
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
            if cur.fetchone():
                print(f"  БД уже есть: {dbname}")
                return
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))
            print(f"  Создана БД: {dbname}")
    finally:
        conn.close()


def ensure_schema(conn) -> None:
    with conn.cursor() as cur:
        for name in TABLE_ORDER:
            cur.execute(TABLE_DDL[name])
            cur.execute(
                sql.SQL("CREATE INDEX IF NOT EXISTS {} ON {} ({})").format(
                    sql.Identifier(f"ix_{name}_package_id"),
                    sql.Identifier(name),
                    sql.Identifier("package_id"),
                )
            )
    conn.commit()


def wipe_tables(conn, *, dry_run: bool) -> None:
    tables = list(reversed(TABLE_ORDER))
    print(f"Postgres: TRUNCATE {', '.join(tables)}...")
    if dry_run:
        print("  (dry-run) truncate пропущен")
        return
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL("TRUNCATE TABLE {} RESTART IDENTITY CASCADE").format(
                sql.SQL(", ").join(sql.Identifier(t) for t in tables)
            )
        )
    conn.commit()


def _table_columns(conn, table: str) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table,),
        )
        return [r[0] for r in cur.fetchall()]


def _reset_serial(conn, table: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
              AND column_default LIKE 'nextval%%'
            """,
            (table,),
        )
        cols = [r[0] for r in cur.fetchall()]
        for col in cols:
            cur.execute(
                sql.SQL(
                    "SELECT setval("
                    "pg_get_serial_sequence(%s, %s), "
                    "COALESCE((SELECT MAX({col}) FROM {table}), 1))"
                ).format(
                    col=sql.Identifier(col),
                    table=sql.Identifier(table),
                ),
                (table, col),
            )


def restore_table(conn, table: str, rows: list[dict[str, Any]], *, dry_run: bool) -> int:
    if not rows:
        print(f"  {table}: 0")
        return 0
    cols = _table_columns(conn, table)
    usable = [c for c in cols if any(c in r for r in rows)]
    if not usable:
        print(f"  {table}: нет пересечения колонок - пропуск")
        return 0

    if dry_run:
        print(f"  {table}: {len(rows)} (would insert)")
        return len(rows)

    values = []
    for r in rows:
        values.append(tuple(r.get(c) for c in usable))

    insert_sql = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
        sql.Identifier(table),
        sql.SQL(", ").join(sql.Identifier(c) for c in usable),
    )
    with conn.cursor() as cur:
        execute_values(cur, insert_sql.as_string(conn), values, page_size=500)
        _reset_serial(conn, table)
    conn.commit()
    print(f"  {table}: {len(rows)} -> ok")
    return len(rows)


def restore_postgres(
    backup_dir: Path,
    database_url: str,
    *,
    wipe: bool,
    dry_run: bool,
) -> dict[str, Any]:
    if psycopg2 is None or execute_values is None:
        raise RuntimeError("Установите psycopg2-binary")

    pg_dir = backup_dir / "postgres"
    if not pg_dir.is_dir():
        raise FileNotFoundError(f"Нет папки {pg_dir}")

    ensure_database(database_url, dry_run=dry_run)

    result: dict[str, Any] = {"tables": {}, "row_count_total": 0}
    if dry_run:
        for table in TABLE_ORDER:
            rows = _load_jsonl(pg_dir / f"{table}.jsonl")
            result["tables"][table] = len(rows)
            result["row_count_total"] += len(rows)
            print(f"  {table}: {len(rows)} (dry-run)")
        extras = sorted(
            p.stem
            for p in pg_dir.glob("*.jsonl")
            if p.stem not in TABLE_DDL
        )
        if extras:
            print(f"  неизвестные таблицы (пропуск): {', '.join(extras)}")
        return result

    kw = _uri_to_connect_kwargs(database_url)
    conn = psycopg2.connect(**kw)
    try:
        ensure_schema(conn)
        if wipe:
            wipe_tables(conn, dry_run=False)

        known = set(TABLE_ORDER)
        for table in TABLE_ORDER:
            rows = _load_jsonl(pg_dir / f"{table}.jsonl")
            n = restore_table(conn, table, rows, dry_run=False)
            result["tables"][table] = n
            result["row_count_total"] += n

        extras = sorted(p.stem for p in pg_dir.glob("*.jsonl") if p.stem not in known)
        if extras:
            print(f"  неизвестные таблицы (пропуск): {', '.join(extras)}")
            result["skipped_unknown_tables"] = extras
    finally:
        conn.close()

    return result


# ── S3 ───────────────────────────────────────────────────────────────────────


def ensure_bucket(client, bucket: str, *, dry_run: bool) -> None:
    print(f"S3: бакет {bucket!r}...")
    if dry_run:
        print("  (dry-run) create_bucket пропущен")
        return
    try:
        client.head_bucket(Bucket=bucket)
        print("  бакет уже есть")
    except ClientError:
        client.create_bucket(Bucket=bucket)
        print("  бакет создан")


def restore_s3(
    backup_dir: Path,
    client,
    bucket: str,
    *,
    key_prefix: str,
    skip_existing: bool,
    dry_run: bool,
) -> dict[str, Any]:
    s3_root = backup_dir / "s3"
    if not s3_root.is_dir():
        raise FileNotFoundError(f"Нет папки {s3_root}")

    prefix = normalize_prefix(key_prefix)
    files = [p for p in s3_root.rglob("*") if p.is_file()]
    uploaded = skipped = errors = 0
    total_bytes = 0

    print(f"S3: заливка {len(files)} файлов -> s3://{bucket}/{prefix}")
    ensure_bucket(client, bucket, dry_run=dry_run)

    for path in files:
        rel = path.relative_to(s3_root).as_posix()
        key = f"{prefix}{rel}"
        size = path.stat().st_size
        total_bytes += size

        if skip_existing and not dry_run:
            try:
                client.head_object(Bucket=bucket, Key=key)
                skipped += 1
                continue
            except ClientError:
                pass

        if dry_run:
            uploaded += 1
            continue

        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        try:
            extra = {"ContentType": ctype}
            client.upload_file(str(path), bucket, key, ExtraArgs=extra)
            uploaded += 1
            if uploaded % 100 == 0:
                print(f"  ... {uploaded}/{len(files)}")
        except (BotoCoreError, ClientError, OSError) as e:
            errors += 1
            print(f"  ERROR {key}: {e}", file=sys.stderr)

    print(
        f"  скачано в цель: {uploaded}, пропущено: {skipped}, "
        f"ошибок: {errors}, байт (локально): {total_bytes}"
    )
    return {
        "files_local": len(files),
        "objects_uploaded": uploaded,
        "objects_skipped_existing": skipped,
        "errors": errors,
        "bytes_local": total_bytes,
        "key_prefix": prefix,
    }


# ── CLI ──────────────────────────────────────────────────────────────────────


def _print_ui_hint(database_url: str, bucket: str, endpoint: str, key_prefix: str) -> None:
    prefix = normalize_prefix(key_prefix)
    if prefix:
        storage = f"s3://{bucket}/{prefix}"
    else:
        storage = f"s3://{bucket}/"
    print("\n--- Подставьте в UI проекта (Изменить хранилище) ---")
    print(f"  database_uri = {database_url}")
    print(f"  storage_uri  = {storage}")
    print(f"  endpoint_url = {endpoint or 'http://localhost:9000'}")
    print("  access key   = (как --access-key / minioadmin)")
    print("  secret key   = (как --secret-key / minioadmin)")
    print("Затем: Проверить хранилище.")


def cmd_restore(args: argparse.Namespace) -> int:
    backup_dir = Path(args.backup).expanduser().resolve()
    if not backup_dir.is_dir():
        print(f"Нет папки бэкапа: {backup_dir}", file=sys.stderr)
        return 1

    database_url = (
        (args.database_url or "").strip()
        or os.environ.get("TARGET_DATABASE_URL", "").strip()
    )
    bucket = (
        (args.bucket or "").strip()
        or os.environ.get("TARGET_S3_BUCKET", "").strip()
        or os.environ.get("S3_BUCKET", "").strip()
    )
    endpoint = (
        (args.endpoint_url or "").strip()
        or os.environ.get("TARGET_S3_ENDPOINT_URL", "").strip()
        or os.environ.get("S3_ENDPOINT_URL", "").strip()
    )
    key_prefix = args.key_prefix if args.key_prefix is not None else os.environ.get(
        "TARGET_S3_PREFIX", ""
    )

    if not database_url and not args.skip_postgres:
        print("Нужен --database-url или TARGET_DATABASE_URL", file=sys.stderr)
        return 1
    if not bucket and not args.skip_s3:
        print("Нужен --bucket или TARGET_S3_BUCKET", file=sys.stderr)
        return 1
    if args.wipe and not args.yes and not args.dry_run:
        print("Для --wipe нужен --yes (иначе dry-run).", file=sys.stderr)
        return 1

    assert_safe_targets(
        database_url if not args.skip_postgres else "",
        endpoint if not args.skip_s3 else "",
        allow_remote=bool(args.allow_remote),
    )

    print("=== data-collector project restore ===")
    print(f"Backup: {backup_dir}")
    if args.dry_run:
        print("DRY RUN - ничего не пишем\n")

    if not args.skip_postgres:
        print("Postgres: восстановление...")
        pg = restore_postgres(
            backup_dir,
            database_url,
            wipe=bool(args.wipe),
            dry_run=bool(args.dry_run),
        )
        print(
            f"  итого строк: {pg['row_count_total']} "
            f"({len(pg['tables'])} таблиц)"
        )
    else:
        print("Postgres: пропуск (--skip-postgres)")

    if not args.skip_s3:
        client, resolved_endpoint = make_s3_client(args)
        endpoint = endpoint or resolved_endpoint or ""
        print("S3: восстановление...")
        restore_s3(
            backup_dir,
            client,
            bucket,
            key_prefix=key_prefix or "",
            skip_existing=bool(args.skip_existing),
            dry_run=bool(args.dry_run),
        )
    else:
        print("S3: пропуск (--skip-s3)")

    if not args.dry_run and not args.skip_postgres:
        _print_ui_hint(database_url, bucket or "dc-packages", endpoint, key_prefix or "")

    print("\nГотово.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Восстановить бэкап в локальные Postgres + MinIO (test_dev)",
    )
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("restore", help="Залить бэкап в локальную цель")
    r.add_argument(
        "--backup",
        required=True,
        help="Папка бэкапа (с postgres/ и s3/)",
    )
    r.add_argument(
        "--database-url",
        default="",
        help="Целевой Postgres URI (или TARGET_DATABASE_URL)",
    )
    r.add_argument("--bucket", default="", help="Целевой S3 bucket")
    r.add_argument("--endpoint-url", default="", help="S3 endpoint (MinIO)")
    r.add_argument("--access-key", default="", help="S3 access key")
    r.add_argument("--secret-key", default="", help="S3 secret key")
    r.add_argument("--region", default="", help="AWS region (для boto3)")
    r.add_argument(
        "--key-prefix",
        default=None,
        help="Префикс ключей в бакете (по умолчанию пусто = как в бэкапе)",
    )
    r.add_argument("--dry-run", action="store_true")
    r.add_argument(
        "--wipe",
        action="store_true",
        help="TRUNCATE таблиц цели перед заливкой",
    )
    r.add_argument(
        "--yes",
        action="store_true",
        help="Подтвердить --wipe",
    )
    r.add_argument(
        "--skip-existing",
        action="store_true",
        help="S3: не перезаливать уже существующие ключи",
    )
    r.add_argument("--skip-postgres", action="store_true")
    r.add_argument("--skip-s3", action="store_true")
    r.add_argument(
        "--allow-remote",
        action="store_true",
        help="Разрешить non-localhost цель (опасно)",
    )
    r.set_defaults(func=cmd_restore)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
