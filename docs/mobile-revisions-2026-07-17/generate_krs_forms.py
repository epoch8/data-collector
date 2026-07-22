"""
Генерация форм krs-label по документу «Предложения по мобилке 17 июля 2026».

Выход: docs/mobile-revisions-2026-07-17/forms/{bull,young,cow}/config.json
Заливка: скопировать в Git-репозиторий проекта → collector/forms/...
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "django_server/project_git_cache/krs-label/collector/config.json"
# Если локальный git-cache очищен — берём уже сгенерированную форму bull как шаблон.
FALLBACK_BASE = Path(__file__).resolve().parent / "forms" / "bull" / "config.json"
OUT = Path(__file__).resolve().parent / "forms"

SCORE_HINT = "Оценка 1–5."


def _field_map(cfg: dict) -> dict[str, dict]:
    return {f["field_id"]: f for f in cfg["config"]["fields"]}


def _text(fid: str, title: str, instructions: str, required: bool = False) -> dict:
    return {
        "field_id": fid,
        "type": "text_input",
        "title": title,
        "instructions": instructions,
        "validation": {"required": required},
    }


def _instruction(fid: str, title: str, body: str) -> dict:
    return {
        "field_id": fid,
        "type": "instruction",
        "title": title,
        "instructions": body,
    }


def _score_pair(fid: str, title: str, max_desc: str) -> list[dict]:
    return [
        _text(
            fid,
            f"{title} (балл)",
            f"От 1.0 до 5.0. Высший балл: {max_desc}",
        ),
        _text(f"{fid}_desc", f"Описание: {title.lower()}", "По желанию"),
    ]


def _keep_fields(fmap: dict, ids: list[str]) -> list[dict]:
    out = []
    for i in ids:
        if i not in fmap:
            raise KeyError(i)
        out.append(copy.deepcopy(fmap[i]))
    return out


def _common_id_fields(fmap: dict, *, form_label: str, gender_fixed: str) -> list[dict]:
    scan = copy.deepcopy(fmap["scan_time"])
    name = copy.deepcopy(fmap["cow_name"])
    breed = copy.deepcopy(fmap["cow_breed"])
    ident = copy.deepcopy(fmap["cow_identifier"])
    form_note = _instruction(
        "form_scenario_hint",
        "",
        f"## {form_label}\n\n"
        f"Тип животного для этой формы: **{gender_fixed}**.",
    )
    return [scan, name, form_note, breed, ident]


def _age_fields(fmap: dict, hint: str) -> list[dict]:
    skip = copy.deepcopy(fmap["measurements_skip_hint"])
    months = copy.deepcopy(fmap["months"])
    months["instructions"] = hint
    return [skip, months]


def _quantitative_fields(fmap: dict) -> list[dict]:
    # Полный набор промеров; вес и высота в крестце — must have по смыслу заказчика
    # (остальные необязательны, как в текущем config).
    ids = [
        "weight_real",
        "height_at_croup_real",
        "height_at_withers_real",
        "chest_depth_real",
        "chest_width_behind_shoulders_real",
        "width_at_hook_bones_real",
        "width_at_pin_bones_real",
        "body_length_oblique_real",
        "rump_length_oblique_real",
        "chest_girth_real",
        "pastern_girth_real",
        "rump_half_girth_real",
        "head_length_real",
        "forehead_length_real",
        "forehead_width_real",
    ]
    fields = _keep_fields(fmap, ids)
    for f in fields:
        if f["field_id"] == "weight_real":
            f["title"] = "Вес, кг"
            f["instructions"] = (
                "Стандартное взвешивание. Важно для собственника постоянно; "
                "в перспективе — расчёт по фото (must have)."
            )
        if f["field_id"] == "height_at_croup_real":
            f["instructions"] = (
                "От наивысшей точки крестца до земли. "
                "Нужна собственнику любого пола и возраста; после inference — в пакет."
            )
    return fields


def _photo_fields_bull(fmap: dict) -> tuple[list[dict], list[dict]]:
    """Возвращает (все photo fields, один flow-шаг со всеми ракурсами)."""
    guide = copy.deepcopy(fmap["photo_genitals_guide"])
    guide["title"] = "Инструкция: мошонка"
    guide["instructions"] = (
        "## Мошонка\n\nКадр для оценки мошонки быка-производителя "
        "(уровень скакательного сустава, выраженная шейка)."
    )
    scrotum = copy.deepcopy(fmap["photo_scrotum"])
    scrotum["title"] = "Мошонка"
    scrotum["instructions"] = "Кадр мошонки."

    photo_ids_common = [
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
    ]
    fields = _keep_fields(fmap, photo_ids_common) + [guide, scrotum]
    field_ids = [f["field_id"] for f in fields]
    steps = [
        {
            "id": "photos",
            "screen": "scroll_form",
            "form_title": "Фото ракурсы",
            "field_ids": field_ids,
        },
    ]
    return fields, steps


def _photo_fields_cow(fmap: dict) -> tuple[list[dict], list[dict]]:
    guide = copy.deepcopy(fmap["photo_genitals_guide"])
    guide["title"] = "Инструкция: вымя"
    guide["instructions"] = "## Вымя\n\nКадр вымени: достаточно развитое, правильной формы."
    udder = copy.deepcopy(fmap["photo_udder"])
    udder["title"] = "Вымя"
    udder["instructions"] = "Кадр вымени."

    photo_ids_common = [
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
    ]
    fields = _keep_fields(fmap, photo_ids_common) + [guide, udder]
    field_ids = [f["field_id"] for f in fields]
    steps = [
        {
            "id": "photos",
            "screen": "scroll_form",
            "form_title": "Фото ракурсы",
            "field_ids": field_ids,
        },
    ]
    return fields, steps


def _photo_fields_young(fmap: dict) -> tuple[list[dict], list[dict]]:
    # Молодняк: без мошонки/вымени; все ракурсы на одном экране.
    photo_ids = [
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
    ]
    fields = _keep_fields(fmap, photo_ids)
    steps = [
        {
            "id": "photos",
            "screen": "scroll_form",
            "form_title": "Фото ракурсы",
            "field_ids": [f["field_id"] for f in fields],
        },
    ]
    return fields, steps


def build_bull(base: dict) -> dict:
    fmap = _field_map(base)
    ui = copy.deepcopy(base["config"]["ui"])
    qual_scale = _instruction(
        "qual_scale_hint",
        "",
        "## Шкала быков-производителей\n\n"
        "Итого максимум **100** баллов (с коэффициентами). "
        "Ниже — требования для высшего балла по каждой стати.",
    )
    qual_fields = [qual_scale] + (
        _score_pair(
            "overall_type_real",
            "Общий вид, развитие и тип породы",
            "Крупный формат, широкое и округлое туловище с хорошо выраженным мясным типом породы",
        )
        + _score_pair(
            "musculature_real",
            "Мускулатура",
            "Хорошо развитая мускулатура, крепкий, но не грубый костяк",
        )
        + _score_pair(
            "head_and_neck_real",
            "Голова и шея",
            "Голова типичная для породы, шея хорошо обмускуленная",
        )
        + _score_pair(
            "chest_quality_real",
            "Грудь",
            "Широкая, глубокая и округлая, без западин за лопатками; "
            "хорошо развитый, широкий, выдающийся вперед соколок",
        )
        + _score_pair(
            "withers_back_loin_real",
            "Холка, спина, поясница",
            "Широкая, мясистая холка; верхняя линия ровная; "
            "широкие, длинные спина и поясница с хорошо развитой мускулатурой",
        )
        + _score_pair(
            "croup_real",
            "Крестец",
            "Ровный, широкий и длинный, хорошо заполненный мускулатурой; правильно посаженный хвост",
        )
        + _score_pair(
            "scrotum_real",
            "Мошонка",
            "Нормальная с самостоятельно выраженной шейкой достигает уровня скакательного сустава",
        )
        + _score_pair(
            "ham_real",
            "Окорока",
            "Хорошо развитая мускулатура до скакательного сустава; "
            "внутренняя сторона ляжки мясистая; щуп на уровне нижней линии туловища",
        )
        + _score_pair(
            "limbs_real",
            "Конечности",
            "Правильно поставленные с крепкими копытами",
        )
    )
    photo_fields, photo_steps = _photo_fields_bull(fmap)
    id_fields = _common_id_fields(
        fmap, form_label="Бык-производитель", gender_fixed="бык"
    )
    age = _age_fields(
        fmap,
        "Возраст в месяцах. Для этой формы ожидается **от 25 месяцев** (бык-производитель).",
    )
    quant = _quantitative_fields(fmap)
    qual_ids = [f["field_id"] for f in qual_fields]

    return {
        "id": "krs-label",
        "name": "Бык-производитель",
        "version": "2.0",
        "config": {
            "flow": {
                "steps": [
                    {
                        "id": "animal_id",
                        "screen": "scroll_form",
                        "form_title": "Идентификация животного",
                        "cow_id_hints": True,
                        "cow_id_field_id": "cow_identifier",
                        "field_ids": [f["field_id"] for f in id_fields],
                    },
                    {
                        "id": "real_age",
                        "screen": "scroll_form",
                        "form_title": "Возраст",
                        "field_ids": [f["field_id"] for f in age],
                    },
                    {
                        "id": "real_quantitative",
                        "screen": "scroll_form",
                        "form_title": "Количественные замеры",
                        "field_ids": [f["field_id"] for f in quant],
                    },
                    {
                        "id": "real_qualitative",
                        "screen": "scroll_form",
                        "form_title": "Оценка конституции и экстерьера",
                        "field_ids": qual_ids,
                    },
                    *photo_steps,
                    {"id": "review", "screen": "review"},
                ]
            },
            "ui": ui,
            "fields": id_fields + age + quant + qual_fields + photo_fields,
        },
    }


def build_young(base: dict) -> dict:
    fmap = _field_map(base)
    ui = copy.deepcopy(base["config"]["ui"])
    qual_scale = _instruction(
        "qual_scale_hint",
        "",
        "## Шкала мясных форм молодняка\n\n"
        "Применимо к бычкам и тёлкам **до 24 месяцев**. Итого максимум **60** баллов.",
    )
    qual_fields = [qual_scale] + (
        _score_pair(
            "overall_musculature_real",
            "Общий вид и выполненность мускулатуры",
            "Пропорциональное телосложение, типичное для породы. "
            "Широкое, округлое туловище с хорошо развитой мускулатурой",
        )
        + _score_pair(
            "chest_quality_real",
            "Грудь",
            "Широкая, округлая и глубокая, без западин за лопатками. "
            "Хорошо развитый, широкий, выдающийся вперед соколок",
        )
        + _score_pair(
            "withers_back_loin_real",
            "Холка, спина, поясница",
            "Широкая, длинная, ровная, хорошо выполненная мускулатурой",
        )
        + _score_pair(
            "croup_real",
            "Крестец",
            "Ровный, широкий, длинный, хорошо заполненный мускулатурой; правильно посаженный хвост",
        )
        + _score_pair(
            "ham_real",
            "Окорок",
            "Сильно развитая мускулатура до скакательного сустава; "
            "внутренняя сторона ляжки мясистая; щуп в уровень с нижней линией туловища",
        )
    )
    photo_fields, photo_steps = _photo_fields_young(fmap)
    id_fields = _common_id_fields(
        fmap,
        form_label="Молодняк (бычки и тёлки до 24 мес.)",
        gender_fixed="молодняк (бычок / тёлка)",
    )
    # Опционально уточнить пол молодняка
    id_fields.insert(
        3,
        {
            "field_id": "young_sex",
            "type": "single_choice",
            "title": "Пол молодняка",
            "instructions": "Бычок или тёлка.",
            "options": [
                {"value": "bull_calf", "label": "Бычок"},
                {"value": "heifer", "label": "Тёлка"},
            ],
            "validation": {"required": True},
        },
    )
    age = _age_fields(
        fmap,
        "Возраст в месяцах. Для этой формы ожидается **до 24 месяцев** включительно.",
    )
    quant = _quantitative_fields(fmap)
    qual_ids = [f["field_id"] for f in qual_fields]

    return {
        "id": "krs-label",
        "name": "Молодняк (до 24 мес.)",
        "version": "2.0",
        "config": {
            "flow": {
                "steps": [
                    {
                        "id": "animal_id",
                        "screen": "scroll_form",
                        "form_title": "Идентификация животного",
                        "cow_id_hints": True,
                        "cow_id_field_id": "cow_identifier",
                        "field_ids": [f["field_id"] for f in id_fields],
                    },
                    {
                        "id": "real_age",
                        "screen": "scroll_form",
                        "form_title": "Возраст",
                        "field_ids": [f["field_id"] for f in age],
                    },
                    {
                        "id": "real_quantitative",
                        "screen": "scroll_form",
                        "form_title": "Количественные замеры",
                        "field_ids": [f["field_id"] for f in quant],
                    },
                    {
                        "id": "real_qualitative",
                        "screen": "scroll_form",
                        "form_title": "Оценка мясных форм",
                        "field_ids": qual_ids,
                    },
                    *photo_steps,
                    {"id": "review", "screen": "review"},
                ]
            },
            "ui": ui,
            "fields": id_fields + age + quant + qual_fields + photo_fields,
        },
    }


def build_cow(base: dict) -> dict:
    fmap = _field_map(base)
    ui = copy.deepcopy(base["config"]["ui"])
    qual_scale = _instruction(
        "qual_scale_hint",
        "",
        "## Шкала конституции и экстерьера коров\n\n"
        "Итого максимум **100** баллов (с коэффициентами).",
    )
    qual_fields = [qual_scale] + (
        _score_pair(
            "overall_type_real",
            "Общий вид, развитие и тип породы",
            "Крупный формат, широкое и округлое туловище с хорошо выраженным мясным типом породы",
        )
        + _score_pair(
            "musculature_real",
            "Мускулатура",
            "Хорошо развитая мускулатура, крепкий, но не грубый костяк",
        )
        + _score_pair(
            "head_and_neck_real",
            "Голова и шея",
            "Голова легкая, типичная для породы, шея короткая, хорошо обмускуленная",
        )
        + _score_pair(
            "chest_quality_real",
            "Грудь",
            "Широкая, глубокая, без западин за лопатками; хорошо развитый соколок",
        )
        + _score_pair(
            "withers_back_loin_real",
            "Холка, спина, поясница",
            "Широкая, мясистая холка; верхняя линия ровная; "
            "широкие, длинные спина и поясница с хорошо развитой мускулатурой",
        )
        + _score_pair(
            "croup_real",
            "Крестец",
            "Ровный, широкий и длинный, хорошо заполненный мускулатурой; правильно посаженный хвост",
        )
        + _score_pair(
            "ham_real",
            "Окорока",
            "Хорошо развитая мускулатура, спускающаяся до скакательного сустава",
        )
        + _score_pair(
            "udder_real",
            "Вымя",
            "Достаточно развитое, правильной формы",
        )
        + _score_pair(
            "limbs_real",
            "Конечности",
            "Правильно поставленные с крепкими копытами",
        )
    )
    photo_fields, photo_steps = _photo_fields_cow(fmap)
    id_fields = _common_id_fields(fmap, form_label="Корова", gender_fixed="корова")
    age = _age_fields(fmap, "Возраст в месяцах (для коров — по факту).")
    quant = _quantitative_fields(fmap)
    qual_ids = [f["field_id"] for f in qual_fields]

    return {
        "id": "krs-label",
        "name": "Корова",
        "version": "2.0",
        "config": {
            "flow": {
                "steps": [
                    {
                        "id": "animal_id",
                        "screen": "scroll_form",
                        "form_title": "Идентификация животного",
                        "cow_id_hints": True,
                        "cow_id_field_id": "cow_identifier",
                        "field_ids": [f["field_id"] for f in id_fields],
                    },
                    {
                        "id": "real_age",
                        "screen": "scroll_form",
                        "form_title": "Возраст",
                        "field_ids": [f["field_id"] for f in age],
                    },
                    {
                        "id": "real_quantitative",
                        "screen": "scroll_form",
                        "form_title": "Количественные замеры",
                        "field_ids": [f["field_id"] for f in quant],
                    },
                    {
                        "id": "real_qualitative",
                        "screen": "scroll_form",
                        "form_title": "Оценка конституции и экстерьера",
                        "field_ids": qual_ids,
                    },
                    *photo_steps,
                    {"id": "review", "screen": "review"},
                ]
            },
            "ui": ui,
            "fields": id_fields + age + quant + qual_fields + photo_fields,
        },
    }


def main() -> None:
    src = BASE if BASE.is_file() else FALLBACK_BASE
    if not src.is_file():
        raise SystemExit(f"Нет базового config.json: {BASE} или {FALLBACK_BASE}")
    base = json.loads(src.read_text(encoding="utf-8"))
    # Если читаем уже объединённую форму — всё равно пересоберём photo helpers из полей.
    forms = {
        "bull": build_bull(base),
        "young": build_young(base),
        "cow": build_cow(base),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    for fid, data in forms.items():
        d = OUT / fid
        d.mkdir(parents=True, exist_ok=True)
        path = d / "config.json"
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {path.relative_to(ROOT)}  name={data['name']!r} fields={len(data['config']['fields'])}")

    readme = OUT / "README.md"
    readme.write_text(
        """# Формы krs-label (по документу 17 июля 2026)

