"""Сборка протокола бонитировки: форма/превью + PDF + ZIP с медиа."""

from __future__ import annotations

import io
import json
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from django.utils.translation import gettext

from . import packages_ui as pui
from . import project_db as pdb
from . import project_media as pm
from . import project_packages as ppkg
from .models import Project

# field_id → типичные ключи distances из inference (нормализованные / подстроки)
_MEASUREMENT_HINTS: dict[str, tuple[str, ...]] = {
    "weight_real": ("вес", "weight"),
    "height_at_croup_real": ("крестц", "croup"),
    "height_at_withers_real": ("холк", "withers"),
    "chest_depth_real": ("глубина груди", "глубин", "chest depth"),
    "chest_width_behind_shoulders_real": ("ширина груди", "лопатк", "behind shoulder"),
    "width_at_hook_bones_real": ("маклок", "hook"),
    "width_at_pin_bones_real": ("седалищ", "pin bone"),
    "body_length_oblique_real": ("косая длина туловища", "длина туловища", "oblique body"),
    "rump_length_oblique_real": ("косая", "длина зада", "rump length"),
    "chest_girth_real": ("обхват груди", "chest girth"),
    "pastern_girth_real": ("пяст", "pastern"),
    "rump_half_girth_real": ("полуобхват", "half girth"),
    "head_length_real": ("длина головы", "head length"),
    "forehead_length_real": ("длина лба", "forehead length"),
    "forehead_width_real": ("ширина лба", "forehead width"),
}

_QUAL_FIELD_IDS = frozenset(
    {
        "overall_type_real",
        "musculature_real",
        "head_and_neck_real",
        "chest_quality_real",
        "withers_back_loin_real",
        "croup_real",
        "ham_real",
        "udder_real",
        "limbs_real",
        "scrotum_real",
    }
)

_QUANT_STEP_HINTS = ("quantitative", "промер", "замер", "measurement")
_QUAL_STEP_HINTS = ("qualitative", "конституц", "экстерьер", "оценк")
_ID_STEP_HINTS = ("animal", "ident", "возраст", "age", "real_age")


