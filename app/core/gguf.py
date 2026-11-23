"""Read a GGUF file's metadata straight from Hugging Face, without downloading it.

GGUF layout (little-endian): magic "GGUF", u32 version, u64 tensor_count,
u64 kv_count, then kv_count key/value pairs, then tensor infos. We only need the
key/value pairs, which sit at the very start of the file. They are usually a few
MB, mostly the tokenizer arrays. We fetch ranges on demand until the parser is done.
"""
from __future__ import annotations

import struct
from functools import lru_cache

from huggingface_hub import hf_hub_url
from huggingface_hub.utils import build_hf_headers, get_session

CHUNK = 2 * 1024 * 1024          # first request: 2 MB
MAX_HEADER = 64 * 1024 * 1024    # give up past 64 MB of metadata

# GGUF value types
U8, I8, U16, I16, U32, I32, F32, BOOL, STR, ARR, U64, I64, F64 = range(13)
_SCALAR = {U8: "<B", I8: "<b", U16: "<H", I16: "<h", U32: "<I", I32: "<i",
           F32: "<f", BOOL: "<?", U64: "<Q", I64: "<q", F64: "<d"}
_SIZE = {k: struct.calcsize(v) for k, v in _SCALAR.items()}

# Keys we never need the contents of (big arrays): we skip them without decoding.
_SKIP_ARRAYS = ("tokenizer.ggml.tokens", "tokenizer.ggml.scores",
                "tokenizer.ggml.token_type", "tokenizer.ggml.merges")


class NeedMore(Exception):
    """The buffer ended before the parser finished."""


class _RemoteFile:
    def __init__(self, repo_id: str, filename: str, revision: str | None = None):
        self.url = hf_hub_url(repo_id, filename, revision=revision)
        self.headers = build_hf_headers()
        self.buf = b""

    def ensure(self, end: int) -> None:
        if end <= len(self.buf):
            return
        if end > MAX_HEADER:
            raise ValueError("GGUF metadata is larger than 64 MB")
        want = max(end, len(self.buf) * 2, CHUNK)
        start = len(self.buf)
        r = get_session().get(self.url, headers={**self.headers, "Range": f"bytes={start}-{want - 1}"},
                              follow_redirects=True, timeout=30)
        r.raise_for_status()
        data = r.content
        if r.status_code == 200:          # server ignored Range: take what we asked for
            data = data[start:want]
        if not data:
            raise ValueError("unexpected end of file")
        self.buf += data


class _Reader:
    def __init__(self, src: _RemoteFile):
        self.src, self.pos = src, 0

    def take(self, n: int) -> bytes:
        self.src.ensure(self.pos + n)
        b = self.src.buf[self.pos:self.pos + n]
        if len(b) < n:
            raise NeedMore
        self.pos += n
        return b

    def scalar(self, t: int):
        return struct.unpack(_SCALAR[t], self.take(_SIZE[t]))[0]

    def string(self) -> str:
        n = self.scalar(U64)
        return self.take(n).decode("utf-8", "replace")

    def skip_string(self) -> None:
        n = self.scalar(U64)
        self.src.ensure(self.pos + n)
        self.pos += n

    def value(self, t: int, keep: bool = True):
        if t == STR:
            return self.string() if keep else self.skip_string()
        if t == ARR:
            et, n = self.scalar(U32), self.scalar(U64)
            if et in _SIZE:
                size = _SIZE[et] * n
                if not keep or n > 4096:
                    self.src.ensure(self.pos + size)
                    self.pos += size
                    return {"array": et, "len": n}
                return list(struct.unpack(f"<{n}{_SCALAR[et][1]}", self.take(size)))
            if et == STR:
                if not keep or n > 4096:
                    for _ in range(n):
                        self.skip_string()
                    return {"array": et, "len": n}
                return [self.string() for _ in range(n)]
            return [self.value(et, keep) for _ in range(n)]
        return self.scalar(t)


