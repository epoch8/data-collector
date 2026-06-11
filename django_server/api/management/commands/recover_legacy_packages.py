"""Восстановить пакеты из остатков Django DB (db.sqlite3) и media/pkg/ после миграции 0009."""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from api import project_packages as ppkg
from api.legacy_package_recovery import (
    build_legacy_session_index,
    extract_manifests_from_db,
    find_session_for_manifest,
    guess_phase,
    guess_uploader,
)
from api.models import Project


class Command(BaseCommand):
    help = "Восстановить пакеты из db.sqlite3 + media/pkg/ (если DROP TABLE уже выполнен)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--db",
            default="",
            help="Путь к db.sqlite3 (по умолчанию BASE_DIR/db.sqlite3)",
        )
        parser.add_argument(
            "--pkg-root",
            default="",
            help="Путь к media/pkg (по умолчанию MEDIA_ROOT/pkg)",
        )
        parser.add_argument(
            "--project-id",
            default="",
            help="Восстановить только указанный project_id",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
        )
        parser.add_argument(
            "--include-unknown-projects",
            action="store_true",
            help="Импортировать даже если Project нет в Django DB",
        )

    def handle(self, *args, **options):
        db_path = Path(options["db"] or settings.BASE_DIR / "db.sqlite3")
        pkg_root = Path(options["pkg_root"]) if options["pkg_root"] else Path(settings.MEDIA_ROOT) / "pkg"
        only_project = (options.get("project_id") or "").strip()
        dry = bool(options.get("dry_run"))

        if not db_path.is_file():
            self.stderr.write(self.style.ERROR(f"DB not found: {db_path}"))
            return
        if not pkg_root.is_dir():
            self.stderr.write(self.style.ERROR(f"Legacy pkg dir not found: {pkg_root}"))
            return

        manifests = extract_manifests_from_db(db_path)
        if only_project:
            manifests = [m for m in manifests if m.get("project_id") == only_project]

        if not manifests:
            self.stderr.write(self.style.WARNING("Манифесты в DB не найдены."))
            return

        db_text = db_path.read_bytes().decode("utf-8", errors="ignore")
        index = build_legacy_session_index(pkg_root)
        known_projects = set(Project.objects.values_list("project_id", flat=True))

        imported = 0
        skipped = 0
        used_sessions: set[str] = set()

        for manifest in manifests:
            project_id = str(manifest["project_id"])
            package_id = str(manifest["package_id"])

            if project_id not in known_projects and not options.get("include_unknown_projects"):
                self.stdout.write(f"skip {project_id}:{package_id} (unknown project)")
                skipped += 1
                continue

            if ppkg.get_session(project_id, package_id):
                self.stdout.write(f"skip {project_id}:{package_id} (already exists)")
                skipped += 1
                continue

            session_id = find_session_for_manifest(
                manifest,
                index,
                db_text=db_text,
                used_sessions=used_sessions,
            )
            if not session_id:
                self.stderr.write(
                    self.style.WARNING(f"no media session for {project_id}:{package_id}"),
                )
                skipped += 1
                continue

            files = index[session_id]
            refs: set[str] = set()
            from api.utils import collect_blob_refs

            collect_blob_refs(manifest, refs)
            missing = sorted(refs - set(files.keys()))
            if missing:
                self.stderr.write(
                    self.style.WARNING(
                        f"{project_id}:{package_id} session {session_id} missing blobs: {missing[:3]}",
                    ),
                )
                skipped += 1
                continue

            phase = guess_phase(db_text, package_id)
            uid, email = guess_uploader(db_text, package_id)
            created_at = str(manifest.get("created_at") or "")
            project = Project.objects.filter(project_id=project_id).first()
            media_bucket = (project.media_bucket if project else "") or ""

            self.stdout.write(
                f"{'[dry] ' if dry else ''}import {project_id}:{package_id} "
                f"session={session_id} blobs={len(refs) or len(files)} phase={phase}",
            )

            used_sessions.add(session_id)

            if dry:
                imported += 1
                continue

            from api import project_db as pdb

            with pdb.connect(project_id) as conn:
                conn.execute(
                    """
                    INSERT INTO package_session (
                        package_id, phase, manifest_json, failure_reason,
                        uploader_uid, uploader_email, created_at
                    ) VALUES (?, ?, ?, '', ?, ?, ?)
                    """,
                    (
                        package_id,
                        phase,
                        json.dumps(manifest, ensure_ascii=False, separators=(",", ":")),
                        uid,
                        email,
                        created_at or timezone.now().isoformat(),
                    ),
                )

            blob_paths = refs if refs else set(files.keys())
            for logical in sorted(blob_paths):
                data = files[logical].read_bytes()
                ppkg.put_blob(
                    project_id,
                    package_id,
                    logical,
                    data,
                    media_bucket=media_bucket,
                )

            imported += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done: imported={imported}, skipped={skipped}, total_manifests={len(manifests)}",
            ),
        )
