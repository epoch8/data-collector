"""Переназначить Project.storage_uri (корень blobs) на другой бакет/префикс.

Не копирует объекты — только обновляет поле в Django. Перед вызовом
убедитесь, что данные уже лежат по новому URI и что storage_options
дают доступ на запись в целевой бакет.

Пример (Korovas packages: dc-project-korovas → korovas-storage):

    python manage.py repoint_project_storage \\
      --project-id=korovas-2026 \\
      --from-uri=s3://dc-project-korovas/ \\
      --to-uri=s3://korovas-storage/ \\
      --dry-run

    python manage.py repoint_project_storage \\
      --project-id=korovas-2026 \\
      --from-uri=s3://dc-project-korovas/ \\
      --to-uri=s3://korovas-storage/
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from api import project_storage_config as psc
from api.models import Project


class Command(BaseCommand):
    help = "Обновить Project.storage_uri (без копирования blobs)."

    def add_arguments(self, parser):
        parser.add_argument("--project-id", required=True)
        parser.add_argument(
            "--from-uri",
            default="",
            help="Ожидаемый текущий storage_uri (проверка; пусто = не проверять)",
        )
        parser.add_argument("--to-uri", required=True, help="Новый storage_uri (s3://…/)")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        project_id = options["project_id"].strip()
        to_uri = psc.normalize_storage_uri(options["to_uri"])
        from_uri = psc.normalize_storage_uri(options.get("from_uri") or "")
        dry = bool(options.get("dry_run"))

        if not to_uri:
            raise CommandError("--to-uri is required")

        project = Project.objects.filter(project_id=project_id).first()
        if project is None:
            raise CommandError(f"Unknown project: {project_id}")

        current = psc.normalize_storage_uri(project.storage_uri or "")
        self.stdout.write(f"project_id={project_id}")
        self.stdout.write(f"  current: {current or '(empty)'}")
        self.stdout.write(f"  target:  {to_uri}")

        if from_uri and current and current != from_uri:
            raise CommandError(
                f"storage_uri mismatch: expected {from_uri!r}, got {current!r}",
            )

        if current == to_uri:
            self.stdout.write(self.style.WARNING("Already at target URI — nothing to do."))
            return

        if dry:
            self.stdout.write(self.style.WARNING("dry-run: not saving"))
            return

        project.storage_uri = to_uri
        project.save(update_fields=["storage_uri"])
        self.stdout.write(self.style.SUCCESS(f"Updated storage_uri → {to_uri}"))
