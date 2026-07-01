"""Build STEP 02 GIF — Flutter app flow (login → config → form → upload)."""

import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

TARGET_W = 1110
TARGET_H = 1170
TOP_H = 68
BOTTOM_H = 36
IMG_AREA_H = TARGET_H - TOP_H - BOTTOM_H

BG = (18, 18, 24)
HEADER_BG = (30, 42, 61)
ACCENT = (155, 126, 208)  # STEP 02 purple
BADGE = (155, 126, 208)
TEXT = (232, 234, 237)
TEXT_MUTED = (156, 163, 175)

STAGES_TOTAL = 4

# file, stage_no, headline, optional sub-label (for multi-screen stages)
FRAMES_RU = [
    ("1.jpg", 1, "Логин", None),
    ("2.png", 2, "Конфиги с сервера", None),
    ("3.png", 3, "Заполнение данных формы", "1/4"),
    ("4.png", 3, "Заполнение данных формы", "2/4"),
    ("5.png", 3, "Заполнение данных формы", "3/4"),
    ("6.jpg", 3, "Заполнение данных формы", "4/4"),
    ("7.png", 4, "Кэш проекта и отправка", None),
]
FRAMES_EN = [
    ("1.jpg", 1, "Login", None),
    ("2.jpg", 2, "Configs from server", None),
    ("3.jpg", 3, "Filling out the form", "1/4"),
    ("4.jpg", 3, "Filling out the form", "2/4"),
    ("5.jpg", 3, "Filling out the form", "3/4"),
    ("6.jpg", 3, "Filling out the form", "4/4"),
    ("7.jpg", 4, "Project cache and upload", None),
]

HOLD_MS = 2400
FADE_FRAMES = 5


