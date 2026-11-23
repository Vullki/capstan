"""Live machine status: GPU (NVML), RAM, and free disk space per drive."""
from __future__ import annotations

import os
import shutil
import string

import psutil

try:
    import pynvml
    pynvml.nvmlInit()
    _NVML = True
except Exception:  # no NVIDIA driver or no GPU
    _NVML = False

# Only model runners are worth naming; Windows lists every app that draws on the GPU.
_GPU_NAMES = {"ollama": "Ollama", "lm studio": "LM Studio", "lmstudio": "LM Studio",
              "llama-server": "llama.cpp", "llama-cli": "llama.cpp", "llama": "llama.cpp",
              "koboldcpp": "KoboldCpp", "comfyui": "ComfyUI", "jan": "Jan", "vllm": "vLLM"}


def _proc_label(pid: int) -> str | None:
    try:
        name = psutil.Process(pid).name().lower().removesuffix(".exe")
    except Exception:
        return None
    for key, label in _GPU_NAMES.items():
        if name == key or name.startswith(key):
            return label
    return None


def gpu() -> dict | None:
    if not _NVML:
        return None
    try:
        h = pynvml.nvmlDeviceGetHandleByIndex(0)
        mem = pynvml.nvmlDeviceGetMemoryInfo(h)
        name = pynvml.nvmlDeviceGetName(h)
        name = name.decode() if isinstance(name, bytes) else name
        users = []
        try:
            for p in pynvml.nvmlDeviceGetComputeRunningProcesses(h):
                label = _proc_label(p.pid)
                if label:
                    users.append({"name": label, "bytes": p.usedGpuMemory or None})
        except Exception:
            pass
        seen, uniq = set(), []
        for u in users:
            if u["name"] not in seen:
                seen.add(u["name"])
                uniq.append(u)
        return {"name": name.replace("NVIDIA GeForce ", ""), "total": mem.total,
                "used": mem.used, "free": mem.free, "users": uniq}
    except Exception:
        return None


def ram() -> dict:
    vm = psutil.virtual_memory()
    return {"total": vm.total, "available": vm.available}


def drives() -> list[dict]:
    out = []
    for letter in string.ascii_uppercase:
        root = f"{letter}:\\"
        if os.path.exists(root):
            try:
                du = shutil.disk_usage(root)
            except OSError:
                continue
            out.append({"drive": f"{letter}:", "total": du.total, "free": du.free})
    return out


def free_at(path: str) -> int | None:
    """Free bytes on the drive that holds `path` (the folder may not exist yet)."""
    p = os.path.abspath(path)
    while p and not os.path.exists(p):
        parent = os.path.dirname(p)
        if parent == p:
            break
        p = parent
    try:
        return shutil.disk_usage(p).free
    except OSError:
        return None


def snapshot() -> dict:
    return {"gpu": gpu(), "ram": ram(), "drives": drives()}
