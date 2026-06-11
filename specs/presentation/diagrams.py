"""Minimal vector diagrams for Data Collector presentation."""

from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

BG_DEEP = RGBColor(0x0A, 0x0E, 0x18)
BG_CARD = RGBColor(0x1E, 0x2A, 0x3D)
BG_PANEL = RGBColor(0x14, 0x1A, 0x26)
ACCENT = RGBColor(0x5B, 0x8D, 0xEF)
ACCENT_GREEN = RGBColor(0x3D, 0xCC, 0x85)
ACCENT_GOLD = RGBColor(0xD4, 0xA8, 0x4B)
ACCENT_PURPLE = RGBColor(0x9B, 0x7E, 0xD0)
ACCENT_CYAN = RGBColor(0x8B, 0xC9, 0xF7)
TEXT = RGBColor(0xE8, 0xEA, 0xED)
TEXT_MUTED = RGBColor(0x9C, 0xA3, 0xAF)
BORDER = RGBColor(0x3A, 0x45, 0x58)


def _box(slide, l, t, w, h, fill, line, title, sub="", ts=11, ss=8):
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, l, t, w, h)
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    s.line.color.rgb = line
    s.line.width = Pt(1.5)
    tf = s.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = Pt(8)
    tf.margin_right = Pt(8)
    p0 = tf.paragraphs[0]
    p0.text = title
    p0.font.size = Pt(ts)
    p0.font.bold = True
    p0.font.color.rgb = TEXT
    p0.alignment = PP_ALIGN.CENTER
    if sub:
        p1 = tf.add_paragraph()
        p1.text = sub
        p1.font.size = Pt(ss)
        p1.font.color.rgb = TEXT_MUTED
        p1.alignment = PP_ALIGN.CENTER
        p1.space_before = Pt(3)
    return s


def _arrow_h(slide, x1, y, x2, color=ACCENT, dashed=False):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, y, x2, y)
    c.line.color.rgb = color
    c.line.width = Pt(2)
    if dashed:
        c.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    return c


def _arrow_v(slide, x, y1, y2, color=ACCENT, dashed=False):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x, y1, x, y2)
    c.line.color.rgb = color
    c.line.width = Pt(2)
    if dashed:
        c.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    return c


def _caption(slide, l, t, w, text, color=TEXT_MUTED, size=8):
    box = slide.shapes.add_textbox(l, t, w, Inches(0.22))
    p = box.text_frame.paragraphs[0]
    p.text = text
    p.font.size = Pt(size)
    p.font.color.rgb = color
    p.alignment = PP_ALIGN.CENTER


def _canvas(slide, l, t, w, h):
    outer = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, l, t, w, h)
    outer.fill.solid()
    outer.fill.fore_color.rgb = BG_DEEP
    outer.line.color.rgb = BORDER
    outer.line.width = Pt(1)
    outer.text_frame.clear()
    return outer


# ── Cover: Admin → Server → App + Admin ───────────────────────────────────────

def draw_cover_architecture(slide, l, t, w, h):
    _canvas(slide, l, t, w, h)
    pad = Inches(0.2)
    bw = w - pad * 2
    bh = Inches(0.52)
    gap = Inches(0.38)
    y = t + Inches(0.25)
    cx = l + w / 2

    nodes = [
        ("Staff Admin", "конфиг", RGBColor(0x3D, 0x34, 0x20), ACCENT_GOLD),
        ("Django Server", "API + хранилище", BG_CARD, ACCENT),
        ("Flutter App", "сбор", RGBColor(0x2A, 0x24, 0x38), ACCENT_PURPLE),
        ("Admin UI", "пакеты", RGBColor(0x1A, 0x2E, 0x28), ACCENT_GREEN),
    ]
    for title, sub, fill, line in nodes:
        _box(slide, l + pad, y, bw, bh, fill, line, title, sub, 10, 7)
        y += bh + gap
        if title != nodes[-1][0]:
            _arrow_v(slide, cx, y - gap + Inches(0.02), y - Inches(0.02), line)

    _arrow_h(slide, l + pad + bw * 0.55, t + Inches(0.25) + bh * 2 + gap * 2 + bh * 0.5,
              l + pad + bw * 0.85, ACCENT_PURPLE, dashed=True)


# ── Stack: platform + N projects ────────────────────────────────────────────

def draw_stack_diagram(slide, l, t, w, h):
    _canvas(slide, l, t, w, h)
    pad = Inches(0.16)
    ix, iy = l + pad, t + Inches(0.18)
    iw = w - pad * 2

    row_h = Inches(0.58)
    gap = Inches(0.14)
    cw = (iw - gap * 2) / 3

    clients = [
        ("Flutter", ACCENT_PURPLE),
        ("Staff Admin", ACCENT_GOLD),
        ("Client Admin", ACCENT_GREEN),
    ]
    for i, (name, c) in enumerate(clients):
        _box(slide, ix + i * (cw + gap), iy, cw, row_h, BG_CARD, c, name, "", 10, 7)

    sy = iy + row_h + Inches(0.28)
    _box(slide, ix, sy, iw, row_h, BG_CARD, ACCENT, "django_server", "", 10, 7)
    _arrow_v(slide, ix + iw / 2, iy + row_h, sy, ACCENT)

    dy = sy + row_h + Inches(0.28)
    _box(slide, ix, dy, iw, row_h, RGBColor(0x1A, 0x33, 0x29), ACCENT_GREEN, "DB + медиа", "пакеты всех проектов", 10, 7)
    _arrow_v(slide, ix + iw / 2, sy + row_h, dy, ACCENT_GREEN)

    py = dy + row_h + Inches(0.28)
    ph = t + h - py - Inches(0.14)
    _box(slide, ix, py, iw, ph, RGBColor(0x1E, 0x24, 0x33), ACCENT_CYAN,
         "Проект × N", "Git: config.json · viz.json", 10, 8)
    _arrow_v(slide, ix + iw / 2, dy + row_h, py, ACCENT_CYAN)


