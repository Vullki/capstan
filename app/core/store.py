"""Settings, download history, the GGUF header cache, and the library scan.

Everything lives as JSON in %APPDATA%\\Capstan\\ (override with CAPSTAN_DATA).
"""
from __future__ import annotations

import json
import os
import shutil
import threading
import time

_APPDATA = os.environ.get("APPDATA", os.path.expanduser("~"))
DATA_DIR = os.environ.get("CAPSTAN_DATA") or os.path.join(_APPDATA, "Capstan")

# The app was called "DARK Pull" before 1.2.0: carry its settings, queue and history over once.
_OLD = os.path.join(_APPDATA, "DARK Pull")
if not os.environ.get("CAPSTAN_DATA") and not os.path.exists(DATA_DIR) and os.path.isdir(_OLD):
    try:
        shutil.move(_OLD, DATA_DIR)
    except OSError:
        pass
os.makedirs(DATA_DIR, exist_ok=True)
_lock = threading.RLock()

DEFAULT_SETTINGS = {
    "download_root": "D:\\Models" if os.path.exists("D:\\") else os.path.join(os.path.expanduser("~"), "Models"),
    "extra_roots": [],          # more folders to scan for the library
    "concurrency": 1,           # parallel downloads
    "verify": True,             # SHA-256 check after download
    "context": 8192,            # default context for the fit lights
    "judge": "free",            # "free" (VRAM free now) or "total"
    "kv_type": "f16",           # f16 | q8_0 | q4_0
    "gguf_only": True,
    "sort": "downloads",
}
KV_BYTES = {"f16": 2.0, "q8_0": 1.0625, "q4_0": 0.5625}


def _path(name: str) -> str:
    return os.path.join(DATA_DIR, name)


def _load(name: str, default):
    try:
        with open(_path(name), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _save(name: str, data) -> None:
    tmp = _path(name) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    os.replace(tmp, _path(name))


# ── settings ────────────────────────────────────────────────────────────
def settings() -> dict:
    with _lock:
        return {**DEFAULT_SETTINGS, **_load("settings.json", {})}


def update_settings(patch: dict) -> dict:
    with _lock:
        s = {**settings(), **{k: v for k, v in patch.items() if k in DEFAULT_SETTINGS}}
        _save("settings.json", s)
        return s


# ── queue persistence ───────────────────────────────────────────────────
def load_queue() -> list[dict]:
    return _load("queue.json", [])


def save_queue(jobs: list[dict]) -> None:
    with _lock:
        _save("queue.json", jobs)


# ── history (what we downloaded, so the library knows the source) ──────
def add_history(entry: dict) -> None:
    with _lock:
        h = _load("history.json", {})
        h[os.path.normcase(os.path.abspath(entry["path"]))] = {**entry, "date": time.time()}
        _save("history.json", h)


def history() -> dict:
    return _load("history.json", {})


def forget(path: str) -> None:
    with _lock:
        h = _load("history.json", {})
        h.pop(os.path.normcase(os.path.abspath(path)), None)
        _save("history.json", h)


# ── GGUF header cache (shape per repo file) ─────────────────────────────
def cached_shape(key: str):
    return _load("headers.json", {}).get(key)


def cache_shape(key: str, shape: dict) -> None:
    with _lock:
        c = _load("headers.json", {})
        c[key] = shape
        if len(c) > 2000:                       # keep it small
            for k in list(c)[: len(c) - 2000]:
                c.pop(k)
        _save("headers.json", c)


# ── library scan ────────────────────────────────────────────────────────
_MODEL_EXT = (".gguf", ".safetensors", ".bin", ".onnx", ".pt", ".pth")


def scan_library() -> list[dict]:
    s = settings()
    roots = [s["download_root"], *s.get("extra_roots", [])]
    hist = history()
    seen, out = set(), []
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for fn in filenames:
                low = fn.lower()
                if not low.endswith(_MODEL_EXT):
                    continue
                p = os.path.join(dirpath, fn)
                key = os.path.normcase(os.path.abspath(p))
                if key in seen:
                    continue
                seen.add(key)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                h = hist.get(key, {})
                out.append({
                    "path": p, "name": fn, "folder": dirpath, "size": st.st_size,
                    "date": h.get("date") or st.st_mtime,
                    "repo_id": h.get("repo_id"), "quant": h.get("quant"),
                    "mmproj": "mmproj" in low, "gguf": low.endswith(".gguf"),
                })
    out.sort(key=lambda x: x["date"], reverse=True)
    return out
