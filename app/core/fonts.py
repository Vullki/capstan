"""Satoshi, fetched from Fontshare on first run.

Satoshi is a Fontshare "Closed Source" font (ITF Free Font License): free to use,
but its files may not be redistributed. So the repository doesn't ship it; the app
downloads the three weights it uses straight from Fontshare, once, into
app/ui/assets/fonts. Until then the UI falls back to Inter Display.
"""
from __future__ import annotations

import os
import re

from huggingface_hub.utils import get_session  # an httpx client that's already configured

FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui", "assets", "fonts")
WEIGHTS = (400, 500, 700)
CSS_URL = "https://api.fontshare.com/v2/css?f[]=satoshi@400,500,700&display=swap"


def path(weight: int) -> str:
    return os.path.join(FONTS_DIR, f"Satoshi-{weight}.woff2")


def missing() -> list[int]:
    return [w for w in WEIGHTS if not os.path.exists(path(w)) or os.path.getsize(path(w)) < 1000]


def ensure() -> bool:
    """Download any missing weight. Returns True if something new was installed."""
    need = missing()
    if not need:
        return False
    s = get_session()
    css = s.get(CSS_URL, timeout=20).text
    # Each @font-face block holds one weight and its woff2 URL.
    urls = {}
    for block in css.split("@font-face")[1:]:
        w = re.search(r"font-weight:\s*(\d+)", block)
        u = re.search(r"url\('([^']+\.woff2)'\)", block)
        if w and u:
            urls[int(w.group(1))] = ("https:" + u.group(1)) if u.group(1).startswith("//") else u.group(1)
    got = False
    for w in need:
        if w not in urls:
            continue
        r = s.get(urls[w], timeout=30, follow_redirects=True)
        r.raise_for_status()
        if not r.content.startswith(b"wOF2"):
            continue
        tmp = path(w) + ".tmp"
        with open(tmp, "wb") as f:
            f.write(r.content)
        os.replace(tmp, path(w))
        got = True
    return got
