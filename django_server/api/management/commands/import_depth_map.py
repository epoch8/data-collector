"""Импорт путей к depth .npy в project SQLite (таблица depth_map)."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from api import project_db as pdb
from api import project_media as pm
from api import project_packages as ppkg
from api.models import Project


class Command(BaseCommand):
    help = "Привязка depth .npy → depth_map для кадра пакета (логический путь в пакете)."

    def add_arguments(self, parser):
        parser.add_argument("project_id")
        parser.add_argument("package_id")
        parser.add_argument(
            "depth_path",
            help="Логический путь в пакете, напр. blobs/img_0001_depth.npy",
        )
        parser.add_argument(
            "--blob",
            dest="manifest_blob_key",
            required=True,
            help="Кадр: blobs/img_0001.jpg",
        )
        parser.add_argument("--format", default="npy")
        parser.add_argument("--unit", default="m")
        parser.add_argument("--image-width", type=int, default=0)
        parser.add_argument("--image-height", type=int, default=0)
        parser.add_argument("--source-label", default="")

    def handle(self, *args, **options):
        project_id = options["project_id"]
        package_id = options["package_id"]
        project = Project.objects.filter(project_id=project_id).first()
        if not project:
            self.stderr.write(self.style.ERROR("Project not found"))
            return
        session = ppkg.get_session(project_id, package_id)
        if not session:
            self.stderr.write(self.style.ERROR("Package session not found"))
            return

        blob_key = (options["manifest_blob_key"] or "").strip()
        blob = ppkg.get_blob_by_path(project_id, package_id, blob_key)
        if not blob:
            self.stderr.write(self.style.ERROR(f"Blob not found: {blob_key}"))
            return

        iw = int(options["image_width"] or 0)
        ih = int(options["image_height"] or 0)
        if iw <= 0 or ih <= 0:
            from api.yolo_labels import sniff_image_size

            head = pm.read_blob_head(
                project_id,
                blob.storage_path,
                media_bucket=project.media_bucket or "",
            )
            if head:
                size = sniff_image_size(head)
                if size:
                    iw, ih = size

        depth_path = options["depth_path"].replace("\\", "/").strip()
        pdb.insert_depth_map(
            project_id,
            package_id=package_id,
            manifest_blob_key=blob_key,
            depth_path=depth_path,
            image_size={"width": iw, "height": ih} if iw and ih else None,
            fmt=options["format"],
            unit=options["unit"],
            width=iw or None,
            height=ih or None,
            source_label=options.get("source_label") or "",
        )
        self.stdout.write(
            self.style.SUCCESS(f"{blob_key} → depth_map {depth_path}"),
        )
