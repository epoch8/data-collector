"""Build STEP 04 GIF — admin package list, filter, view/edit."""

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
ACCENT = (61, 204, 133)  # STEP 04 green
BADGE = (61, 204, 133)
TEXT = (232, 234, 237)
TEXT_MUTED = (156, 163, 175)

STAGES_TOTAL = 3

FRAMES = [
    ("1.png", 1, "Список всех принятых пакетов", None),
    ("2.png", 2, "Фильтрация пакетов по параметрам формы", None),
    ("3.png", 3, "Просмотр и редактирование пакета", "1/4"),
    ("4.png", 3, "Просмотр и редактирование пакета", "2/4"),
    ("5.png", 3, "Просмотр и редактирование пакета", "3/4"),
    ("6.png", 3, "Просмотр и редактирование пакета", "4/4"),
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
    hf = _font(22 if len(title) < 42 else 19, True)
    draw.text((bx + badge_r + 14, 20), title, font=hf, fill=TEXT)
    return bar


def _bottom_bar(stage: int, frame_idx: int) -> Image.Image:
    bar = Image.new("RGBA", (TARGET_W, BOTTOM_H), (*BG, 255))
    draw = ImageDraw.Draw(bar)
    label = f"Этап {stage} из {STAGES_TOTAL}  ·  Staff Admin  ·  кадр {frame_idx}/{len(FRAMES)}"
    draw.text((20, 8), label, font=_font(14), fill=TEXT_MUTED)
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
    img_path: Path, stage: int, headline: str, sub: str | None, frame_idx: int
) -> Image.Image:
    out = Image.new("RGB", (TARGET_W, TARGET_H), BG)
    out.paste(_top_header(stage, headline, sub), (0, 0))
    out.paste(_fit_image(Image.open(img_path)), (0, TOP_H))
    out.paste(_bottom_bar(stage, frame_idx), (0, TOP_H + IMG_AREA_H))
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


def _save_with_ffmpeg(png_dir: Path, out_gif: Path, fps: float = 2.0) -> bool:
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
            [
                ffmpeg, "-y", "-framerate", str(fps), "-i",
                str(png_dir / "frame_%03d.png"), "-vf", vf, "-loop", "0", str(out_gif),
            ],
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def build(src_dir: Path, out_gif: Path) -> Path:
    key_frames = [
        _compose_frame(src_dir / fname, stage, headline, sub, i + 1)
        for i, (fname, stage, headline, sub) in enumerate(FRAMES)
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
    root = Path(__file__).resolve().parent
    src = root / "img" / "UI"
    out = root / "img" / "admin-packages.gif"
    result = build(src, out)
    print(f"Created: {result}")
    print(f"Size: {TARGET_W}x{TARGET_H} px, {result.stat().st_size // 1024} KB")
    print("For slide STEP 04 - Prosmotr prinyatykh paketov")