# ── 5-step product flow ───────────────────────────────────────────────────────

def draw_five_step_flow(slide, l, t, w, h):
    """Horizontal pipeline: config → sync → collect → upload → view."""
    _canvas(slide, l, t, w, h)
    pad = Inches(0.14)
    ix = l + pad
    iw = w - pad * 2
    n = 5
    gap = Inches(0.12)
    bw = (iw - gap * (n - 1)) / n
    bh = min(Inches(1.05), h - Inches(0.28))
    iy = t + (h - bh) / 2

    steps = [
        ("①", "Конфиг", ACCENT_GOLD),
        ("②", "Синк в МП", ACCENT),
        ("③", "Сбор", ACCENT_PURPLE),
        ("④", "Upload", ACCENT_PURPLE),
        ("⑤", "Админка", ACCENT_GREEN),
    ]
    for i, (num, label, c) in enumerate(steps):
        x = ix + i * (bw + gap)
        _box(slide, x, iy, bw, bh, BG_CARD, c, num, label, 16, 10)
        if i < n - 1:
            _arrow_h(slide, x + bw, iy + bh / 2, x + bw + gap, c)


# ── Config: fields → flow → package ─────────────────────────────────────────

def draw_config_entities(slide, l, t, w, h):
    _canvas(slide, l, t, w, h)
    pad = Inches(0.16)
    ix, iy = l + pad, t + Inches(0.22)
    iw = w - pad * 2
    gap = Inches(0.12)
    bw = (iw - gap * 2) / 3
    bh = Inches(0.72)

    chain = [
        ("fields", "что собираем", ACCENT),
        ("flow", "порядок экранов", ACCENT_PURPLE),
        ("package", "результат", ACCENT_GREEN),
    ]
    cy = iy + bh / 2
    for i, (title, sub, c) in enumerate(chain):
        x = ix + i * (bw + gap)
        _box(slide, x, iy, bw, bh, BG_CARD, c, title, sub, 11, 8)
        if i < 2:
            _arrow_h(slide, x + bw, cy, x + bw + gap, c)

    _caption(slide, ix, iy + bh + Inches(0.12), iw, "JSON в Git → UI в приложении → те же поля в админке")


# ── Package viewing (Step 4) ──────────────────────────────────────────────────

def draw_package_viewing_flow(slide, l, t, w, h):
    """List → open package → workspace tabs."""
    _canvas(slide, l, t, w, h)
    pad = Inches(0.14)
    ix, iy = l + pad, t + Inches(0.2)
    iw = w - pad * 2
    cx = ix + iw / 2

    # 1 List
    lh = Inches(0.68)
    _box(slide, ix + iw * 0.15, iy, iw * 0.7, lh, BG_CARD, ACCENT_GREEN,
         "/ui/packages/", "список принятых пакетов", 11, 8)

    # 2 filters row
    fy = iy + lh + Inches(0.32)
    fw = (iw - Inches(0.2)) / 3
    for i, label in enumerate(["проект", "статус", "поиск"]):
        _box(slide, ix + Inches(0.1) + i * (fw + Inches(0.05)), fy, fw, Inches(0.42),
             BG_PANEL, BORDER, label, "", 9, 7)
    _arrow_v(slide, cx, iy + lh, fy, ACCENT_GREEN)

    # 3 workspace
    wy = fy + Inches(0.58)
    wh = Inches(0.62)
    _box(slide, ix + iw * 0.1, wy, iw * 0.8, wh, RGBColor(0x1A, 0x2E, 0x28), ACCENT_GREEN,
         "Package Workspace", "один пакет · все данные", 11, 8)
    _arrow_v(slide, cx, fy + Inches(0.42), wy, ACCENT_GREEN)

    # 4 tabs
    ty = wy + wh + Inches(0.28)
    tw = (iw - Inches(0.09 * 3)) / 4
    th = t + h - ty - Inches(0.12)
    tabs = [
        ("Данные", ACCENT),
        ("Медиа", ACCENT_PURPLE),
        ("Viz", ACCENT_GREEN),
        ("История", ACCENT_GOLD),
    ]
    for i, (tab, c) in enumerate(tabs):
        _box(slide, ix + i * (tw + Inches(0.09)), ty, tw, th, BG_CARD, c, tab, "", 10, 7)
    _arrow_v(slide, cx, wy + wh, ty, ACCENT_GREEN)


def draw_admin_workspace_mini(slide, l, t, w, h):
    """Compact 4-tab view for step slide sidebar."""
    draw_package_viewing_flow(slide, l, t, w, h)


# Legacy alias for client-server — now same as five step
def draw_client_server_flow(slide, l, t, w, h):
    draw_five_step_flow(slide, l, t, w, h)


def draw_admin_workspace(slide, l, t, w, h):
    draw_package_viewing_flow(slide, l, t, w, h)
