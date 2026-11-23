"""Will this GGUF run on this machine? An estimate in the style of llama.cpp.

Memory on the GPU when everything is offloaded:
  weights      = the file size
  KV cache     = full-attention layers × context, sliding-window layers × window (f16),
                 plus the fixed recurrent state of linear-attention layers (hybrid models)
  overhead     = CUDA context + compute buffer (grows with vocab and context)

When it doesn't all fit, llama.cpp offloads N layers. Each offloaded layer brings
its weights and its share of the KV cache to the GPU.
"""
from __future__ import annotations

GB = 1024 ** 3
MARGIN = 0.95          # use at most 95% of the memory we judge against
UBATCH = 512           # llama.cpp default micro-batch
CUDA_CONTEXT = 0.40 * GB


def kv_cache_bytes(shape: dict, ctx: int, kv_bytes: float = 2.0) -> int:
    """KV cache at a given context. kv_bytes: 2 for f16, 1 for q8_0, ~0.56 for q4_0."""
    total = 0
    k, v = shape["k_dim"], shape["v_dim"]
    window = shape.get("sliding_window") or 0
    kv_heads = shape["kv_heads"] or [0] * shape["layers"]
    for i, kind in enumerate(shape["layer_kind"]):
        heads = kv_heads[i] if i < len(kv_heads) else kv_heads[-1]
        if kind == "linear":
            total += shape.get("ssm_state_bytes", 0)
            continue
        n = min(ctx, window) if kind == "swa" and window else ctx
        total += heads * (k + v) * n * kv_bytes
    return int(total)


def overhead_bytes(shape: dict | None, ctx: int) -> int:
    """CUDA context + compute buffer. Rough, but it scales the right way."""
    if not shape:
        return int(CUDA_CONTEXT + 0.6 * GB)
    logits = shape.get("vocab", 0) * UBATCH * 4                 # output logits, f32
    activations = shape.get("embedding", 0) * UBATCH * 4 * 12   # working tensors
    attention = min(ctx, 131072) * UBATCH * 4 * 0.5             # scores scratch, grows with ctx
    return int(CUDA_CONTEXT + 0.15 * GB + logits + activations + attention)


def estimate(size: int, shape: dict | None, ctx: int, vram: int, ram: int, kv_bytes: float = 2.0,
             text: bool = True) -> dict:
    """size: file bytes; vram/ram: bytes available to judge against.
    text=False: not a chat model (image/video/music/TTS/embeddings), so no KV cache."""
    if shape and shape.get("context_max"):
        ctx = min(ctx, shape["context_max"])
    if text:
        kv = kv_cache_bytes(shape, ctx, kv_bytes) if shape else int(size * 0.10)
        over = overhead_bytes(shape, ctx)
    else:
        kv, over = 0, overhead_bytes(None, 0)
    need = size + kv + over
    vram_ok = vram * MARGIN
    usable = vram_ok + ram * 0.90          # what the "won't run" check actually compares against
    out = {
        "usable": int(usable),
        "vram_usable": int(vram_ok),
        "ctx": ctx,
        "weights": size,
        "kv": kv,
        "overhead": over,
        "need": need,
        "approx": shape is None,
        "layers": shape["layers"] if shape else None,
    }

    if need <= vram_ok:
        return {**out, "level": "fits", "gpu_layers": out["layers"]}

    # Total memory: GPU + RAM (leave RAM a 10% cushion for Windows).
    if need > usable:
        return {**out, "level": "none", "gpu_layers": 0}

    if not shape or not shape["layers"]:
        return {**out, "level": "partial", "gpu_layers": None}

    layers = shape["layers"]
    per_layer = (size + kv) / layers
    gpu_layers = int(max(0, (vram_ok - over)) // per_layer)
    gpu_layers = max(0, min(layers - 1, gpu_layers))
    return {**out, "level": "partial", "gpu_layers": gpu_layers}
