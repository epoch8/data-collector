#!/usr/bin/env python
"""Компиляция .po -> .mo без GNU gettext (чистый Python).

Django читает скомпилированные каталоги `.mo`, а штатная команда
`manage.py compilemessages` требует установленного `msgfmt` из GNU gettext.
В окружениях без gettext (Windows-разработка, минимальные Docker-образы)
используйте этот скрипт:

    python scripts/compilemessages.py

Он обходит `locale/<lang>/LC_MESSAGES/*.po` и пишет рядом `*.mo`.
Поддерживаются многострочные msgid/msgstr и экранирование; формы
множественного числа (msgid_plural) не используются в этом проекте.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOCALE_DIR = BASE_DIR / "locale"

_ESCAPES = {
    "n": "\n",
    "t": "\t",
    "r": "\r",
    '"': '"',
    "\\": "\\",
}


def _unescape(s: str) -> str:
    out: list[str] = []
    it = iter(range(len(s)))
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            out.append(_ESCAPES.get(nxt, nxt))
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _parse_quoted(line: str) -> str:
    line = line.strip()
    first = line.find('"')
    last = line.rfind('"')
    if first == -1 or last <= first:
        return ""
    return _unescape(line[first + 1:last])


def parse_po(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    msgid: list[str] = []
    msgstr: list[str] = []
    state = None  # 'id' | 'str'

    def flush() -> None:
        if state is not None and (msgid or msgstr):
            key = "".join(msgid)
            val = "".join(msgstr)
            # Пустой перевод => пусть остаётся исходный язык (не записываем).
            if val:
                entries[key] = val

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("msgid "):
            flush()
            msgid = [_parse_quoted(line[len("msgid "):])]
            msgstr = []
            state = "id"
        elif line.startswith("msgstr "):
            msgstr = [_parse_quoted(line[len("msgstr "):])]
            state = "str"
        elif line.startswith('"'):
            chunk = _parse_quoted(line)
            if state == "id":
                msgid.append(chunk)
            elif state == "str":
                msgstr.append(chunk)
    flush()
    # Заголовок каталога (msgid "") нужен gettext для метаданных.
    entries.setdefault("", "Content-Type: text/plain; charset=UTF-8\n")
    return entries


def write_mo(entries: dict[str, str], out: Path) -> None:
    keys = sorted(entries.keys())
    offsets: list[tuple[int, int, int, int]] = []
    ids = b""
    strs = b""
    for key in keys:
        kb = key.encode("utf-8")
        vb = entries[key].encode("utf-8")
        offsets.append((len(ids), len(kb), len(strs), len(vb)))
        ids += kb + b"\x00"
        strs += vb + b"\x00"

    keystart = 7 * 4 + 16 * len(keys)
    valuestart = keystart + len(ids)
    koffsets: list[int] = []
    voffsets: list[int] = []
    for o1, l1, o2, l2 in offsets:
        koffsets += [l1, o1 + keystart]
        voffsets += [l2, o2 + valuestart]

    output = struct.pack(
        "Iiiiiii",
        0x950412DE,        # magic
        0,                 # version
        len(keys),         # number of entries
        7 * 4,             # offset of key table
        7 * 4 + len(keys) * 8,  # offset of value table
        0,                 # hash size
        0,                 # hash offset
    )
    output += struct.pack("i" * len(koffsets), *koffsets)
    output += struct.pack("i" * len(voffsets), *voffsets)
    output += ids
    output += strs
    out.write_bytes(output)


def main() -> int:
    if not LOCALE_DIR.is_dir():
        print(f"Нет каталога locale: {LOCALE_DIR}", file=sys.stderr)
        return 1
    count = 0
    for po in sorted(LOCALE_DIR.glob("*/LC_MESSAGES/*.po")):
        entries = parse_po(po)
        mo = po.with_suffix(".mo")
        write_mo(entries, mo)
        translated = sum(1 for k, v in entries.items() if k and v)
        print(f"{po.relative_to(BASE_DIR)} -> {mo.name} ({translated} строк)")
        count += 1
    if count == 0:
        print("Файлы .po не найдены.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
