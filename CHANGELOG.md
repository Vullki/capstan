# Changelog

All notable changes to Capstan (called DΛЯK Pull before 1.2.0). The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow [Semantic Versioning](https://semver.org/).

## [1.4.0] — 2026-11-23 · model type badges and type filter

### Added
- **Type badges** on every search row and repo page: Text, Vision, Omni, Speech-to-text, Text-to-speech, Music, Audio gen (sound effects, text-to-audio), Audio, Image gen, Video gen, Embeddings, or an honest **Unlabeled** when nothing says what a model does.
  - Evidence, strongest first: Hugging Face's own type label, then the repo's tags, then its files. When the official label exists, tags only add types from the same family (a stray `feature-extraction` tag doesn't make a chat model an embedding model). An `mmproj` file means vision input, unless the model is about audio or generates media.
  - About 1 in 5 GGUF repos has no official type (including `unsloth/Qwen3.8-27B-GGUF`); these are still classified from their tags and files. On a repo page, a still-unlabeled repo borrows its base model's type.
  - **Vision · no mmproj** marks repos labeled vision that ship no projector, since image input won't work from the GGUF alone.
- **Type filter** under Sort: All · Text · Vision · Audio · Image · Video · Embeddings, remembered like Sort. A filter runs Hugging Face's own type query and a wider 200-repo search classified by Capstan, in parallel, then merges them, so repos Hugging Face left untagged still show up.

### Changed
- **Non-chat models** (image, video, music, text-to-speech, embeddings) have no context cache: their repo page hides the context slider and KV type, and the fit light counts the file plus runtime overhead.

## [1.3.2] — 2026-11-23 · machine strip with Windows text scaling

### Fixed
- **Machine strip totals hidden on normal-size windows.** Windows' Accessibility "Text size" makes WebView2 zoom the page (at 114%, a 1264 px window has ~1109 CSS px), so window-size breakpoints misfired. The strip now uses a CSS container query on its own width and drops things in order of importance: gauge width, then drive bars, then totals, then the GPU name. Verified at 1264 px with 114% text (totals shown) and at the 980 px minimum (no overlap).

## [1.3.1] — 2026-11-23 · polish and screenshots

### Fixed
- **Fit text could contradict itself** ("Won't run · needs 11.4 GB · you have 12.0 GB"). The check keeps margins (5% of VRAM, 10% of RAM), so the text now shows the same **usable** figure the check uses. "Won't run" always means needs > usable.
- **Stale UI after updates:** the WebView now runs in private mode, so a cached old stylesheet can never mix with new code.
- **Long repo titles** (e.g. `Qwen3.5-9B-…-GGUF`) split after hyphens, so each piece carries its own metal gradient (DESIGN.md §3.4), and the header has a dark halo over bright Mist.
- **Hero headline:** a stronger, wider halo, so the ends ("model.") keep their edge over the brightest smoke. The home-screen Mist is slightly dimmer (0.32).
- **Machine strip:** near-solid background and visible empty gauge segments, so the VRAM gauge no longer looks broken where the Mist shows through.
- **Settings files with a BOM** (written by Windows PowerShell 5.1 or some editors) are read correctly instead of silently falling back to defaults.

### Added
- **README screenshots:** the search screen, and a repo at 128K context showing Partial (GPU layer counts) and Won't run.
- **`tools/capture.py --pid N --size WxH`:** captures a specific Capstan window at a set size.

## [1.3.0] — 2026-11-23 · open-source ready

### Added
- **MIT license** (`LICENSE`), © 2026 The BlackWolf (DΛЯK), with third-party font and icon licenses listed.
- **Satoshi fetched on first run** (`app/core/fonts.py`). Satoshi is a Fontshare closed-source font (ITF Free Font License) that may not be redistributed, so the repo no longer carries its files.
  - The app downloads the three weights it uses from Fontshare in the background, then swaps them in live without a restart.
  - Until then, or when offline, the UI uses the bundled Inter Display.
  - Verified: with the files removed, the app fetched all three byte-identical to the originals and switched the headline font live.

### Changed
- **`.gitignore` hardened for a public repo:** excludes the private session memory (`.remember/`), agent config (`.claude/`, `CLAUDE.md`), `.env*`, partial downloads (`*.part`), the Satoshi files, and the original icon handoff files in the root.
- **README:** License section, a first-run font note, and corrected font credits.

## [1.2.0] — 2026-11-23 · renamed to Capstan

### Changed
- **New name: Capstan** (wordmark **CΛPSTΛN**), ahead of an open-source release. A capstan is the winch that hauls heavy loads in under tension. "DΛЯK Pull" was too generic to find, and the new name was checked against PyPI and GitHub for collisions in AI tooling.
- **System-facing names use plain `Capstan`:** window title, `Capstan.lnk`, AppUserModelID `BlackWolf.Capstan`, `Capstan.bat` and `Capstan (debug).bat`, icon files `capstan*`, and the project folder.
- **Data folder:** `%APPDATA%\DARK Pull` → `%APPDATA%\Capstan`, moved automatically on first start. The WebView profile now lives inside it too. The override variable is `CAPSTAN_DATA` (was `DARKPULL_DATA`).
- **Settings → about line:** shows `CΛPSTΛN <version> · by DΛЯK · The BlackWolf` and the real data folder.
- **New app icon, designed by The BlackWolf:** a brushed-silver block lowered into a U-shaped bay, with two motion bars above it. It's the capstan pull, drawn literally.
  - Built on the design system's exact silver stops and brushed grain.
  - The full mark is for large sizes; `capstan-icon-small.svg` is a flatter, brighter mark that stays crisp at 16–32 px.
  - The set: `capstan.ico` (16–256), 13 PNG sizes (16–1024), and black/white glyphs (`design/icon/`).
  - The 1.1.0 wolf icon is archived in `design/icon/wolf-concept/`.

## [1.1.0] — 2026-11-23 · icon, shortcut, window

### Added
- **App icon:** a faceted brushed-silver wolf head whose snout narrows into a download chevron above a landing bar, with one crimson eye (`design/icon/`).
  - `dark-pull.svg` is the full mark; `dark-pull-small.svg` is a simplified mark for 16–32 px.
  - `render.py` renders both through headless Edge into PNGs and a multi-size `.ico` (16–256 px).
- **Window and taskbar icon:** the window gets the wolf icon through `WM_SETICON`. The process sets its own AppUserModelID (`BlackWolf.DARKPull`), so the app has its own taskbar entry instead of grouping under Python.
- **`tools/install-shortcut.ps1`:** creates a Desktop shortcut (add `-StartMenu` for a Start menu one) with the icon and the matching AppUserModelID. It uses the Unicode `IShellLinkW` API, because `WScript.Shell` saves paths as ANSI and broke the `DΛЯK Pull` folder name.
- **Resizable frameless window:** invisible edges and corners. A Win32 loop (`GetCursorPos` + `SetWindowPos`) follows the cursor and keeps the 980×640 minimum.
- **Title bar drag**, done the same way. Double-click maximizes; dragging a maximized window restores it under the cursor.
- **Launch options:** `--open <repo or link>` opens a repo at start; `--view library|queue|settings` opens a view.
- **`tools/capture.py`:** captures the app window to PNG with `PrintWindow`, even when other windows cover it (used for the README screenshots).
- **Title bar mark and favicon.**
- **`DARKPULL_DATA`** environment variable to use another data folder (for tests).

### Fixed
- **Window drag:** pywebview's built-in drag region did not move the window (Python 3.14, WebView2), so it's replaced by our own.
- **Empty-search list:** the list followed "Trending" while "Downloads" was highlighted. It now follows the selected sort, and the heading says which.
- **Hero headline:** the last word lost contrast over bright Mist. The hero now has the soft dark halo from DESIGN.md §3.4.
- **Machine strip at narrow widths:** values overlapped. Below 1180 px it drops totals and drive bars, and the gauge gets finer.
- **Destination drive marker:** the `◂` wrapped onto two lines. It's an underline now.

## [1.0.0] — 2026-11-23 · first build

### Added
- **Backend (`app/core/`):**
  - **Hub:** live search, link parsing (repo IDs, URLs, file links), and file listing with GGUF grouping (split parts merged, mmproj separated, quant detection, sorted small to large).
  - **GGUF header reader** over HTTP range requests. It fetches only the metadata (a few MB), with no extra dependency.
  - **Fit estimator:** weights + KV cache + CUDA overhead; handles hybrid linear-attention and sliding-window layers; computes partial-offload GPU layers; f16/q8_0/q4_0 KV cache.
  - **Machine stats** through NVML, psutil and disk usage, naming known model runners that hold VRAM.
  - **Download queue:** one worker process per file, pause/resume/cancel, persisted across restarts.
  - **Resumable downloader** of our own, with a `.part` file, HTTP Range, retries and a SHA-256 check.
  - **Store:** settings, history, header cache and library scan in `%APPDATA%\DARK Pull`.
- **UI (`app/ui/`):**
  - frameless window with a glass title bar, the machine strip (segmented VRAM gauge) and a side rail
  - Search, Repo, Queue, Library and Settings views
  - Mist background (half resolution, 24 fps, pauses when hidden), word-split metal headlines, blur-in rows, toasts, and a native `<dialog>` for confirmations
  - bundled fonts (Satoshi, Inter Display, Plus Jakarta Sans, JetBrains Mono) and Phosphor duotone icons
- **Launchers:** `DARK Pull.bat` and `DARK Pull (debug).bat`.

### Verified
- **GGUF headers** parsed for Qwen3.5 9B (hybrid: 8 full-attention layers of 33), Llama 3.2 3B and Gemma 3 4B (sliding window 1024). The Llama 3B KV cache at 8K is 896 MiB, the same figure llama.cpp reports.
- **Downloader:** stopped at 86 MB, resumed from byte 85,983,232, finished, and the SHA-256 matched Hugging Face.
- **Queue:** run, pause, resume and done, with history and UI events, tested headlessly with a separate data folder.
- **App window:** launches with the live machine strip, trending search results and the Settings view (seen on screen). It read a GGUF header from a repo opened in the UI, and the log is clean.

### Not verified yet
- The fit lights and context slider in the repo view were not watched on screen during this build (the window was in use at the time).
- Library delete (Recycle Bin) and the folder picker were not clicked through.

### Changed from the spec
- **Downloads use our own resumable downloader, not `hf_hub_download`.** In `huggingface_hub` 2.x, `hf_hub_download` writes each run to a new temp file and deletes it on failure, so it never resumes. With Xet the partial file stays at 0 bytes. Measured on this line: HTTP and Xet both took about 78 s for 851 MB.

## [0.0.0] — 2026-11-23 · setup

### Added — 2026-11-23
- **Project folder and structure:** `design/`, `app/core/`, `app/ui/assets/{fonts,icons}`.
- **`design/DESIGN.md`:** a pinned copy of `#DΛЯK_DESIGNS/designv2.md` (Brushed Silver Noir v2, system 1.1.0).
- **`design/reference-shaders.js`:** the Mist and liquid-chrome shader from `#DΛЯK_DESIGNS`, kept for reusing the Mist background.
- **`app/ui/tokens.css`:** DESIGN.md §2 tokens unchanged, plus app additions: dense surface steps, a compact type scale, spacing, fit-status tokens, progress-bar metal, and app motion durations.
- **`SPEC.md`:** features, architecture, the fit-estimate method, the design mapping, layout, and build order.
- **No app code yet.**
