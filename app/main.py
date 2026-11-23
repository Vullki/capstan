"""Capstan: launch the window."""
from __future__ import annotations

import os
import sys

import webview

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from api import Api  # noqa: E402
from core import store  # noqa: E402

TITLE = "Capstan"
APP_ID = "BlackWolf.Capstan"   # must match the shortcut (tools/install-shortcut.ps1)
ICON = os.path.join(HERE, "ui", "assets", "capstan.ico")


def _set_app_id():
    """Own taskbar group and icon, instead of being grouped under Python."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
        except Exception:
            pass


def _set_window_icon(window):
    if sys.platform != "win32" or not os.path.exists(ICON):
        return
    try:
        import ctypes
        u = ctypes.windll.user32
        u.LoadImageW.restype = ctypes.c_void_p
        u.SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
        hwnd = None
        try:
            hwnd = int(window.native.Handle.ToInt64())
        except Exception:
            hwnd = u.FindWindowW(None, TITLE)
        if not hwnd:
            return
        big = u.LoadImageW(None, ICON, 1, 256, 256, 0x10)    # IMAGE_ICON, LR_LOADFROMFILE
        small = u.LoadImageW(None, ICON, 1, 32, 32, 0x10)
        u.SendMessageW(hwnd, 0x80, 1, big)     # WM_SETICON, ICON_BIG
        u.SendMessageW(hwnd, 0x80, 0, small)   # ICON_SMALL
    except Exception:
        pass


def main():
    debug = "--debug" in sys.argv

    def arg(name):
        return sys.argv[sys.argv.index(name) + 1] if name in sys.argv[:-1] else None

    _set_app_id()
    api = Api(open_target=arg("--open"), view=arg("--view"))
    window = webview.create_window(
        TITLE,
        url=os.path.join(HERE, "ui", "index.html"),
        js_api=api,
        width=1280, height=820, min_size=(980, 640),
        frameless=True, easy_drag=False,
        background_color="#000000",
        text_select=True,
    )
    api.attach(window)
    window.events.closing += lambda: api._queue.shutdown()
    window.events.shown += lambda: _set_window_icon(window)
    webview.start(debug=debug, http_server=True, private_mode=False,
                  storage_path=os.path.join(store.DATA_DIR, "webview"))


if __name__ == "__main__":
    main()
