"""Build presentation-ready GIF from Config step screenshots."""

import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Step-slide right panel: 5.55" x 5.85" @ 200 DPI (16:9 deck)
TARGET_W = 1110
TARGET_H = 1170
TOP_H = 68
BOTTOM_H = 36
IMG_AREA_H = TARGET_H - TOP_H - BOTTOM_H

BG = (18, 18, 24)
HEADER_BG = (30, 42, 61)
ACCENT = (91, 141, 239)
ACCENT_GOLD = (212, 168, 75)
TEXT = (232, 234, 237)
TEXT_MUTED = (156, 163, 175)

# file, step_no, headline (shown above screenshot)
FRAMES_RU = [
    ("1.png", 1, "Создаёт проект и привязывает в Git"),
    ("2.png", 2, "Редактирование конфига"),
    ("3.png", 3, "Назначение сборщиков"),
    ("4.png", 4, "Сохранение проекта"),
]
FRAMES_EN = [
    ("1.png", 1, "Creates project and links to Git"),
    ("2.png", 2, "Config editing"),
    ("3.png", 3, "Assigning collectors"),
    ("4.png", 4, "Saving project"),
]

HOLD_MS = 2800
FADE_FRAMES = 6


def _font(size: int, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _top_header(step: int, headline: str) -> Image.Image:
    bar = Image.new("RGBA", (TARGET_W, TOP_H), (*HEADER_BG, 255))
    draw = ImageDraw.Draw(bar)
    draw.rectangle((0, TOP_H - 3, TARGET_W, TOP_H), fill=ACCENT)

    badge_r = 22
    bx, by = 18, TOP_H // 2
    draw.ellipse(
        (bx - badge_r, by - badge_r, bx + badge_r, by + badge_r),
        fill=ACCENT_GOLD,
    )
    step_font = _font(20, True)
    step_text = str(step)
    bbox = draw.textbbox((0, 0), step_text, font=step_font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((bx - tw // 2, by - th // 2 - 2), step_text, font=step_font, fill=BG)

    headline_font = _font(24, True)
    draw.text((bx + badge_r + 16, 18), headline, font=headline_font, fill=TEXT)
    return bar


def _bottom_bar(step: int, frames: list, step_label: str) -> Image.Image:
    bar = Image.new("RGBA", (TARGET_W, BOTTOM_H), (*BG, 255))
    draw = ImageDraw.Draw(bar)
    label = f"{step_label} {step} / {len(frames)}  ·  Staff Admin"
    draw.text((20, 8), label, font=_font(15), fill=TEXT_MUTED)
    return bar


def _fit_image(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    iw, ih = img.size
    scale = min((TARGET_W - 32) / iw, (IMG_AREA_H - 32) / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    resized = img.resize((nw, nh), Image.Resampling.LANCZOS)

    canvas = Image.new("RGBA", (TARGET_W, IMG_AREA_H), (*BG, 255))
    x = (TARGET_W - nw) // 2
    y = (IMG_AREA_H - nh) // 2
    pad = 10
    card = Image.new("RGBA", (nw + pad * 2, nh + pad * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle(
        (0, 0, nw + pad * 2 - 1, nh + pad * 2 - 1),
        radius=14,
        fill=(24, 32, 48, 255),
        outline=(58, 69, 88, 255),
        width=2,
    )
    canvas.paste(card, (x - pad, y - pad), card)
    canvas.paste(resized, (x, y), resized)
    return canvas


def _compose_frame(
    img_path: Path, step: int, headline: str, frames: list, step_label: str
) -> Image.Image:
    header = _top_header(step, headline)
    body = _fit_image(Image.open(img_path))
    footer = _bottom_bar(step, frames, step_label)

    out = Image.new("RGB", (TARGET_W, TARGET_H), BG)
    out.paste(header, (0, 0))
    out.paste(body, (0, TOP_H))
    out.paste(footer, (0, TOP_H + IMG_AREA_H))
    return out


def _timeline(frames: list[Image.Image]) -> list[Image.Image]:
    seq: list[Image.Image] = []
    for i, frame in enumerate(frames):
        seq.append(frame)
        if i < len(frames) - 1:
            nxt = frames[i + 1]
            for step in range(1, FADE_FRAMES + 1):
                alpha = step / (FADE_FRAMES + 1)
                seq.append(Image.blend(frame, nxt, alpha))
    return seq


def _save_with_ffmpeg(png_dir: Path, out_gif: Path, fps: float = 2.0) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False
    pattern = str(png_dir / "frame_%03d.png")
    vf = (
        f"fps={fps},scale={TARGET_W}:{TARGET_H}:flags=lanczos,split[s0][s1];"
        "[s0]palettegen=max_colors=256:stats_mode=diff[p];"
        "[s1][p]paletteuse=dither=bayer:bayer_scale=2"
    )
    cmd = [
        ffmpeg, "-y", "-framerate", str(fps), "-i", pattern,
        "-vf", vf, "-loop", "0", str(out_gif),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False


def build(
    src_dir: Path,
    out_gif: Path,
    frames: list | None = None,
    step_label: str = "Шаг",
) -> Path:
    frames = frames or FRAMES_RU
    key_frames = [
        _compose_frame(src_dir / f, n, h, frames, step_label) for f, n, h in frames
    ]
    seq = _timeline(key_frames)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for i, frame in enumerate(seq):
            frame.save(tmp_path / f"frame_{i:03d}.png")

        if _save_with_ffmpeg(tmp_path, out_gif, fps=2.0):
            return out_gif

        durations = [HOLD_MS] * len(key_frames)
        key_frames[0].save(
            out_gif,
            save_all=True,
            append_images=key_frames[1:],
            duration=durations,
            loop=0,
            optimize=True,
        )
    return out_gif


if __name__ == "__main__":
    import sys

    root = Path(__file__).resolve().parent
    en = "--en" in sys.argv
    if en:
        src = root / "img" / "Config_en"
        gif_path = root / "img" / "config-steps-admin-en.gif"
        result = build(src, gif_path, FRAMES_EN, "Step")
    else:
        src = root / "img" / "Config"
        gif_path = root / "img" / "config-steps-admin.gif"
        result = build(src, gif_path, FRAMES_RU, "Шаг")
    kb = result.stat().st_size // 1024
    print(f"Created: {result}")
    print(f"Size: {TARGET_W}x{TARGET_H} px, {kb} KB")
