"""Импорт ссылок CVAT в project SQLite (таблица cvat_link)."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from api import project_db as pdb
from api import project_packages as ppkg


class Command(BaseCommand):
    help = "Привязка URL задачи CVAT → cvat_link для кадра пакета."

    def add_arguments(self, parser):
        parser.add_argument("project_id")
        parser.add_argument("package_id")
        parser.add_argument("url", help="https://app.cvat.ai/tasks/…")
        parser.add_argument(
            "--blob",
            dest="manifest_blob_key",
            required=True,
            help="Кадр: blobs/img_0001.jpg",
        )
        parser.add_argument("--label", default="", help="Подпись в UI (опционально)")

    def handle(self, *args, **options):
        project_id = options["project_id"]
        package_id = options["package_id"]
        session = ppkg.get_session(project_id, package_id)
        if not session:
            self.stderr.write(self.style.ERROR("Package session not found"))
            return

        blob_key = (options["manifest_blob_key"] or "").strip()
        if not ppkg.get_blob_by_path(project_id, package_id, blob_key):
            self.stderr.write(self.style.ERROR(f"Blob not found: {blob_key}"))
            return

        url = (options["url"] or "").strip()
        if not url.startswith("http"):
            self.stderr.write(self.style.ERROR("url должен начинаться с http(s)://"))
            return

        pdb.insert_cvat_link(
            project_id,
            package_id=package_id,
            manifest_blob_key=blob_key,
            url=url,
            label=(options.get("label") or "").strip(),
        )
        self.stdout.write(
            self.style.SUCCESS(f"{blob_key} → cvat_link {url}"),
        )
