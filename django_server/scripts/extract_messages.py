#!/usr/bin/env python
"""Извлекает msgid из шаблонов и Python без GNU xgettext.

Шаблоны: через django.utils.translation.template.templatize — это ровно та же
логика, что использует `makemessages`, поэтому msgid (включая %(var)s из
blocktrans и нормализацию trimmed) совпадает с тем, что Django ищет в рантайме.

Python: через ast — берём строковые аргументы вызовов gettext / gettext_lazy /
ugettext / _ (в т.ч. неявную конкатенацию строковых литералов).

Запуск: python scripts/extract_messages.py
Печатает уникальные msgid (по одному на строку, в python-repr).
"""

from __future__ import annotations

import ast
import os
import re
import sys
from pathlib import Path

import django
from django.utils.translation.template import templatize

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "collector_site.settings")
os.environ.setdefault("DJANGO_ENV", "local")
django.setup()

GETTEXT_NAMES = {"gettext", "gettext_lazy", "ugettext", "ugettext_lazy", "_"}

_MSGID_RE = re.compile(r"gettext\(\s*('(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\")", re.DOTALL)


TEMPLATE_DIRS = [BASE_DIR / "api" / "templates", BASE_DIR / "templates"]


def _from_templates() -> set[str]:
    out: set[str] = set()
    files: list[Path] = []
    for root in TEMPLATE_DIRS:
        files += sorted(root.rglob("*.html"))
    for path in files:
        src = path.read_text(encoding="utf-8")
        try:
            pseudo = templatize(src, origin=str(path))
        except Exception as exc:  # pragma: no cover
            print(f"! templatize fail {path}: {exc}", file=sys.stderr)
            continue
        for m in re.finditer(
            r"gettext\(\s*((?:u?(?:'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\")\s*)+)\)",
            pseudo,
            re.DOTALL,
        ):
            literal = m.group(1)
            try:
                value = ast.literal_eval(literal)
            except (SyntaxError, ValueError):
                continue
            if value:
                out.add(value)
    return out


def _from_python() -> set[str]:
    out: set[str] = set()
    for path in (BASE_DIR / "api").rglob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            fn = node.func
            name = fn.id if isinstance(fn, ast.Name) else getattr(fn, "attr", None)
            if name not in GETTEXT_NAMES:
                continue
            arg = node.args[0]
            value = _const_str(arg)
            if value:
                out.add(value)
    return out


def _const_str(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    # Неявная конкатенация: "a" "b" парсится как один Constant в 3.12+,
    # но на всякий случай поддержим BinOp/JoinedStr нет — только Constant.
    return None


def main() -> int:
    ids = _from_templates() | _from_python()
    out_file = BASE_DIR / "scripts" / "_msgids.txt"
    with out_file.open("w", encoding="utf-8") as fh:
        for msgid in sorted(ids):
            fh.write(repr(msgid) + "\n")
    print(f"total: {len(ids)} -> {out_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
