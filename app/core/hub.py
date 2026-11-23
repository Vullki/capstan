"""Hugging Face Hub: search, link parsing, file listing, quant grouping."""
from __future__ import annotations

import re
from urllib.parse import urlparse

from huggingface_hub import HfApi
from huggingface_hub.utils import GatedRepoError, RepositoryNotFoundError

api = HfApi()

SORTS = {"downloads": "downloads", "trending": "trending_score", "likes": "likes", "updated": "last_modified"}

_QUANT = re.compile(
    r"(?<![A-Za-z0-9])("
    r"IQ[1-4]_(?:XXS|XS|S|M|NL|L)|IQ4_NL|IQ4_XS|"
    r"Q[2-8]_K(?:_[XSML]{1,2})?|Q[4-8]_[01]|Q2_K_L|Q3_K_XL|Q4_K_XL|Q5_K_XL|Q6_K_XL|Q8_K_XL|"
    r"TQ[12]_0|MXFP4(?:_MOE)?|NVFP4|F16|F32|BF16|FP16|FP8"
    r")(?![A-Za-z0-9])", re.IGNORECASE)
_SPLIT = re.compile(r"-(\d{5})-of-(\d{5})\.gguf$", re.IGNORECASE)
_PARAMS = re.compile(r"(?<![A-Za-z0-9.])(E?\d+(?:\.\d+)?)\s?([BM])(?![A-Za-z])", re.IGNORECASE)
_REPO_ID = re.compile(r"^[A-Za-z0-9][\w.\-]*/[\w.\-]+$")

# Rough bits per weight, used to sort quants from small to large.
_QUANT_ORDER = ["IQ1", "TQ1", "IQ2", "TQ2", "Q2", "IQ3", "Q3", "IQ4", "MXFP4", "NVFP4", "Q4",
                "Q5", "Q6", "Q8", "FP8", "F16", "FP16", "BF16", "F32"]


def size_class(text: str) -> str | None:
    m = None
    for m in _PARAMS.finditer(text.replace("_", " ")):
        pass  # take the last match, e.g. "Qwen3.5-9B" -> 9B, not the 3.5
    if not m:
        return None
    n, unit = m.group(1).upper(), m.group(2).upper()
    return f"{n}{unit}"


def search(query: str, sort: str = "downloads", gguf_only: bool = True, limit: int = 40) -> list[dict]:
    kwargs = dict(search=query or None, sort=SORTS.get(sort, "downloads"), limit=limit,
                  expand=["downloads", "likes", "lastModified", "trendingScore", "gated", "pipeline_tag", "tags"])
    if gguf_only:
        kwargs["filter"] = "gguf"
    out = []
    for m in api.list_models(**kwargs):
        author, _, name = m.id.partition("/")
        out.append({
            "id": m.id, "author": author, "name": name,
            "downloads": m.downloads or 0, "likes": m.likes or 0,
            "updated": m.last_modified.isoformat() if m.last_modified else None,
            "gated": bool(m.gated), "pipeline": m.pipeline_tag,
            "size_class": size_class(name),
            "gguf": "gguf" in (m.tags or []),
        })
    return out


def parse_link(text: str) -> dict | None:
    """Repo ID or Hugging Face URL -> {repo_id, file?, revision?}. None if it isn't one."""
    t = text.strip().strip('"').strip("'")
    if not t:
        return None
    if _REPO_ID.match(t) and "://" not in t:
        return {"repo_id": t}
    if "://" not in t and t.split("/")[0] in ("huggingface.co", "hf.co", "www.huggingface.co"):
        t = "https://" + t
    u = urlparse(t)
    if u.netloc.lower() not in ("huggingface.co", "www.huggingface.co", "hf.co"):
        return None
    parts = [p for p in u.path.split("/") if p]
    if parts and parts[0] in ("models",):
        parts = parts[1:]
    if parts and parts[0] in ("datasets", "spaces"):
        return {"error": "That link is a dataset or Space. Capstan downloads models."}
    if len(parts) < 2:
        return None
    out = {"repo_id": f"{parts[0]}/{parts[1]}"}
    if len(parts) >= 4 and parts[2] in ("blob", "resolve", "tree"):
        out["revision"] = parts[3]
        if len(parts) > 4 and parts[2] != "tree":
            out["file"] = "/".join(parts[4:])
    return out


