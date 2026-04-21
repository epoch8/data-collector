"""
Проверка JSON проекта перед сохранением — правила согласованы с
lib/features/collection/logic/collection_flow_resolver.dart (resolveCollectionFlow).
"""

from __future__ import annotations

from typing import Any


def _parse_screen(raw: str) -> str:
    s = raw.strip().lower().replace("-", "_")
    allowed = {
        "form",
        "instruction",
        "camera_pose",
        "cameraphoto",
        "review",
        "scroll_form",
        "scrollform",
    }
    if s in allowed:
        return s
    raise ValueError(f'Неизвестный screen "{raw}"')


def _norm_screen(s: str) -> str:
    return _parse_screen(s)


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
        for key in ("priority", "type", "title", "instructions"):
            if key not in f:
                errs.append(f'config.fields[{i}] ({fid}): отсутствует поле "{key}".')
        if not isinstance(f.get("priority"), (int, float)):
            errs.append(f'config.fields[{i}] ({fid}): priority должен быть числом.')
        if not isinstance(f.get("type"), str):
            errs.append(f'config.fields[{i}] ({fid}): type должен быть строкой.')
        if not isinstance(f.get("title"), str):
            errs.append(f'config.fields[{i}] ({fid}): title должен быть строкой.')
        if not isinstance(f.get("instructions"), str):
            errs.append(f'config.fields[{i}] ({fid}): instructions должен быть строкой.')
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

    if len(steps) > 1:
        for st, k in zip(steps, kinds):
            if k in ("scroll_form", "scrollform"):
                errs.append(
                    f'Шаг "{st.get("id", "?")}": screen scroll_form допустим только как единственный шаг сценария.',
                )

    for st, k in zip(steps, kinds):
        sid = str(st.get("id", "?"))

        if k in ("scroll_form", "scrollform"):
            ids = st.get("field_ids")
            if ids is not None:
                if not isinstance(ids, list):
                    errs.append(f'Шаг "{sid}": field_ids должен быть массивом или отсутствовать.')
                elif ids:
                    for fid in ids:
                        if fid not in by_id:
                            errs.append(f'Шаг "{sid}": неизвестный field_id "{fid}" в field_ids.')

        elif k == "form":
            ids = st.get("field_ids")
            if not isinstance(ids, list) or not ids:
                errs.append(f'Шаг "{sid}" (form): нужен непустой field_ids.')
            else:
                allowed_types = {"text_input", "datetime"}
                for fid in ids:
                    f = by_id.get(fid)
                    if f is None:
                        errs.append(f'Шаг "{sid}": неизвестный field_id "{fid}" в field_ids.')
                        continue
                    t = f.get("type")
                    if t not in allowed_types:
                        errs.append(
                            f'Шаг "{sid}": поле "{fid}" имеет type "{t}", для form допустимо: {sorted(allowed_types)}.',
                        )
                hint_field = st.get("cow_id_field_id")
                if hint_field is not None and isinstance(ids, list) and hint_field not in ids:
                    errs.append(
                        f'Шаг "{sid}": cow_id_field_id "{hint_field}" должен входить в field_ids.',
                    )

        elif k == "instruction":
            fid = st.get("field_id")
            if not isinstance(fid, str) or not fid:
                errs.append(f'Шаг "{sid}" (instruction): нужен field_id.')
            else:
                f = by_id.get(fid)
                if f is None:
                    errs.append(f'Шаг "{sid}": неизвестный field_id "{fid}".')
                elif f.get("type") != "instruction":
                    errs.append(
                        f'Шаг "{sid}": поле "{fid}" должно иметь type instruction, сейчас {f.get("type")!r}.',
                    )

        elif k in ("camera_pose", "cameraphoto"):
            fid = st.get("field_id")
            if not isinstance(fid, str) or not fid:
                errs.append(f'Шаг "{sid}" (camera_pose): нужен field_id.')
            else:
                f = by_id.get(fid)
                if f is None:
                    errs.append(f'Шаг "{sid}": неизвестный field_id "{fid}".')
                elif f.get("type") != "camera_photo":
                    errs.append(
                        f'Шаг "{sid}": поле "{fid}" должно иметь type camera_photo, сейчас {f.get("type")!r}.',
                    )

        elif k == "review":
            pass

    has_camera = any(k in ("camera_pose", "cameraphoto") for k in kinds)
    has_review = any(k == "review" for k in kinds)
    if has_camera and not has_review:
        # клиент автоматически добавляет review — не ошибка
        pass

    ui = cfg.get("ui")
    if ui is not None and not isinstance(ui, dict):
        errs.append("config.ui, если задан, должен быть объектом.")

    return errs
