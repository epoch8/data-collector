"""Build GIF for datapipe stage-2 train screenshots (sequential frames).

Run: python docs/e2e-korovas/make_datapipe_train_gif.py
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "img" / "datapipe" / "stage-2-train"
OUT = SRC / "screenshot.gif"

# Wide panel for landscape Datapipe Ops UI (~6.4" x 4.8" @ 180 DPI)
TARGET_W = 1150
TARGET_H = 860
TOP_H = 64
BOTTOM_H = 32
IMG_AREA_H = TARGET_H - TOP_H - BOTTOM_H

BG = (9, 13, 22)
HEADER_BG = (19, 26, 42)
ACCENT = (183, 242, 64)
TEXT = (232, 234, 237)
TEXT_MUTED = (156, 163, 175)
CARD = (24, 32, 48)
BORDER = (58, 69, 88)

# Order: train run → metrics → preview
FRAMES = [
    ("run train.png", 1, "Обучение модели"),
    ("metrix.png", 2, "Метрики на val"),
    ("annotation image preview.png", 3, "Превью разметки"),
]

HOLD_MS = 3200
FADE_FRAMES = 5


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

    badge_r = 20
    bx, by = 22, TOP_H // 2
    draw.ellipse((bx - badge_r, by - badge_r, bx + badge_r, by + badge_r), fill=ACCENT)
    step_font = _font(18, True)
    step_text = str(step)
    bbox = draw.textbbox((0, 0), step_text, font=step_font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((bx - tw // 2, by - th // 2 - 2), step_text, font=step_font, fill=BG)

    draw.text((bx + badge_r + 14, 16), headline, font=_font(22, True), fill=TEXT)
    return bar


def _bottom_bar(step: int) -> Image.Image:
    bar = Image.new("RGBA", (TARGET_W, BOTTOM_H), (*BG, 255))
    draw = ImageDraw.Draw(bar)
    draw.text((18, 6), f"Шаг {step} / {len(FRAMES)}  ·  Datapipe · стадия обучения", font=_font(13), fill=TEXT_MUTED)
    return bar


def _fit_image(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    iw, ih = img.size
    pad = 12
    max_w = TARGET_W - 40
    max_h = IMG_AREA_H - 24
    scale = min(max_w / iw, max_h / ih)
    nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
    resized = img.resize((nw, nh), Image.Resampling.LANCZOS)

    canvas = Image.new("RGBA", (TARGET_W, IMG_AREA_H), (*BG, 255))
    x = (TARGET_W - nw) // 2
    y = (IMG_AREA_H - nh) // 2
    card = Image.new("RGBA", (nw + pad * 2, nh + pad * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle(
        (0, 0, nw + pad * 2 - 1, nh + pad * 2 - 1),
        radius=12,
        fill=(*CARD, 255),
        outline=(*BORDER, 255),
        width=2,
    )
    canvas.paste(card, (x - pad, y - pad), card)
    canvas.paste(resized, (x, y), resized)
    return canvas


def _compose_frame(img_path: Path, step: int, headline: str) -> Image.Image:
    out = Image.new("RGB", (TARGET_W, TARGET_H), BG)
    out.paste(_top_header(step, headline), (0, 0))
    out.paste(_fit_image(Image.open(img_path)), (0, TOP_H))
    out.paste(_bottom_bar(step), (0, TOP_H + IMG_AREA_H))
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


def _save_ffmpeg(png_dir: Path, out_gif: Path, fps: float = 1.8) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False
    vf = (
        f"fps={fps},scale={TARGET_W}:{TARGET_H}:flags=lanczos,split[s0][s1];"
        "[s0]palettegen=max_colors=256:stats_mode=diff[p];"
        "[s1][p]paletteuse=dither=bayer:bayer_scale=2"
    )
    cmd = [
        ffmpeg, "-y", "-framerate", str(fps), "-i", str(png_dir / "frame_%03d.png"),
        "-vf", vf, "-loop", "0", str(out_gif),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False


def build() -> Path:
    missing = [f for f, _, _ in FRAMES if not (SRC / f).exists()]
    if missing:
        raise FileNotFoundError(f"Missing in {SRC}: {missing}")

    key_frames = [_compose_frame(SRC / f, n, h) for f, n, h in FRAMES]
    seq = _timeline(key_frames)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for i, frame in enumerate(seq):
            frame.save(tmp_path / f"frame_{i:03d}.png")

        if _save_ffmpeg(tmp_path, OUT):
            return OUT

        # PIL fallback: hold each key frame
        key_frames[0].save(
            OUT,
            save_all=True,
            append_images=key_frames[1:],
            duration=[HOLD_MS] * len(key_frames),
            loop=0,
            optimize=True,
        )
    return OUT


if __name__ == "__main__":
    result = build()
    print(f"Created: {result}")
    print(f"Size: {TARGET_W}x{TARGET_H} px, {result.stat().st_size // 1024} KB")