Сгенерировано скриптом `generate_krs_forms.py` из текущего `collector/config.json`
и приложений 2–4 документа заказчика.

| form_id | Название в picker | Шкала |
|---------|-------------------|--------|
| `bull`  | Бык-производитель | Прил. 2 (актуальная), до 100 баллов |
| `young` | Молодняк (до 24 мес.) | Прил. 3, до 60 баллов |
| `cow`   | Корова | Прил. 4, до 100 баллов |

## Как залить в проект

Скопировать каталоги в Git-репозиторий проекта:

```text
collector/forms/bull/config.json
collector/forms/young/config.json
collector/forms/cow/config.json
```

Опционально оставить/обновить `collector/forms/default/` или legacy `collector/config.json`
для старых пакетов без `form_id`.

Либо в админке: Редактор → «Новая форма» → ID `bull` / `young` / `cow`, затем
вставить JSON или править визуально.

## Что заложено

- Порода: `single_choice` (прил. 1) — уже в базе.
- Пол не выбирается отдельно: выбор формы = тип животного; у молодняка дополнительно `young_sex`.
- Возраст: подсказка по порогу 24/25 мес.
- Промеры: полный набор; акцент на вес и высоту в крестце.
- Баллы: тексты высшего балла из прил. 2–4 (без колонки «Требования…» в отчёте — это отдельная задача).
- Фото: у быка — мошонка; у коровы — вымя; у молодняка — без генитального шага.
  Все ракурсы на **одном** экране `photos` (не step-by-step): в приложении сверху чипы для перехода к ракурсу.
""",
        encoding="utf-8",
    )
    print(f"wrote {readme.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
