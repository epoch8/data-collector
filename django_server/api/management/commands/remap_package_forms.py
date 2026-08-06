"""Remap packages with form_id=default → bull / young / cow by months + cow_gender."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from django.core.management.base import BaseCommand, CommandError

from api import project_db as pdb
from api import project_packages as ppkg
from api.models import Project
from api.package_form_remap import apply_decision_to_manifest, decide_remap
from api.project_forms import load_project_forms
from api.project_storage_config import mask_database_uri, normalize_database_uri


def _load_form_meta_from_dir(forms_dir: Path) -> dict[str, tuple[str, str]]:
    meta: dict[str, tuple[str, str]] = {}
    if not forms_dir.is_dir():
        raise CommandError(f"forms-dir не найден: {forms_dir}")
    for child in sorted(forms_dir.iterdir()):
        if not child.is_dir():
            continue
        cfg_path = child / "config.json"
        if not cfg_path.is_file():
            continue
        try:
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            raise CommandError(f"Не удалось прочитать {cfg_path}: {e}") from e
        if not isinstance(data, dict):
            continue
        meta[child.name] = (str(data.get("name") or child.name), str(data.get("version") or ""))
    return meta


@contextmanager
def _override_project_database(database_uri: str):
    """Направить project_db.connect на переданный URI (не трогая Project в Django)."""
    uri = normalize_database_uri(database_uri)
    if not uri:
        raise CommandError("Пустой --database-uri")
    engine = pdb.get_engine_for_uri(uri)
    with patch.object(pdb, "_engine_for_project", lambda _project_id: engine):
        yield uri


class Command(BaseCommand):
    help = (
        "Переназначить пакеты form_id=default на bull/young/cow "
        "по полям months и cow_gender (по умолчанию dry-run)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "project_id",
            type=str,
            help="project_id в package_session (и Django Project, если без --database-uri)",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Записать изменения (без флага — только dry-run)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=10000,
            help="Максимум пакетов для обхода (default 10000)",
        )
        parser.add_argument(
            "--database-uri",
            default="",
            help="SQLAlchemy URI продовой/чужой БД (иначе берётся из Project)",
        )
        parser.add_argument(
            "--forms-dir",
            default="",
            help="Локальный collector/forms для form_name/version (вместо git Project)",
        )

    def handle(self, *args, **options):
        project_id = options["project_id"].strip()
        apply = bool(options["apply"])
        limit = int(options["limit"])
        database_uri = (options.get("database_uri") or "").strip()
        forms_dir_raw = (options.get("forms_dir") or "").strip()

        form_meta: dict[str, tuple[str, str]] = {}
        if forms_dir_raw:
            form_meta = _load_form_meta_from_dir(Path(forms_dir_raw))
            self.stdout.write(
                f"Формы из {forms_dir_raw}: {', '.join(sorted(form_meta)) or '(пусто)'}",
            )
        else:
            try:
                project = Project.objects.get(project_id=project_id)
            except Project.DoesNotExist as e:
                if not database_uri:
                    raise CommandError(
                        f'Проект "{project_id}" не найден. '
                        "Укажите --database-uri и --forms-dir для внешней БД.",
                    ) from e
                self.stdout.write(
                    self.style.WARNING(
                        f'Проект "{project_id}" не в Django — form_name/version не подтянутся '
                        "(передайте --forms-dir).",
                    ),
                )
                project = None
            else:
                try:
                    forms = load_project_forms(project, fetch_remote=True)
                    for f in forms:
                        form_meta[f["form_id"]] = (
                            f.get("name") or f["form_id"],
                            f.get("version") or "",
                        )
                except Exception as exc:  # noqa: BLE001
                    self.stdout.write(
                        self.style.WARNING(f"Не удалось загрузить формы проекта: {exc}"),
                    )

        def run() -> None:
            sessions = ppkg.list_sessions(project_id, limit=limit)
            if not sessions:
                self.stdout.write(self.style.WARNING(f"{project_id}: пакетов нет"))
                return

            mode = "APPLY" if apply else "DRY-RUN"
            self.stdout.write(f"{project_id}: {len(sessions)} пакет(ов) [{mode}]\n")
            header = (
                f"{'package_id':<40} {'old->new':<22} {'months':>6} "
                f"{'sex':<6} {'status':<18} gender / reason"
            )
            self.stdout.write(header)
            self.stdout.write("-" * len(header))

            counts: dict[str, int] = {}
            applied = 0

            for session in sessions:
                manifest = session.manifest_dict
                if manifest is None:
                    self.stdout.write(
                        f"{session.package_id:<40} {'?':<22} {'':>6} {'':<6} "
                        f"{'skip_manifest':<18} invalid JSON",
                    )
                    counts["skip_manifest"] = counts.get("skip_manifest", 0) + 1
                    continue

                decision = decide_remap(session.package_id, manifest)
                counts[decision.status] = counts.get(decision.status, 0) + 1

                arrow = (
                    f"{decision.old_form_id}->{decision.new_form_id}"
                    if decision.new_form_id
                    else f"{decision.old_form_id}->-"
                )
                months_s = "" if decision.months is None else str(decision.months)
                sex_s = decision.sex or ""
                detail = decision.raw_gender or decision.skip_reason
                if decision.skip_reason and decision.raw_gender:
                    detail = f"{decision.raw_gender!r} | {decision.skip_reason}"

                self.stdout.write(
                    f"{decision.package_id:<40} {arrow:<22} {months_s:>6} "
                    f"{sex_s:<6} {decision.status:<18} {detail}",
                )

                if not decision.should_apply or not apply:
                    continue

                name, version = form_meta.get(decision.new_form_id or "", ("", ""))
                updated = apply_decision_to_manifest(
                    manifest,
                    decision,
                    form_name=name or None,
                    form_version=version or None,
                )
                ppkg.update_manifest(
                    project_id,
                    session.package_id,
                    json.dumps(updated, ensure_ascii=False),
                )
                applied += 1

            self.stdout.write("")
            for status, n in sorted(counts.items()):
                self.stdout.write(f"  {status}: {n}")
            if apply:
                self.stdout.write(self.style.SUCCESS(f"\nЗаписано: {applied}"))
            else:
                ok_n = counts.get("ok", 0)
                self.stdout.write(
                    self.style.WARNING(
                        f"\nDry-run: к применению {ok_n}. Запуск с --apply для записи.",
                    ),
                )
                skip_n = sum(n for k, n in counts.items() if k.startswith("skip_"))
                if skip_n:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skip: {skip_n} — добейте вручную перед удалением forms/default.",
                        ),
                    )

        if database_uri:
            with _override_project_database(database_uri) as uri:
                self.stdout.write(f"DB override: {mask_database_uri(uri)}")
                run()
        else:
            if not Project.objects.filter(project_id=project_id).exists():
                raise CommandError(
                    f'Проект "{project_id}" не найден. '
                    "Укажите --database-uri для внешней БД.",
                )
            run()
