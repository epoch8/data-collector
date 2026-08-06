"""Показать project_id и число пакетов в project DB (удобно для прода)."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import patch

from django.core.management.base import BaseCommand, CommandError

from api import project_db as pdb
from api.models import Project
from api.project_storage_config import mask_database_uri, normalize_database_uri


@contextmanager
def _override_project_database(database_uri: str):
    uri = normalize_database_uri(database_uri)
    if not uri:
        raise CommandError("Пустой --database-uri")
    engine = pdb.get_engine_for_uri(uri)
    with patch.object(pdb, "_engine_for_project", lambda _project_id: engine):
        yield uri


class Command(BaseCommand):
    help = "Список project_id и count(*) из package_session."

    def add_arguments(self, parser):
        parser.add_argument(
            "--database-uri",
            default="",
            help="SQLAlchemy URI (иначе нужен project_id Django-проекта)",
        )
        parser.add_argument(
            "project_id",
            nargs="?",
            default="",
            help="Если без --database-uri — взять БД этого Django Project",
        )

    def handle(self, *args, **options):
        database_uri = (options.get("database_uri") or "").strip()
        project_id = (options.get("project_id") or "").strip()

        def dump() -> None:
            # connect нужен любой project_id — движок уже переопределён или из Project
            pid = project_id or "_inspect_"
            with pdb.connect(pid) as conn:
                try:
                    rows = conn.execute(
                        """
                        SELECT COALESCE(project_id, '') AS project_id, COUNT(*) AS n
                        FROM package_session
                        GROUP BY 1
                        ORDER BY 1
                        """,
                    ).fetchall()
                except Exception as e:  # noqa: BLE001
                    raise CommandError(f"Ошибка чтения package_session: {e}") from e
                total = sum(int(r["n"]) for r in rows)
                self.stdout.write(f"package_session: {total} всего")
                for r in rows:
                    self.stdout.write(f"  {r['project_id']!r}: {r['n']}")

        if database_uri:
            with _override_project_database(database_uri) as uri:
                self.stdout.write(f"DB: {mask_database_uri(uri)}")
                dump()
            return

        if not project_id:
            raise CommandError("Укажите project_id или --database-uri")
        if not Project.objects.filter(project_id=project_id).exists():
            raise CommandError(f'Проект "{project_id}" не найден')
        dump()
