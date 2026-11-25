# Capstan privacy policy

_Last updated: 25 November 2026. Applies to Capstan 1.5.0 and later, from the Microsoft Store, the GitHub installer, or source._

Capstan is a Windows app by VULLKI that finds models on Hugging Face and checks whether they fit your computer before you download them. It runs on your PC. VULLKI runs no server for it and never receives your data.

## What Capstan collects

**Nothing.** No telemetry, no analytics, no crash reports, no advertising IDs, no account with VULLKI.

## What Capstan sends, and to whom

Capstan only talks to these services, and only to do what you ask:

| Service | Why | What it sees |
|---|---|---|
| **Hugging Face** (`huggingface.co` and its file storage) | Search, repo and file listings, reading a model's header for the fit check, and downloading the files you choose | Your searches and the repos and files you open or download, like any visit to huggingface.co. If you're logged in, your Hugging Face token is sent with these requests so gated models work. Their privacy policy: https://huggingface.co/privacy |
| **Fontshare** (`api.fontshare.com` and its CDN) | Downloading the Satoshi display font once, on first run | A normal font download request |

Like any internet request, these services see your IP address. Capstan sends no other information about you or your computer.

## What Capstan keeps on your PC

- **Settings, download queue, download history and a cache of model headers**, in `%APPDATA%\Capstan` (the Store build keeps them in Windows' private folder for the app, under `%LOCALAPPDATA%\Packages`).
- **Your GPU, memory and disk readings** are read live from Windows and your NVIDIA driver to work out the fit. They're shown to you and never sent anywhere.
- **Your Hugging Face token**, only if you log in, in the same file the official Hugging Face tools use (`%USERPROFILE%\.cache\huggingface\token`). Log out in Settings to remove it.
- **The models you download**, in the folder you choose.

Uninstalling the Store app removes its private data folder. Uninstalling the GitHub installer version keeps your settings and models; delete `%APPDATA%\Capstan` to remove the settings.

## Children

Capstan isn't directed at children and collects no personal information from anyone.

## Changes

If this policy changes, the new version will be published here with a new date.

## Contact

VULLKI: contact@vullki.com · https://vullki.com · Issues: https://github.com/Vullki/capstan/issues
