"""Download one file in its own process and report progress as JSON lines on stdout.

Usage: python -m core.worker <json job>
  job = {"repo_id", "filename", "local_dir", "revision"?, "size"?, "sha256"?}

Resumable: bytes go to "<dest>.part". Stopping the process pauses the download;
the next run continues from the end of the .part file with an HTTP Range request.
(huggingface_hub 2.x's hf_hub_download starts over every time, so we do our own.)
At the end, the file is checked against Hugging Face's size and LFS SHA-256.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

CHUNK = 1024 * 1024
RETRIES = 6


def emit(**kw) -> None:
    sys.stdout.write(json.dumps(kw) + "\n")
    sys.stdout.flush()


def sha256_of(path: str, total: int) -> str:
    h = hashlib.sha256()
    done, last = 0, 0.0
    with open(path, "rb") as f:
        while chunk := f.read(8 * CHUNK):
            h.update(chunk)
            done += len(chunk)
            now = time.monotonic()
            if now - last >= 0.25:
                last = now
                emit(type="verify", done=done, total=total)
    return h.hexdigest()


def main() -> int:
    job = json.loads(sys.argv[1])
    from huggingface_hub import hf_hub_url
    from huggingface_hub.utils import build_hf_headers, get_session

    repo_id, filename = job["repo_id"], job["filename"]
    dest = os.path.normpath(os.path.join(job["local_dir"], *filename.split("/")))
    part = dest + ".part"
    expected = job.get("size") or None
    sha = job.get("sha256") or None
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    if os.path.exists(dest) and (not expected or os.path.getsize(dest) == expected):
        emit(type="done", path=dest, skipped=True)
        return 0

    url = hf_hub_url(repo_id, filename, revision=job.get("revision"))
    headers = build_hf_headers()
    session = get_session()
    emit(type="start", resume=os.path.getsize(part) if os.path.exists(part) else 0)

    attempt = 0
    while True:
        have = os.path.getsize(part) if os.path.exists(part) else 0
        if expected and have >= expected:
            break
        h = dict(headers)
        if have:
            h["Range"] = f"bytes={have}-"
        try:
            with session.stream("GET", url, headers=h, follow_redirects=True, timeout=60) as r:
                if r.status_code in (401, 403):
                    emit(type="error", message="No access: this repo is gated or private. Request access on "
                                               "Hugging Face, then run `hf auth login`.")
                    return 2
                if r.status_code == 404:
                    emit(type="error", message="File not found on Hugging Face (it may have been removed).")
                    return 3
                if r.status_code == 416:          # nothing left to fetch
                    break
                r.raise_for_status()
                if have and r.status_code == 200:  # server ignored Range: start over
                    have = 0
                total = expected or (have + int(r.headers.get("content-length", 0)) or None)
                mode = "ab" if have else "wb"
                done, last, t0, base = have, 0.0, time.monotonic(), have
                with open(part, mode) as f:
                    for chunk in r.iter_bytes(CHUNK):
                        f.write(chunk)
                        done += len(chunk)
                        now = time.monotonic()
                        if now - last >= 0.25:
                            last = now
                            speed = (done - base) / max(now - t0, 1e-6)
                            emit(type="progress", done=done, total=total or 0, speed=int(speed))
                emit(type="progress", done=done, total=total or done, speed=0)
            attempt = 0
            if not expected or done >= expected:
                break
        except OSError as e:
            if getattr(e, "errno", None) == 28:   # ENOSPC
                emit(type="error", message="The drive is full. Free some space and resume.")
                return 4
            attempt += 1
            if attempt > RETRIES:
                emit(type="error", message=f"Network error: {e}"[:300])
                return 5
            emit(type="retry", attempt=attempt, message=str(e)[:200])
            time.sleep(min(2 ** attempt, 30))
        except Exception as e:
            name = type(e).__name__
            attempt += 1
            if attempt > RETRIES or "HTTPStatusError" in name:
                emit(type="error", message=f"{name}: {e}"[:300])
                return 1
            emit(type="retry", attempt=attempt, message=f"{name}: {e}"[:200])
            time.sleep(min(2 ** attempt, 30))

    size = os.path.getsize(part)
    if expected and size != expected:
        emit(type="error", message=f"Size mismatch: got {size}, expected {expected}. Delete and retry.")
        return 6
    if sha:
        emit(type="verify", done=0, total=size)
        if sha256_of(part, size) != sha:
            os.replace(part, part + ".bad")
            emit(type="error", message="Checksum mismatch: the file is corrupted. Retry to download it again.")
            return 7
    os.replace(part, dest)
    emit(type="done", path=dest)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
