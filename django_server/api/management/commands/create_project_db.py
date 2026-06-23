"""Создать БД проекта (Postgres, db-per-project) и схему таблиц."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from api import project_storage_config as psc
from api.models import Project


class Command(BaseCommand):
    help = "Создать БД проекта (Postgres) и применить схему таблиц."

    def add_arguments(self, parser):
        parser.add_argument("--project-id", default="")
        parser.add_argument(
            "--database-uri",
            default="",
            help="Явный URI (если не задан --project-id)",
        )

    def handle(self, *args, **options):
        project_id = (options.get("project_id") or "").strip()
        database_uri = (options.get("database_uri") or "").strip()

        if database_uri:
            ok, msg = psc.ensure_database_uri(database_uri)
        else:
            if not project_id:
                raise CommandError("Нужен --project-id или --database-uri")
            project = Project.objects.filter(project_id=project_id).first()
            if project is None:
                raise CommandError(f"Unknown project: {project_id}")
            ok, msg = psc.ensure_project_database(project)

        if ok:
            self.stdout.write(self.style.SUCCESS(msg))
        else:
            raise CommandError(msg)
