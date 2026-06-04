"""Импорт YOLO .txt разметки в project SQLite (таблица yolo_detection)."""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand

from api.models import PackageSession, UploadedBlob
from api.packages_ui import is_image_path
from api import project_db as pdb
from api.yolo_labels import (
    parse_class_names,
    parse_yolo_detection_lines,
    sniff_image_size,
)


def _image_size_for_blob(blob: UploadedBlob) -> tuple[int, int]:
    with blob.file.open("rb") as f:
        head = f.read(256 * 1024)
    size = sniff_image_size(head)
    if size:
        return size
    raise ValueError(
        f"Не удалось прочитать размер изображения для {blob.logical_path}",
    )


class Command(BaseCommand):
    help = "Импорт YOLO label (.txt) → yolo_detection для кадров пакета."

    def add_arguments(self, parser):
        parser.add_argument("project_id")
        parser.add_argument("package_id")
        parser.add_argument(
            "labels",
            nargs="+",
            help="Путь к .txt или каталог с .txt (Roboflow export)",
        )
        parser.add_argument(
            "--blob",
            dest="manifest_blob_key",
            help="Явная привязка: blobs/img_0001.jpg (для одного файла)",
        )
        parser.add_argument(
            "--class-names",
            default="",
            help="Имена классов через запятую: cow,person",
        )
        parser.add_argument(
            "--image-width",
            type=int,
            default=0,
            help="Ширина, если не удаётся прочитать из JPEG/PNG",
        )
        parser.add_argument(
            "--image-height",
            type=int,
            default=0,
            help="Высота, если не удаётся прочитать из JPEG/PNG",
        )

    def handle(self, *args, **options):
        session = (
            PackageSession.objects.filter(
                project__project_id=options["project_id"],
                package_id=options["package_id"],
            )
            .select_related("project")
            .first()
        )
        if not session:
            self.stderr.write(self.style.ERROR("Package session not found"))
            return

        project_id = session.project.project_id
        package_id = session.package_id
        class_names = parse_class_names(options.get("class_names"))

        label_paths: list[Path] = []
        for raw in options["labels"]:
            p = Path(raw)
            if p.is_dir():
                label_paths.extend(sorted(p.glob("*.txt")))
            elif p.is_file():
                label_paths.append(p)
            else:
                self.stderr.write(self.style.ERROR(f"Not found: {p}"))
                return

        if not label_paths:
            self.stderr.write(self.style.ERROR("No .txt label files"))
            return

        images = sorted(
            [b for b in session.blobs.all() if is_image_path(b.logical_path)],
            key=lambda b: b.logical_path,
        )
        if not images:
            self.stderr.write(self.style.ERROR("No image blobs in package"))
            return

        explicit_blob = (options.get("manifest_blob_key") or "").strip()
        imported = 0

        for lp in label_paths:
            text = lp.read_text(encoding="utf-8").strip()
            if not text:
                self.stderr.write(self.style.WARNING(f"Empty label file: {lp}"))
                continue

            blob: UploadedBlob | None = None
            if explicit_blob and len(label_paths) == 1:
                blob = session.blobs.filter(logical_path=explicit_blob).first()
            else:
                stem = lp.stem
                for b in images:
                    name = Path(b.logical_path.replace("\\", "/")).name
                    base = Path(name).stem
                    if stem == name or stem == base or stem in name or base in stem:
                        blob = b
                        break
                if blob is None and len(images) == 1 and len(label_paths) == 1:
                    blob = images[0]

            if not blob:
                self.stderr.write(
                    self.style.WARNING(
                        f"No matching image for {lp.name}; use --blob blobs/…",
                    ),
                )
                continue

            iw = int(options["image_width"] or 0)
            ih = int(options["image_height"] or 0)
            if iw <= 0 or ih <= 0:
                try:
                    iw, ih = _image_size_for_blob(blob)
                except ValueError as e:
                    self.stderr.write(self.style.ERROR(str(e)))
                    return

            boxes = parse_yolo_detection_lines(
                text,
                image_width=iw,
                image_height=ih,
                class_names=class_names,
            )
            pdb.insert_yolo_detection(
                project_id,
                package_id=package_id,
                manifest_blob_key=blob.logical_path,
                image_size={"width": iw, "height": ih},
                boxes=boxes,
                source_label=str(lp),
            )
            imported += 1
            self.stdout.write(
                f"{blob.logical_path}: {len(boxes)} box(es) from {lp.name}",
            )

        self.stdout.write(self.style.SUCCESS(f"Imported {imported} frame(s)"))