def quant_of(filename: str) -> str | None:
    base = filename.rsplit("/", 1)[-1]
    found = _QUANT.findall(base)
    return found[-1].upper() if found else None


def _quant_rank(q: str | None) -> int:
    if not q:
        return 999
    for i, p in enumerate(_QUANT_ORDER):
        if q.startswith(p):
            return i
    return 500


def _common_prefix(names: list[str]) -> str:
    if len(names) < 2:
        return ""
    a, b = min(names), max(names)
    i = 0
    while i < len(a) and i < len(b) and a[i] == b[i]:
        i += 1
    cut = max(a.rfind("-", 0, i + 1), a.rfind("_", 0, i + 1), a.rfind(".", 0, i + 1))
    return a[:cut + 1] if cut > 0 else ""


def repo(repo_id: str, revision: str | None = None) -> dict:
    """Repo summary plus its files, with GGUFs grouped into downloadable models."""
    try:
        info = api.model_info(repo_id, revision=revision, expand=["downloads", "likes", "lastModified", "gated", "gguf", "cardData", "tags"])
    except RepositoryNotFoundError:
        return {"error": "Repo not found. It may be private, or the name is wrong."}
    except GatedRepoError:
        info = None

    files, folders = [], set()
    try:
        for f in api.list_repo_tree(repo_id, recursive=True, revision=revision):
            if hasattr(f, "size"):
                lfs = getattr(f, "lfs", None)
                sha = getattr(lfs, "sha256", None) if lfs else None
                files.append({"path": f.path, "size": f.size or 0, "sha256": sha})
    except GatedRepoError:
        return {"error": "gated", "repo_id": repo_id,
                "message": "This repo is gated. Request access on its page, then log in with `hf auth login`."}

    # Group GGUFs: split parts become one model; mmproj files are separate.
    groups: dict[str, dict] = {}
    others = []
    for f in files:
        p = f["path"]
        if not p.lower().endswith(".gguf"):
            others.append(f)
            continue
        m = _SPLIT.search(p)
        key = _SPLIT.sub(".gguf", p) if m else p
        g = groups.setdefault(key, {"key": key, "files": [], "size": 0, "parts": 0})
        g["files"].append({"path": p, "size": f["size"], "sha256": f["sha256"]})
        g["size"] += f["size"]
        g["parts"] += 1
    gguf = []
    names = [k.rsplit("/", 1)[-1] for k in groups if "mmproj" not in k.lower()]
    prefix = _common_prefix(names)
    for key, g in groups.items():
        base = key.rsplit("/", 1)[-1]
        is_mmproj = "mmproj" in base.lower()
        g["files"].sort(key=lambda x: x["path"])
        q = quant_of(base)
        label = base[len(prefix):] if prefix and base.startswith(prefix) else base
        label = label.removesuffix(".gguf")
        gguf.append({**g, "name": base, "label": label or base, "quant": q,
                     "folder": key.rsplit("/", 1)[0] if "/" in key else "",
                     "mmproj": is_mmproj, "header_file": g["files"][0]["path"]})
    gguf.sort(key=lambda x: (x["mmproj"], _quant_rank(x["quant"]), x["size"]))

    gi = getattr(info, "gguf", None) or {}
    return {
        "repo_id": repo_id,
        "revision": revision,
        "author": repo_id.split("/")[0],
        "name": repo_id.split("/")[1],
        "downloads": getattr(info, "downloads", 0) or 0,
        "likes": getattr(info, "likes", 0) or 0,
        "updated": info.last_modified.isoformat() if info and info.last_modified else None,
        "gated": bool(getattr(info, "gated", False)),
        "params": gi.get("total"),
        "architecture": gi.get("architecture"),
        "context_max": gi.get("context_length"),
        "size_class": size_class(repo_id.split("/")[1]),
        "gguf": gguf,
        "other": sorted(others, key=lambda f: f["path"]),
        "total_size": sum(f["size"] for f in files),
    }