@lru_cache(maxsize=256)
def read_metadata(repo_id: str, filename: str, revision: str | None = None) -> dict:
    """Return the GGUF key/value metadata (big tokenizer arrays reduced to their length)."""
    src = _RemoteFile(repo_id, filename, revision)
    rd = _Reader(src)
    if rd.take(4) != b"GGUF":
        raise ValueError("not a GGUF file")
    version = rd.scalar(U32)
    if version < 2:
        raise ValueError(f"GGUF v{version} is too old")
    tensors, kvs = rd.scalar(U64), rd.scalar(U64)
    meta: dict = {"__version": version, "__tensor_count": tensors}
    for _ in range(kvs):
        key = rd.string()
        t = rd.scalar(U32)
        meta[key] = rd.value(t, keep=not key.startswith(_SKIP_ARRAYS))
    meta["__header_bytes"] = rd.pos
    return meta


def model_shape(meta: dict) -> dict:
    """Pull out what the fit estimate needs, for any architecture."""
    arch = meta.get("general.architecture", "")

    def g(name, default=None):
        return meta.get(f"{arch}.{name}", default)

    layers = int(g("block_count", 0) or 0)
    heads = g("attention.head_count", 0)
    kv_heads = g("attention.head_count_kv", heads)
    embd = int(g("embedding_length", 0) or 0)

    # Per-layer arrays exist for some architectures (e.g. heterogeneous heads).
    def per_layer(v):
        if isinstance(v, list):
            return v
        if isinstance(v, dict):          # skipped big array: no per-layer info
            return None
        return [v] * layers if layers else []

    heads_l = per_layer(heads) or [0] * layers
    kv_l = per_layer(kv_heads) or heads_l
    head_dim = int(heads_l[0] and embd // heads_l[0] or 0) if heads_l else 0
    k_dim = int(g("attention.key_length", head_dim) or head_dim)
    v_dim = int(g("attention.value_length", k_dim) or k_dim)

    # Which layers keep a full-context KV cache.
    swa = int(g("attention.sliding_window", 0) or 0)
    swa_pattern = g("attention.sliding_window_pattern")
    full_interval = int(g("full_attention_interval", 0) or 0)  # hybrid linear-attention models
    layer_kind = []
    for i in range(layers):
        if full_interval:
            layer_kind.append("full" if (i + 1) % full_interval == 0 else "linear")
        elif isinstance(swa_pattern, list) and i < len(swa_pattern):
            layer_kind.append("swa" if swa_pattern[i] else "full")
        elif isinstance(swa_pattern, int) and swa_pattern > 1 and swa:
            layer_kind.append("full" if (i + 1) % swa_pattern == 0 else "swa")
        elif swa and arch.startswith(("gemma2", "gemma3", "gemma4", "cohere2")):
            layer_kind.append("full" if (i + 1) % (6 if arch != "gemma2" else 2) == 0 else "swa")
        else:
            layer_kind.append("full")
    if kv_l and all(k == 0 for k in kv_l):
        kv_l = heads_l

    # Recurrent state per linear-attention layer (hybrid models such as Qwen3.5), f32.
    ssm_inner = int(g("ssm.inner_size", 0) or 0)
    ssm_state = int(g("ssm.state_size", 0) or 0)
    ssm_conv = int(g("ssm.conv_kernel", 0) or 0)
    ssm_groups = int(g("ssm.group_count", 0) or 0)
    ssm_bytes = 4 * (ssm_inner * ssm_state + max(ssm_conv - 1, 0) * (ssm_inner + 2 * ssm_groups * ssm_state))

    tokens = meta.get("tokenizer.ggml.tokens")
    vocab = int(g("vocab_size", 0) or (tokens.get("len") if isinstance(tokens, dict) else len(tokens or [])) or 0)

    return {
        "architecture": arch,
        "name": meta.get("general.name"),
        "size_label": meta.get("general.size_label"),
        "layers": layers,
        "context_max": int(g("context_length", 0) or 0),
        "kv_heads": [int(x or 0) for x in kv_l],
        "k_dim": k_dim,
        "v_dim": v_dim,
        "sliding_window": swa,
        "layer_kind": layer_kind,
        "ssm_state_bytes": ssm_bytes,
        "vocab": vocab,
        "embedding": embd,
        "expert_count": int(g("expert_count", 0) or 0),
        "file_type": meta.get("general.file_type"),
    }
