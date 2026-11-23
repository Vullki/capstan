# Model Type Badges + Type Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show what every model does (Text, Vision, Speech, Music, Image, Video, Embeddings…) and let Search filter by type without hiding untagged repos.

**Architecture:** One pure classifier in a new `app/core/modeltype.py` turns `pipeline_tag` + tags + file names into badges and filter buckets. `hub.search` merges a Hub-side `pipeline_tag` query set with a 200-result general pool when a filter is active (approach C). The UI renders badges from the `types` list the backend returns.

**Tech Stack:** Python 3.14, huggingface_hub, pywebview, vanilla JS/CSS. Tests: stdlib `unittest` (no pytest on this PC, no new deps).

**Spec:** `docs/superpowers/specs/2026-11-23-model-type-badges-design.md`

## Global Constraints
- No new dependencies.
- Unknown type is shown as **Unlabeled**, never guessed.
- Filter chips, in order: `all, text, vision, audio, image, video, embeddings`. Setting key `type_filter`, default `"all"`.
- General pool is 200 when a filter is active, 40 otherwise.
- Version `1.4.0`.

## Review Focus
1. Repo with an audio `mmproj` (LiquidAI/LFM2.5-Audio-1.5B-GGUF) must not get Vision. → test in Task 1.
2. Vision-labeled repo without an `mmproj` file gets `vision_no_proj`. → test in Task 1.
3. Repo with no tag and no tags at all → `["unlabeled"]`, excluded from every filter but All. → test in Task 1.
4. A Hub query per `pipeline_tag` that fails (network) must not fail the whole search; return what succeeded. → handled in Task 2 with a try/except per future.
5. Same repo returned by both queries appears once. → test in Task 2 (`merge_results`).

---

### Task 1: Classifier

**Files:**
- Create: `app/core/modeltype.py`
- Test: `tests/test_modeltype.py`

**Interfaces:**
- Produces: `classify(pipeline_tag: str | None, tags: list[str], files: list[str]) -> dict` returning
  `{"types": list[str], "buckets": list[str], "vision_projector": bool}`.
  Type ids: `text, vision, vision_no_proj, stt, tts, music, image_gen, video_gen, embeddings, omni, unlabeled`.
  Buckets: subset of `text, vision, audio, image, video, embeddings`.
- Produces: `BUCKET_PIPELINES: dict[str, list[str]]` — Hub `pipeline_tag`s queried per bucket.

- [ ] Write tests: Qwen3.8-27B (None, [conversational], [x.gguf, mmproj-F16.gguf]) → types `[text, vision]`, buckets ⊇ `{text, vision}`; YuE2 (None, [music-generation]) → `[music]`, buckets `[audio]`; LFM2.5-Audio (None, [audio, speech, conversational], [mmproj]) → no `vision`; image-text-to-text with no mmproj → contains `vision_no_proj`; (None, [gguf], []) → `[unlabeled]`, buckets `[]`; feature-extraction → `[embeddings]`; image-text-to-video → `[video_gen]`; any-to-any → `omni`, buckets ⊇ `{text, vision}`.
- [ ] Run `python -m unittest discover -s tests` → fails (module missing).
- [ ] Implement per spec table. Vision implies Text bucket.
- [ ] Run tests → pass. Commit.

### Task 2: Merged search + repo types

**Files:** Modify `app/core/hub.py`, `app/api.py:90-91`, `app/core/store.py:35`. Test: `tests/test_hub_merge.py`.

**Interfaces:**
- Consumes: `modeltype.classify`, `BUCKET_PIPELINES`.
- Produces: `hub.search(query, sort="downloads", gguf_only=True, type_filter="all", limit=40) -> list[dict]`; each row gains `types: list[str]`, `buckets: list[str]`.
- Produces: `hub.merge_results(lists: list[list[dict]], sort: str) -> list[dict]` (dedupe by `id`, sort by `downloads|likes|updated|trending` desc).
- Produces: `hub.repo()` adds `types`, `vision_projector`; falls back to the base model's `pipeline_tag` (one `model_info` call) only when types == `["unlabeled"]`.
- `api.search(query, sort, gguf_only, type_filter="all")`; `DEFAULT_SETTINGS["type_filter"] = "all"`.

- [ ] Test `merge_results`: duplicate id kept once; ordering by downloads desc.
- [ ] Implement: expand `siblings`, `cardData`; keep `trending_score` on rows for sorting; ThreadPoolExecutor runs the general query (limit 200) plus one per `BUCKET_PIPELINES[type_filter]` (limit 40 each), each wrapped so one failure is skipped; filter rows whose `buckets` contain `type_filter`; cap at 60.
- [ ] Live check: `search("", type_filter="text")` contains `unsloth/Qwen3.8-27B-GGUF`; `type_filter="audio"` contains `Serveurperso/YuE2-GGUF`. Commit.

### Task 3: UI — badges, filter row, repo page

**Files:** Modify `app/ui/index.html:65-74`, `app/ui/app.js` (`resultRow`, `runSearch`, init/binding ~703-728, `renderRepo`, `refit`), `app/ui/app.css`, `app/core/fit.py`, `app/api.py:116`.

**Interfaces:**
- Consumes: row `types`, repo `types`/`vision_projector`.
- Produces: JS `typeChips(types) -> string`; `TYPE_META` map id → {label, icon}. Labels: Text, Vision, "Vision · no mmproj", Speech-to-text, Text-to-speech, Music, Image gen, Video gen, Embeddings, Omni, Unlabeled.
- `fit.estimate(..., text=True)`; when `text=False` KV = 0. `api.fit(..., text=True)` passes it through.

- [ ] Filter seg `data-type` under Sort, persisted via `call('settings', {type_filter})`, re-runs search; results meta says "N text models" etc.
- [ ] Badges in search rows (before size chip) and in repo header; `chip--type` style; `vision_no_proj` uses `chip--dim` with a tooltip explaining image input needs an mmproj.
- [ ] Repo page: if no type in `text|vision|omni` and types ≠ unlabeled → hide context slider and KV select, call fit with `text=false`; mmproj caption says "Projectors (mmproj)" when not vision.
- [ ] Launch app, check: Search shows badges; each filter chip returns rows; Qwen3.8-27B page shows Text + Vision; YuE2 page hides context.

### Task 4: Release
- [ ] `VERSION = "1.4.0"` in `app/api.py`; CHANGELOG 1.4.0 entry; README feature line. Commit.
