"""Перенос PackageSession/UploadedBlob/PackageFieldChange из Django DB в per-project SQLite + project_media."""

from __future__ import annotations

import json

from django.apps import apps
from django.core.management.base import BaseCommand
from django.utils import timezone

from api import project_db as pdb
from api import project_media as pm
from api import project_packages as ppkg


class Command(BaseCommand):
    help = "Перенести пакеты из Django ORM в project.sqlite3 и project_media/ (однократно)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Только показать, что будет перенесено",
        )
        parser.add_argument(
            "--delete-legacy",
            action="store_true",
            help="После переноса удалить строки из Django DB (таблицы ещё должны существовать)",
        )

    def handle(self, *args, **options):
        dry = bool(options.get("dry_run"))
        delete_legacy = bool(options.get("delete_legacy"))

        try:
            PackageSession = apps.get_model("api", "PackageSession")
            UploadedBlob = apps.get_model("api", "UploadedBlob")
            PackageFieldChange = apps.get_model("api", "PackageFieldChange")
        except LookupError:
            self.stderr.write(
                self.style.ERROR(
                    "Модели пакетов уже удалены из Django. Миграция не требуется.",
                ),
            )
            return

        sessions = PackageSession.objects.select_related("project").order_by("created_at")
        total_sessions = sessions.count()
        if total_sessions == 0:
            self.stdout.write(self.style.WARNING("Нет пакетов в Django DB."))
            return

        moved_sessions = 0
        moved_blobs = 0
        moved_changes = 0

        for session in sessions:
            project_id = session.project.project_id
            package_id = session.package_id
            media_bucket = getattr(session.project, "media_bucket", "") or ""

            if ppkg.get_session(project_id, package_id):
                self.stdout.write(f"skip session {project_id}:{package_id} (already in project sqlite)")
                continue

            created_at = session.created_at.isoformat() if session.created_at else timezone.now().isoformat()
            self.stdout.write(f"session {project_id}:{package_id} phase={session.phase}")

            if dry:
                moved_sessions += 1
                blob_count = session.blobs.count()
                change_count = session.field_changes.count()
                moved_blobs += blob_count
                moved_changes += change_count
                self.stdout.write(f"  blobs={blob_count} changes={change_count}")
                continue

            with pdb.connect(project_id) as conn:
                conn.execute(
                    """
                    INSERT INTO package_session (
                        package_id, phase, manifest_json, failure_reason,
                        uploader_uid, uploader_email, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        package_id,
                        session.phase,
                        session.manifest_json or "",
                        session.failure_reason or "",
                        session.uploader_uid or "",
                        session.uploader_email or "",
                        created_at,
                    ),
                )

            for blob in session.blobs.all().order_by("id"):
                if not blob.file:
                    self.stderr.write(self.style.WARNING(f"  empty file: {blob.logical_path}"))
                    continue
                with blob.file.open("rb") as f:
                    data = f.read()
                ppkg.put_blob(
                    project_id,
                    package_id,
                    blob.logical_path,
                    data,
                    media_bucket=media_bucket,
                )
                moved_blobs += 1
                self.stdout.write(f"  blob {blob.logical_path} ({len(data)} bytes)")

            for change in session.field_changes.all().order_by("id"):
                with pdb.connect(project_id) as conn:
                    conn.execute(
                        """
                        INSERT INTO package_field_change (
                            package_id, field_id, before_value, after_value,
                            reason, verifier_email, changed_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            package_id,
                            change.field_id,
                            json.dumps(change.before_value, ensure_ascii=False),
                            json.dumps(change.after_value, ensure_ascii=False),
                            change.reason,
                            change.verifier_email or "",
                            change.changed_at.isoformat() if change.changed_at else timezone.now().isoformat(),
                        ),
                    )
                moved_changes += 1

            moved_sessions += 1

            if delete_legacy:
                session.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Done: sessions={moved_sessions}/{total_sessions}, "
                f"blobs={moved_blobs}, changelog={moved_changes}"
                + (" (dry-run)" if dry else ""),
            ),
        )

        if not dry and not delete_legacy:
            self.stdout.write(
                "Запустите с --delete-legacy после проверки, затем python manage.py migrate.",
            )
