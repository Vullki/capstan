# Third-party notices

Capstan is MIT licensed (see [LICENSE](LICENSE)). These bundled assets keep their own licenses:

| Asset | Location | License |
|---|---|---|
| Inter Display, by Rasmus Andersson | `app/ui/assets/fonts/InterDisplay-*.woff2` | SIL Open Font License 1.1 |
| Plus Jakarta Sans, by Tokotype | `app/ui/assets/fonts/PlusJakartaSans-*.woff2` | SIL Open Font License 1.1 |
| JetBrains Mono, by JetBrains | `app/ui/assets/fonts/JetBrainsMono-*.woff2` | SIL Open Font License 1.1 |
| Phosphor Icons (duotone) | `app/ui/assets/icons/` | MIT License |

**Not included:** the **Satoshi** font by Indian Type Foundry. It's a Fontshare "Closed Source" font under the ITF Free Font License, which doesn't allow redistribution. Capstan downloads it from Fontshare on first run (`app/core/fonts.py`) and uses Inter Display until then.

## Running from source

Python dependencies are installed separately with pip (not part of this repository). They're listed in `requirements.txt` and keep their own licenses.

## The installer and the Microsoft Store package

From 1.5.0 the Windows builds (`Capstan-<version>-Setup.exe` and the MSIX) carry their own Python runtime and libraries, so nobody needs Python installed. These are included, each under its own license. Exact versions are in `packaging/requirements-lock.txt`.

| Component | License |
|---|---|
| Python 3.14 runtime | PSF License 2.0 |
| PyInstaller bootloader | GPL 2.0 with the PyInstaller bootloader exception (allows distributing the bundled app under any license) |
| pywebview, bottle, proxy_tools | BSD 3-Clause, MIT, MIT |
| pythonnet, clr_loader | MIT |
| Microsoft WebView2 SDK (`Microsoft.Web.WebView2.*.dll`, shipped inside pywebview) | Microsoft WebView2 SDK license (BSD-style) |
| huggingface_hub, hf-xet | Apache 2.0 |
| httpx2, httpcore2, h11, anyio, idna, truststore | BSD 3-Clause, BSD 3-Clause, MIT, MIT, BSD 3-Clause, MIT |
| psutil | BSD 3-Clause |
| nvidia-ml-py | BSD |
| filelock, fsspec, tqdm, PyYAML, click, colorama, typing_extensions | MIT, BSD 3-Clause, MPL 2.0 and MIT, MIT, BSD 3-Clause, BSD, PSF 2.0 |
| cffi, pycparser | MIT-0, BSD 3-Clause |

Satoshi is not in the installer or the MSIX either: the build script refuses to finish if a Satoshi file ends up in the bundle.