def _font(size: int, bold: bool = False):
    for path in (
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _top_header(stage: int, headline: str, sub: str | None) -> Image.Image:
    bar = Image.new("RGBA", (TARGET_W, TOP_H), (*HEADER_BG, 255))
    draw = ImageDraw.Draw(bar)
    draw.rectangle((0, TOP_H - 3, TARGET_W, TOP_H), fill=ACCENT)

    badge_r = 22
    bx, by = 18, TOP_H // 2
    draw.ellipse(
        (bx - badge_r, by - badge_r, bx + badge_r, by + badge_r),
        fill=BADGE,
    )
    sf = _font(20, True)
    st = str(stage)
    bbox = draw.textbbox((0, 0), st, font=sf)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((bx - tw // 2, by - th // 2 - 2), st, font=sf, fill=BG)

    title = headline if not sub else f"{headline}  ({sub})"
    hf = _font(22 if len(title) < 38 else 20, True)
    draw.text((bx + badge_r + 14, 20), title, font=hf, fill=TEXT)
    return bar


def _bottom_bar(
    stage: int, frame_idx: int, frames: list, stage_label: str, frame_label: str
) -> Image.Image:
    bar = Image.new("RGBA", (TARGET_W, BOTTOM_H), (*BG, 255))
    draw = ImageDraw.Draw(bar)
    label = (
        f"{stage_label} {stage} / {STAGES_TOTAL}  ·  Flutter App  ·  "
        f"{frame_label} {frame_idx}/{len(frames)}"
    )
    draw.text((20, 8), label, font=_font(14), fill=TEXT_MUTED)
    return bar


def _fit_phone(img: Image.Image) -> Image.Image:
    """Center portrait screenshot with phone-style frame."""
    img = img.convert("RGBA")
    iw, ih = img.size
    # prioritize height for phone aspect
    max_w = TARGET_W - 120
    max_h = IMG_AREA_H - 40
    scale = min(max_w / iw, max_h / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    resized = img.resize((nw, nh), Image.Resampling.LANCZOS)

    canvas = Image.new("RGBA", (TARGET_W, IMG_AREA_H), (*BG, 255))
    x = (TARGET_W - nw) // 2
    y = (IMG_AREA_H - nh) // 2

    # phone bezel
    bezel = 14
    frame = Image.new("RGBA", (nw + bezel * 2, nh + bezel * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame)
    draw.rounded_rectangle(
        (0, 0, nw + bezel * 2 - 1, nh + bezel * 2 - 1),
        radius=28,
        fill=(14, 18, 28, 255),
        outline=(58, 69, 88, 255),
        width=3,
    )
    # notch hint
    notch_w, notch_h = max(40, nw // 4), 8
    draw.rounded_rectangle(
        ((nw + bezel * 2 - notch_w) // 2, 6, (nw + bezel * 2 + notch_w) // 2, 6 + notch_h),
        radius=4,
        fill=(8, 10, 16, 255),
    )
    canvas.paste(frame, (x - bezel, y - bezel), frame)
    canvas.paste(resized, (x, y), resized)
    return canvas


def _compose_frame(
    img_path: Path,
    stage: int,
    headline: str,
    sub: str | None,
    frame_idx: int,
    frames: list,
    stage_label: str,
    frame_label: str,
) -> Image.Image:
    out = Image.new("RGB", (TARGET_W, TARGET_H), BG)
    out.paste(_top_header(stage, headline, sub), (0, 0))
    out.paste(_fit_phone(Image.open(img_path)), (0, TOP_H))
    out.paste(_bottom_bar(stage, frame_idx, frames, stage_label, frame_label), (0, TOP_H + IMG_AREA_H))
    return out


def _timeline(frames: list[Image.Image]) -> list[Image.Image]:
    seq: list[Image.Image] = []
    for i, frame in enumerate(frames):
        seq.append(frame)
        if i < len(frames) - 1:
            nxt = frames[i + 1]
            for step in range(1, FADE_FRAMES + 1):
                seq.append(Image.blend(frame, nxt, step / (FADE_FRAMES + 1)))
    return seq


def _save_with_ffmpeg(png_dir: Path, out_gif: Path, fps: float = 2.2) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False
    vf = (
        f"fps={fps},scale={TARGET_W}:{TARGET_H}:flags=lanczos,split[s0][s1];"
        "[s0]palettegen=max_colors=256:stats_mode=diff[p];"
        "[s1][p]paletteuse=dither=bayer:bayer_scale=2"
    )
    try:
        subprocess.run(
            [ffmpeg, "-y", "-framerate", str(fps), "-i", str(png_dir / "frame_%03d.png"), "-vf", vf, "-loop", "0", str(out_gif)],
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def build(
    src_dir: Path,
    out_gif: Path,
    frames: list | None = None,
    stage_label: str = "Этап",
    frame_label: str = "кадр",
) -> Path:
    frames = frames or FRAMES_RU
    key_frames = [
        _compose_frame(
            src_dir / fname, stage, headline, sub, i + 1, frames, stage_label, frame_label
        )
        for i, (fname, stage, headline, sub) in enumerate(frames)
    ]
    seq = _timeline(key_frames)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for i, frame in enumerate(seq):
            frame.save(tmp_path / f"frame_{i:03d}.png")

        if _save_with_ffmpeg(tmp_path, out_gif):
            return out_gif

        key_frames[0].save(
            out_gif,
            save_all=True,
            append_images=key_frames[1:],
            duration=[HOLD_MS] * len(key_frames),
            loop=0,
            optimize=True,
        )
    return out_gif


if __name__ == "__main__":
    import sys

    root = Path(__file__).resolve().parent
    en = "--en" in sys.argv
    if en:
        src = root / "img" / "Flutter_en"
        out = root / "img" / "flutter-steps-app-en.gif"
        result = build(src, out, FRAMES_EN, "Stage", "frame")
    else:
        src = root / "img" / "Flutter"
        out = root / "img" / "flutter-steps-app.gif"
        result = build(src, out, FRAMES_RU, "Этап", "кадр")
    print(f"Created: {result}")
    print(f"Size: {TARGET_W}x{TARGET_H} px, {result.stat().st_size // 1024} KB")
