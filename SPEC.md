# Capstan · Spec

> Named **DΛЯK Pull** until 1.2.0.

**What it is:** a Windows desktop app for finding and downloading models from Hugging Face, built for The BlackWolf's machine. It tells you whether a model will run on your PC *before* you download it.

**Status:** v1.0.0 built 2026-11-23. See `CHANGELOG.md` for what was verified. The downloader differs from §2: it's our own resumable HTTP downloader, because `hf_hub_download` in huggingface_hub 2.x doesn't resume.

**Design:** Brushed Silver Noir v2. See `design/DESIGN.md` (a pinned copy of `#DΛЯK_DESIGNS/designv2.md`) and `app/ui/tokens.css`.

---

## 1. Features

### 1.1 Live Hub search
- Results update as you type, with a ~300 ms debounce so the Hub isn't hit on every key.
- GGUF repos only by default. A toggle shows all models.
- Sort by downloads (default), trending, most liked, or recently updated.
- Each result shows author, repo name, downloads, likes, last update, and a size class (2B / 9B / 27B…) when the repo says it.
- Clicking a result opens its file list.

### 1.2 Paste a link
- Accepts a repo ID (`owner/name`), any `huggingface.co/...` URL (including `/blob/` and `/tree/` file links), or an `hf.co` short link.
- The repo opens with its file list. A file link pre-selects that file.

### 1.3 File list
- Every file with its real size.
- GGUFs grouped by quant (Q2_K … Q8_0, F16, BF16, IQ*). Split files (`-00001-of-00003.gguf`) count as one model with a combined size.
- `mmproj` (vision projector) files are labelled and suggested alongside the model.
- Checkboxes, so you take only what you want (the GUI form of `--include`).

### 1.4 Machine status and fit indicator
**Machine strip (always visible at the top):**
- **GPU:** RTX 3060 VRAM, total and *free right now*. If Ollama or LM Studio has a model loaded, the free figure shows it.
- **RAM:** total and available.
- **Disk:** free space on C:, D:, and the chosen destination drive.
- Refreshes every ~2 s while the window is visible, and pauses when it's hidden.

**Per-file fit light:**

| Level | Meaning | Look |
|---|---|---|
| **Fits** | Weights + KV cache + overhead fit in free VRAM | Bright silver, full gauge |
| **Partial** | Fits in VRAM + RAM; shows about how many layers go on the GPU | Mid silver, half gauge |
| **Won't run** | Bigger than free VRAM + RAM together | Crimson wolf eye, empty gauge |
| **Unknown** | Header not read yet, or not a GGUF | Charcoal, dashed gauge |
| **Disk** | A separate warning when the destination drive lacks space | Engraved label beside the light |

