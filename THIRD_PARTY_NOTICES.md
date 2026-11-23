# Third-party notices

Capstan is MIT licensed (see [LICENSE](LICENSE)). These bundled assets keep their own licenses:

| Asset | Location | License |
|---|---|---|
| Inter Display, by Rasmus Andersson | `app/ui/assets/fonts/InterDisplay-*.woff2` | SIL Open Font License 1.1 |
| Plus Jakarta Sans, by Tokotype | `app/ui/assets/fonts/PlusJakartaSans-*.woff2` | SIL Open Font License 1.1 |
| JetBrains Mono, by JetBrains | `app/ui/assets/fonts/JetBrainsMono-*.woff2` | SIL Open Font License 1.1 |
| Phosphor Icons (duotone) | `app/ui/assets/icons/` | MIT License |

**Not included:** the **Satoshi** font by Indian Type Foundry. It's a Fontshare "Closed Source" font under the ITF Free Font License, which doesn't allow redistribution. Capstan downloads it from Fontshare on first run (`app/core/fonts.py`) and uses Inter Display until then.

Python dependencies (installed separately with pip, not bundled) are listed in `requirements.txt` and keep their own licenses.
