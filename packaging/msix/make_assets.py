"""Make the MSIX logo set (packaging/msix/Assets) from the app icon in design/icon/png.

Run once after the icon changes:  python packaging/msix/make_assets.py   (needs Pillow)
Small sizes use the hand-tuned PNGs where they exist; the rest are scaled from 1024.
"""
from __future__ import annotations

import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "design", "icon", "png")
OUT = os.path.join(HERE, "Assets")
TUNED = {int(n.split("-")[1].split(".")[0]): os.path.join(SRC, n)
         for n in os.listdir(SRC) if n.startswith("capstan-") and n.endswith(".png")}
MASTER = Image.open(TUNED[1024]).convert("RGBA")


def icon(px: int) -> Image.Image:
    if px in TUNED:
        return Image.open(TUNED[px]).convert("RGBA")
    return MASTER.resize((px, px), Image.LANCZOS)


def canvas(w: int, h: int, glyph: int) -> Image.Image:
    """The icon centred on a transparent canvas (tiles show it with room around it)."""
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    g = icon(glyph)
    im.alpha_composite(g, ((w - glyph) // 2, (h - glyph) // 2))
    return im


def save(im: Image.Image, name: str) -> None:
    im.save(os.path.join(OUT, name), optimize=True)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))
    for scale in (100, 125, 150, 200, 400):
        k = scale / 100
        save(icon(round(44 * k)), f"Square44x44Logo.scale-{scale}.png")
        save(canvas(round(150 * k), round(150 * k), round(96 * k)), f"Square150x150Logo.scale-{scale}.png")
        save(canvas(round(71 * k), round(71 * k), round(48 * k)), f"Square71x71Logo.scale-{scale}.png")
        save(canvas(round(310 * k), round(150 * k), round(96 * k)), f"Wide310x150Logo.scale-{scale}.png")
        save(icon(round(50 * k)), f"StoreLogo.scale-{scale}.png")
    # Taskbar, Start list and file explorer: exact pixel sizes, with and without the tile plate.
    for px in (16, 20, 24, 30, 32, 36, 40, 48, 60, 64, 72, 80, 96, 256):
        save(icon(px), f"Square44x44Logo.targetsize-{px}.png")
        save(icon(px), f"Square44x44Logo.targetsize-{px}_altform-unplated.png")
        save(icon(px), f"Square44x44Logo.targetsize-{px}_altform-lightunplated.png")
    print(len(os.listdir(OUT)), "files in", OUT)


if __name__ == "__main__":
    main()
