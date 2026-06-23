"""Перенести данные проекта из дефолтного локального хранилища в целевое.

Источник — дефолт (локальный SQLite + папка project_media/).
Цель — то, что задано в проекте (database_uri / storage_uri), напр. Postgres + S3.

Порядок: задайте в UI хранилище проекта, при Postgres создайте БД
(create_project_db), затем запустите эту команду.

    python manage.py migrate_project_storage --project-id=krs-label --dry-run
    python manage.py migrate_project_storage --project-id=krs-label
    python manage.py migrate_project_storage --project-id=krs-label --wipe-target
"""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from sqlalchemy import insert, select

from api import project_db as pdb
from api import project_storage_config as psc
from api.models import Project


class Command(BaseCommand):
    help = "Перенести project DB + blobs из локального дефолта в целевое хранилище проекта."

    def add_arguments(self, parser):
        parser.add_argument("--project-id", required=True)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--wipe-target",
            action="store_true",
            help="Очистить целевые таблицы перед переносом (идемпотентный повтор)",
        )

    def handle(self, *args, **options):
        project_id = options["project_id"].strip()
        dry = bool(options.get("dry_run"))
        wipe = bool(options.get("wipe_target"))

        project = Project.objects.filter(project_id=project_id).first()
        if project is None:
            raise CommandError(f"Unknown project: {project_id}")

        target = psc.resolve(project)
        source = psc.StorageConfig(
            project_id=project_id,
            database_uri=psc.default_database_uri(project_id),
            storage_uri=psc.default_storage_uri(project_id),
            storage_options={},
        )

        db_same = target.database_uri == source.database_uri
        st_same = target.storage_uri == source.storage_uri
        if db_same and st_same:
            self.stdout.write(
                self.style.WARNING(
                    "Цель совпадает с локальным дефолтом — переносить нечего. "
                    "Сначала задайте database_uri/storage_uri в UI.",
                ),
            )
            return

        self.stdout.write(f"Проект: {project_id}")
        self.stdout.write(f"  DB:      {source.database_uri}")
        self.stdout.write(f"     ->    {target.database_uri}" + ("  (без изменений)" if db_same else ""))
        self.stdout.write(f"  Storage: {source.storage_uri}")
        self.stdout.write(f"     ->    {target.storage_uri}" + ("  (без изменений)" if st_same else ""))

        if not db_same:
            self._migrate_db(source, target, dry=dry, wipe=wipe)
        if not st_same:
            self._migrate_blobs(source, target, dry=dry)

        self.stdout.write(self.style.SUCCESS("Готово" + (" (dry-run)" if dry else "")))

    # --- DB -----------------------------------------------------------------

    def _migrate_db(self, source, target, *, dry: bool, wipe: bool) -> None:
        src_path = psc.sqlite_path_from_uri(source.database_uri)
        if src_path is None or not src_path.exists():
            self.stdout.write(self.style.WARNING("  DB: источник пуст (нет sqlite-файла) — пропуск."))
            return

        src_engine = pdb.get_engine_for_uri(source.database_uri)
        tgt_engine = pdb.get_engine_for_uri(target.database_uri)  # create_all внутри

        with src_engine.connect() as src, tgt_engine.begin() as tgt:
            for table in pdb.metadata.sorted_tables:
                rows = src.execute(select(table)).mappings().all()
                if wipe and not dry:
                    tgt.execute(table.delete())
                if not rows:
                    self.stdout.write(f"  DB {table.name}: 0")
                    continue
                if dry:
                    self.stdout.write(f"  DB {table.name}: {len(rows)} (would copy)")
                    continue
                has_id = "id" in table.c
                payload = [
                    {k: v for k, v in r.items() if not (has_id and k == "id")}
                    for r in rows
                ]
                tgt.execute(insert(table), payload)
                self.stdout.write(f"  DB {table.name}: {len(rows)} -> ok")

    # --- Blobs --------------------------------------------------------------

    def _migrate_blobs(self, source, target, *, dry: bool) -> None:
        src_root = psc.file_uri_to_path(source.storage_uri)
        if not src_root.exists():
            self.stdout.write(self.style.WARNING("  Storage: источник пуст (нет папки) — пропуск."))
            return

        files = [p for p in src_root.rglob("*") if p.is_file()]
        if not files:
            self.stdout.write("  Storage: 0 файлов")
            return

        if dry:
            total = sum(p.stat().st_size for p in files)
            self.stdout.write(f"  Storage: {len(files)} файл(ов), {total} байт (would copy)")
            return

        fs = psc.filesystem_for(target)
        copied = 0
        for p in files:
            rel = p.relative_to(src_root).as_posix()
            dest = psc.object_path(target, rel)
            if target.is_local_storage:
                Path(dest).parent.mkdir(parents=True, exist_ok=True)
            else:
                parent = dest.rsplit("/", 1)[0]
                try:
                    fs.makedirs(parent, exist_ok=True)
                except (NotImplementedError, FileExistsError):
                    pass
            with open(p, "rb") as fsrc, fs.open(dest, "wb") as fdst:
                fdst.write(fsrc.read())
            copied += 1
        self.stdout.write(f"  Storage: {copied} файл(ов) -> ok")
