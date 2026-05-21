"""
Проверка JSON проекта перед сохранением — правила согласованы с
lib/features/collection/logic/collection_flow_resolver.dart (resolveCollectionFlow).
Допускаются только шаги scroll_form и review; каждое поле из config.fields встречается ровно в одном scroll_form.
"""

from __future__ import annotations

from typing import Any

ALLOWED_FIELD_TYPES = frozenset({"text_input", "datetime", "instruction", "camera_photo"})


def _norm_screen(raw: str) -> str:
    s = raw.strip().lower().replace("-", "_")
    if s in ("scroll_form", "scrollform"):
        return "scroll_form"
    if s == "review":
        return "review"
    raise ValueError(f'Неизвестный или устаревший screen "{raw}". Допустимо: scroll_form, review.')


def validate_project_payload(data: dict[str, Any], project_id: str) -> list[str]:
    """Возвращает список ошибок; пустой список — конфиг можно сохранить."""
    errs: list[str] = []

    if not isinstance(data, dict):
        return ["Корень JSON должен быть объектом."]

    rid = data.get("id")
    if rid is not None and rid != project_id:
        errs.append(f'Поле id в JSON ("{rid}") должно совпадать с project_id проекта ("{project_id}").')

    if not isinstance(data.get("name"), str) or not (data.get("name") or "").strip():
        errs.append("Поле name должно быть непустой строкой.")

    ver = data.get("version")
    if ver is not None and not isinstance(ver, str):
        errs.append("Поле version должно быть строкой.")

    cfg = data.get("config")
    if not isinstance(cfg, dict):
        errs.append("Поле config должно быть объектом.")
        return errs

    fields_raw = cfg.get("fields")
    if not isinstance(fields_raw, list) or not fields_raw:
        errs.append("config.fields должен быть непустым массивом полей.")
        fields_raw = []

    by_id: dict[str, dict[str, Any]] = {}
    for i, f in enumerate(fields_raw):
        if not isinstance(f, dict):
            errs.append(f"config.fields[{i}]: элемент должен быть объектом.")
            continue
        fid = f.get("field_id")
        if not isinstance(fid, str) or not fid.strip():
            errs.append(f"config.fields[{i}]: нужен непустой field_id.")
            continue
        if fid in by_id:
            errs.append(f'Дублируется field_id "{fid}".')
        for key in ("type", "title", "instructions"):
            if key not in f:
                errs.append(f'config.fields[{i}] ({fid}): отсутствует поле "{key}".')
        pr = f.get("priority")
        if pr is not None and not isinstance(pr, (int, float)):
            errs.append(f'config.fields[{i}] ({fid}): priority, если задан, должен быть числом.')
        if not isinstance(f.get("type"), str):
            errs.append(f'config.fields[{i}] ({fid}): type должен быть строкой.')
        if not isinstance(f.get("title"), str):
            errs.append(f'config.fields[{i}] ({fid}): title должен быть строкой.')
        if not isinstance(f.get("instructions"), str):
            errs.append(f'config.fields[{i}] ({fid}): instructions должен быть строкой.')
        ft = str(f.get("type", "")).strip()
        if ft not in ALLOWED_FIELD_TYPES:
            errs.append(
                f'config.fields[{i}] ({fid}): неизвестный type "{ft}". '
                f"Допустимо: {sorted(ALLOWED_FIELD_TYPES)}.",
            )
        by_id[fid] = f

    flow = cfg.get("flow")
    if not isinstance(flow, dict):
        errs.append("config.flow должен быть объектом.")
        return errs

    steps_raw = flow.get("steps")
    if not isinstance(steps_raw, list) or not steps_raw:
        errs.append("config.flow.steps должен быть непустым массивом шагов.")
        return errs

    steps: list[dict[str, Any]] = [s for s in steps_raw if isinstance(s, dict)]
    if len(steps) != len(steps_raw):
        errs.append("Каждый элемент config.flow.steps должен быть объектом.")

    try:
        kinds = [_norm_screen(str(s.get("screen", ""))) for s in steps]
    except ValueError as e:
        errs.append(str(e))
        return errs

    field_step: dict[str, str] = {}

    for st, k in zip(steps, kinds):
        sid = str(st.get("id", "?"))

        if k == "review":
            continue

        ftit = st.get("form_title")
        if ftit is not None and not isinstance(ftit, str):
            errs.append(f'Шаг "{sid}": form_title, если задан, должен быть строкой.')

        if k != "scroll_form":
            errs.append(f'Шаг "{sid}": допускается только screen scroll_form или review.')
            continue

        ids = st.get("field_ids")
        if not isinstance(ids, list) or not ids:
            errs.append(f'Шаг "{sid}" (scroll_form): нужен непустой массив field_ids.')
            continue

        for j, fid in enumerate(ids):
            if not isinstance(fid, str) or not fid.strip():
                errs.append(f'Шаг "{sid}": field_ids[{j}] должен быть непустой строкой.')
                continue
            if fid not in by_id:
                errs.append(f'Шаг "{sid}": неизвестный field_id "{fid}" в field_ids.')
                continue
            if fid in field_step:
                prev = field_step[fid]
                if prev == sid:
                    errs.append(f'Шаг "{sid}": field_id "{fid}" повторяется в field_ids.')
                else:
                    errs.append(
                        f'Поле "{fid}" уже назначено шагу "{prev}" и снова в "{sid}"; '
                        f"каждое поле — только в одном scroll_form.",
                    )
            else:
                field_step[fid] = sid

        if st.get("cow_id_hints") is True:
            cf = st.get("cow_id_field_id")
            if not isinstance(cf, str) or not cf.strip():
                errs.append(f'Шаг "{sid}": при cow_id_hints нужен непустой cow_id_field_id.')
            elif cf not in ids:
                errs.append(f'Шаг "{sid}": cow_id_field_id "{cf}" должен входить в field_ids.')

    for fid in by_id:
        if fid not in field_step:
            errs.append(f'Поле "{fid}" не указано ни в одном шаге scroll_form (field_ids).')

    ui = cfg.get("ui")
    if ui is not None and not isinstance(ui, dict):
        errs.append("config.ui, если задан, должен быть объектом.")

    return errs
