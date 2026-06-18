"""Создать БД проекта (Postgres, db-per-project) и схему таблиц.

Для sqlite ничего создавать не нужно — файл и схема появляются автоматически.
Для Postgres: создаёт базу из database_uri (если её нет) и применяет create_all.

Примеры:
    python manage.py create_project_db --project-id=krs-label
    python manage.py create_project_db --database-uri="postgresql+psycopg2://collector:collector@localhost:55432/proj_krs_label"
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from api import project_db as pdb
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

        if not database_uri:
            if not project_id:
                raise CommandError("Нужен --project-id или --database-uri")
            if not Project.objects.filter(project_id=project_id).exists():
                raise CommandError(f"Unknown project: {project_id}")
            database_uri = psc.resolve_by_id(project_id).database_uri

        if database_uri.startswith("sqlite"):
            pdb.get_engine_for_uri(database_uri)
            self.stdout.write(
                self.style.SUCCESS(f"SQLite — файл и схема готовы: {database_uri}"),
            )
            return

        url = make_url(database_uri)
        dbname = url.database
        if not dbname:
            raise CommandError("В database_uri отсутствует имя базы")

        admin_url = url.set(database="postgres")
        self.stdout.write(f"Проверяю/создаю базу '{dbname}' на {admin_url.host}:{admin_url.port}…")
        admin_engine = create_engine(admin_url, future=True, isolation_level="AUTOCOMMIT")
        try:
            with admin_engine.connect() as conn:
                exists = conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :n"),
                    {"n": dbname},
                ).scalar()
                if exists:
                    self.stdout.write(self.style.WARNING(f"База '{dbname}' уже существует."))
                else:
                    conn.execute(text(f'CREATE DATABASE "{dbname}"'))
                    self.stdout.write(self.style.SUCCESS(f"База '{dbname}' создана."))
        finally:
            admin_engine.dispose()

        pdb.get_engine_for_uri(database_uri)
        self.stdout.write(self.style.SUCCESS(f"Схема применена: {database_uri}"))
