"""The bridge the UI calls (pywebview js_api). Every public method returns JSON-safe data."""
from __future__ import annotations

import ctypes
import json
import os
import re
import subprocess
import sys
import threading
import webbrowser
from concurrent.futures import ThreadPoolExecutor

from core import fit, fonts, gguf, hub, machine, store
from core.downloads import Queue

VERSION = "1.5.0"
_pool = ThreadPoolExecutor(max_workers=4)


def _safe(fn):
    def wrap(*a, **kw):
        try:
            return fn(*a, **kw)
        except Exception as e:  # surface errors to the UI instead of a silent promise rejection
            return {"error": f"{type(e).__name__}: {e}"[:400], "_exc": True}
    wrap.__name__ = fn.__name__
    return wrap


def _folder_name(repo_id: str) -> str:
    name = repo_id.split("/", 1)[-1]
    name = re.sub(r"[-_.]?gguf$", "", name, flags=re.IGNORECASE)
    return re.sub(r'[<>:"/\\|?*]', "_", name) or "model"


class Api:
    def __init__(self, open_target: str | None = None, view: str | None = None):
        self._window = None
        self._open = open_target
        self._view = view
        self._queue = Queue(self._emit)

    def attach(self, window):
        self._window = window

    def _emit(self, event: dict):
        w = self._window
        if not w:
            return
        try:
            w.evaluate_js(f"window.DP && window.DP.onEvent({json.dumps(event)})")
        except Exception:
            pass

    # ── app ───────────────────────────────────────────────────────────
    def _fetch_fonts(self):
        """First run: fetch Satoshi from Fontshare, then tell the UI to swap it in."""
        try:
            if fonts.ensure():
                self._emit({"type": "fonts", "weights": list(fonts.WEIGHTS)})
        except Exception:
            pass   # offline or Fontshare unreachable: the UI keeps Inter Display, try again next run

    @_safe
    def init(self):
        if fonts.missing():
            threading.Thread(target=self._fetch_fonts, daemon=True).start()
        return {"version": VERSION, "settings": store.settings(), "machine": machine.snapshot(),
                "queue": self._queue.snapshot(), "user": self._whoami(),
                "open": self._open, "view": self._view, "data_dir": store.DATA_DIR,
                "fonts": fonts.present()}

    @_safe
    def font_data(self):
        """Satoshi as base64 (it lives in the data folder, outside what the UI can load by URL)."""
        return fonts.data()

    def _whoami(self):
        try:
            from huggingface_hub import whoami
            return whoami().get("name")
        except Exception:
            return None

    @_safe
    def hf_login(self, token):
        """Save a Hugging Face token, the same way `hf auth login` does (the installed app has no hf CLI)."""
        token = (token or "").strip()
        if not token.startswith("hf_"):
            return {"error": "That isn't a Hugging Face token: they start with hf_."}
        from huggingface_hub import login, whoami
        try:
            name = whoami(token=token).get("name")
        except Exception:
            return {"error": "Hugging Face didn't accept that token. Check it at huggingface.co/settings/tokens."}
        login(token=token, add_to_git_credential=False, skip_if_logged_in=False)
        return {"user": name}

    @_safe
    def hf_logout(self):
        from huggingface_hub import logout
        try:
            logout()
        except Exception:
            pass   # no saved token: already logged out
        return {"user": self._whoami()}

    @_safe
    def settings(self, patch=None):
        return store.update_settings(patch) if patch else store.settings()

    @_safe
    def machine(self):
        return machine.snapshot()

    # ── search / repo ─────────────────────────────────────────────────
    @_safe
    def search(self, query, sort="downloads", gguf_only=True, type_filter="all"):
        return {"query": query, "type_filter": type_filter,
                "results": hub.search(query, sort=sort, gguf_only=gguf_only, type_filter=type_filter)}

    @_safe
    def parse_link(self, text):
        return hub.parse_link(text)

    @_safe
    def open_repo(self, repo_id, revision=None):
        r = hub.repo(repo_id, revision)
        if "gguf" in r:
            r["default_dir"] = os.path.join(store.settings()["download_root"], _folder_name(repo_id))
        return r

    @_safe
    def shape(self, repo_id, header_file, revision=None):
        key = f"{repo_id}@{revision or 'main'}:{header_file}"
        s = store.cached_shape(key)
        if s and s.get("layers"):
            return {"shape": s, "cached": True}
        meta = gguf.read_metadata(repo_id, header_file, revision)
        s = gguf.model_shape(meta)
        if not s.get("layers"):
            # No layers means this isn't a model header (calibration data, a tokenizer...).
            # An empty shape would zero the KV cache and make every quant look like it fits.
            return {"shape": None, "cached": False}
        store.cache_shape(key, s)
        return {"shape": s, "cached": False}

    @_safe
    def fit(self, items, shape, ctx, judge="free", kv_type="f16", text=True):
        """items: [{key, size}] -> {key: estimate}. Judged against the live machine.
        text=False: not a chat model (image/video/music/TTS/embeddings), so no KV cache."""
        m = machine.snapshot()
        g = m["gpu"]
        vram = (g["free"] if judge == "free" else g["total"]) if g else 0
        ram = m["ram"]["available"] if judge == "free" else m["ram"]["total"]
        kvb = store.KV_BYTES.get(kv_type, 2.0)
        return {"vram": vram, "ram": ram, "gpu": bool(g),
                "est": {it["key"]: fit.estimate(int(it["size"]), shape, int(ctx), vram, ram, kvb, text=bool(text)) for it in items}}

    # ── downloads ─────────────────────────────────────────────────────
    @_safe
    def disk_check(self, local_dir, nbytes):
        free = machine.free_at(local_dir)
        drive = os.path.splitdrive(os.path.abspath(local_dir))[0]
        pending = self._queue.pending_bytes_on(drive)
        return {"free": free, "pending": pending, "need": int(nbytes),
                "ok": free is None or free - pending >= int(nbytes), "drive": drive}

    @_safe
    def download(self, repo_id, revision, files, local_dir, quant=None):
        os.makedirs(local_dir, exist_ok=True)
        return {"added": self._queue.add(repo_id, revision, files, local_dir, quant)}

    @_safe
    def pause(self, job_id):
        self._queue.pause(job_id)
        return True

    @_safe
    def resume(self, job_id):
        self._queue.resume(job_id)
        return True

    @_safe
    def cancel(self, job_id):
        self._queue.cancel(job_id)
        return True

    @_safe
    def clear_finished(self):
        self._queue.clear_finished()
        return True

    @_safe
    def queue_state(self):
        return self._queue.snapshot()

    # ── library ───────────────────────────────────────────────────────
    @_safe
    def library(self):
        return store.scan_library()

    @_safe
    def delete_file(self, path):
        """Move to the Recycle Bin (recoverable), not a permanent delete."""
        path = os.path.abspath(path)
        if not os.path.isfile(path):
            return {"error": "File not found."}
        ok = _recycle(path)
        if ok:
            store.forget(path)
        return {"ok": ok}

    # ── OS helpers ────────────────────────────────────────────────────
    @_safe
    def open_folder(self, path):
        path = os.path.abspath(path)
        if os.path.isfile(path):
            subprocess.Popen(["explorer", "/select,", path])
        else:
            os.makedirs(path, exist_ok=True)
            os.startfile(path)
        return True

    @_safe
    def copy(self, text):
        p = subprocess.Popen(["clip"], stdin=subprocess.PIPE, creationflags=0x08000000)
        p.communicate(text.encode("utf-16-le"))
        return True

    @_safe
    def open_url(self, url):
        if url.startswith("https://huggingface.co/"):
            webbrowser.open(url)
        return True

    @_safe
    def choose_folder(self, start=None):
        import webview
        r = self._window.create_file_dialog(webview.FileDialog.FOLDER, directory=start or "")
        return r[0] if r else None

    # ── window controls (frameless) ───────────────────────────────────
    def minimize(self):
        self._window.minimize()

    def toggle_maximize(self):
        w = self._window
        zoomed = bool(ctypes.windll.user32.IsZoomed(self._hwnd())) if sys.platform == "win32" else getattr(self, "_max", False)
        if zoomed:
            w.restore()
            self._max = False
        else:
            w.maximize()
            self._max = True
        return not zoomed

    def close(self):
        threading.Thread(target=self._window.destroy, daemon=True).start()

    # ── resizing (a frameless window has no native border to drag) ───
    def _hwnd(self):
        u = ctypes.windll.user32
        try:
            return int(self._window.native.Handle.ToInt64())
        except Exception:
            return u.FindWindowW(None, "Capstan")

    def begin_resize(self, edge):
        """Called on mousedown on an edge zone. Follows the cursor until the button is released.

        Done with GetCursorPos + SetWindowPos from a worker thread, so it doesn't depend on
        mouse capture inside WebView2. edge: n, s, e, w, ne, nw, se, sw.
        """
        if sys.platform != "win32" or getattr(self, "_resizing", False):
            return
        u = ctypes.windll.user32
        hwnd = self._hwnd()
        if not hwnd or u.IsZoomed(hwnd):
            return
        self._resizing = True
        threading.Thread(target=self._resize_loop, args=(hwnd, edge), daemon=True).start()

    def begin_move(self, grab_x=0.5):
        """Called on mousedown on the title bar. Moves the window with the cursor until release.

        grab_x: where along the title bar the user grabbed (0..1), so a maximized window
        restores under the cursor at the same relative spot.
        """
        if sys.platform != "win32" or getattr(self, "_resizing", False):
            return
        hwnd = self._hwnd()
        if not hwnd:
            return
        self._resizing = True
        threading.Thread(target=self._move_loop, args=(hwnd, float(grab_x)), daemon=True).start()

    def _move_loop(self, hwnd, grab_x):
        import ctypes.wintypes as wt
        import time
        u = ctypes.windll.user32
        u.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                                   ctypes.c_int, ctypes.c_int, ctypes.c_uint]
        r, p = wt.RECT(), wt.POINT()
        try:
            u.GetCursorPos(ctypes.byref(p))
            x0, y0 = p.x, p.y
            restored = not u.IsZoomed(ctypes.c_void_p(hwnd))
            u.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(r))
            l0, t0 = r.left, r.top
            last = None
            while u.GetAsyncKeyState(0x01) & 0x8000:
                u.GetCursorPos(ctypes.byref(p))
                dx, dy = p.x - x0, p.y - y0
                if not restored:
                    if abs(dx) + abs(dy) < 6:          # a click, not a drag
                        time.sleep(0.008)
                        continue
                    self._window.restore()
                    self._max = False
                    time.sleep(0.05)
                    u.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(r))
                    w = r.right - r.left
                    l0, t0 = p.x - int(w * grab_x), p.y - 18
                    x0, y0 = p.x, p.y
                    dx = dy = 0
                    restored = True
                    self._emit({"type": "window", "maximized": False})
                pos = (l0 + dx, t0 + dy)
                if pos != last:
                    last = pos
                    u.SetWindowPos(ctypes.c_void_p(hwnd), None, pos[0], pos[1], 0, 0, 0x0015)  # NOSIZE|NOZORDER|NOACTIVATE
                time.sleep(0.008)
        finally:
            self._resizing = False

    def _resize_loop(self, hwnd, edge):
        import ctypes.wintypes as wt
        import time
        u = ctypes.windll.user32
        u.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                                   ctypes.c_int, ctypes.c_int, ctypes.c_uint]
        try:
            scale = u.GetDpiForWindow(ctypes.c_void_p(hwnd)) / 96 or 1
        except Exception:
            scale = 1
        min_w, min_h = int(980 * scale), int(640 * scale)
        r, p = wt.RECT(), wt.POINT()
        u.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(r))
        u.GetCursorPos(ctypes.byref(p))
        x0, y0, l0, t0, r0, b0 = p.x, p.y, r.left, r.top, r.right, r.bottom
        last = None
        try:
            while u.GetAsyncKeyState(0x01) & 0x8000:          # left button still down
                u.GetCursorPos(ctypes.byref(p))
                dx, dy = p.x - x0, p.y - y0
                left, top, right, bottom = l0, t0, r0, b0
                if "e" in edge:
                    right = max(r0 + dx, l0 + min_w)
                if "s" in edge:
                    bottom = max(b0 + dy, t0 + min_h)
                if "w" in edge:
                    left = min(l0 + dx, r0 - min_w)
                if "n" in edge:
                    top = min(t0 + dy, b0 - min_h)
                rect = (left, top, right - left, bottom - top)
                if rect != last:
                    last = rect
                    u.SetWindowPos(ctypes.c_void_p(hwnd), None, *rect, 0x0014)  # NOZORDER | NOACTIVATE
                time.sleep(0.008)
        finally:
            self._resizing = False


def _recycle(path: str) -> bool:
    if sys.platform != "win32":
        return False

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [("hwnd", ctypes.c_void_p), ("wFunc", ctypes.c_uint), ("pFrom", ctypes.c_wchar_p),
                    ("pTo", ctypes.c_wchar_p), ("fFlags", ctypes.c_ushort), ("fAnyOperationsAborted", ctypes.c_int),
                    ("hNameMappings", ctypes.c_void_p), ("lpszProgressTitle", ctypes.c_wchar_p)]

    FO_DELETE, FOF_ALLOWUNDO, FOF_NOCONFIRMATION, FOF_SILENT = 3, 0x40, 0x10, 0x4
    op = SHFILEOPSTRUCTW(None, FO_DELETE, path + "\0", None, FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT, 0, None, None)
    return ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op)) == 0
