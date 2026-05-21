import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from api.media_sync import sync_project_media_from_repo
from api.models import Project


class Command(BaseCommand):
    help = "Импорт проектов из Flutter assets/config (projects.json + JSON проектов)."

    def handle(self, *args, **options):
        config_dir = Path(settings.ASSETS_CONFIG_ROOT)
        manifest_path = config_dir / "projects.json"
        if not manifest_path.is_file():
            self.stderr.write(f"Нет файла: {manifest_path}")
            return

        repo_root = Path(settings.BASE_DIR).parent
        raw = manifest_path.read_text(encoding="utf-8")
        manifest = json.loads(raw)
        paths = manifest.get("projects") or []
        if not isinstance(paths, list):
            self.stderr.write("projects.json: поле projects должно быть массивом строк.")
            return

        n = 0
        for rel in paths:
            if not isinstance(rel, str):
                continue
            abs_path = repo_root / rel
            if not abs_path.is_file():
                self.stderr.write(f"Пропуск (нет файла): {abs_path}")
                continue
            body = abs_path.read_text(encoding="utf-8")
            data = json.loads(body)
            pid = data.get("id")
            if not pid:
                self.stderr.write(f"Пропуск (нет id): {abs_path}")
                continue
            name = data.get("name") or pid
            version = str(data.get("version") or "1")
            Project.objects.update_or_create(
                project_id=pid,
                defaults={
                    "name": name,
                    "config_version": version,
                    "raw_json": body,
                },
            )
            sync_project_media_from_repo(repo_root, pid)
            n += 1
            self.stdout.write(f"OK {pid} ({name}) + media")

        self.stdout.write(self.style.SUCCESS(f"Готово, проектов в БД: {n}"))
