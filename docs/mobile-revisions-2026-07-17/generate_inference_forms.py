#!/usr/bin/env python3
"""Build bull/young/cow_inference forms: ID+age + photos with example images."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
FORMS = HERE / "forms"
BACKUP = Path(r"C:\Users\admin\Desktop\backup\korovas")
MEDIA_REL = "collector/media/examples/poses"
MEDIA_OUT = FORMS / "media" / "examples" / "poses"

ALL_POSES = [
    "photo_profile_left",
    "photo_profile_right",
    "photo_top",
    "photo_rear_23_left",
    "photo_rear_23_right",
    "photo_front_23_left",
    "photo_front_23_right",
    "photo_front_legs",
    "photo_scrotum",
    "photo_udder",
    "photo_head_side",
    "photo_head_top",
]

# Preferred package (and optional hash prefix) when auto-pick is wrong for the pose.
PREFERRED_POSE_SOURCE: dict[str, tuple[str, str | None]] = {
    "photo_head_top": ("pkg_1783492400354", "f06ff8c7"),
    "photo_front_23_left": ("pkg_1783492400354", "a4cd4c8d"),
    "photo_front_23_right": ("pkg_1783492400354", "c657b156"),
}

GUIDE_EXAMPLES = {
    "photo_profile_guide": ["photo_profile_left", "photo_profile_right"],
    "photo_top_guide": ["photo_top"],
    "photo_rear_23_guide": ["photo_rear_23_left", "photo_rear_23_right"],
    "photo_front_23_guide": ["photo_front_23_left", "photo_front_23_right"],
    "photo_front_legs_guide": ["photo_front_legs"],
    "photo_head_guide": ["photo_head_side", "photo_head_top"],
}

KEEP_IDENTITY = {
    "bull": [
        "scan_time",
        "cow_name",
        "form_scenario_hint",
        "cow_breed",
        "cow_identifier",
        "months",
    ],
    "young": [
        "scan_time",
        "cow_name",
        "form_scenario_hint",
        "young_sex",
        "cow_breed",
        "cow_identifier",
        "months",
    ],
    "cow": [
        "scan_time",
        "cow_name",
        "form_scenario_hint",
        "cow_breed",
        "cow_identifier",
        "months",
    ],
}

PHOTO_FIELD_IDS = {
    "bull": [
        "photo_profile_guide",
        "photo_profile_left",
        "photo_profile_right",
        "photo_top_guide",
        "photo_top",
        "photo_rear_23_guide",
        "photo_rear_23_left",
        "photo_rear_23_right",
        "photo_front_23_guide",
        "photo_front_23_left",
        "photo_front_23_right",
        "photo_front_legs_guide",
        "photo_front_legs",
        "photo_genitals_guide",
        "photo_scrotum",
        "photo_head_guide",
        "photo_head_side",
        "photo_head_top",
    ],
    "young": [
        "photo_profile_guide",
        "photo_profile_left",
        "photo_profile_right",
        "photo_top_guide",
        "photo_top",
        "photo_rear_23_guide",
        "photo_rear_23_left",
        "photo_rear_23_right",
        "photo_front_23_guide",
        "photo_front_23_left",
        "photo_front_23_right",
        "photo_front_legs_guide",
        "photo_front_legs",
        "photo_head_guide",
        "photo_head_side",
        "photo_head_top",
    ],
    "cow": [
        "photo_profile_guide",
        "photo_profile_left",
        "photo_profile_right",
        "photo_top_guide",
        "photo_top",
        "photo_rear_23_guide",
        "photo_rear_23_left",
        "photo_rear_23_right",
        "photo_front_23_guide",
        "photo_front_23_left",
        "photo_front_23_right",
        "photo_front_legs_guide",
        "photo_front_legs",
        "photo_genitals_guide",
        "photo_udder",
        "photo_head_guide",
        "photo_head_side",
        "photo_head_top",
    ],
}

NAMES = {
    "bull": "Бык — съёмка (инференс)",
    "young": "Молодняк — съёмка (инференс)",
    "cow": "Корова — съёмка (инференс)",
}

HINTS = {
    "bull": (
        "## Бык-производитель — съёмка под инференс\n\n"
        "Форма для сбора **фото ракурсов** (без промеров и бальности).\n"
        "Заполните идентификацию и возраст, затем снимите ракурсы по примерам."
    ),
    "young": (
        "## Молодняк (до 24 мес.) — съёмка под инференс\n\n"
        "Форма для сбора **фото ракурсов** (без промеров и бальности).\n"
        "Заполните идентификацию и возраст, затем снимите ракурсы по примерам."
    ),
    "cow": (
        "## Корова — съёмка под инференс\n\n"
        "Форма для сбора **фото ракурсов** (без промеров и бальности).\n"
        "Заполните идентификацию и возраст, затем снимите ракурсы по примерам."
    ),
}


def md_example(pose_key: str, caption: str | None = None) -> str:
    cap = caption or pose_key.replace("photo_", "").replace("_", " ")
    return f"![{cap}]({MEDIA_REL}/{pose_key}.jpg)"


def enrich_guide(instructions: str, example_poses: list[str]) -> str:
    text = instructions
    marker = "\n\n### Пример\n"
    if marker in text:
        text = text.split(marker, 1)[0]
    text = text.rstrip()
    lines = [marker]
    for pose in example_poses:
        if not isinstance(pose, str):
            raise TypeError(f"example pose must be str, got {type(pose)}: {pose!r}")
        lines.append(f"\n{md_example(pose)}\n")
    lines.append(
        "\n_Ориентируйтесь на ракурс, кадрирование и видимость ключевых точек._"
    )
    return text + "".join(lines)


def _save_resized(src: Path, dst: Path) -> None:
    im = Image.open(src).convert("RGB")
    w, h = im.size
    max_w = 1280
    if w > max_w:
        im = im.resize((max_w, int(h * max_w / w)), Image.Resampling.LANCZOS)
    im.save(dst, "JPEG", quality=82, optimize=True)


def export_media() -> None:
    """Pick one distinct example image per pose across packages (by content hash)."""
    MEDIA_OUT.mkdir(parents=True, exist_ok=True)
    candidates: dict[str, list[tuple[str, Path, str]]] = {p: [] for p in ALL_POSES}
    seen_per_pose: dict[str, set[str]] = {p: set() for p in ALL_POSES}

    with open(BACKUP / "manifests.jsonl", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            pid = row["package_id"]
            data = row["manifest"]["data"]
            pkg_blobs = BACKUP / "s3" / "packages" / pid / "blobs"
            for pose in ALL_POSES:
                v = data.get(pose)
                if not isinstance(v, dict) or not v:
                    continue
                fname = next(iter(v.keys())).removeprefix("blobs/")
                src = pkg_blobs / fname
                if not src.exists():
                    continue
                h = hashlib.md5(src.read_bytes()).hexdigest()
                if h in seen_per_pose[pose]:
                    continue
                seen_per_pose[pose].add(h)
                candidates[pose].append((h, src, pid))

    chosen_hashes: set[str] = set()
    chosen: dict[str, tuple[str, Path, str]] = {}
    for pose in ALL_POSES:
        pick = None
        pref = PREFERRED_POSE_SOURCE.get(pose)
        if pref:
            pref_pid, pref_hash = pref
            for h, src, pid in candidates[pose]:
                if pid != pref_pid:
                    continue
                if pref_hash and not h.startswith(pref_hash):
                    continue
                pick = (h, src, pid)
                break
        if pick is None:
            for h, src, pid in candidates[pose]:
                if h not in chosen_hashes:
                    pick = (h, src, pid)
                    break
        if pick is None and candidates[pose]:
            pick = candidates[pose][0]
        if pick is None:
            raise RuntimeError(f"No example image for {pose}")
        chosen[pose] = pick
        chosen_hashes.add(pick[0])

    for pose, (h, src, pid) in chosen.items():
        dst = MEDIA_OUT / f"{pose}.jpg"
        _save_resized(src, dst)
        print(
            f"media {pose}: {dst.stat().st_size // 1024} KB "
            f"(from {pid}, hash={h[:8]})"
        )
    uniq = len({h for h, _, _ in chosen.values()})
    print(f"unique example hashes: {uniq}/{len(chosen)}")


def build_form(kind: str) -> dict:
    src = json.loads((FORMS / kind / "config.json").read_text(encoding="utf-8"))
    fields_by_id = {f["field_id"]: f for f in src["config"]["fields"]}

    keep_ids = set(KEEP_IDENTITY[kind]) | set(PHOTO_FIELD_IDS[kind])
    out_fields: list[dict] = []

    for fid in KEEP_IDENTITY[kind]:
        f = deepcopy(fields_by_id[fid])
        if fid == "form_scenario_hint":
            f["instructions"] = HINTS[kind]
        if fid == "months":
            age_hint = {
                "bull": "Возраст в месяцах. Для быка-производителя обычно **от 25 месяцев**.",
                "young": "Возраст в месяцах. Для молодняка ожидается **до 24 месяцев**.",
                "cow": "Возраст в месяцах.",
            }[kind]
            f["instructions"] = age_hint
            f["validation"] = {"required": False}
        out_fields.append(f)

    for fid in PHOTO_FIELD_IDS[kind]:
        f = deepcopy(fields_by_id[fid])
        if f["type"] == "instruction":
            if fid == "photo_genitals_guide":
                examples = ["photo_scrotum"] if kind == "bull" else ["photo_udder"]
            else:
                examples = list(GUIDE_EXAMPLES.get(fid) or [])
            if examples:
                f["instructions"] = enrich_guide(f["instructions"], examples)
        out_fields.append(f)

    cfg = {
        "id": "krs-label",
        "name": NAMES[kind],
        "version": "2.2-inference",
        "config": {
            "flow": {
                "steps": [
                    {
                        "id": "animal_id",
                        "screen": "scroll_form",
                        "form_title": "Идентификация и возраст",
                        "cow_id_hints": True,
                        "cow_id_field_id": "cow_identifier",
                        "field_ids": KEEP_IDENTITY[kind],
                    },
                    {
                        "id": "photos",
                        "screen": "scroll_form",
                        "form_title": "Фото ракурсы",
                        "field_ids": PHOTO_FIELD_IDS[kind],
                    },
                    {"id": "review", "screen": "review"},
                ]
            },
            "ui": src["config"]["ui"],
            "fields": out_fields,
        },
    }
    present = {f["field_id"] for f in out_fields}
    for step in cfg["config"]["flow"]["steps"]:
        for fid in step.get("field_ids") or []:
            if fid not in present:
                raise RuntimeError(f"{kind}: missing field {fid}")
    unused = keep_ids - present
    if unused:
        raise RuntimeError(f"{kind}: unused keep ids {unused}")
    return cfg


def main() -> None:
    export_media()
    for kind in ("bull", "young", "cow"):
        form_id = f"{kind}_inference"
        out_dir = FORMS / form_id
        out_dir.mkdir(parents=True, exist_ok=True)
        cfg = build_form(kind)
        path = out_dir / "config.json"
        path.write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {path}")

    readme = FORMS / "README.md"
    text = readme.read_text(encoding="utf-8")
    marker = "## Формы под инференс"
    block = """## Формы под инференс

Урезанные сценарии только для съёмки (без промеров и бальности):

| form_id | Название |
|---------|----------|
| `bull_inference` | Бык — съёмка (инференс) |
| `young_inference` | Молодняк — съёмка (инференс) |
| `cow_inference` | Корова — съёмка (инференс) |

Шаги: **идентификация + возраст** → **фото ракурсы** → review.

Примеры кадров лежат в `media/examples/poses/` (из бекапа korovas).  
При заливке в проект скопировать в `collector/media/examples/poses/` — пути в markdown инструкций: `examples/poses/<field_id>.jpg`.

Сгенерировано: `generate_inference_forms.py`.

"""
    if marker in text:
        before, _, rest = text.partition(marker)
        lines = rest.splitlines(True)
        i = 1
        while i < len(lines) and not (
            lines[i].startswith("## ") and not lines[i].startswith("## Формы")
        ):
            i += 1
        text = before.rstrip() + "\n\n" + block + "".join(lines[i:])
    else:
        text = text.rstrip() + "\n\n" + block
    readme.write_text(text, encoding="utf-8")
    print("updated README")


if __name__ == "__main__":
    main()
