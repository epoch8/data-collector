"""Привязать pipeline-разметку к новому package_id после повторной загрузки пакета."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from api import project_db as pdb
from api import project_packages as ppkg
from api.models import Project


class Command(BaseCommand):
    help = "UPDATE package_id в pipeline-таблицах: старый id → новый (пакет уже загружен)."

    def add_arguments(self, parser):
        parser.add_argument("project_id")
        parser.add_argument("old_package_id", help="package_id в pipeline.sqlite3")
        parser.add_argument("new_package_id", help="package_id принятого пакета")
        parser.add_argument(
            "--dry-run",
            action="store_true",
        )

    def handle(self, *args, **options):
        project_id = options["project_id"]
        old_id = options["old_package_id"]
        new_id = options["new_package_id"]
        dry = bool(options.get("dry_run"))

        if not Project.objects.filter(project_id=project_id).exists():
            self.stderr.write(self.style.ERROR(f"Unknown project: {project_id}"))
            return

        session = ppkg.get_session(project_id, new_id)
        if session is None:
            self.stderr.write(
                self.style.ERROR(f"New package not found: {project_id}:{new_id}"),
            )
            return
        if session.phase != ppkg.Phase.COMPLETED:
            self.stderr.write(
                self.style.ERROR(f"New package not completed: {session.phase}"),
            )
            return

        new_blobs = {b.logical_path for b in ppkg.list_blobs(project_id, new_id)}
        with pdb.connect(project_id) as conn:
            old_keys: set[str] = set()
            for tbl in pdb.PIPELINE_TABLES:
                try:
                    rows = conn.execute(
                        f"SELECT DISTINCT manifest_blob_key FROM {tbl} WHERE package_id = ?",
                        (old_id,),
                    ).fetchall()
                    old_keys.update(r[0] for r in rows if r[0])
                except Exception:
                    pass

        if not old_keys:
            self.stderr.write(
                self.style.WARNING(f"No pipeline rows for old package_id: {old_id}"),
            )
            return

        missing = sorted(old_keys - new_blobs)
        if missing:
            self.stderr.write(
                self.style.ERROR(
                    f"New package missing blobs for pipeline keys: {missing}",
                ),
            )
            return

        self.stdout.write(
            f"{project_id}: {old_id} -> {new_id} "
            f"({len(old_keys)} manifest_blob_key, {len(new_blobs)} blobs)",
        )

        if dry:
            with pdb.connect(project_id) as conn:
                for tbl in pdb.PIPELINE_TABLES:
                    n = conn.execute(
                        f"SELECT COUNT(*) FROM {tbl} WHERE package_id = ?",
                        (old_id,),
                    ).fetchone()[0]
                    if n:
                        self.stdout.write(f"  would update {tbl}: {n} row(s)")
            return

        counts = pdb.rebind_pipeline_package_id(project_id, old_id, new_id)
        if not counts:
            self.stderr.write(self.style.WARNING("Nothing updated"))
            return
        for tbl, n in counts.items():
            self.stdout.write(self.style.SUCCESS(f"  {tbl}: {n} row(s)"))
        self.stdout.write(self.style.SUCCESS("Done."))
