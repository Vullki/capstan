"""Render the icon SVGs to PNGs and a multi-size .ico, using headless Edge.

Usage: python design/icon/render.py
Outputs (in design/icon/ and app/ui/assets/):
  wolf-1024.png, wolf-256.png, wolf.ico (16-256)
Small sizes (16, 24, 32) come from wolf-small.svg, a simplified mark that stays
readable when tiny.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
RENDER = 1024


def render(svg_name: str) -> Image.Image:
    svg = open(os.path.join(HERE, svg_name), encoding="utf-8").read()
    svg = svg.replace('width="256" height="256"', f'width="{RENDER}" height="{RENDER}"')
    tmp = tempfile.mkdtemp()
    html = os.path.join(tmp, "i.html")
    with open(html, "w", encoding="utf-8") as f:
        f.write(f"<!doctype html><html><body style='margin:0;background:transparent'>{svg}</body></html>")
    out = os.path.join(tmp, "o.png")
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--default-background-color=00000000", f"--window-size={RENDER},{RENDER}",
                    f"--screenshot={out}", "file:///" + html.replace("\\", "/")],
                   check=True, capture_output=True, timeout=60)
    im = Image.open(out).convert("RGBA").crop((0, 0, RENDER, RENDER))
    shutil.rmtree(tmp, ignore_errors=True)
    return im


def main():
    big = render("wolf.svg")
    small = render("wolf-small.svg")
    big.save(os.path.join(HERE, "wolf-1024.png"))
    sizes = {}
    for s in (256, 128, 64, 48):
        sizes[s] = big.resize((s, s), Image.LANCZOS)
    for s in (32, 24, 16):
        sizes[s] = small.resize((s, s), Image.LANCZOS)
    sizes[256].save(os.path.join(HERE, "wolf-256.png"))
    sizes[32].save(os.path.join(HERE, "wolf-32.png"))
    ico = os.path.join(HERE, "wolf.ico")
    order = [256, 128, 64, 48, 32, 24, 16]
    sizes[256].save(ico, format="ICO", sizes=[(s, s) for s in order],
                    append_images=[sizes[s] for s in order[1:]])
    return  # archived concept: no longer copied into the app
    assets = os.path.join(ROOT, "app", "ui", "assets")
    shutil.copy(ico, os.path.join(assets, "wolf.ico"))
    shutil.copy(os.path.join(HERE, "wolf-256.png"), os.path.join(assets, "wolf-256.png"))
    shutil.copy(os.path.join(HERE, "wolf-32.png"), os.path.join(assets, "wolf-32.png"))
    print("ok: icon written")


if __name__ == "__main__":
    main()
