"""Capstan: launch the window."""
from __future__ import annotations

import os
import sys

# Installed build (PyInstaller): the app's files sit in sys._MEIPASS; from source, next to this file.
HERE = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# Each download runs in its own process. From source that is "python -m core.worker";
# the installed build has no python.exe, so it starts itself again with --worker.
if __name__ == "__main__" and len(sys.argv) > 2 and sys.argv[1] == "--worker":
    from core import worker
    sys.argv = [sys.argv[0], sys.argv[2]]
    sys.exit(worker.main())

import webview  # noqa: E402

from api import Api  # noqa: E402
from core import store  # noqa: E402

TITLE = "Capstan"
APP_ID = "VULLKI.Capstan"   # must match the shortcut (tools/install-shortcut.ps1)
ICON = os.path.join(HERE, "ui", "assets", "capstan.ico")


def _is_packaged() -> bool:
    """True inside the Microsoft Store (MSIX) package, where Windows owns the app's identity."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        n = ctypes.c_uint32(0)
        # ERROR_INSUFFICIENT_BUFFER (122) = has a package; APPMODEL_ERROR_NO_PACKAGE (15700) = doesn't
        return ctypes.windll.kernel32.GetCurrentPackageFullName(ctypes.byref(n), None) == 122
    except Exception:
        return False


def _set_app_id():
    """Own taskbar group and icon, instead of being grouped under Python."""
    if sys.platform == "win32" and not _is_packaged():   # a packaged app already has its own ID
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
    # private_mode: no persistent WebView cache, so an update is never hidden behind stale CSS/JS
    webview.start(debug=debug, http_server=True, private_mode=True,
                  storage_path=os.path.join(store.DATA_DIR, "webview"))


if __name__ == "__main__":
    main()
