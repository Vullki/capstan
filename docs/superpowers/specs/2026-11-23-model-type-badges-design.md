# Model type badges + type filter (Capstan 1.4.0)

## Why
People browsing the Hub can't tell a chat model from a music, video or embedding
model by name alone. Every search row and every repo page should say what the model
*does* at a glance, and Search should be able to narrow to one kind.

## Goals
- A type badge on every search row, link card and repo page.
- A type filter on Search: All · Text · Vision · Audio · Image · Video · Embeddings.
- Honest results: unlabeled repos are classified and still appear under the right filter.

## Non-goals / anti-goals
- No guessing dressed up as fact: if nothing tells us the type, the badge says **Unlabeled**.
- A filter that silently drops repos because Hugging Face left them untagged is a failure,
  even if it "works".
- No new dependencies.

## Facts this is built on (top 200 GGUF repos, 2026-11-23)
- 81% carry an official `pipeline_tag`; 19% carry none, including `unsloth/Qwen3.8-27B-GGUF`.
- Most untagged repos are still identifiable from tags (`conversational`, `music-generation`,
  `text-to-music`, `feature-extraction`, `i2v`, `vision`, `vlm`, `multimodal`, `audio`, `speech`)
  and from an `mmproj` file in the repo.
- Fetching 200 results with `siblings` (file names) expanded takes about 1 s.

## Approaches considered
- **A. Hub-side filter only** (`pipeline_tag=`): simple and deep, but hides every untagged repo. Rejected.
- **B. Local filter only** (fetch 200, classify, filter): honest, but rare types come back thin.
- **C. Both, merged** ✅ chosen by Bu Ajlan: with a type selected, run the Hub's own
  `pipeline_tag` queries *and* the general 200-result query in parallel, classify everything
  with our rules, keep only matches, de-duplicate, rank by the chosen sort.

## Classification (one function, `hub.classify()`, used by search and repo view)
Order of evidence: `pipeline_tag` → tags → files (`mmproj`) → (repo view only) base model's `pipeline_tag`.
A model can carry more than one badge (a VLM is **Text + Vision**).

| Badge | Filter chip | Evidence |
|---|---|---|
| Text | Text | text-generation, text2text-generation, `conversational` tag, translation, summarization |
| Vision | Vision (also counts as Text) | image-text-to-text, image-to-text, visual-question-answering, video-text-to-text; tags vision/vlm/multimodal; an `mmproj` file |
| Speech-to-text | Audio | automatic-speech-recognition, audio-text-to-text, audio-classification |
| Text-to-speech | Audio | text-to-speech, text-to-audio, tags speech/tts |
| Music | Audio | tags music-generation, text-to-music, music |
| Image gen | Image | text-to-image, image-to-image |
| Video gen | Video | text-to-video, image-to-video, image-text-to-video; tags i2v, t2v, video-generation |
| Embeddings | Embeddings | feature-extraction, sentence-similarity; tag embedding |
| Omni | (shows under Text and Vision) | any-to-any |
| Unlabeled | only under All | nothing matched |

**mmproj detail:** an `mmproj` file means Vision unless the evidence points to audio
(e.g. LFM2.5-Audio ships an audio projector), in which case it doesn't add Vision.
A repo labeled Vision with **no** `mmproj` file gets the badge "Vision · no mmproj",
because image input won't work in llama.cpp / LM Studio from the GGUF alone.

## UI
- **Search row:** type badges sit before the size chip, each with a Phosphor duotone icon,
  same chip style as today. Example: `[Text] [Vision · mmproj] [27B]  7.7M ♡6.3K 11d`.
- **Filter row:** a second segmented control under Sort with the 7 chips. Remembered in
  settings like Sort (`type_filter`, default `all`).
- **Results meta:** when filtering, "N text models" instead of "N results".
- **Repo page:** the same badges in the header chip row, with the base-model fallback
  (one extra `model_info` call, only when the repo itself is still Unlabeled).

## Backend changes
- `hub.search(query, sort, gguf_only, type_filter)`: expand `siblings`; raise the general
  pool to 200 when a filter is active (40 otherwise, as today); when a filter is active also
  run one Hub query per mapped `pipeline_tag` in a thread pool; merge, classify, filter, sort.
- `hub.repo()`: add `types` (list of badges) and `vision_projector` (bool).
- `api.search` passes `type_filter` through; `store` gets the `type_filter` default.

## My calls (Bu Ajlan can overrule)
- Vision models also appear under **Text**, since they are chat models too.
- Speech-to-text, TTS and Music all live under the one **Audio** chip; the badge shows which.
- For non-text types (Image, Video, Music, TTS, Embeddings), the repo page hides the context
  slider, because KV-cache sizing doesn't apply to them; the fit light then uses weights + overhead.
- Version bump to **1.4.0**, CHANGELOG + README updated.

## Left to the builder
- Exact icon per badge, chip spacing, and how many badges fit before wrapping on narrow windows.
