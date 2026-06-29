#!/usr/bin/env python3
"""Сборка status-notion.csv / .tsv для импорта в Notion."""
from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = Path(__file__).resolve().parent / "status.csv"
DST_CSV = Path(__file__).resolve().parent / "status-notion.csv"
DST_TSV = Path(__file__).resolve().parent / "status-notion.tsv"

STATUS_MAP = {
    "зелёный": "🟢 Готово",
    "зеленый": "🟢 Готово",
    "жёлтый": "🟡 Частично",
    "желтый": "🟡 Частично",
    "красный": "🔴 Не готово",
}

# path fragment (lower) -> краткое описание
REF_HINTS: list[tuple[str, str]] = [
    ("specs/01-overview.md", "обзор продукта, scope и архитектура"),
    ("specs/02-data-models-schema.md", "JSON-конфиг, Django/SQLAlchemy/Drift модели"),
    ("specs/03-user-journey-screens.md", "экраны Flutter и веб-админки"),
    ("specs/04-tech-stack-architecture.md", "стек, зависимости, структура lib/ и django_server/"),
    ("specs/05-stage-1-mvp.md", "история MVP и текущий scope"),
    ("specs/06-upload-lifecycle.md", "жизненный цикл upload на устройстве"),
    ("specs/07-package-payload-structure.md", "структура пакета, blobs, camera metadata"),
    ("specs/08-server-api-package-upload.md", "HTTP API загрузки пакетов, auth, коды ошибок"),
    ("specs/09-server-project-config-delivery.md", "доставка конфигов: каталог, ETag, assets"),
    ("specs/git-backed-projects.md", "Git-репозиторий проекта, deploy key, config.json"),
    ("specs/project-storage-uris.md", "database_uri / storage_uri, Postgres, S3, GCS"),
    ("specs/collector-vis-config.md", "collector/viz.json, плагины визуализации в админке"),
    ("specs/todo", "backlog багов и доработок"),
    ("specs/config/json-driven-collection-ui.md", "как JSON конфиг строит UI сбора"),
    ("specs/config/09-project-json-builder-guide.md", "гайд по сборке JSON проекта"),
    ("specs/presentation/", "презентационные материалы и скриншоты UI"),
    ("specs/main-scheme/01-abstract-config-entities.drawio", "диаграмма: сущности конфига"),
    ("specs/main-scheme/04-auth-firebase-django.drawio", "диаграмма: Firebase + Django auth"),
    ("specs/main-scheme/05-admin-roles-access.drawio", "диаграмма: роли staff / client-admin"),
    ("specs/main-scheme/11-stack.drawio", "диаграмма: полный стек системы"),
    ("specs/", "каталог продуктовых спецификаций"),
    ("README.md", "корневой README: запуск, структура репо, прод URL"),
    ("django_server/README.md", "Django: роли, Git, пакеты, viz, хранилище"),
    ("django_server/requirements.txt", "Python-зависимости бэкенда"),
    ("django_server/api/project_db.py", "SQLAlchemy: сессии пакетов, pipeline-таблицы"),
    ("django_server/api/management/commands/import_depth_map.py", "команда импорта depth-карт в project DB"),
    ("test_dev/README.md", "Docker Compose Postgres + MinIO для локального прода-подобного стенда"),
    ("test_dev/docker-compose.yml", "compose-файл Postgres и MinIO"),
    ("pubspec.yaml", "Flutter-зависимости и assets"),
    ("docs/web-vs-android.md", "отличия Web и Android клиента"),
    ("lib/main.dart", "точка входа, GoRouter, login, dashboard"),
    ("lib/l10n/", "локализация RU/EN"),
    ("lib/core/quality/", "анализ качества изображений"),
    ("lib/core/device/", "камера, EXIF, intrinsic-параметры"),
    ("lib/features/sync/server_sync_tab.dart", "вкладка «Сервер»: очередь upload"),
    ("lib/features/help/", "встроенная справка в приложении"),
    ("assets/config/", "bundled offline-конфиги демо-проектов"),
    ("korovas/", "смежные ML/разметка korovas (вне runtime data-collector)"),
    ("cowmetric/", "смежный код cowmetric / измерений"),
]

STAGE_RE = re.compile(r"^(\d+)\s+Этап$", re.IGNORECASE)


def flat(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", s.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")).strip()


def describe_ref(token: str) -> str:
    token = flat(token)
    if not token:
        return ""
    low = token.lower()
    clean = re.sub(r"\s*\([^)]*\)\s*", "", token).strip()
    # Сначала более длинные (специфичные) пути
    for path, desc in sorted(REF_HINTS, key=lambda x: len(x[0]), reverse=True):
        p = path.lower()
        if p in low or low.startswith(p.rstrip("/")):
            return f"• {clean} — {desc}"
    return f"• {clean}"


def format_refs(raw: str) -> str:
    if not raw or not raw.strip():
        return ""
    parts = [p.strip() for p in raw.split(";") if p.strip()]
    lines = [describe_ref(p) for p in parts]
    return "\n".join(lines)


def format_status(raw: str) -> str:
    return STATUS_MAP.get(raw.lower().strip(), raw) if raw else ""


def is_stage_row(num: str, name: str) -> bool:
    return bool(STAGE_RE.match(num.strip()))


def format_stage_name(num: str, name: str) -> str:
    """Выделение строки этапа для Notion (** рендерится как жирный при вставке)."""
    n = num.strip()
    title = name.strip() if name.strip() else ""
    if title:
        return f"**{n} · {title}**"
    return f"**{n}**"


def read_source_rows() -> list[list[str]]:
    rows: list[list[str]] = []
    with SRC.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or all(not c.strip() for c in row):
                continue
            if row[0].strip() == "№ п/п":
                continue
            while len(row) < 6:
                row.append("")
            rows.append(row[:6])
    return rows


def normalize_row(row: list[str]) -> list[str]:
    num, name, stages, refs, status, comment = row
    num, name, stages, refs, status, comment = map(flat, [num, name, stages, refs, status, comment])
    if not num and not name and stages:
        name = stages
        stages = ""
    return [num, name, stages, refs, status, comment]


def build() -> list[list[str]]:
    header = ["№", "Наименование работ", "Этапы работ", "Референсные файлы", "Статус", "Комментарий"]
    out = [header]
    for raw in read_source_rows():
        num, name, stages, refs, status, comment = normalize_row(raw)
        refs_fmt = format_refs(refs)
        status_fmt = format_status(status)

        if is_stage_row(num, name):
            name = format_stage_name(num, name)
            stages = ""
            # визуальный разделитель в комментарии этапа
            if comment:
                comment = f"▸ {comment}"

        out.append([num, name, stages, refs_fmt, status_fmt, comment])
    return out


def write_csv(rows: list[list[str]]) -> None:
    with DST_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f, lineterminator="\n").writerows(rows)


def write_tsv(rows: list[list[str]]) -> None:
    with DST_TSV.open("w", encoding="utf-8-sig", newline="") as f:
        for row in rows:
            # TSV: multiline cells — в кавычках для Excel
            cells = []
            for cell in row:
                if "\n" in cell or "\t" in cell or '"' in cell:
                    cells.append('"' + cell.replace('"', '""') + '"')
                else:
                    cells.append(cell)
            f.write("\t".join(cells) + "\n")


def main() -> None:
    rows = build()
    write_csv(rows)
    write_tsv(rows)
    print(f"Rows: {len(rows)} -> {DST_CSV.name}, {DST_TSV.name}")


if __name__ == "__main__":
    main()
