"""
Экспертная презентация СТП КалмГУ для технологической сессии «АПК».

Запуск:
    python docs/business/generate_stp_session_presentation.py

Результат:
    docs/business/STP-Expert-Session-2026-11.pptx
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
IMG = Path(r"c:\Users\admin\Desktop\epoch8\publication korovas\habr\01-zadacha-i-kontur\img")
BRAND = REPO / "assets" / "brand"
OUT = ROOT / "STP-Expert-Session-2026-11.pptx"

W = Inches(13.333)
H = Inches(7.5)
HEAD = "Georgia"
BODY = "Calibri"
TOTAL = 16


class C:
    paper = RGBColor(0xFF, 0xFF, 0xFF)
    ink = RGBColor(0x1C, 0x1A, 0x17)
    muted = RGBColor(0x5E, 0x58, 0x50)
    faint = RGBColor(0x9A, 0x93, 0x89)
    rule = RGBColor(0xE3, 0xDD, 0xD4)
    blue = RGBColor(0x1F, 0x4E, 0x89)
    soft = RGBColor(0xF6, 0xF3, 0xEE)


def px(inches: float, dpi: int = 140) -> int:
    return max(1, int(round(inches * dpi)))


def new_deck() -> Presentation:
    prs = Presentation()
    prs.slide_width = W
    prs.slide_height = H
    prs.core_properties.title = "СТП КалмГУ. Агробиотех в степях Калмыкии"
    prs.core_properties.subject = "Экспертное рассмотрение, технологическая сессия АПК, Приоритет-2030"
    prs.core_properties.author = "Калмыцкий государственный университет им. Б. Б. Городовикова"
    return prs


def blank(prs: Presentation):
    return prs.slides.add_slide(prs.slide_layouts[6])


def solid(shape, color: RGBColor) -> None:
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    shape.shadow.inherit = False


def rect(slide, l, t, w, h, fill: RGBColor):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, l, t, w, h)
    solid(shape, fill)
    return shape


def bg(slide, color: RGBColor = C.paper) -> None:
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def text(
    slide,
    l,
    t,
    w,
    h,
    value: str,
    *,
    size=16,
    bold=False,
    italic=False,
    font=BODY,
    color: RGBColor | None = None,
    align=PP_ALIGN.LEFT,
    anchor=MSO_ANCHOR.TOP,
    spacing=1.0,
):
    box = slide.shapes.add_textbox(l, t, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    tf.vertical_anchor = anchor
    tf.margin_left = Emu(0)
    tf.margin_right = Emu(0)
    tf.margin_top = Emu(0)
    tf.margin_bottom = Emu(0)
    for i, line in enumerate(str(value).split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_before = Pt(0)
        p.space_after = Pt(0)
        p.line_spacing = spacing
        run = p.add_run()
        run.text = line
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.italic = italic
        run.font.name = font
        run.font.color.rgb = color or C.ink
        rpr = run._r.get_or_add_rPr()
        for tag in ("latin", "cs", "ea"):
            node = rpr.find(qn(f"a:{tag}"))
            if node is None:
                node = rpr.makeelement(qn(f"a:{tag}"), {})
                rpr.append(node)
            node.set("typeface", font)
    return box


def notes(slide, value: str) -> None:
    slide.notes_slide.notes_text_frame.text = value


def hairline(slide, l, t, w, color: RGBColor = C.rule) -> None:
    rect(slide, l, t, w, Inches(0.01), color)


def vline(slide, l, t, h, color: RGBColor = C.rule) -> None:
    rect(slide, l, t, Inches(0.012), h, color)


def page(slide, n: int, section: str) -> None:
    text(slide, Inches(0.62), Inches(0.32), Inches(8.5), Inches(0.28), section, size=13, color=C.blue)
    text(
        slide,
        Inches(11.15),
        Inches(0.3),
        Inches(1.5),
        Inches(0.28),
        f"{n:02d}",
        size=13,
        font=HEAD,
        color=C.faint,
        align=PP_ALIGN.RIGHT,
    )


def title(slide, value: str, y=0.68, size=32, width=12.0) -> None:
    text(slide, Inches(0.62), Inches(y), Inches(width), Inches(0.7), value, size=size, bold=True, font=HEAD, color=C.ink)


_STREAMS: list[BytesIO] = []


def _cover(im: Image.Image, tw: int, th: int, focus: str) -> Image.Image:
    im = im.convert("RGB")
    scale = max(tw / im.width, th / im.height)
    nw, nh = max(1, round(im.width * scale)), max(1, round(im.height * scale))
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    left = 0 if focus == "left" else (nw - tw if focus == "right" else (nw - tw) // 2)
    top = max(0, (nh - th) // 2)
    return im.crop((left, top, left + tw, top + th))


def _contain(im: Image.Image, tw: int, th: int) -> Image.Image:
    im = im.convert("RGB")
    scale = min(tw / im.width, th / im.height)
    nw, nh = max(1, round(im.width * scale)), max(1, round(im.height * scale))
    resized = im.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (tw, th), (255, 255, 255))
    canvas.paste(resized, ((tw - nw) // 2, (th - nh) // 2))
    return canvas


def picture(slide, path: Path, l, t, w, h, *, mode: str = "cover", focus: str = "center"):
    im = Image.open(path)
    tw, th = px(w / 914400), px(h / 914400)
    framed = _contain(im, tw, th) if mode == "contain" else _cover(im, tw, th, focus)
    buf = BytesIO()
    framed.save(buf, format="PNG")
    buf.seek(0)
    _STREAMS.append(buf)
    return slide.shapes.add_picture(buf, l, t, width=w, height=h)


def logo(slide, l, t, size) -> None:
    im = Image.open(BRAND / "kalmgu-icon-1024.png").convert("RGBA")
    side = px(size / 914400, 180)
    im = im.resize((side, side), Image.Resampling.LANCZOS)
    buf = BytesIO()
    im.save(buf, format="PNG")
    buf.seek(0)
    _STREAMS.append(buf)
    slide.shapes.add_picture(buf, l, t, width=size, height=size)


def slide_cover(prs: Presentation) -> None:
    s = blank(prs)
    bg(s)
    picture(s, IMG / "promery-na-profile.jpg", Inches(6.15), 0, Inches(7.19), H, focus="left")
    logo(s, Inches(0.58), Inches(0.42), Inches(0.78))
    text(s, Inches(0.58), Inches(1.38), Inches(5.2), Inches(0.7), "Калмыцкий государственный\nуниверситет им. Б. Б. Городовикова", size=14, color=C.muted, spacing=1.05)
    text(s, Inches(0.56), Inches(2.45), Inches(5.3), Inches(1.7), "Агробиотех\nв степях\nКалмыкии", size=36, bold=True, font=HEAD, spacing=0.92)
    text(s, Inches(0.58), Inches(4.85), Inches(5.15), Inches(0.85), "Агросервисный центр мирового уровня\nв мясном животноводстве", size=16, italic=True, font=HEAD, color=C.ink, spacing=1.05)
    hairline(s, Inches(0.58), Inches(5.9), Inches(1.15), C.blue)
    text(s, Inches(0.58), Inches(6.1), Inches(5.2), Inches(0.85), "26 ноября 2026, РГАУ-МСХА\nЭкспертное рассмотрение\nДокладчик: руководитель СТП. Цифровой проект: А. А. Онтаев", size=13, color=C.muted, spacing=1.08)
    notes(s, "Единица обсуждения: весь СТП. «Электронная бонитировка» - один проект портфеля, имя рабочее.")


def slide_goal(prs: Presentation) -> None:
    s = blank(prs)
    bg(s)
    page(s, 2, "Цель")
    title(s, "Осмотр вместо ленты и бланка")
    text(
        s,
        Inches(0.62),
        Inches(1.55),
        Inches(12.0),
        Inches(1.05),
        "По фотографиям заданных ракурсов система получает промеры\nв сантиметрах и баллы статей экстерьера.",
        size=22,
        italic=True,
        font=HEAD,
        spacing=1.02,
    )

    cols = [
        ("Задача", "Нет национальной системы оценки экстерьера мясного КРС и МРС."),
        ("Продукт", "Карточка животного: длины, высоты, оценка веса и баллы статей. Съёмка с телефона, проверку делает специалист."),
        ("Кому", "Владелец племенного животного, орган управления АПК, научная организация."),
    ]
    for i, (head, body) in enumerate(cols):
        x = 0.62 + i * 4.15
        if i:
            vline(s, Inches(x - 0.22), Inches(2.9), Inches(2.15))
        text(s, Inches(x), Inches(2.85), Inches(3.7), Inches(0.4), head, size=20, bold=True, font=HEAD)
        text(s, Inches(x), Inches(3.35), Inches(3.7), Inches(1.55), body, size=15, color=C.muted, spacing=1.05)

    hairline(s, Inches(0.62), Inches(5.25), Inches(12.05))
    marks = [
        ("2025", "прототип", True),
        ("2026", "приложение", True),
        ("I кв. 2027", "эксплуатация", False),
        ("2027", "20 хозяйств", False),
        ("2027-2028", "реестры", False),
    ]
    hairline(s, Inches(0.9), Inches(6.28), Inches(11.5), C.rule)
    for i, (year, name, done) in enumerate(marks):
        x = 1.15 + i * 2.35
        rect(s, Inches(x), Inches(6.22), Inches(0.14), Inches(0.14), C.blue if done else C.faint)
        text(s, Inches(x - 0.85), Inches(5.45), Inches(1.9), Inches(0.55), year, size=14, bold=done, font=HEAD, align=PP_ALIGN.CENTER, color=C.ink if done else C.muted)
        text(s, Inches(x - 0.85), Inches(6.5), Inches(1.9), Inches(0.4), name, size=13, color=C.muted, align=PP_ALIGN.CENTER)
    notes(s, "Синие точки: задел на 01.10.2026. Серые: план, не факт эксплуатации. Если цель центра шире цифрового проекта, назвать её по паспорту СТП.")


def slide_architecture(prs: Presentation) -> None:
    s = blank(prs)
    bg(s)
    page(s, 3, "Архитектура")
    title(s, "От карточки животного к реестру")
    text(s, Inches(0.62), Inches(1.48), Inches(12), Inches(0.4), "Осмотр, проверка человеком, региональный учёт, федеральный реестр.", size=16, italic=True, font=HEAD, color=C.muted)

    steps = [
        ("1", "Протокол", "сценарий съёмки"),
        ("2", "Поле", "телефон, без сети"),
        ("3", "Пакет", "анкета и фото"),
        ("4", "Расчёт", "промеры и баллы"),
        ("5", "Сверка", "специалист"),
        ("6", "Реестр", "план 2027-2028"),
    ]
    hairline(s, Inches(1.05), Inches(2.42), Inches(11.1))
    for i, (num, name, sub) in enumerate(steps):
        x = 0.62 + i * 2.08
        rect(s, Inches(x + 0.15), Inches(2.22), Inches(0.55), Inches(0.4), C.paper)
        text(s, Inches(x), Inches(2.12), Inches(1.7), Inches(0.45), num, size=22, font=HEAD, color=C.blue, align=PP_ALIGN.CENTER)
        text(s, Inches(x), Inches(2.62), Inches(1.85), Inches(0.32), name, size=16, bold=True, align=PP_ALIGN.CENTER)
        text(s, Inches(x), Inches(2.94), Inches(1.85), Inches(0.4), sub, size=13, color=C.muted, align=PP_ALIGN.CENTER)

    notes_row = [
        ("Съёмка задаёт промер.", "Одно животное целиком, заданный ракурс, свет и данные камеры в файле."),
        ("Фото не даёт класс.", "Происхождение, продуктивность и потомство берутся из учёта."),
        ("Реестр в плане.", "АИС «Монолит» и ФГИАС ПР ещё не подключены."),
    ]
    for i, (head, body) in enumerate(notes_row):
        x = 0.62 + i * 4.15
        text(s, Inches(x), Inches(3.6), Inches(3.85), Inches(0.35), head, size=16, bold=True, font=HEAD)
        text(s, Inches(x), Inches(4.0), Inches(3.85), Inches(0.75), body, size=14, color=C.muted, spacing=1.02)

    text(s, Inches(0.62), Inches(4.9), Inches(10), Inches(0.3), "Портфель СТП", size=13, italic=True, font=HEAD, color=C.muted)
    headers = ["Проект", "Что отдаёт центру", "Где сейчас"]
    widths = [4.3, 4.5, 3.25]
    x = 0.62
    for head, w in zip(headers, widths):
        text(s, Inches(x), Inches(5.3), Inches(w), Inches(0.28), head, size=12, color=C.faint)
        x += w
    hairline(s, Inches(0.62), Inches(5.62), Inches(12.05))
    rows = [
        ("Электронная бонитировка", "карточка осмотра", "собрано"),
        ("АИС «Монолит»", "класс, индексы, отчёт", "план, 2027"),
        ("ФГИАС ПР", "федеральная выгрузка", "план, 2027-2028"),
        ("Проекты паспорта СТП", "общий результат центра", "по программе"),
    ]
    y = 5.72
    for a, b, c in rows:
        vals = [a, b, c]
        x = 0.62
        for val, w in zip(vals, widths):
            text(s, Inches(x), Inches(y), Inches(w - 0.2), Inches(0.32), val, size=14, color=C.ink)
            x += w
        y += 0.34
    notes(s, "Руководитель СТП называет остальные проекты паспорта и их вклад в общий результат.")


def slide_results(prs: Presentation) -> None:
    s = blank(prs)
    bg(s)
    page(s, 4, "Результаты")
    title(s, "Достигнутые результаты")
    text(s, Inches(0.62), Inches(1.48), Inches(12), Inches(0.4), "Сквозной путь собран. Эксплуатация и реестры в плане.", size=18, italic=True, font=HEAD)

    headers = ["", "Уже есть", "Ещё план"]
    widths = [2.5, 4.9, 4.65]
    x = 0.62
    for head, w in zip(headers, widths):
        text(s, Inches(x), Inches(2.15), Inches(w), Inches(0.32), head, size=14, italic=True, font=HEAD, color=C.blue)
        x += w
    hairline(s, Inches(0.62), Inches(2.52), Inches(12.05), C.ink)

    rows = [
        ("Прототип", "Получен в 2025 году", "нет"),
        ("Приложение", "Съёмка, пакет, карточка осмотра", "Регистрация ПО до конца 2026"),
        ("Расчёт", "Промеры и баллы трёх шкал", "нет"),
        ("УГТ", "УГТ 6 заявлено на 01.10.2026", "Протокол показа"),
        ("Эксплуатация", "Прототип, без эксплуатации", "До 31 марта 2027"),
        ("Тираж", "нет", "20 хозяйств и 2 000 голов в 2027"),
        ("Реестры", "Канала нет", "«Монолит» в 2027, ФГИАС в 2027-2028"),
    ]
    y = 2.68
    for cells in rows:
        x = 0.62
        for val, w in zip(cells, widths):
            text(
                s,
                Inches(x),
                Inches(y),
                Inches(w - 0.25),
                Inches(0.4),
                val,
                size=15,
                bold=(w == widths[0]),
                color=C.faint if val == "нет" else C.ink,
            )
            x += w
        hairline(s, Inches(0.62), Inches(y + 0.42), Inches(12.05))
        y += 0.58
    notes(s, "Процент точности не называть. Локализация по формулировке университета: открытый код, для стенда есть отечественные аналоги, сопровождение готовят студенты и наставники.")


def slide_partners(prs: Presentation) -> None:
    s = blank(prs)
    bg(s)
    page(s, 5, "Кооперация")
    title(s, "Кто за что отвечает")
    vline(s, Inches(6.66), Inches(1.6), Inches(4.15))
    hairline(s, Inches(0.62), Inches(3.85), Inches(12.05))

    cells = [
        (0.62, 1.6, "КалмГУ", "Заказчик продукта", "Цель центра, методика бонитировки, регистрация программы и пилот в хозяйствах."),
        (6.95, 1.6, "А. А. Онтаев", "Цифровой проект", "Протокол, три шкалы, порода, вес по фото, приёмка сценария съёмки."),
        (0.62, 4.1, "Партнёр", "Компьютерное зрение", "Мобильный сбор, обработка данных, промеры, баллы статей, подготовка команды сопровождения."),
        (6.95, 4.1, "Хозяйства", "Площадка и реестры", "Животные и обратная связь. Приём записи: АИС «Монолит» и ФГИАС ПР."),
    ]
    for x, y, name, role, body in cells:
        text(s, Inches(x), Inches(y), Inches(5.3), Inches(0.45), name, size=26, font=HEAD)
        text(s, Inches(x), Inches(y + 0.48), Inches(5.3), Inches(0.32), role, size=14, italic=True, font=HEAD, color=C.blue)
        text(s, Inches(x), Inches(y + 0.88), Inches(5.3), Inches(0.9), body, size=15, color=C.muted, spacing=1.02)
    text(
        s,
        Inches(0.62),
        Inches(6.55),
        Inches(12.0),
        Inches(0.5),
        "Соглашения с хозяйствами и оператором реестра готовятся к пилоту 2027 года.",
        size=14,
        italic=True,
        font=HEAD,
        color=C.muted,
    )
    notes(s, "Партнёра назвать по согласованной формулировке: Epoch8 или «партнёр контура компьютерного зрения». Численность смены сопровождения не названа.")


def slide_adoption(prs: Presentation) -> None:
    s = blank(prs)
    bg(s)
    page(s, 6, "Применение")
    title(s, "Потребители результата")
    people = [
        ("Хозяйство", "Владелец получает промеры и баллы без ручного обмера."),
        ("Орган АПК", "Актуальный ряд промеров и баллов вместо архива бланков."),
        ("Исследование", "100-150 голов проходят первичный отбор сразу. Анализы назначают прошедшим его."),
    ]
    for i, (name, body) in enumerate(people):
        x = 0.62 + i * 4.15
        text(s, Inches(x), Inches(1.7), Inches(3.85), Inches(0.55), name, size=28, font=HEAD)
        text(s, Inches(x), Inches(2.4), Inches(3.85), Inches(1.3), body, size=16, color=C.muted, spacing=1.05)
    hairline(s, Inches(0.62), Inches(4.05), Inches(12.05))
    text(s, Inches(0.62), Inches(4.35), Inches(3), Inches(0.3), "Условия пилота", size=14, italic=True, font=HEAD, color=C.blue)
    text(
        s,
        Inches(0.62),
        Inches(4.8),
        Inches(12.0),
        Inches(1.7),
        "Съёмка по протоколу: животное целиком, заданный ракурс, одно в кадре. В анкете указаны пол, возраст, порода и номер. Специалист проверяет результат. Хозяйство допускает съёмку. Старт: I квартал 2027 года.",
        size=20,
        font=HEAD,
        spacing=1.08,
    )
    notes(s, "Пример 100-150 голов взят из наброска 01.10.2026. Это схема отбора, не измеренная экономия. План тиража: не менее 20 хозяйств и 2000 голов.")


def slide_gaps(prs: Presentation) -> None:
    s = blank(prs)
    bg(s)
    page(s, 7, "Разрывы")
    title(s, "Ограничения")
    items = [
        ("01", "Реестр не подключён", "Сначала согласуется состав выгрузки в «Монолит» и ФГИАС ПР."),
        ("02", "Фото не даёт класс", "Комплексная бонитировка остаётся в учёте. Осмотр и класс считаются раздельно."),
        ("03", "Точность не закрыта", "Экспертные оценки собраны на высоких баллах. Процент по всей шкале пока не приводится."),
        ("04", "Кадр задаёт промер", "Второе животное, обрез и файл без данных камеры в расчёт не входят."),
        ("05", "Сейчас только КРС", "МРС, лошади и верблюды требуют отдельных шкал и сроков."),
        ("06", "Портфель шире проекта", "Здесь представлен цифровой проект. Полный состав задан паспортом СТП."),
    ]
    for i, (num, head, body) in enumerate(items):
        col = i % 2
        row = i // 2
        x = 0.62 + col * 6.35
        y = 1.6 + row * 1.7
        text(s, Inches(x), Inches(y), Inches(0.7), Inches(0.4), num, size=18, font=HEAD, color=C.blue)
        text(s, Inches(x + 0.85), Inches(y), Inches(5.2), Inches(0.4), head, size=18, font=HEAD)
        text(s, Inches(x + 0.85), Inches(y + 0.48), Inches(5.2), Inches(0.9), body, size=15, color=C.muted, spacing=1.02)
    notes(s, "Индикаторы «Приоритет-2030» сверять с картой СТП. Если отклонений нет, сказать об этом со ссылкой на отчёт.")


def slide_next(prs: Presentation) -> None:
    s = blank(prs)
    bg(s)
    page(s, 8, "План")
    title(s, "Ближайшие шаги", width=6.2)
    steps = [
        ("До конца 2026", "Регистрация программы и протокол показа"),
        ("I квартал 2027", "Эксплуатация по мясному КРС"),
        ("2027", "20 хозяйств, МРС, стыковка с «Монолит»"),
        ("2027-2028", "Выгрузка во ФГИАС ПР"),
        ("2028", "Лошади и верблюды, отдельные протоколы"),
    ]
    y = 1.65
    for when, what in steps:
        text(s, Inches(0.62), Inches(y), Inches(2.15), Inches(0.55), when, size=14, italic=True, font=HEAD, color=C.blue)
        text(s, Inches(2.85), Inches(y), Inches(3.7), Inches(0.55), what, size=16)
        y += 0.85
    vline(s, Inches(7.15), Inches(1.65), Inches(4.7), C.blue)
    text(s, Inches(7.5), Inches(1.6), Inches(5.2), Inches(0.3), "Вопросы на обсуждение", size=14, italic=True, font=HEAD, color=C.blue)
    text(s, Inches(7.5), Inches(2.15), Inches(5.2), Inches(1.8), "Какой документ нужен, чтобы перевести прототип в пилот племенного учёта?", size=24, font=HEAD, spacing=1.02)
    text(s, Inches(7.5), Inches(4.3), Inches(5.2), Inches(1.9), "Автоматический балл остаётся рекомендацией специалисту или входит в племенную запись?", size=24, font=HEAD, spacing=1.02)
    notes(s, "Ресурсы 2027: доступ в хозяйства, эксперт-бонитёр, формат «Монолит», смена сопровождения.")


def slide_divider(prs: Presentation) -> None:
    s = blank(prs)
    bg(s)
    picture(s, IMG / "promery-na-profile.jpg", 0, 0, Inches(6.35), H, focus="left")
    text(s, Inches(6.85), Inches(1.7), Inches(5.8), Inches(0.3), "Цифровой проект", size=14, italic=True, font=HEAD, color=C.blue)
    text(s, Inches(6.82), Inches(2.2), Inches(5.9), Inches(1.8), "Электронная\nбонитировка", size=40, bold=True, font=HEAD, spacing=0.95)
    text(s, Inches(6.85), Inches(4.3), Inches(5.7), Inches(1.2), "Мобильный осмотр крупного рогатого скота.\nПромеры в сантиметрах и баллы статей экстерьера.", size=16, color=C.muted, spacing=1.08)
    text(s, Inches(6.85), Inches(6.7), Inches(4.5), Inches(0.3), "Рабочее название", size=13, color=C.faint)
    text(s, Inches(11.15), Inches(6.7), Inches(1.5), Inches(0.3), "09", size=13, font=HEAD, color=C.faint, align=PP_ALIGN.RIGHT)
    notes(s, "Раздел про цифровой проект. В пятиминутный доклад его не включать, открывать по вопросу.")


def slide_product(prs: Presentation) -> None:
    s = blank(prs)
    bg(s)
    page(s, 10, "Приложение")
    text(s, Inches(0.6), Inches(0.68), Inches(6.0), Inches(1.35), "Мобильное\nприложение осмотра", size=32, bold=True, font=HEAD, spacing=0.95)
    text(
        s,
        Inches(0.62),
        Inches(2.15),
        Inches(5.9),
        Inches(1.15),
        "Оператор выбирает хозяйство, заполняет карточку и снимает заданные ракурсы: профиль, перед и зад, вид сверху.",
        size=16,
        color=C.muted,
        spacing=1.05,
    )
    text(s, Inches(0.62), Inches(3.5), Inches(5.9), Inches(0.32), "Входит в результат", size=14, italic=True, font=HEAD, color=C.blue)
    text(s, Inches(0.62), Inches(3.88), Inches(5.9), Inches(0.85), "Промеры и статьи, которые видны на животном. Пакет хранится в телефоне до появления сети.", size=16, color=C.ink, spacing=1.02)
    text(s, Inches(0.62), Inches(4.9), Inches(5.9), Inches(0.32), "Остаётся в учёте", size=14, italic=True, font=HEAD, color=C.blue)
    text(s, Inches(0.62), Inches(5.28), Inches(5.9), Inches(1.15), "Происхождение, продуктивность, потомство и комплексный индекс. Эти сведения ведутся в учётной системе.", size=16, color=C.ink, spacing=1.02)
    picture(s, IMG / "app-three-steps.png", Inches(6.85), Inches(1.55), Inches(6.0), Inches(5.3), mode="contain")
    notes(s, "Имя из методики 17.07.2026 длиннее рабочего: программа визуальной оценки параметров КРС. На слайде оставлено рабочее.")


def slide_path(prs: Presentation) -> None:
    s = blank(prs)
    bg(s)
    page(s, 11, "Осмотр")
    title(s, "Порядок одного осмотра")
    steps = [
        ("1", "Сценарий", "поля и слоты\nсъёмки"),
        ("2", "Анкета", "номер, возраст,\nподсказка ракурса"),
        ("3", "Пакет", "фото хранится\nна телефоне"),
        ("4", "Отправка", "очередь уходит\nпри появлении связи"),
        ("5", "Расчёт", "промеры и баллы\nсчитаются отдельно"),
        ("6", "Сверка", "специалист видит\nлинии на фото"),
    ]
    for i, (num, name, body) in enumerate(steps):
        x = 0.62 + i * 2.1
        text(s, Inches(x), Inches(1.55), Inches(1.9), Inches(0.35), num, size=18, font=HEAD, color=C.blue)
        text(s, Inches(x), Inches(1.95), Inches(1.9), Inches(0.35), name, size=16, bold=True)
        text(s, Inches(x), Inches(2.35), Inches(1.9), Inches(0.7), body, size=13, color=C.muted, spacing=1.02)
    picture(s, IMG / "raznye-rakursy.jpg", Inches(0.62), Inches(4.15), Inches(12.05), Inches(2.22), mode="contain")
    text(s, Inches(0.62), Inches(6.5), Inches(12), Inches(0.35), "Четыре ракурса одного животного. Нужный ракурс указан рядом с камерой.", size=14, italic=True, font=HEAD, color=C.muted)
    notes(s, "Полоса внизу: четыре ракурса с рамкой детекции. Подсказка стоит в приложении у камеры.")


def slide_measure(prs: Presentation) -> None:
    s = blank(prs)
    bg(s)
    page(s, 12, "Промеры")
    title(s, "Как считаются промеры", width=12)
    picture(s, IMG / "promery-na-profile.jpg", Inches(0.62), Inches(1.6), Inches(7.15), Inches(5.35), mode="contain")
    bits = [
        ("Камера", "Без параметров камеры кадр в расчёт промеров не берётся."),
        ("21 точка", "Холка, крестец, грудь, маклоки, седалищные бугры и опоры высоты."),
        ("Пол", "Высота считается до плоскости пола."),
        ("Условия", "Одно животное целиком, ракурс по протоколу, достаточный свет."),
    ]
    y = 1.65
    for head, body in bits:
        text(s, Inches(8.05), Inches(y), Inches(4.6), Inches(0.35), head, size=18, font=HEAD)
        text(s, Inches(8.05), Inches(y + 0.4), Inches(4.6), Inches(0.75), body, size=14, color=C.muted, spacing=1.02)
        y += 1.28
    notes(s, "На кадре: высота в холке, высота в крестце, косая длина туловища, глубина груди. Это пример метода, не паспортная погрешность. Вес считается по промерам.")


def slide_scales(prs: Presentation) -> None:
    s = blank(prs)
    bg(s)
    page(s, 13, "Баллы")
    title(s, "Три шкалы баллов")
    text(s, Inches(0.62), Inches(1.5), Inches(12), Inches(0.7), "Категорию задают возраст и пол. Программа отмечает непройденные\nпроверки по статье и по ним ставит балл.", size=18, italic=True, font=HEAD, spacing=1.02)
    scales = [
        ("60", "Молодняк", "Моложе 24 месяцев, любой пол. Пять статей: общий вид, грудь, верх, крестец, окорок."),
        ("100", "Бык", "От 24 месяцев. Девять статей, среди них голова, мошонка и конечности."),
        ("100", "Корова", "От 24 месяцев. Девять статей. Вместо мошонки в шкале вымя."),
    ]
    for i, (score, name, body) in enumerate(scales):
        x = 0.62 + i * 4.15
        if i:
            vline(s, Inches(x - 0.22), Inches(2.5), Inches(2.7))
        text(s, Inches(x), Inches(2.45), Inches(3.7), Inches(0.9), score, size=60, font=HEAD, color=C.blue)
        text(s, Inches(x), Inches(3.5), Inches(3.7), Inches(0.45), name, size=24, font=HEAD)
        text(s, Inches(x), Inches(4.1), Inches(3.7), Inches(1.15), body, size=15, color=C.muted, spacing=1.05)
    hairline(s, Inches(0.62), Inches(5.5), Inches(12.05))
    text(s, Inches(0.62), Inches(5.75), Inches(12.0), Inches(1.1), "Взрослое животное без указанного пола не оценивается. Комплексный класс по фото не вычисляется. Баллы статей при этом выдаются.", size=16, spacing=1.05)
    notes(s, "Порода нужна учёту и статьям «общий вид» и «голова и шея». В методике 17 мясных пород, включая калмыцкую и казахскую белоголовую.")


def slide_status(prs: Presentation) -> None:
    s = blank(prs)
    bg(s)
    page(s, 14, "Готовность")
    title(s, "Состав системы")
    rows = [
        ("готово", "Съёмка по сценарию, очередь без сети, карточка пакета"),
        ("готово", "Промеры на кадрах, снятых по протоколу"),
        ("готово", "Баллы трёх шкал. Для низких баллов пока мало экспертных оценок"),
        ("готово", "Разметка точек и дообучение идут отдельно от осмотра"),
        ("план", "Официальный протокол в АИС «Монолит»"),
        ("план", "ФГИАС ПР, МРС, лошади и верблюды: 2027-2028"),
    ]
    y = 1.65
    for tag, body in rows:
        text(s, Inches(0.62), Inches(y), Inches(1.5), Inches(0.45), tag, size=18, italic=True, font=HEAD, color=C.blue)
        text(s, Inches(2.3), Inches(y), Inches(10.2), Inches(0.45), body, size=18)
        hairline(s, Inches(0.62), Inches(y + 0.58), Inches(12.05))
        y += 0.85
    notes(s, "Осмотр не ждёт дообучения модели. Точность разбирается на следующем слайде.")


def slide_accuracy(prs: Presentation) -> None:
    s = blank(prs)
    bg(s)
    page(s, 15, "Точность")
    title(s, "Оценка точности", size=36)
    text(s, Inches(0.62), Inches(1.6), Inches(11.5), Inches(0.7), "Итоговый процент по всей шкале пока не приводится.", size=20, italic=True, font=HEAD)
    items = [
        ("Кадр", "Промер устойчив при съёмке по протоколу. Долю непригодных кадров измерят на пилоте."),
        ("Балл", "Балл статьи считается по числу непройденных проверок."),
        ("Выборка", "Сравнение с экспертом собрано на молодых быках и высоких баллах. На этих данных процент будет завышен."),
        ("Эксперты", "Согласованность двух экспертов ещё не измерена. До этой цифры потолок точности не задаётся."),
    ]
    y = 2.6
    for head, body in items:
        text(s, Inches(0.62), Inches(y), Inches(1.8), Inches(0.7), head, size=18, font=HEAD, color=C.blue)
        text(s, Inches(2.55), Inches(y), Inches(9.9), Inches(0.75), body, size=18, spacing=1.02)
        y += 1.05
    notes(s, "Не называть внутренние метрики ошибки, стоимость расчётов и даты остановки проверки.")


def slide_demo(prs: Presentation) -> None:
    s = blank(prs)
    bg(s)
    page(s, 16, "Материалы")
    title(s, "Материалы осмотра")
    text(s, Inches(0.62), Inches(1.45), Inches(12), Inches(0.4), "Подсказка ракурса, промеры на кадре, результат в карточке.", size=16, italic=True, font=HEAD, color=C.muted)
    shots = [
        (IMG / "rakursy-v-instrukcii.png", "Подсказка ракурса", "contain"),
        (IMG / "promery-na-profile.jpg", "Промеры на кадре", "contain"),
        (IMG / "admin-view-clean.png", "Карточка в админке", "contain"),
    ]
    for i, (path, caption, mode) in enumerate(shots):
        x = 0.55 + i * 4.2
        picture(s, path, Inches(x), Inches(2.1), Inches(4.0), Inches(4.15), mode=mode)
        text(s, Inches(x), Inches(6.4), Inches(4.0), Inches(0.4), caption, size=14, italic=True, font=HEAD, align=PP_ALIGN.CENTER)
    notes(s, "Демонстрацию открывать с ноутбука, без сетевой ссылки.")


def build() -> Path:
    prs = new_deck()
    slide_cover(prs)
    slide_goal(prs)
    slide_architecture(prs)
    slide_results(prs)
    slide_partners(prs)
    slide_adoption(prs)
    slide_gaps(prs)
    slide_next(prs)
    slide_divider(prs)
    slide_product(prs)
    slide_path(prs)
    slide_measure(prs)
    slide_scales(prs)
    slide_status(prs)
    slide_accuracy(prs)
    slide_demo(prs)
    prs.save(OUT)
    return OUT


if __name__ == "__main__":
    print(build())