def _norm(text: str) -> str:
    s = (text or "").casefold()
    s = s.replace("ё", "е")
    s = re.sub(r"[^\w\s]+", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def _fmt_value(value: Any) -> str:
    if _is_blank(value):
        return ""
    if isinstance(value, float):
        if value == int(value):
            return str(int(value))
        return f"{value:.1f}".rstrip("0").rstrip(".")
    return str(value)


def collect_inference_distances(project_id: str, package_id: str) -> dict[str, float]:
    """Объединяет distances из всех inference-записей пакета (первый ключ побеждает)."""
    out: dict[str, float] = {}
    for row in pdb.list_inference(project_id, package_id):
        inf = row.get("inference") or {}
        if not isinstance(inf, dict):
            continue
        distances = inf.get("distances")
        if not isinstance(distances, dict):
            continue
        for key, raw in distances.items():
            if key in out:
                continue
            try:
                out[str(key)] = float(raw)
            except (TypeError, ValueError):
                continue
    return out


def _match_distance(
    field_id: str,
    label: str,
    distances: dict[str, float],
    used_keys: set[str],
) -> tuple[str | None, float | None]:
    if not distances:
        return None, None
    candidates = [(k, v) for k, v in distances.items() if k not in used_keys]
    if not candidates:
        return None, None

    label_n = _norm(label)
    fid_n = _norm(field_id.replace("_real", "").replace("_", " "))
    hints = _MEASUREMENT_HINTS.get(field_id, ())

    def score(key: str) -> int:
        kn = _norm(key)
        s = 0
        if kn == label_n:
            s += 100
        if label_n and (label_n in kn or kn in label_n):
            s += 60
        if fid_n and (fid_n in kn or kn in fid_n):
            s += 40
        for h in hints:
            hn = _norm(h)
            if hn and hn in kn:
                s += 50
        # убрать единицы из сравнения
        for unit in (" см", " кг", " cm", " kg"):
            if label_n.replace(unit.strip(), "").strip() == kn:
                s += 80
        return s

    best_key, best_val = None, None
    best_score = 0
    for key, val in candidates:
        sc = score(key)
        if sc > best_score:
            best_score = sc
            best_key, best_val = key, val
    if best_score < 40:
        return None, None
    return best_key, best_val


def _step_kind(step: dict[str, Any]) -> str:
    blob = " ".join(
        str(step.get(k) or "") for k in ("id", "form_title", "screen")
    ).casefold()
    if any(h in blob for h in _QUANT_STEP_HINTS):
        return "measurements"
    if any(h in blob for h in _QUAL_STEP_HINTS):
        return "qualitative"
    if any(h in blob for h in _ID_STEP_HINTS):
        return "identity"
    return "other"


def _field_kind(field: dict[str, Any], step_kind: str) -> str:
    fid = field.get("field_id") or ""
    if fid in _QUAL_FIELD_IDS or fid.endswith("_real_desc"):
        return "qualitative"
    if fid.endswith("_desc"):
        return "qualitative"
    if step_kind == "measurements":
        return "measurements"
    if step_kind == "qualitative":
        return "qualitative"
    if step_kind == "identity":
        return "identity"
    if fid in _MEASUREMENT_HINTS or fid.endswith("_real"):
        # *_real вне qual → промер (если не известный балл)
        if fid not in _QUAL_FIELD_IDS:
            return "measurements"
    title = _norm(pui.field_label(field))
    if title.endswith("см") or title.endswith("кг") or " см" in title or " кг" in title:
        return "measurements"
    return "identity" if step_kind == "other" else step_kind


@dataclass
class ProtocolRow:
    field_id: str
    label: str
    manual: str = ""
    inference: str = ""
    inference_key: str | None = None
    value: str = ""  # итог для протокола
    source: str = "empty"  # manual | inference | empty
    kind: str = "identity"
    editable: bool = True
    hint: str = ""
    field_type: str = "text_input"
    options: list[dict[str, str]] = field(default_factory=list)
    display_value: str = ""


@dataclass
class ProtocolMediaItem:
    field_id: str
    label: str
    path: str
    url: str = ""
    filename: str = ""


@dataclass
class ProtocolDraft:
    package_id: str
    project_id: str
    project_name: str
    identity: list[ProtocolRow] = field(default_factory=list)
    measurements: list[ProtocolRow] = field(default_factory=list)
    qualitative: list[ProtocolRow] = field(default_factory=list)
    other_fields: list[ProtocolRow] = field(default_factory=list)
    extra_inference: list[dict[str, str]] = field(default_factory=list)
    media: list[ProtocolMediaItem] = field(default_factory=list)
    inference_count: int = 0


def build_protocol_draft(
    project_id: str,
    package_id: str,
    *,
    config: dict[str, Any],
    data: dict[str, Any],
    blobs: list[dict[str, Any]] | None = None,
    editable: bool = True,
) -> ProtocolDraft:
    fields = pui.config_fields(config)
    by_id = {f["field_id"]: f for f in fields}
    distances = collect_inference_distances(project_id, package_id)
    used_dist_keys: set[str] = set()

    project_name = (config.get("name") if isinstance(config, dict) else None) or project_id
    draft = ProtocolDraft(
        package_id=package_id,
        project_id=project_id,
        project_name=str(project_name),
        inference_count=len(distances),
    )

    flow = config.get("config", {}).get("flow") if isinstance(config.get("config"), dict) else None
    steps = (flow or {}).get("steps") or [] if isinstance(flow, dict) else []
    seen: set[str] = set()

    def add_row(f: dict[str, Any], kind: str) -> None:
        fid = f["field_id"]
        if fid in seen:
            return
        seen.add(fid)
        label = pui.field_label(f)
        manual_raw = data.get(fid)
        manual = _fmt_value(manual_raw)
        inf_key, inf_val = (None, None)
        if kind == "measurements":
            inf_key, inf_val = _match_distance(fid, label, distances, used_dist_keys)
            if inf_key:
                used_dist_keys.add(inf_key)
        inference = _fmt_value(inf_val) if inf_val is not None else ""
        if not _is_blank(manual):
            value, source = manual, "manual"
        elif inference:
            value, source = inference, "inference"
        else:
            value, source = "", "empty"
        options = pui.field_choice_options(f)
        if options and value and value not in {o["value"] for o in options}:
            options = [*options, {"value": value, "label": value}]
        row = ProtocolRow(
            field_id=fid,
            label=label,
            manual=manual,
            inference=inference,
            inference_key=inf_key,
            value=value,
            source=source,
            kind=kind,
            editable=editable and f.get("type") in ("text_input", "single_choice"),
            hint=pui.field_hint(f),
            field_type=str(f.get("type") or "text_input"),
            options=options,
            display_value=pui.choice_label(f, value) if f.get("type") == "single_choice" else value,
        )
        if kind == "measurements":
            draft.measurements.append(row)
        elif kind == "qualitative":
            draft.qualitative.append(row)
        elif kind == "identity":
            draft.identity.append(row)
        else:
            draft.other_fields.append(row)

    for step in steps:
        if not isinstance(step, dict) or step.get("screen") != "scroll_form":
            continue
        sk = _step_kind(step)
        for fid in step.get("field_ids") or []:
            f = by_id.get(fid)
            if not f or not pui.is_data_tab_field(f):
                continue
            add_row(f, _field_kind(f, sk))

    for f in fields:
        if not pui.is_data_tab_field(f):
            continue
        if f["field_id"] in seen:
            continue
        add_row(f, _field_kind(f, "other"))

    for key, val in distances.items():
        if key in used_dist_keys:
            continue
        draft.extra_inference.append({"label": key, "value": _fmt_value(val)})

    blob_urls = {}
    if blobs:
        for b in blobs:
            blob_urls[b.get("logical_path")] = b.get("url") or ""

    media_sections, _media_used = pui.build_media_sections(config, fields, data)
    for sec in media_sections:
        for fld in sec.get("fields") or []:
            for sh in fld.get("shots") or []:
                path = sh["path"]
                draft.media.append(
                    ProtocolMediaItem(
                        field_id=fld["field_id"],
                        label=fld["label"],
                        path=path,
                        url=blob_urls.get(path, ""),
                        filename=pui.blob_file_name(path),
                    ),
                )

    # сироты — тоже в протокол
    used_paths = {m.path for m in draft.media}
    if blobs:
        for b in blobs:
            path = b.get("logical_path") or ""
            if not path or path in used_paths:
                continue
            # skip non-images for preview gallery? ещё кладём в zip всё — здесь для PDF только картинки
            lower = path.lower()
            if not lower.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic")):
                continue
            draft.media.append(
                ProtocolMediaItem(
                    field_id="_orphan",
                    label=gettext("Прочее"),
                    path=path,
                    url=b.get("url") or "",
                    filename=pui.blob_file_name(path),
                ),
            )

    return draft


def draft_to_template_context(draft: ProtocolDraft) -> dict[str, Any]:
    def rows(items: list[ProtocolRow]) -> list[dict[str, Any]]:
        return [
            {
                "field_id": r.field_id,
                "label": r.label,
                "manual": r.manual,
                "inference": r.inference,
                "inference_key": r.inference_key or "",
                "value": r.value,
                "display_value": row_display(r),
                "source": r.source,
                "editable": r.editable,
                "hint": r.hint,
                "type": r.field_type,
                "options": r.options,
            }
            for r in items
        ]

    return {
        "identity": rows(draft.identity),
        "measurements": rows(draft.measurements),
        "qualitative": rows(draft.qualitative),
        "other_fields": rows(draft.other_fields),
        "extra_inference": draft.extra_inference,
        "media": [
            {
                "field_id": m.field_id,
                "label": m.label,
                "path": m.path,
                "url": m.url,
                "filename": m.filename,
            }
            for m in draft.media
        ],
        "inference_count": draft.inference_count,
        "project_name": draft.project_name,
    }


def _pdf_text(value: Any, *, empty: str = "-") -> str:
    """Текст для PDF: без длинных тире; пустое → empty."""
    if _is_blank(value):
        return empty
    text = str(value)
    for ch in ("\u2014", "\u2013", "—", "–"):
        text = text.replace(ch, ",")
    # «Профиль , левый» → «Профиль, левый»
    text = re.sub(r"\s*,\s*", ", ", text).strip(" ,")
    return text or empty


def _media_caption(item: ProtocolMediaItem) -> str:
    """Подпись фото в PDF: только ракурс, без имени файла."""
    return _pdf_text(item.label or item.field_id or "Фото", empty="Фото")


def _choice_display(value: str, options: list[dict[str, str]]) -> str:
    """Подпись варианта для UI/PDF; value остаётся машинным (bull_calf и т.п.)."""
    if _is_blank(value):
        return ""
    text = str(value)
    for opt in options or []:
        if opt.get("value") == text:
            return opt.get("label") or text
    return text


def row_display(row: ProtocolRow) -> str:
    """Что показывать человеку в превью/PDF (для single_choice — русский label)."""
    if row.field_type == "single_choice" or row.options:
        shown = _choice_display(row.value, row.options)
        if shown:
            return shown
    if row.display_value:
        return row.display_value
    return row.value or ""


def apply_overrides(draft: ProtocolDraft, overrides: dict[str, str]) -> ProtocolDraft:
    """Подставить значения из формы протокола (POST) в draft.value."""
    if not overrides:
        return draft
    for group in (draft.identity, draft.measurements, draft.qualitative, draft.other_fields):
        for row in group:
            if row.field_id in overrides:
                row.value = overrides[row.field_id]
                row.display_value = (
                    _choice_display(row.value, row.options)
                    if (row.field_type == "single_choice" or row.options)
                    else row.value
                )
                if not _is_blank(row.value):
                    if row.value == row.manual and row.manual:
                        row.source = "manual"
                    elif row.value == row.inference and row.inference:
                        row.source = "inference"
                    else:
                        row.source = "manual"
                else:
                    row.source = "empty"
    return draft


def _resolve_pdf_font() -> tuple[str, str | None]:
    """Возвращает (regular_path, bold_path|None)."""
    here = Path(__file__).resolve().parent
    bundled = [
        here / "static" / "fonts" / "DejaVuSans.ttf",
        here / "static" / "fonts" / "ProtocolSans.ttf",
    ]
    candidates = [
        *bundled,
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/Library/Fonts/Arial.ttf"),
    ]
    bold_map = {
        "arial.ttf": "arialbd.ttf",
        "DejaVuSans.ttf": "DejaVuSans-Bold.ttf",
        "ProtocolSans.ttf": "ProtocolSans-Bold.ttf",
        "LiberationSans-Regular.ttf": "LiberationSans-Bold.ttf",
    }
    for path in candidates:
        if path.is_file():
            bold = None
            bold_name = bold_map.get(path.name)
            if bold_name:
                bp = path.with_name(bold_name)
                if bp.is_file():
                    bold = str(bp)
            return str(path), bold
    return "", None


def _register_fonts() -> tuple[str, str]:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    regular_path, bold_path = _resolve_pdf_font()
    if not regular_path:
        return "Helvetica", "Helvetica-Bold"
    pdfmetrics.registerFont(TTFont("ProtocolSans", regular_path))
    if bold_path:
        pdfmetrics.registerFont(TTFont("ProtocolSans-Bold", bold_path))
        return "ProtocolSans", "ProtocolSans-Bold"
    return "ProtocolSans", "ProtocolSans"


def _read_blob_bytes(project_id: str, package_id: str, logical_path: str) -> bytes | None:
    project = Project.objects.filter(project_id=project_id).first()
    blob = ppkg.get_blob_by_path(project_id, package_id, logical_path)
    if not blob:
        return None
    return pm.read_blob_bytes(
        project_id,
        blob.storage_path,
        media_bucket=(project.media_bucket if project else "") or "",
    )


def build_protocol_pdf(
    draft: ProtocolDraft,
    *,
    image_bytes: dict[str, bytes] | None = None,
) -> bytes:
    """PDF: шапка, поля, промеры (ручной/инференс/итог), качественные, фото в документе."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Image,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    font, font_bold = _register_fonts()
    image_bytes = image_bytes or {}

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=gettext("Протокол бонитировки"),
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="PTitle",
            fontName=font_bold,
            fontSize=16,
            leading=20,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
    )
    styles.add(
        ParagraphStyle(
            name="PSub",
            fontName=font,
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#444444"),
            spaceAfter=12,
        ),
    )
    styles.add(
        ParagraphStyle(
            name="PH",
            fontName=font_bold,
            fontSize=12,
            leading=15,
            spaceBefore=10,
            spaceAfter=6,
        ),
    )
    styles.add(
        ParagraphStyle(
            name="PBody",
            fontName=font,
            fontSize=9,
            leading=12,
            alignment=TA_LEFT,
        ),
    )
    styles.add(
        ParagraphStyle(
            name="PSmall",
            fontName=font,
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#555555"),
        ),
    )
    styles.add(
        ParagraphStyle(
            name="PCell",
            fontName=font,
            fontSize=8,
            leading=10,
        ),
    )
    styles.add(
        ParagraphStyle(
            name="PCellBold",
            fontName=font_bold,
            fontSize=8,
            leading=10,
        ),
    )

    story: list[Any] = []
    story.append(Paragraph(gettext("Протокол бонитировки"), styles["PTitle"]))
    story.append(
        Paragraph(
            f"{draft.project_name} · {draft.package_id}",
            styles["PSub"],
        ),
    )

    def section_table(title: str, rows: list[ProtocolRow], *, with_inference: bool) -> None:
        if not rows:
            return
        story.append(Paragraph(title, styles["PH"]))
        if with_inference:
            data = [[
                Paragraph(gettext("Показатель"), styles["PCellBold"]),
                Paragraph(gettext("В протоколе"), styles["PCellBold"]),
                Paragraph(gettext("Ручной"), styles["PCellBold"]),
                Paragraph(gettext("Инференс"), styles["PCellBold"]),
            ]]
            for r in rows:
                data.append([
                    Paragraph(_pdf_text(r.label or r.field_id), styles["PCell"]),
                    Paragraph(_pdf_text(row_display(r)), styles["PCell"]),
                    Paragraph(_pdf_text(r.manual), styles["PCell"]),
                    Paragraph(_pdf_text(r.inference), styles["PCell"]),
                ])
            col_widths = [70 * mm, 30 * mm, 30 * mm, 30 * mm]
        else:
            data = [[
                Paragraph(gettext("Показатель"), styles["PCellBold"]),
                Paragraph(gettext("Значение"), styles["PCellBold"]),
            ]]
            for r in rows:
                data.append([
                    Paragraph(_pdf_text(r.label or r.field_id), styles["PCell"]),
                    Paragraph(_pdf_text(row_display(r)), styles["PCell"]),
                ])
            col_widths = [100 * mm, 60 * mm]
        t = Table(data, colWidths=col_widths, repeatRows=1)
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEEEEE")),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ],
            ),
        )
        story.append(t)

    section_table(gettext("Идентификация"), draft.identity, with_inference=False)
    section_table(gettext("Промеры"), draft.measurements, with_inference=True)
    if draft.extra_inference:
        story.append(Paragraph(gettext("Дополнительные метрики инференса"), styles["PH"]))
        data = [[
            Paragraph(gettext("Метрика"), styles["PCellBold"]),
            Paragraph(gettext("Значение"), styles["PCellBold"]),
        ]]
        for item in draft.extra_inference:
            data.append([
                Paragraph(_pdf_text(item["label"]), styles["PCell"]),
                Paragraph(_pdf_text(item["value"]), styles["PCell"]),
            ])
        t = Table(data, colWidths=[120 * mm, 40 * mm], repeatRows=1)
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEEEEE")),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ],
            ),
        )
        story.append(t)
    section_table(gettext("Качественные признаки"), draft.qualitative, with_inference=False)
    if draft.other_fields:
        section_table(gettext("Прочее"), draft.other_fields, with_inference=False)

    if draft.media:
        story.append(PageBreak())
        story.append(Paragraph(gettext("Медиаматериалы"), styles["PH"]))
        story.append(
            Paragraph(
                gettext("Фото ракурсов пакета с подписями."),
                styles["PSmall"],
            ),
        )
        story.append(Spacer(1, 4 * mm))
        page_w = A4[0] - 28 * mm
        max_w = page_w
        max_h = 90 * mm
        for m in draft.media:
            raw = image_bytes.get(m.path)
            story.append(
                Paragraph(
                    f"<b>{_media_caption(m)}</b>",
                    styles["PBody"],
                ),
            )
            if not raw:
                story.append(Paragraph(gettext("Файл недоступен"), styles["PSmall"]))
                story.append(Spacer(1, 3 * mm))
                continue
            try:
                img = Image(io.BytesIO(raw))
                img.hAlign = "CENTER"
                iw, ih = float(img.imageWidth), float(img.imageHeight)
                scale = min(max_w / iw, max_h / ih, 1.0)
                img.drawWidth = iw * scale
                img.drawHeight = ih * scale
                story.append(img)
            except Exception:
                story.append(Paragraph(gettext("Не удалось вставить изображение"), styles["PSmall"]))
            story.append(Spacer(1, 4 * mm))

    doc.build(story)
    return buf.getvalue()


def build_protocol_zip(
    project_id: str,
    package_id: str,
    draft: ProtocolDraft,
    *,
    include_media_files: bool = True,
) -> bytes:
    """ZIP: protocol.pdf (всегда с фото внутри) + protocol.json;
    при include_media_files — ещё папка media/ с оригиналами."""
    image_bytes: dict[str, bytes] = {}
    all_blob_bytes: dict[str, bytes] = {}

    paths: list[str] = []
    for m in draft.media:
        if m.path not in paths:
            paths.append(m.path)
    # для PDF достаточно фото из draft.media; для media/ — все блобы пакета
    pdf_paths = list(paths)
    if include_media_files:
        for b in ppkg.list_blobs(project_id, package_id):
            path = getattr(b, "logical_path", None) or ""
            if path and path not in paths:
                paths.append(path)

    for path in paths:
        data = _read_blob_bytes(project_id, package_id, path)
        if data is None:
            continue
        if include_media_files:
            all_blob_bytes[path] = data
        lower = path.lower()
        if path in pdf_paths and lower.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
            image_bytes[path] = data

    pdf_bytes = build_protocol_pdf(draft, image_bytes=image_bytes)

    snapshot = {
        "package_id": package_id,
        "project_id": project_id,
        "project_name": draft.project_name,
        "identity": [
            {
                "field_id": r.field_id,
                "label": r.label,
                "value": r.value,
                "display": row_display(r),
                "source": r.source,
            }
            for r in draft.identity
        ],
        "measurements": [
            {
                "field_id": r.field_id,
                "label": r.label,
                "value": r.value,
                "display": row_display(r),
                "manual": r.manual,
                "inference": r.inference,
                "source": r.source,
            }
            for r in draft.measurements
        ],
        "qualitative": [
            {
                "field_id": r.field_id,
                "label": r.label,
                "value": r.value,
                "display": row_display(r),
            }
            for r in draft.qualitative
        ],
        "extra_inference": draft.extra_inference,
        "include_media_files": include_media_files,
        "media": [{"path": m.path, "label": m.label, "field_id": m.field_id} for m in draft.media],
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("protocol.pdf", pdf_bytes)
        zf.writestr(
            "protocol.json",
            json.dumps(snapshot, ensure_ascii=False, indent=2),
        )
        if include_media_files:
            used_names: set[str] = set()
            for path, data in all_blob_bytes.items():
                name = Path(path.replace("\\", "/")).name or "file.bin"
                rel = path.replace("\\", "/").lstrip("/")
                if rel.startswith("blobs/"):
                    arc = f"media/{rel[len('blobs/'):]}"
                else:
                    arc = f"media/{name}"
                base_arc = arc
                n = 1
                while arc in used_names:
                    stem = Path(base_arc).stem
                    suffix = Path(base_arc).suffix
                    parent = str(Path(base_arc).parent).replace("\\", "/")
                    arc = f"{parent}/{stem}_{n}{suffix}"
                    n += 1
                used_names.add(arc)
                zf.writestr(arc, data)

    return buf.getvalue()