- A **context slider** (4K / 8K / 16K / 32K / 64K / 128K, capped at the model's max context) updates every light live.
- **"Free now" vs "Total" toggle:** judge against VRAM free right now, or the full 12 GB as if nothing else were loaded.
- Labelled as an estimate, with a safety margin on the "Fits" level.

### 1.5 Downloads
- A queue with per-file progress, speed, ETA, pause, resume and cancel.
- Resumes after a dropped connection or an app restart.
- Uses `hf_xet` acceleration when the repo supports it.
- **Destination:** default `D:\Models\<repo-name>`. You can pick a folder per download. The app warns *before* starting if the drive is short on space.
- Real filenames, no hashed blobs.
- Gated repos use your cached `hf auth login` token. If you lack access, it says so and links to the repo's access page.

### 1.6 Library
- Everything downloaded, with its size, source repo, quant and date.
- Open folder, copy path (ready for LM Studio, llama.cpp or our benchmark harness), delete (with confirmation).
- Scans the download roots, so files you got with `hf download` from the terminal show up too.

---

## 2. Architecture

| Layer | Choice | Why |
|---|---|---|
| Window | **pywebview** (Edge WebView2) | Native window, HTML/CSS UI, so the design system applies 1:1. Frameless, with a custom title bar. |
| Backend | **Python 3.14** + `huggingface_hub` 2.2.0 | The same library `hf.exe` uses; already installed. |
| Bridge | pywebview `js_api` | JS calls Python directly; Python pushes events (progress, machine stats) to JS. |
| GPU stats | `nvidia-ml-py` (NVML) | Real free and used VRAM, without shelling out to `nvidia-smi`. |
| RAM / disk | `psutil`, `shutil.disk_usage` | Already installed. |
| Downloads | One **child process per file** running `hf_hub_download` | Cancel or pause = stop the process. Resume = start it again; the `.incomplete` file continues. The UI never freezes. |
| Progress | Poll the growing `.incomplete` file size | Works the same with and without `hf_xet`. |
| Settings / history | JSON in `%APPDATA%\Capstan\` | No database needed. |
| Launch | `Capstan.bat` + a desktop shortcut | Double-click to open. |

### 2.1 How the fit estimate works
1. **Read the GGUF header without downloading the file.** HTTP range requests fetch only the start of the file. The header is the first few MB, and more is fetched if the tokenizer arrays are large. A small built-in parser reads the metadata. This is our own code, no extra dependency.
2. **Values read:** architecture, layer count, attention heads, KV heads, key/value head dimensions, max context length, sliding-window and hybrid-layer settings where the architecture has them.
3. **Estimate:**
   - weights = the file size (combined, for split files)
   - KV cache = 2 × layers × KV heads × head dim × context × 2 bytes (f16). Sliding-window and linear-attention layers are counted at their real window, not the full context.
   - overhead = CUDA context + compute buffer (~0.6–1.0 GB, scaling with context)
   - **GPU layers (partial)** = (free VRAM − KV cache − overhead) ÷ (weights ÷ layers)
4. **Safety margin:** "Fits" needs ~5% headroom, so an estimate that's just under 12 GB shows as "Partial", not "Fits".
5. **If the header can't be read** (not a GGUF, or a network error), fall back to file size + overhead and mark the light as approximate.

---

## 3. Design mapping (Brushed Silver Noir → desktop app)

`DESIGN.md` was written for marketing sites. This is how it applies to a dense utility app:

| System rule | In Capstan |
|---|---|
| `#000` stage, `#0D0D0D` surfaces | Same. Rows and panels use the app steps in `tokens.css` (`#090909`, `#141416`, `#1E1E20` hover). |
| Metal headlines | Window title, panel titles and empty states use the silver gradient, split into words (§3.3). Sized down to the app scale in `tokens.css`. |
| Engraved labels | Column headers, section labels, machine-strip labels: flat `#C2C2C2`, uppercase, 0.3em tracking. |
| Glass over solid | Title bar, side rail and the machine strip are blurred glass over the Mist. |
| Mist background (§6.3) | Behind the search home and empty states, at hero-underlay brightness (~0.35). Reuses `design/reference-shaders.js`. Pauses when the window is hidden. |
| "Something always alive" | Mist on the home screen; progress bars and the live VRAM gauge elsewhere. |
| Blur entrances, play once | Result rows and file rows blur in with a short stagger the first time they appear. |
| Phosphor duotone icons | Same, bundled locally. |
| Reduced motion | Mist becomes a still frame; entrances become fades. |
| Colour kept out | Status uses brightness, shape and words. The one exception is crimson for "won't run", the brand's wolf-eye accent. |

**Left out on purpose, because they don't fit a utility app:** the custom cursor, Lenis smooth scroll, tickers, the collage, and marketing-size type (92px H1).

**Fonts** (Satoshi, Plus Jakarta Sans, Inter Display, JetBrains Mono for IDs and paths) are bundled in `app/ui/assets/fonts`, so the app works offline.

---

## 4. Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│ DΛЯK PULL                         (glass title bar)        _  □  ×   │
├──────────────────────────────────────────────────────────────────────┤
│ GPU ▮▮▮▮▮▮▮▯▯▯ 3.1 / 12 GB FREE · RAM 9.4 / 16 GB · C: 37.9 · D: 68.6│
├──────┬───────────────────────────────────────────────────────────────┤
│  ⌕   │  [ search the Hub or paste a link ...................... ]   │
│Search│                                                               │
│  ▤   │  results / repo view                                          │
│Libr. │   ┌ repo header: owner/name · ↓ downloads · ♥ likes ──────┐   │
│  ⇣   │   │ context  4K ─●──────── 128K      [ Free now | Total ] │   │
│Queue │   │ ☐ Q4_K_M   5.6 GB   ● FITS                            │   │
│  ⚙   │   │ ☐ Q6_K     7.4 GB   ◐ PARTIAL · 30/36 layers          │   │
│Sett. │   │ ☐ F16     18.0 GB   ○ WON'T RUN                       │   │
│      │   └ destination D:\Models\<name>   [ PULL ] ──────────────┘   │
└──────┴───────────────────────────────────────────────────────────────┘
```

---

## 5. Build order (after the go-ahead)
1. Backend core: Hub search, repo file listing, link parsing, machine stats.
2. GGUF header reader and fit estimator, with tests against real repos.
3. Download worker processes: queue, progress, pause, resume, cancel.
4. UI shell: window, title bar, rail, machine strip, design tokens, fonts, icons.
5. Search, repo and fit views.
6. Queue and Library views.
7. Launcher, shortcut, README. Verified end to end with a real download to `D:\Models`.

## 6. Not in scope (for now)
- Registering models in Ollama. `ollama create` copies the file into its blob store, which doubles the storage.
- Non-GGUF fit estimates (safetensors, MLX, AWQ). They download fine but show "Unknown" fit.
- Uploading to the Hub.
