"""Удалить пакеты (session, blobs, media), сохранив pipeline-разметку в project.sqlite3."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from api import project_db as pdb
from api import project_packages as ppkg
from api.models import Project

PIPELINE_TABLES = (
    "cow_keypoint_annotation",
    "cow_inference_result",
    "yolo_detection",
    "depth_map",
    "cvat_link",
)


def _pipeline_summary(project_id: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    with pdb.connect(project_id) as conn:
        for tbl in PIPELINE_TABLES:
            try:
                rows = conn.execute(
                    f"SELECT DISTINCT package_id FROM {tbl} ORDER BY package_id",
                ).fetchall()
            except Exception:
                continue
            if rows:
                out[tbl] = [r[0] for r in rows]
    return out


class Command(BaseCommand):
    help = "Удалить все пакеты проекта, оставив pipeline-таблицы (yolo, keypoints, …)."

    def add_arguments(self, parser):
        parser.add_argument(
            "project_id",
            nargs="*",
            help="project_id (пусто = все проекты с пакетами)",
        )
        parser.add_argument(
            "--delete-pipeline",
            action="store_true",
            help="Также удалить pipeline-разметку (по умолчанию сохраняется)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
        )

    def handle(self, *args, **options):
        ids = list(options["project_id"]) or None
        keep_pipeline = not bool(options.get("delete_pipeline"))
        dry = bool(options.get("dry_run"))

        qs = Project.objects.all().order_by("project_id")
        if ids:
            qs = qs.filter(project_id__in=ids)

        total_removed = 0
        for project in qs:
            pid = project.project_id
            sessions = ppkg.list_sessions(pid, limit=10000)
            if not sessions:
                continue

            pipeline_before = _pipeline_summary(pid) if keep_pipeline else {}
            self.stdout.write(
                f"\n{pid}: удалить {len(sessions)} пакет(ов)"
                + (" (pipeline сохраняется)" if keep_pipeline else ""),
            )
            for s in sessions:
                self.stdout.write(f"  - {s.package_id} ({s.phase})")

            if keep_pipeline and pipeline_before:
                self.stdout.write(self.style.WARNING("  pipeline package_id (останутся):"))
                for tbl, pkg_ids in pipeline_before.items():
                    self.stdout.write(f"    {tbl}: {', '.join(pkg_ids)}")

            if dry:
                total_removed += len(sessions)
                continue

            n = ppkg.purge_all_packages(
                pid,
                media_bucket=project.media_bucket or "",
                keep_pipeline=keep_pipeline,
            )
            total_removed += n

        suffix = " (dry-run)" if dry else ""
        self.stdout.write(self.style.SUCCESS(f"\nГотово: удалено пакетов: {total_removed}{suffix}"))
        if keep_pipeline and not dry:
            self.stdout.write(
                "Загрузите пакет заново с телефона, затем привяжите pipeline "
                "(rebind_pipeline — когда будет готов).",
            )
