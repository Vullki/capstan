"""Capture the Capstan window to a PNG, even when other windows cover it.

Usage: python tools/capture.py <out.png> [--pid N] [--size WxH]
Uses PrintWindow with PW_RENDERFULLCONTENT, so WebView2 content is included.
"""
import ctypes
import ctypes.wintypes as wt
import sys

from PIL import Image

TITLE = "Capstan"
user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
user32.SetProcessDPIAware()


def find_window(pid: int | None = None) -> int:
    """The Capstan window; with pid, the one owned by that process (when several are open)."""
    if pid is None:
        return user32.FindWindowW(None, TITLE)
    found = []
    proc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    def cb(hwnd, _):
        owner = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        buf = ctypes.create_unicode_buffer(64)
        user32.GetWindowTextW(hwnd, buf, 64)
        if owner.value == pid and buf.value == TITLE and user32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True

    user32.EnumWindows(proc(cb), 0)
    return found[0] if found else 0


def capture(out: str, pid: int | None = None, size: tuple[int, int] | None = None) -> None:
    hwnd = find_window(pid)
    if not hwnd:
        sys.exit("Capstan window not found")
    if size:   # resize first (used for README shots)
        import time
        r0 = wt.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(r0))
        user32.SetWindowPos(hwnd, None, max(r0.left, 0), max(r0.top, 0), size[0], size[1], 0x14)
        time.sleep(2.5)
    r = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    hdc = user32.GetWindowDC(hwnd)
    mdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mdc, bmp)
    user32.PrintWindow(hwnd, mdc, 2)  # PW_RENDERFULLCONTENT

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [("biSize", wt.DWORD), ("biWidth", wt.LONG), ("biHeight", wt.LONG), ("biPlanes", wt.WORD),
                    ("biBitCount", wt.WORD), ("biCompression", wt.DWORD), ("biSizeImage", wt.DWORD),
                    ("biXPelsPerMeter", wt.LONG), ("biYPelsPerMeter", wt.LONG), ("biClrUsed", wt.DWORD),
                    ("biClrImportant", wt.DWORD)]

    bi = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
    Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).convert("RGB").save(out)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mdc)
    user32.ReleaseDC(hwnd, hdc)
    print(f"{w}x{h}")


if __name__ == "__main__":
    # python tools/capture.py out.png [--pid N] [--size 1440x1000]
    args = sys.argv[1:]
    pid = int(args[args.index("--pid") + 1]) if "--pid" in args else None
    size = tuple(int(v) for v in args[args.index("--size") + 1].split("x")) if "--size" in args else None
    capture(args[0], pid, size)
