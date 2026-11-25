# Building Capstan for release

One script builds all three pieces from the source in `app/`:

| Output (in `packaging/out/`) | What | Where it goes |
|---|---|---|
| `Capstan-<version>-Setup.exe` | Inno Setup installer, per-user, no admin prompt | GitHub Releases |
| `Capstan-<version>.msix` | MSIX package, unsigned (Microsoft signs it) | Microsoft Store (Partner Center) |
| `dist/Capstan/` | The app bundle both are made from (PyInstaller, one folder) | not shipped on its own |

The version comes from `VERSION` in `app/api.py`. The MSIX gets `<version>.0`, because the Store needs the fourth number to be 0.

## One-time setup

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r packaging\requirements-lock.txt
winget install --id JRSoftware.InnoSetup -e --scope user
```

You also need the **Windows 10/11 SDK** (for `makeappx.exe`, `makepri.exe`, `signtool.exe` and the App Certification Kit).

For a Store build, copy `msix/identity.example.json` to `msix/identity.json` and fill in the values from **Partner Center → Capstan → Product management → Product identity**:

| identity.json | Partner Center |
|---|---|
| `name` | Package/Identity/Name |
| `publisher` | Package/Identity/Publisher (`CN=…`) |
| `publisher_display` | Package/Properties/PublisherDisplayName |
| `display_name` | the reserved app name |

None of these are secret: they're printed inside every published package.

## Build

```powershell
.\packaging\build.ps1                 # all three
.\packaging\build.ps1 -Skip msix      # leave a step out: bundle, installer, msix
```

The build stops if a Satoshi font file ends up in the bundle: its licence forbids redistribution, and the app downloads it on first run instead.

After changing the app icon, regenerate the MSIX logo set: `python packaging\msix\make_assets.py` (needs Pillow).

## Check before submitting

**Windows App Certification Kit (WACK).** It installs the package to test it, so it needs a signed copy. Sign a *test copy* with a temporary self-signed certificate whose subject equals the manifest's `Publisher`, trust it in `LocalMachine\TrustedPeople`, run the kit as administrator, then remove the certificate:

```powershell
& "${env:ProgramFiles(x86)}\Windows Kits\10\App Certification Kit\appcert.exe" reset
& "${env:ProgramFiles(x86)}\Windows Kits\10\App Certification Kit\appcert.exe" test -appxpackagepath <signed copy>.msix -reportoutputpath wack-report.xml
```

Last result (1.5.0, 2026-11-25): **overall WARNING = passes**, 22 of 24 tests pass. Two known flags, neither blocks submission:

- *Blocked executables* (optional test): a text scan finds strings like `cmd` and `CreateProcessW` inside the Python runtime, OpenSSL and the C runtime. Every Python app trips it.
- *DPI awareness* (warning): pywebview makes the process DPI-aware at runtime (`SetProcessDPIAware`), which a static scan can't see. Declaring Per-Monitor V2 in the manifest would silence it but change how the window scales, so it's left as is on purpose.

Upload the **unsigned** `.msix` from `packaging/out/` to the Store, never the test-signed copy.

**Quick packaged run without signing** (Developer Mode on):

```powershell
Add-AppxPackage -Register packaging\build\msix-layout\AppxManifest.xml
# Start menu → Capstan. Remove afterwards:
Get-AppxPackage *Capstan* | Remove-AppxPackage
```

## Store submission

Paste-ready listing text, age-rating answers and certification notes: [`store/listing.md`](store/listing.md). Privacy policy: [`../PRIVACY.md`](../PRIVACY.md).

1. Partner Center → **Apps and games → New product → MSIX or PWA app** → reserve the name.
2. Copy the product identity into `msix/identity.json`, then run `build.ps1`.
3. New submission: Pricing (Free, all markets), Properties (Developer tools, privacy policy URL), Age ratings (questionnaire), Packages (upload the `.msix`), Store listing (from `store/listing.md`, screenshots from `docs/`), Submission options (the certification notes).
4. Submit. Review usually takes a few business days.

## Updating

Bump `VERSION` in `app/api.py`, add a CHANGELOG entry, run `build.ps1`, upload the new `.msix` in a new Store submission, and attach the new `Setup.exe` to a GitHub release. The installer's `AppId` in `installer/capstan.iss` must never change: Windows uses it to recognise an upgrade.
