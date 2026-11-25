"""Satoshi, fetched from Fontshare on first run.

Satoshi is a Fontshare "Closed Source" font (ITF Free Font License): free to use,
but its files may not be redistributed. So neither the repository nor the installer
ships it; the app downloads the three weights it uses straight from Fontshare, once,
into the data folder (%APPDATA%\\Capstan\\fonts). The install folder is read-only once
Capstan is installed, so the UI loads the files through the bridge (Api.font_data)
instead of by URL. Until then it falls back to Inter Display.
"""
from __future__ import annotations

import base64
import os
import re
import shutil

from . import store

FONTS_DIR = os.path.join(store.DATA_DIR, "fonts")
# Before 1.5.0 the files went into the app's own folder: copy them over once.
_OLD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui", "assets", "fonts")
WEIGHTS = (400, 500, 700)
CSS_URL = "https://api.fontshare.com/v2/css?f[]=satoshi@400,500,700&display=swap"


def path(weight: int) -> str:
    return os.path.join(FONTS_DIR, f"Satoshi-{weight}.woff2")


def _ok(p: str) -> bool:
    return os.path.exists(p) and os.path.getsize(p) >= 1000


def _migrate() -> None:
    for w in WEIGHTS:
        old = os.path.join(_OLD_DIR, f"Satoshi-{w}.woff2")
        if not _ok(path(w)) and _ok(old):
            try:
                os.makedirs(FONTS_DIR, exist_ok=True)
                shutil.copyfile(old, path(w))
            except OSError:
                pass


def missing() -> list[int]:
    _migrate()
    return [w for w in WEIGHTS if not _ok(path(w))]


def present() -> list[int]:
    return [w for w in WEIGHTS if _ok(path(w))]


def data() -> dict[str, str]:
    """The installed weights as base64, for the UI's FontFace loader."""
    out = {}
    for w in present():
        with open(path(w), "rb") as f:
            out[str(w)] = base64.b64encode(f.read()).decode("ascii")
    return out


def ensure() -> bool:
    """Download any missing weight. Returns True if something new was installed."""
    need = missing()
    if not need:
        return False
    from huggingface_hub.utils import get_session  # an httpx client that's already configured
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
    os.makedirs(FONTS_DIR, exist_ok=True)
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
