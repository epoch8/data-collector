#!/usr/bin/env python3
"""Выгрузить manifests.jsonl из project Postgres (шаг 2 перед download_photos_from_s3.py).

Только SELECT, ничего не меняет в БД.

Пример:
  $env:DATABASE_URL = "postgresql+psycopg2://USER:PASS@host:6432/dc-project-korovas?sslmode=require"
  cd tools/photo-export
  python export_manifests.py -o manifests.jsonl

Или:
  python export_manifests.py \\
    --host rc1b-hl1x61akq81cvefa.mdb.yandexcloud.net \\
    --port 6432 \\
    --db dc-project-korovas \\
    --user dc-project-korovas \\
    --password "..." \\
    -o manifests.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


def _uri_to_connect_kwargs(database_url: str) -> dict:
    """SQLAlchemy-style URI -> psycopg2 connect kwargs."""
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


def export_manifests(
  connect_kwargs: dict,
  output: Path,
  *,
  phase: str = "completed",
) -> int:
    try:
        import psycopg2
    except ImportError:
        print("Установите psycopg2: pip install psycopg2-binary", file=sys.stderr)
        return 1

    sql = """
        SELECT package_id, phase, manifest_json
        FROM package_session
        WHERE manifest_json IS NOT NULL
          AND manifest_json <> ''
    """
    params: tuple = ()
    if phase:
        sql += " AND phase = %s"
        params = (phase,)
    sql += " ORDER BY created_at"

    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0

    with psycopg2.connect(**connect_kwargs) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            with output.open("w", encoding="utf-8") as f:
                for package_id, pkg_phase, manifest_json in cur:
                    try:
                        manifest = json.loads(manifest_json)
                    except json.JSONDecodeError:
                        print(f"skip {package_id}: bad manifest JSON", file=sys.stderr)
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

    print(f"Записано пакетов: {count}")
    print(f"Файл: {output.resolve()}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Экспорт manifests.jsonl из Postgres (read-only)")
    p.add_argument(
        "-o",
        "--output",
        default="manifests.jsonl",
        help="Куда сохранить (по умолчанию manifests.jsonl)",
    )
    p.add_argument(
        "--database-url",
        default="",
        help="URI (или env DATABASE_URL)",
    )
    p.add_argument("--host", default="")
    p.add_argument("--port", type=int, default=6432)
    p.add_argument("--db", default="")
    p.add_argument("--user", default="")
    p.add_argument("--password", default="")
    p.add_argument(
        "--phase",
        default="completed",
        help="Фаза пакетов (по умолчанию completed; пусто = все)",
    )
    p.add_argument(
        "--all-phases",
        action="store_true",
        help="Экспортировать все фазы (не только completed)",
    )
    args = p.parse_args()

    database_url = (args.database_url or os.environ.get("DATABASE_URL", "")).strip()
    if database_url:
        connect_kwargs = _uri_to_connect_kwargs(database_url)
    else:
        host = args.host or os.environ.get("PGHOST", "")
        user = args.user or os.environ.get("PGUSER", "")
        password = args.password or os.environ.get("PGPASSWORD", "")
        dbname = args.db or os.environ.get("PGDATABASE", "")
        if not all([host, user, dbname]):
            print(
                "Укажите --database-url / DATABASE_URL "
                "или --host --user --db (--password)",
                file=sys.stderr,
            )
            return 1
        connect_kwargs = {
            "host": host,
            "port": args.port,
            "dbname": dbname,
            "user": user,
            "password": password,
            "sslmode": os.environ.get("PGSSLMODE", "require"),
        }

    if args.all_phases:
        phase = ""
    else:
        phase = (args.phase or "").strip()
    return export_manifests(connect_kwargs, Path(args.output), phase=phase)


if __name__ == "__main__":
    raise SystemExit(main())
