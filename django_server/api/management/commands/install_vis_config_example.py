"""Скопировать examples/collector/viz.json в Git-кэш проекта (локальная разработка)."""

import json
import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from api.models import Project
from api.project_git import repo_dir
from api.project_vis_config import VIS_CONFIG_REL_PATH, parse_vis_json_text, validate_vis_config


class Command(BaseCommand):
    help = "Положить пример collector/viz.json в кэш Git проекта."

    def add_arguments(self, parser):
        parser.add_argument("project_id")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Перезаписать существующий файл",
        )
        parser.add_argument(
            "--example",
            default="viz.json",
            help="Имя файла в examples/collector/ (viz.json, viz_yolo.json)",
        )

    def handle(self, *args, **options):
        project_id = options["project_id"]
        project = Project.objects.filter(project_id=project_id).first()
        if not project:
            self.stderr.write(self.style.ERROR(f"Project {project_id} not found"))
            return

        example_name = options["example"]
        src = Path(settings.BASE_DIR) / "examples" / "collector" / example_name
        if not src.is_file():
            self.stderr.write(self.style.ERROR(f"Example missing: {src}"))
            return

        dest = repo_dir(project_id) / VIS_CONFIG_REL_PATH
        if dest.is_file() and not options["force"]:
            self.stderr.write(self.style.WARNING(f"Already exists: {dest} (use --force)"))
            return

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        errs = validate_vis_config(parse_vis_json_text(dest.read_text(encoding="utf-8")))
        if errs:
            self.stderr.write(self.style.ERROR("; ".join(errs)))
            return
        self.stdout.write(self.style.SUCCESS(f"Written {dest}"))
