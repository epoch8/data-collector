"""
Generate customer-facing presentation for the Korovas training implementation.

Run:
    python docs/business/generate_training_presentation.py

Output:
    docs/business/Training-Program.pptx
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

try:
    from PIL import Image
except ImportError:  # pragma: no cover - fallback for minimal envs
    Image = None

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
IMG = REPO / "specs" / "presentation" / "img"
OUT = ROOT / "Training-Program.pptx"

W = Inches(13.333)
H = Inches(7.5)
TOTAL = 7


class C:
    paper = RGBColor(0xFB, 0xFA, 0xF4)
    paper_2 = RGBColor(0xF1, 0xEE, 0xE6)
    ink = RGBColor(0x13, 0x16, 0x1D)
    muted = RGBColor(0x5F, 0x66, 0x73)
    faint = RGBColor(0xB6, 0xB8, 0xB2)
    line = RGBColor(0xDD, 0xDA, 0xCF)
    cobalt = RGBColor(0x22, 0x4E, 0xF2)
    lime = RGBColor(0xB7, 0xF2, 0x40)
    coral = RGBColor(0xFF, 0x6B, 0x57)
    mint = RGBColor(0x20, 0xC9, 0x9A)
    night = RGBColor(0x09, 0x0D, 0x16)
    night_2 = RGBColor(0x13, 0x1A, 0x2A)
    white = RGBColor(0xFF, 0xFF, 0xFF)


def new_deck() -> Presentation:
    prs = Presentation()
    prs.slide_width = W
    prs.slide_height = H
    return prs


def solid(shape, color: RGBColor) -> None:
    shape.fill.solid()
    shape.fill.fore_color.rgb = color


def no_line(shape) -> None:
    shape.line.fill.background()


def line(shape, color: RGBColor, width: float = 1.0) -> None:
    shape.line.color.rgb = color
    shape.line.width = Pt(width)


def rect(slide, l, t, w, h, fill: RGBColor, border: RGBColor | None = None, radius: bool = False):
    kind = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(kind, l, t, w, h)
    solid(shape, fill)
    if border:
        line(shape, border, 0.8)
    else:
        no_line(shape)
    return shape


def oval(slide, l, t, w, h, fill: RGBColor, border: RGBColor | None = None):
    shape = slide.shapes.add_shape(MSO_SHAPE.OVAL, l, t, w, h)
    solid(shape, fill)
    if border:
        line(shape, border, 0.8)
    else:
        no_line(shape)
    return shape


def text(
    slide,
    l,
    t,
    w,
    h,
    value: str,
    *,
    size=14,
    bold=False,
    color: RGBColor | None = None,
    align=PP_ALIGN.LEFT,
    anchor=MSO_ANCHOR.TOP,
):
    box = slide.shapes.add_textbox(l, t, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    p = tf.paragraphs[0]
    p.text = value
    p.font.size = Pt(size)
    p.font.bold = bold
    p.font.color.rgb = color or C.ink
    p.alignment = align
    return box


def bg(slide, color: RGBColor = C.paper) -> None:
    solid(slide.background, color)


def footer(slide, n: int, dark: bool = False) -> None:
    color = RGBColor(0x7C, 0x83, 0x90) if dark else C.faint
    text(slide, Inches(0.65), Inches(7.1), Inches(4.5), Inches(0.22), "Epoch8 · обучение Korovas", size=8, color=color)
    text(
        slide,
        Inches(12.15),
        Inches(7.1),
        Inches(0.7),
        Inches(0.22),
        f"{n:02d}/{TOTAL:02d}",
        size=8,
        color=color,
        align=PP_ALIGN.RIGHT,
    )


def title(slide, title_text: str, subtitle: str | None = None, *, dark: bool = False):
    color = C.white if dark else C.ink
    muted = RGBColor(0xB0, 0xB7, 0xC5) if dark else C.muted
    text(slide, Inches(0.65), Inches(0.55), Inches(10.2), Inches(0.9), title_text, size=30, bold=True, color=color)
    rect(slide, Inches(0.65), Inches(1.48), Inches(1.8), Pt(5), C.lime if dark else C.cobalt)
    if subtitle:
        text(slide, Inches(0.65), Inches(1.65), Inches(10.2), Inches(0.45), subtitle, size=12, color=muted)


def pill(slide, l, t, w, label: str, fill: RGBColor, fg: RGBColor = C.ink):
    p = rect(slide, l, t, w, Inches(0.36), fill, radius=True)
    p.text_frame.clear()
    para = p.text_frame.paragraphs[0]
    para.text = label
    para.font.size = Pt(9)
    para.font.bold = True
    para.font.color.rgb = fg
    para.alignment = PP_ALIGN.CENTER
    p.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE


def card(slide, l, t, w, h, heading: str, body: str, accent: RGBColor = C.cobalt, dark: bool = False):
    fill = C.night_2 if dark else C.white
    border = RGBColor(0x2D, 0x36, 0x48) if dark else C.line
    muted = RGBColor(0xA7, 0xB0, 0xC0) if dark else C.muted
    rect(slide, l, t, w, h, fill, border, radius=True)
    rect(slide, l, t, Inches(0.08), h, accent)
    text(slide, l + Inches(0.22), t + Inches(0.18), w - Inches(0.35), Inches(0.35), heading, size=13, bold=True, color=accent)
    text(slide, l + Inches(0.22), t + Inches(0.58), w - Inches(0.35), h - Inches(0.7), body, size=10, color=muted)


def add_image_fit(slide, path: Path, l, t, w, h, *, bg_fill: RGBColor = C.white):
    """Insert image into a frame without changing its aspect ratio."""
    frame = rect(slide, l, t, w, h, bg_fill, C.line, radius=True)
    frame.text_frame.clear()
    if not path.exists():
        text(slide, l, t + h / 2 - Inches(0.15), w, Inches(0.3), path.name, size=9, color=C.faint, align=PP_ALIGN.CENTER)
        return frame

    if Image is None:
        pic = slide.shapes.add_picture(str(path), l, t, width=w)
        line(pic, C.line, 1)
        return pic

    with Image.open(path) as img:
        img_w, img_h = img.size

    box_ratio = float(w) / float(h)
    img_ratio = img_w / img_h
    if img_ratio > box_ratio:
        final_w = w
        final_h = int(w / img_ratio)
    else:
        final_h = h
        final_w = int(h * img_ratio)
    final_l = l + int((w - final_w) / 2)
    final_t = t + int((h - final_h) / 2)
    pic = slide.shapes.add_picture(str(path), final_l, final_t, width=final_w, height=final_h)
    line(pic, C.line, 0.8)
    return pic


def arrow(slide, x1, y1, x2, y2, color=C.cobalt):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, y1, x2, y2)
    line(c, color, 2)
    return c


def slide_cover(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg(s, C.night)
    rect(s, Inches(0), Inches(0), Inches(5.0), H, C.cobalt)
    rect(s, Inches(0), Inches(5.65), W, Inches(1.85), C.lime)
    text(s, Inches(0.7), Inches(0.65), Inches(3.5), Inches(0.35), "EPOCH8 / KOROVAS", size=9, bold=True, color=C.lime)
    text(s, Inches(0.7), Inches(1.4), Inches(4.0), Inches(2.7), "Передача\nсопровождения\nсистемы", size=36, bold=True, color=C.white)
    text(
        s,
        Inches(0.7),
        Inches(4.45),
        Inches(3.9),
        Inches(0.7),
        "Программа обучения для full-stack и ML-инженера",
        size=13,
        color=RGBColor(0xD8, 0xDE, 0xFF),
    )
    text(s, Inches(5.55), Inches(0.9), Inches(6.6), Inches(0.45), "data-collector · datapipe · CVAT · инференс · эксплуатация", size=13, color=RGBColor(0xB7, 0xC0, 0xD0))
    add_image_fit(s, IMG / "Flutter_en" / "1.jpg", Inches(5.65), Inches(1.75), Inches(1.9), Inches(3.25), bg_fill=C.night_2)
    add_image_fit(s, IMG / "UI_en" / "1.png", Inches(7.85), Inches(1.75), Inches(2.1), Inches(3.25), bg_fill=C.night_2)
    add_image_fit(s, IMG / "Config_en" / "1.png", Inches(10.25), Inches(1.75), Inches(2.1), Inches(3.25), bg_fill=C.night_2)
    text(s, Inches(0.7), Inches(6.18), Inches(5.5), Inches(0.45), "300 ч · 15 недель · 2 роли · учебный стенд", size=18, bold=True, color=C.ink)
    footer(s, 1, dark=True)


def slide_system(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg(s)
    title(s, "Из чего состоит система", "И почему обучение строится вокруг пути одного пакета")
    cards = [
        ("data-collector", "мобильная съёмка, загрузка пакетов, админка, визуализация", C.cobalt),
        ("datapipe", "пайплайны обработки, CVAT, инференс, метрики", C.mint),
        ("слой Korovas", "бонитировка КРС, правила съёмки, экспертная оценка", C.coral),
    ]
    x = Inches(0.75)
    for head, body, color in cards:
        card(s, x, Inches(2.05), Inches(3.7), Inches(1.35), head, body, color)
        x += Inches(4.05)

    stages = [
        ("01", "Съёмка", "приложение", C.cobalt),
        ("02", "Загрузка", "пакет", C.coral),
        ("03", "Пайплайн", "datapipe", C.mint),
        ("04", "Просмотр", "визуализация и измерения", C.lime),
        ("05", "Протокол", "Монолит и внешние сервисы", C.coral),
    ]
    x = Inches(0.75)
    y = Inches(4.55)
    w = Inches(2.25)
    for i, (num, head, body, color) in enumerate(stages):
        rect(s, x, y, w, Inches(1.25), C.white, C.line, radius=True)
        pill(s, x + Inches(0.18), y + Inches(0.18), Inches(0.62), num, color, C.ink if color == C.lime else C.white)
        text(s, x + Inches(0.18), y + Inches(0.62), w - Inches(0.36), Inches(0.28), head, size=14, bold=True)
        text(s, x + Inches(0.18), y + Inches(0.9), w - Inches(0.36), Inches(0.3), body, size=7, color=C.muted)
        if i < len(stages) - 1:
            arrow(s, x + w, y + Inches(0.62), x + w + Inches(0.33), y + Inches(0.62), C.ink)
        x += w + Inches(0.38)
    footer(s, 2)


def slide_outcome(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg(s, C.night)
    title(s, "Финальный результат", "Что должна уметь команда после 15 недель", dark=True)
    outcomes = [
        ("01", "Провести пакет end-to-end", "От съёмки коровы до визуализации инференса в админке."),
        ("02", "Диагностировать сбой", "Загрузка, хранилище, datapipe, CVAT, пустая визуализация."),
        ("03", "Оценить качество ML", "Сравнить модель, GT и экспертную оценку по метрикам."),
        ("04", "Перенести подход", "Повторить сценарий на смежной предметной области, например баранах."),
    ]
    y = Inches(1.95)
    for num, head, body in outcomes:
        text(s, Inches(0.8), y, Inches(0.7), Inches(0.42), num, size=18, bold=True, color=C.lime)
        text(s, Inches(1.65), y, Inches(4.3), Inches(0.35), head, size=15, bold=True, color=C.white)
        text(s, Inches(1.65), y + Inches(0.38), Inches(5.5), Inches(0.35), body, size=10, color=RGBColor(0xAE, 0xB7, 0xC7))
        rect(s, Inches(0.8), y + Inches(0.88), Inches(5.5), Pt(1), RGBColor(0x2B, 0x34, 0x45))
        y += Inches(1.15)
    add_image_fit(s, IMG / "UI_en" / "5.png", Inches(7.35), Inches(1.65), Inches(5.0), Inches(4.45), bg_fill=C.night_2)
    footer(s, 3, dark=True)


def slide_program(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg(s)
    title(s, "15 недель как три этапа", "Внутри остаются 8 блоков roadmap, но маршрут для запуска проще")
    acts = [
        ("I", "Войти в систему", "нед. 1–4", "Предметная область, инженерная база, архитектура, первый E2E на стенде.", C.cobalt),
        ("II", "Разойтись по ролям", "нед. 5–7", "Full-stack работает с загрузкой и визуализацией, ML — с пайплайном, CVAT и метриками.", C.mint),
        ("III", "Принять сопровождение", "нед. 8–15", "Инциденты, production-практика, аттестация, перенос на новую предметку.", C.coral),
    ]
    x = Inches(0.75)
    for num, head, weeks, body, color in acts:
        rect(s, x, Inches(2.1), Inches(3.75), Inches(3.8), C.white, C.line, radius=True)
        oval(s, x + Inches(0.25), Inches(2.4), Inches(0.58), Inches(0.58), color)
        text(s, x + Inches(0.25), Inches(2.52), Inches(0.58), Inches(0.25), num, size=14, bold=True, color=C.white, align=PP_ALIGN.CENTER)
        text(s, x + Inches(0.25), Inches(3.15), Inches(3.1), Inches(0.5), head, size=22, bold=True)
        text(s, x + Inches(0.25), Inches(3.85), Inches(3.1), Inches(0.3), weeks, size=12, bold=True, color=C.muted)
        text(s, x + Inches(0.25), Inches(4.45), Inches(3.15), Inches(1.0), body, size=11, color=C.muted)
        x += Inches(4.05)
    footer(s, 4)


def slide_learning_process(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg(s)
    title(s, "Из чего состоит учебный процесс", "Один модуль повторяет понятный цикл")
    steps = [
        ("01", "Контекст", "короткое видео или вводный разбор"),
        ("02", "Демо", "показываем рабочий сценарий на стенде"),
        ("03", "Практика", "участник повторяет сценарий сам"),
        ("04", "Поломка", "разбор заранее подготовленного сбоя"),
        ("05", "Артефакт", "PR, отчёт, ноутбук или runbook"),
        ("06", "Ревью", "обратная связь и приёмка результата"),
    ]
    x = Inches(0.75)
    y = Inches(2.1)
    w = Inches(3.7)
    for i, (num, head, body) in enumerate(steps):
        col = i % 3
        row = i // 3
        sx = x + col * Inches(4.05)
        sy = y + row * Inches(1.65)
        color = [C.cobalt, C.mint, C.coral][col]
        rect(s, sx, sy, w, Inches(1.25), C.white, C.line, radius=True)
        pill(s, sx + Inches(0.22), sy + Inches(0.2), Inches(0.62), num, color, C.white)
        text(s, sx + Inches(1.0), sy + Inches(0.18), Inches(2.35), Inches(0.28), head, size=14, bold=True)
        text(s, sx + Inches(1.0), sy + Inches(0.55), Inches(2.35), Inches(0.5), body, size=9, color=C.muted)
    text(s, Inches(0.9), Inches(5.8), Inches(11.3), Inches(0.5), "Так участник не просто слушает материал, а каждый раз проходит мини-цикл сопровождения.", size=15, bold=True, color=C.cobalt, align=PP_ALIGN.CENTER)
    footer(s, 5)


def slide_practice_base(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg(s)
    title(s, "Практическая база и специфика", "Готовим демо-примеры, локальные стенды и поломанные кейсы")
    left_items = [
        ("korovas-training", "обучение через datapipe: формирование выборок, оценка метрик и анализ ошибок", C.mint),
        ("korovas-broken", "набор намеренно сломанных кейсов: загрузка, datapipe, визуализация, хранилище", C.coral),
        ("ноутбуки и отчёты", "демо-примеры для метрик, сравнения модели и эксперта, анализа ошибок", C.cobalt),
        ("локальные стенды", "шаблоны конфигураций для локального развёртывания БД, S3 и других сервисов", C.lime),
    ]
    y = Inches(2.0)
    for head, body, color in left_items:
        card(s, Inches(0.7), y, Inches(5.75), Inches(0.86), head, body, color)
        y += Inches(0.98)
    add_image_fit(s, IMG / "packege_list_slide_2.png", Inches(6.85), Inches(1.95), Inches(5.65), Inches(4.45))
    footer(s, 6)


def slide_final_roadmap(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg(s)
    rect(s, Inches(0), Inches(0), W, Inches(1.25), C.night)
    text(s, Inches(0.75), Inches(0.38), Inches(9.0), Inches(0.5), "Финальный roadmap подготовки", size=28, bold=True, color=C.white)
    items = [
        ("01", "Собрать учебные данные", "korovas-training, korovas-broken, примеры для CVAT и инференса"),
        ("02", "Подготовить конфигурации", "шаблоны для локального развёртывания БД, S3, data-collector и datapipe"),
        ("03", "Подготовить стартовые материалы", "микровидео, инструкции, чек-листы, шаблоны техотчётов"),
        ("04", "Описать практикумы", "E2E, загрузка, визуализация, пайплайн, CVAT, метрики, инциденты"),
        ("05", "Подготовить задания по ролям", "full-stack и ML-инженер, критерии ревью и приёмки"),
        ("06", "Запустить неделю 1", "демо полного сценария на коровах и первый разбор пути пакета"),
    ]
    y = Inches(1.75)
    for num, head, body in items:
        text(s, Inches(0.9), y, Inches(0.65), Inches(0.35), num, size=13, bold=True, color=C.cobalt)
        text(s, Inches(1.65), y, Inches(3.8), Inches(0.35), head, size=16, bold=True, color=C.ink)
        text(s, Inches(5.65), y + Inches(0.03), Inches(6.7), Inches(0.32), body, size=10, color=C.muted)
        rect(s, Inches(1.65), y + Inches(0.5), Inches(10.7), Pt(1), C.line)
        y += Inches(0.72)
    footer(s, 7)


def build() -> Path:
    prs = new_deck()
    slide_cover(prs)
    slide_system(prs)
    slide_outcome(prs)
    slide_program(prs)
    slide_learning_process(prs)
    slide_practice_base(prs)
    slide_final_roadmap(prs)
    prs.save(OUT)
    return OUT


if __name__ == "__main__":
    print(f"Saved: {build()}")
