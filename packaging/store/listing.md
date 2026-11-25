# Microsoft Store listing: Capstan by VULLKI

Everything Partner Center asks for, ready to paste. Language: English (United States).

## Product setup

| Field | Value |
|---|---|
| Reserved name | **Capstan by VULLKI** (plain "Capstan" was taken). Store ID `9PDMZQ06VL6B`, link https://apps.microsoft.com/detail/9PDMZQ06VL6B. Must equal `display_name` in `msix/identity.json`. |
| Package type | MSIX (`Capstan-<version>.msix`, x64). Microsoft signs it. |
| Pricing | Free |
| Markets | All markets |
| Visibility | Public |
| Category | **Developer tools** (subcategory: none) |
| Privacy policy URL | `https://github.com/Vullki/capstan/blob/main/PRIVACY.md` (live once this branch is merged and pushed) |
| Website | `https://github.com/Vullki/capstan` |
| Support contact | `contact@vullki.com` |
| Copyright | `© 2026 VULLKI` |
| Additional license terms | `MIT License: https://github.com/Vullki/capstan/blob/main/LICENSE` |
| System requirements | Minimum: Windows 10 version 2004 (19041), x64, 8 GB RAM. Recommended: an NVIDIA GPU (for VRAM readings and fit lights) |
| Restricted capability `runFullTrust` | Justification: "Capstan is a desktop (Win32) app packaged as MSIX. It needs full trust to read GPU memory through the NVIDIA driver (NVML), list the user's drives, and write downloaded model files to the folder the user picks." |

## Short description (Store search results)

Find Hugging Face models and see whether each one fits your GPU before you download it.

## Description

Capstan finds AI models on Hugging Face and tells you, before you download anything, whether each one will run on your PC.

Search the Hub live, or paste any model link. For every GGUF file Capstan shows a fit light: Fits, Partial or Won't run. It reads the model's header straight from Hugging Face without downloading the file, then adds up the weights, the context cache at the context length you choose, and the runtime overhead, and compares that with the VRAM and RAM that are free right now. Hybrid and sliding-window models are handled, and the estimate matches llama.cpp's own figures.

When you've picked a file, Capstan downloads it with its own resumable downloader: pause, resume, survive a restart, and check every file against Hugging Face's SHA-256 so you know it arrived intact.

• Live Hub search with type badges: Text, Vision, Speech, Image and Video generation, Embeddings and more
• A fit light for every quant, for your GPU, at your context length
• A machine strip that shows free VRAM, RAM and disk space, and which app is holding your VRAM
• Resumable, verified downloads with a queue
• A library of the models already on your drives, LM Studio's folder included
• Gated models: log in with your own Hugging Face token

Private by design: no account, no telemetry, no analytics. Capstan talks only to Hugging Face, and to Fontshare once for its display font. Free and open source under the MIT License.

An NVIDIA GPU is needed for the VRAM readings and fit lights. Without one, search and downloads still work.

## What's new in this version

First release on the Microsoft Store.

## Product features (one per line)

- See whether each GGUF fits your GPU before downloading
- Fit check counts weights, context cache and runtime overhead
- Live Hugging Face search with model type badges
- Resumable downloads with SHA-256 verification
- Library of the models already on your drives
- No account, no telemetry: talks only to Hugging Face

## Search terms (max 7)

GGUF · Hugging Face · LLM · llama.cpp · local AI · VRAM · model downloader

## Screenshots (Desktop, PNG, at least 1366×768)

1. `docs/screenshot-search.png` (1919×1078): "Search the Hub live, or paste any model link."
2. `docs/screenshot-repo.png` (1440×1000): "Every quant gets a fit light for this PC, at your context length."

## Store logos

Optional. The package's own logos (`packaging/msix/Assets`) are used. For a 1:1 Store logo, upload `design/icon/png/capstan-1024.png` (300×300 minimum).

## Age rating (IARC questionnaire)

Category: **All other app types**. Answer **No** to every content question: no violence, sexual content, profanity, drugs, gambling or user interaction between people; it doesn't share the user's location; no in-app purchases; no ads. It does browse content from the internet (Hugging Face model listings): answer **Yes** to "unrestricted internet access", if asked. Expected result: suitable for everyone, possibly 12+/PEGI 12 where unrestricted internet counts.

## Notes for certification

"Capstan downloads AI model files from Hugging Face (huggingface.co) to a folder the user chooses. It needs no account; to test, search for 'qwen3', open a repo, tick a small file and press Pull. An NVIDIA GPU enables the fit lights; without one the app still searches and downloads."
