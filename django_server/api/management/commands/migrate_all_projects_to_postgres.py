"""Перевести все проекты с локального SQLite на Postgres (db-per-project) + S3.

Создаёт отдельную БД на каждый проект, прописывает database_uri / storage_uri
в Project и переносит данные из локального дефолта.

    python manage.py migrate_all_projects_to_postgres --dry-run
    python manage.py migrate_all_projects_to_postgres
    python manage.py migrate_all_projects_to_postgres --skip-storage
    python manage.py migrate_all_projects_to_postgres --project-id=yolo

По умолчанию — test_dev (localhost:55432, MinIO :9000, бакет dc-packages).
"""

from __future__ import annotations

import os

from django.core.management import call_command
from django.core.management.base import BaseCommand

from api import project_storage_config as psc
from api.models import Project


class Command(BaseCommand):
    help = "Миграция всех проектов: SQLite → Postgres (отдельная БД) + S3 (MinIO)."

    def add_arguments(self, parser):
        parser.add_argument("--project-id", action="append", default=[])
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--skip-storage",
            action="store_true",
            help="Только Postgres, blobs оставить локально (file://)",
        )
        parser.add_argument("--pg-host", default=os.environ.get("TESTDEV_PG_HOST", "localhost"))
        parser.add_argument("--pg-port", type=int, default=int(os.environ.get("TESTDEV_PG_PORT", "55432")))
        parser.add_argument("--pg-user", default=os.environ.get("TESTDEV_PG_USER", "collector"))
        parser.add_argument("--pg-password", default=os.environ.get("TESTDEV_PG_PASSWORD", "collector"))
        parser.add_argument("--s3-bucket", default=os.environ.get("TESTDEV_S3_BUCKET", "dc-packages"))
        parser.add_argument(
            "--s3-endpoint",
            default=os.environ.get("TESTDEV_S3_ENDPOINT", "http://localhost:9000"),
        )
        parser.add_argument("--s3-key", default=os.environ.get("TESTDEV_S3_KEY", "minioadmin"))
        parser.add_argument("--s3-secret", default=os.environ.get("TESTDEV_S3_SECRET", "minioadmin"))

    def handle(self, *args, **options):
        dry = bool(options["dry_run"])
        skip_storage = bool(options["skip_storage"])
        ids = options["project_id"] or None

        qs = Project.objects.all().order_by("project_id")
        if ids:
            qs = qs.filter(project_id__in=ids)

        if not qs.exists():
            self.stdout.write(self.style.WARNING("Нет проектов для миграции."))
            return

        self.stdout.write(
            f"{'DRY-RUN: ' if dry else ''}Migrating {qs.count()} project(s) to Postgres"
            + ("" if skip_storage else " + S3"),
        )

        for project in qs:
            pid = project.project_id
            db_uri_base = psc.build_postgres_database_uri_base(
                pid,
                host=options["pg_host"],
                port=options["pg_port"],
            )
            db_opts = psc.default_postgres_database_options(
                user=options["pg_user"],
                password=options["pg_password"],
            )
            db_uri_full = psc.apply_database_credentials(db_uri_base, db_opts)
            dbname = psc.postgres_db_name(pid)
            st_uri = "" if skip_storage else psc.build_s3_storage_uri(pid, bucket=options["s3_bucket"])
            st_opts = (
                {}
                if skip_storage
                else psc.default_s3_storage_options(
                    endpoint_url=options["s3_endpoint"],
                    key=options["s3_key"],
                    secret=options["s3_secret"],
                )
            )

            self.stdout.write(f"\n=== {pid} ===")
            self.stdout.write(f"  DB:      {dbname}  ({db_uri_base})")
            if not skip_storage:
                self.stdout.write(f"  Storage: {st_uri}")

            if dry:
                self.stdout.write("  (dry-run — URI не сохраняются, данные не копируются)")
                continue

            call_command("create_project_db", "--database-uri", db_uri_full, verbosity=0)

            project.database_uri = db_uri_base
            project.database_options_encrypted = psc.encode_database_options(db_opts)
            project.storage_uri = st_uri
            project.storage_options_encrypted = psc.encode_storage_options(st_opts)
            project.save(
                update_fields=[
                    "database_uri",
                    "database_options_encrypted",
                    "storage_uri",
                    "storage_options_encrypted",
                    "updated_at",
                ],
            )

            call_command(
                "migrate_project_storage",
                "--project-id",
                pid,
                "--wipe-target",
                verbosity=1,
            )

            notes = psc.check_storage(psc.resolve(project))
            for note in notes:
                self.stdout.write(f"  check: {note}")

        self.stdout.write(self.style.SUCCESS(f"\nDone{' (dry-run)' if dry else ''}."))
