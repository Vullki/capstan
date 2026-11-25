# PyInstaller spec: builds dist/Capstan/ (one folder, Capstan.exe + _internal/).
# Run through packaging/build.ps1, which also makes the installer and the MSIX.
import os
import re

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
APP = os.path.join(ROOT, "app")
UI = os.path.join(APP, "ui")

# The whole UI folder, except Satoshi: its licence forbids redistribution, so the
# app downloads it on first run instead (app/core/fonts.py).
datas = []
for folder, _dirs, files in os.walk(UI):
    for name in files:
        if re.match(r"Satoshi-.*\.woff2", name) or name.endswith((".tmp", ".part")):
            continue
        rel = os.path.relpath(folder, APP)
        datas.append((os.path.join(folder, name), rel))
datas.append((os.path.join(ROOT, "LICENSE"), "."))
datas.append((os.path.join(ROOT, "THIRD_PARTY_NOTICES.md"), "."))

a = Analysis(
    [os.path.join(APP, "main.py")],
    pathex=[APP],
    datas=datas,
    hiddenimports=["core.worker"],
    excludes=["tkinter", "pydoc_data", "test"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Capstan",
    icon=os.path.join(UI, "assets", "capstan.ico"),
    version=os.path.join(SPECPATH, "build", "version_info.txt"),
    console=False,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="Capstan", upx=False)
