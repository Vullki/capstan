"""What does a model do? Badges and filter buckets from Hub metadata.

Evidence, strongest first: the official pipeline_tag, then the repo's tags,
then its files (an mmproj file is a vision projector for llama.cpp).
Nothing matched -> "unlabeled". We never guess.
"""
from __future__ import annotations

# Hub pipeline tags and free-form tags -> type id. Tags often repeat pipeline names,
# so one table serves both.
_TAG_TYPE = {
    # text
    "text-generation": "text", "text2text-generation": "text", "conversational": "text",
    "translation": "text", "summarization": "text", "question-answering": "text",
    # vision (image in, text out)
    "image-text-to-text": "vision", "image-to-text": "vision", "visual-question-answering": "vision",
    "video-text-to-text": "vision", "document-question-answering": "vision",
    "vision": "vision", "vlm": "vision", "multimodal": "vision",
    # everything in, everything out
    "any-to-any": "omni",
    # audio
    "automatic-speech-recognition": "stt", "audio-text-to-text": "stt", "audio-classification": "stt",
    "speech-recognition": "stt", "asr": "stt",
    "text-to-speech": "tts", "text-to-audio": "tts", "tts": "tts",
    "music-generation": "music", "text-to-music": "music", "music": "music",
    "audio-to-audio": "audio", "audio": "audio", "speech": "audio",
    # generation
    "text-to-image": "image_gen", "image-to-image": "image_gen",
    "text-to-video": "video_gen", "image-to-video": "video_gen", "image-text-to-video": "video_gen",
    "video-generation": "video_gen", "i2v": "video_gen", "t2v": "video_gen",
    # retrieval
    "feature-extraction": "embeddings", "sentence-similarity": "embeddings",
    "embedding": "embeddings", "embeddings": "embeddings",
}

# Display order of badges.
_ORDER = ["text", "vision", "vision_no_proj", "omni", "stt", "tts", "music", "audio",
          "image_gen", "video_gen", "embeddings"]

_BUCKETS = {
    "text": {"text", "vision", "vision_no_proj", "omni"},
    "vision": {"vision", "vision_no_proj", "omni"},
    "audio": {"stt", "tts", "music", "audio"},
    "image": {"image_gen"},
    "video": {"video_gen"},
    "embeddings": {"embeddings"},
}
BUCKETS = list(_BUCKETS)

# Hub pipeline tags queried directly when a filter is on (the Hub-side half of the search).
BUCKET_PIPELINES = {
    "text": ["text-generation", "image-text-to-text"],
    "vision": ["image-text-to-text", "any-to-any"],
    "audio": ["automatic-speech-recognition", "text-to-speech", "text-to-audio", "audio-text-to-text"],
    "image": ["text-to-image", "image-to-image"],
    "video": ["text-to-video", "image-to-video", "image-text-to-video"],
    "embeddings": ["feature-extraction", "sentence-similarity"],
}

_AUDIO = {"stt", "tts", "music", "audio"}


def classify(pipeline_tag: str | None, tags: list[str] | None, files: list[str] | None) -> dict:
    """files=None means "not known" (no mmproj judgement); [] means the repo is empty."""
    found: set[str] = set()
    for t in [pipeline_tag, *(tags or [])]:
        kind = _TAG_TYPE.get((t or "").lower())
        if kind:
            found.add(kind)

    names = [f.rsplit("/", 1)[-1].lower() for f in files] if files is not None else None
    has_proj = bool(names) and any("mmproj" in n for n in names)
    has_gguf = bool(names) and any(n.endswith(".gguf") for n in names)
    labeled_vision = "vision" in found

    # An mmproj is a vision projector unless everything else says the model is about audio.
    vision_projector = has_proj and (labeled_vision or not (found & _AUDIO))
    if vision_projector:
        found.add("vision")
        if not (found - {"vision"}):
            found.add("text")   # an untagged GGUF with a vision projector is a chat VLM
    elif labeled_vision and has_gguf:
        # Labeled vision, but no projector shipped: image input won't work from the GGUF alone.
        found.discard("vision")
        found.add("vision_no_proj")

    types = [t for t in _ORDER if t in found] or ["unlabeled"]
    buckets = [b for b, members in _BUCKETS.items() if found & members]
    return {"types": types, "buckets": buckets, "vision_projector": vision_projector}
