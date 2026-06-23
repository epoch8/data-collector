"""Парсинг YOLO detection labels (normalized cx cy w h)."""

from __future__ import annotations

import struct
from typing import Any


def sniff_image_size(data: bytes) -> tuple[int, int] | None:
    """JPEG / PNG размер без внешних зависимостей."""
    if len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", data[16:24])
        return int(w), int(h)
    i = 0
    while i < len(data) - 9:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            h = struct.unpack(">H", data[i + 5 : i + 7])[0]
            w = struct.unpack(">H", data[i + 7 : i + 9])[0]
            return int(w), int(h)
        if marker in (0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0x01):
            i += 2
            continue
        if i + 3 >= len(data):
            break
        seg_len = struct.unpack(">H", data[i + 2 : i + 4])[0]
        i += 2 + seg_len
    return None


def parse_class_names(raw: str | None) -> list[str] | None:
    if not raw or not raw.strip():
        return None
    return [p.strip() for p in raw.split(",") if p.strip()]


def parse_yolo_detection_lines(
    text: str,
    *,
    image_width: int,
    image_height: int,
    class_names: list[str] | None = None,
) -> list[dict[str, Any]]:
    """YOLO detect: `class cx cy w h` или с confidence — координаты 0..1."""
    w_img = max(1, int(image_width))
    h_img = max(1, int(image_height))
    boxes: list[dict[str, Any]] = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        cls_id = int(float(parts[0]))
        cx, cy, bw, bh = (float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4]))
        conf = float(parts[5]) if len(parts) >= 6 else None
        xtl = (cx - bw / 2) * w_img
        ytl = (cy - bh / 2) * h_img
        xbr = (cx + bw / 2) * w_img
        ybr = (cy + bh / 2) * h_img
        if class_names and 0 <= cls_id < len(class_names):
            label = class_names[cls_id]
        else:
            label = str(cls_id)
        box: dict[str, Any] = {
            "class_id": cls_id,
            "label": label,
            "xtl": round(xtl, 2),
            "ytl": round(ytl, 2),
            "xbr": round(xbr, 2),
            "ybr": round(ybr, 2),
        }
        if conf is not None:
            box["confidence"] = conf
        boxes.append(box)
    return boxes
