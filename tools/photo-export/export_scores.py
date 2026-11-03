#!/usr/bin/env python3
"""Текстовые файлы scoring (балл + описание) рядом с папками животных.

Читает manifests.jsonl и таблицу cow_score_result (только SELECT).
Пишет в папку животного scoring.txt (или scoring_<package_id>.txt,
если на одну кличку несколько пакетов).

Пример:
  $env:DATABASE_URL = "postgresql+psycopg2://..."
  python export_scores.py --manifests manifests.jsonl --output %USERPROFILE%\\Desktop\\export\\korovas
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from download_photos_from_s3 import (
    animal_id_from_manifest,
    iter_manifests,
    manifest_body,
    sanitize_dir_name,
)
from export_manifests import _uri_to_connect_kwargs

# trait_id → подпись поля «балл», как в форме бонитировки.
_TRAIT_TITLES: dict[str, dict[str, str]] = {
    "cow": {
        "overall_type": "Общий вид, развитие и тип породы",
        "musculature_bone": "Мускулатура",
        "head_neck": "Голова и шея",
        "chest": "Грудь",
        "withers_back_loin": "Холка, спина, поясница",
        "croup": "Крестец",
        "ham": "Окорока",
        "udder": "Вымя",
        "limbs": "Конечности",
    },
    "bull": {
        "overall_type": "Общий вид, развитие и тип породы",
        "musculature_bone": "Мускулатура",
        "head_neck": "Голова и шея",
        "chest": "Грудь",
        "withers_back_loin": "Холка, спина, поясница",
        "croup": "Крестец",
        "scrotum": "Мошонка",
        "ham": "Окорока",
        "limbs": "Конечности",
    },
    "young": {
        "overall_type": "Общий вид и выполненность мускулатуры",
        "musculature_bone": "Общий вид и выполненность мускулатуры",
        "chest": "Грудь",
        "withers_back_loin": "Холка, спина, поясница",
        "croup": "Крестец",
        "ham": "Окорок",
    },
}

_STATUS_RU = {
    "ok": "оценено",
    "declined": "модель отказалась ставить балл",
    "no_photo": "нет нужных кадров",
    "error": "ошибка",
}


def _fmt_score(value: Any) -> str:
    if value is None or (isinstance(value, str) and not value.strip()):
        return ""
    if isinstance(value, float):
        if value == int(value):
            return str(int(value))
        text = f"{value:.1f}".rstrip("0").rstrip(".")
        return text
    return str(value).strip()


def _is_junk(value: Any) -> bool:
    low = str(value or "").casefold()
    return "jsonschemavalidationerror" in low or "litellm." in low


def _chunks(raw: Any) -> list[str]:
    if isinstance(raw, str):
        items = [raw]
    elif isinstance(raw, list):
        items = [str(x) for x in raw if x is not None]
    else:
        return []
    out: list[str] = []
    for item in items:
        text = item.strip()
        if text and not _is_junk(text):
            out.append(text)
    return out


def _description(trait: dict[str, Any]) -> str:
    parts: list[str] = []
    reason = _chunks(trait.get("reason"))
    if reason:
        parts.append(reason[0])
    observations = _chunks(trait.get("observations"))
    if observations:
        parts.append("\n".join(f"- {item}" for item in observations))
    return "\n".join(parts).strip()


def _trait_title(scale: str, trait_id: str) -> str:
    titles = _TRAIT_TITLES.get(scale) or _TRAIT_TITLES["cow"]
    if trait_id in titles:
        return titles[trait_id]
    fallback = _TRAIT_TITLES["cow"].get(trait_id) or _TRAIT_TITLES["bull"].get(trait_id)
    return fallback or trait_id


def render_score_text(
    *,
    animal: str,
    package_id: str,
    row: dict[str, Any],
) -> str:
    scale = str(row.get("scale") or "").strip() or "cow"
    lines: list[str] = [
        f"Животное: {animal}",
        f"Пакет: {package_id}",
        f"Шкала: {scale}",
        f"Статус: {row.get('status') or ''}",
    ]
    model = (row.get("model") or "").strip()
    if model:
        lines.append(f"Модель: {model}")
    if row.get("trait_total") is not None:
        lines.append(f"Сумма баллов: {row['trait_total']}")
    if row.get("complex_class"):
        lines.append(f"Комплексный класс: {row['complex_class']}")
    lines.append("")

    traits = row.get("traits") or []
    if not isinstance(traits, list):
        traits = []

    blocks: list[str] = []
    for trait in traits:
        if not isinstance(trait, dict):
            continue
        trait_id = str(trait.get("trait_id") or "").strip()
        if not trait_id:
            continue
        title = _trait_title(scale, trait_id)
        score = _fmt_score(trait.get("score"))
        desc = _description(trait)
        status = str(trait.get("status") or "").strip()
        error = str(trait.get("error") or "").strip()
        if _is_junk(error):
            error = ""

        chunk = [title]
        if score:
            chunk.append(f"Оценка: {score}")
        else:
            note = _STATUS_RU.get(status, status)
            chunk.append(f"Оценка: нет ({note})" if note else "Оценка: нет")
        if desc:
            chunk.append("Описание:")
            chunk.append(desc)
        elif error and not score:
            chunk.append("Описание:")
            chunk.append(error)
        blocks.append("\n".join(chunk))

    if blocks:
        lines.append("\n\n".join(blocks))
    else:
        lines.append("Оценок нет.")

    report = str(row.get("report") or "").strip()
    if report and not _is_junk(report):
        lines.append("")
        lines.append("---")
        lines.append("Отчёт модели")
        lines.append(report)

    return "\n".join(lines).rstrip() + "\n"


def _json_field(raw: Any, default: Any) -> Any:
    if raw is None or raw == "":
        return default
    if isinstance(raw, (dict, list)):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return default
    return default


def load_scores_jsonl(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        package_id = str(row.get("package_id") or "").strip()
        if not package_id:
            continue
        out[package_id] = {
            "scale": row.get("scale"),
            "model": row.get("model"),
            "status": row.get("status"),
            "error": row.get("error"),
            "trait_total": row.get("trait_total"),
            "complex_class": row.get("complex_class"),
            "traits": _json_field(row.get("traits_json"), []),
            "report": row.get("report") or "",
        }
    return out


def fetch_scores(connect_kwargs: dict, package_ids: list[str]) -> dict[str, dict[str, Any]]:
    import psycopg2
    import psycopg2.extras

    if not package_ids:
        return {}
    sql = """
        SELECT package_id, scale, model, status, error,
               trait_total, complex_class,
               traits_json, report
        FROM cow_score_result
        WHERE package_id = ANY(%s)
    """
    out: dict[str, dict[str, Any]] = {}
    with psycopg2.connect(**connect_kwargs) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (package_ids,))
            for row in cur:
                traits = _json_field(row["traits_json"], [])
                out[row["package_id"]] = {
                    "scale": row["scale"],
                    "model": row["model"],
                    "status": row["status"],
                    "error": row["error"],
                    "trait_total": row["trait_total"],
                    "complex_class": row["complex_class"],
                    "traits": traits,
                    "report": row["report"] or "",
                }
    return out


def export_scores(
    manifests_path: Path,
    output_dir: Path,
    *,
    animal_field: str,
    phase: str,
    connect_kwargs: dict | None = None,
    scores_jsonl: Path | None = None,
) -> int:
    packages: list[tuple[str, str]] = []
    for row in iter_manifests(manifests_path):
        package_id = (row.get("package_id") or "").strip()
        if not package_id:
            continue
        pkg_phase = (row.get("phase") or "").strip()
        if phase and pkg_phase != phase:
            continue
        manifest = manifest_body(row)
        if not manifest:
            continue
        animal = animal_id_from_manifest(manifest, animal_field, package_id)
        packages.append((package_id, sanitize_dir_name(animal)))

    if not packages:
        print("В манифестах нет пакетов для scoring", file=sys.stderr)
        return 1

    by_animal: dict[str, list[str]] = defaultdict(list)
    for package_id, animal_dir in packages:
        by_animal[animal_dir].append(package_id)

    package_ids = [pid for pid, _ in packages]
    if scores_jsonl is not None:
        loaded = load_scores_jsonl(scores_jsonl)
        scores = {pid: loaded[pid] for pid in package_ids if pid in loaded}
    elif connect_kwargs is not None:
        scores = fetch_scores(connect_kwargs, package_ids)
    else:
        print("Нужен DATABASE_URL или --scores-jsonl", file=sys.stderr)
        return 1
    written = 0
    missing = 0
    output_dir.mkdir(parents=True, exist_ok=True)

    for animal_dir, ids in by_animal.items():
        folder = output_dir / animal_dir
        folder.mkdir(parents=True, exist_ok=True)
        multi = len(ids) > 1
        for package_id in ids:
            row = scores.get(package_id)
            if row is None:
                missing += 1
                continue
            name = f"scoring_{package_id}.txt" if multi else "scoring.txt"
            text = render_score_text(
                animal=animal_dir,
                package_id=package_id,
                row=row,
            )
            (folder / name).write_text(text, encoding="utf-8")
            written += 1

    print(f"Scoring-файлов: {written}")
    print(f"Пакетов без cow_score_result: {missing}")
    print(f"Папка: {output_dir.resolve()}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Текстовые файлы баллов и описаний scoring")
    p.add_argument("--manifests", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--animal-field", default="cow_name")
    p.add_argument("--database-url", default="")
    p.add_argument(
        "--scores-jsonl",
        default="",
        help="Локальный cow_score_result.jsonl, если Postgres недоступен",
    )
    p.add_argument("--phase", default="completed")
    p.add_argument("--all-phases", action="store_true")
    args = p.parse_args()

    scores_jsonl = Path(args.scores_jsonl) if args.scores_jsonl else None
    connect_kwargs = None
    if scores_jsonl is None:
        database_url = (args.database_url or os.environ.get("DATABASE_URL", "")).strip()
        if not database_url:
            print("Нужен DATABASE_URL или --scores-jsonl", file=sys.stderr)
            return 1
        connect_kwargs = _uri_to_connect_kwargs(database_url)
    elif not scores_jsonl.is_file():
        print(f"Нет файла scoring: {scores_jsonl}", file=sys.stderr)
        return 1

    phase = "" if args.all_phases else (args.phase or "").strip()
    return export_scores(
        Path(args.manifests),
        Path(args.output),
        animal_field=args.animal_field,
        phase=phase,
        connect_kwargs=connect_kwargs,
        scores_jsonl=scores_jsonl,
    )


if __name__ == "__main__":
    raise SystemExit(main())
