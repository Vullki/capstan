"""Download queue: one worker process per file, pause/resume/cancel, persisted."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import uuid

from . import hub, store

APP_DIR = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


def worker_cmd(payload: str) -> list[str]:
    """The command that runs one download (see core/worker.py)."""
    if getattr(sys, "frozen", False):            # installed build: Capstan.exe --worker <job>
        return [sys.executable, "--worker", payload]
    return [sys.executable, "-m", "core.worker", payload]


class Queue:
    def __init__(self, on_event):
        self.on_event = on_event            # callback(dict) -> pushes to the UI
        self.lock = threading.RLock()
        self.jobs: list[dict] = []
        self.procs: dict[str, subprocess.Popen] = {}
        for j in store.load_queue():
            if j["state"] in ("running", "verifying", "queued"):
                j["state"] = "paused"       # restarted app: wait for the user
            j["speed"] = 0
            self.jobs.append(j)

    # ── public ─────────────────────────────────────────────────────────
    def add(self, repo_id: str, revision: str | None, files: list[dict], local_dir: str,
            quant: str | None = None) -> list[dict]:
        added = []
        with self.lock:
            for f in files:
                if any(j["repo_id"] == repo_id and j["filename"] == f["path"] and j["state"] != "done"
                       for j in self.jobs):
                    continue
                job = {
                    "id": uuid.uuid4().hex[:10], "repo_id": repo_id, "revision": revision,
                    "filename": f["path"], "size": f.get("size") or 0, "sha256": f.get("sha256"),
                    "local_dir": local_dir, "quant": quant or hub.quant_of(f["path"]),
                    "state": "queued", "done": 0, "speed": 0, "error": None,
                    "added": time.time(), "path": None,
                }
                part = self._dest(job) + ".part"
                if os.path.exists(part):
                    job["done"] = os.path.getsize(part)
                self.jobs.append(job)
                added.append(job)
            self._persist()
        self._pump()
        self._push()
        return added

    def pause(self, job_id: str) -> None:
        with self.lock:
            j = self._get(job_id)
            if not j:
                return
            if j["state"] in ("running", "verifying"):
                self._kill(job_id)
            if j["state"] in ("running", "verifying", "queued"):
                j["state"], j["speed"] = "paused", 0
            self._persist()
        self._pump()
        self._push()

    def resume(self, job_id: str) -> None:
        with self.lock:
            j = self._get(job_id)
            if j and j["state"] in ("paused", "error"):
                j["state"], j["error"] = "queued", None
                self._persist()
        self._pump()
        self._push()

    def cancel(self, job_id: str) -> None:
        with self.lock:
            j = self._get(job_id)
            if not j:
                return
            self._kill(job_id)
            if j["state"] != "done":
                for suffix in (".part", ".part.bad"):
                    try:
                        os.remove(self._dest(j) + suffix)
                    except OSError:
                        pass
            self.jobs.remove(j)
            self._persist()
        self._pump()
        self._push()

    def clear_finished(self) -> None:
        with self.lock:
            self.jobs = [j for j in self.jobs if j["state"] != "done"]
            self._persist()
        self._push()

    def pause_all(self) -> None:
        for j in list(self.jobs):
            if j["state"] in ("running", "verifying", "queued"):
                self.pause(j["id"])

    def shutdown(self) -> None:
        with self.lock:
            for jid in list(self.procs):
                self._kill(jid)
                j = self._get(jid)
                if j:
                    j["state"] = "paused"
            self._persist()

    def snapshot(self) -> list[dict]:
        with self.lock:
            return [dict(j) for j in self.jobs]

    def pending_bytes_on(self, drive: str) -> int:
        """Bytes still to come for unfinished jobs on a drive (for the disk check)."""
        with self.lock:
            return sum(max(j["size"] - j["done"], 0) for j in self.jobs
                       if j["state"] != "done" and os.path.splitdrive(j["local_dir"])[0].upper() == drive.upper())

    # ── internals ──────────────────────────────────────────────────────
    def _get(self, job_id):
        return next((j for j in self.jobs if j["id"] == job_id), None)

    @staticmethod
    def _dest(j) -> str:
        return os.path.normpath(os.path.join(j["local_dir"], *j["filename"].split("/")))

    def _persist(self):
        store.save_queue([{k: v for k, v in j.items() if k != "speed"} for j in self.jobs])

    def _push(self):
        self.on_event({"type": "queue", "jobs": self.snapshot()})

    def _kill(self, job_id):
        p = self.procs.pop(job_id, None)
        if p and p.poll() is None:
            p.terminate()
            try:
                p.wait(5)
            except subprocess.TimeoutExpired:
                p.kill()

    def _pump(self):
        with self.lock:
            limit = max(1, int(store.settings().get("concurrency", 1)))
            running = sum(1 for j in self.jobs if j["state"] in ("running", "verifying"))
            for j in self.jobs:
                if running >= limit:
                    break
                if j["state"] == "queued":
                    self._start(j)
                    running += 1

    def _start(self, j):
        payload = {"repo_id": j["repo_id"], "filename": j["filename"], "local_dir": j["local_dir"],
                   "revision": j["revision"], "size": j["size"],
                   "sha256": j["sha256"] if store.settings().get("verify", True) else None}
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        p = subprocess.Popen(worker_cmd(json.dumps(payload)), cwd=APP_DIR,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                             encoding="utf-8", env=env, creationflags=_NO_WINDOW)
        self.procs[j["id"]] = p
        j["state"], j["error"] = "running", None
        threading.Thread(target=self._watch, args=(j["id"], p), daemon=True).start()

    def _watch(self, job_id, p: subprocess.Popen):
        last_push = 0.0
        for line in p.stdout:
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            with self.lock:
                j = self._get(job_id)
                if not j or self.procs.get(job_id) is not p:
                    break
                t = ev.get("type")
                if t == "progress":
                    j["state"] = "running"
                    j["done"] = ev["done"]
                    j["speed"] = ev.get("speed", 0)
                    if ev.get("total"):
                        j["size"] = j["size"] or ev["total"]
                elif t == "verify":
                    j["state"], j["speed"] = "verifying", 0
                    j["verify"] = ev["done"] / max(ev["total"], 1)
                elif t == "retry":
                    j["error"] = f"Retrying ({ev['attempt']}): {ev.get('message', '')}"
                elif t == "error":
                    j["state"], j["error"], j["speed"] = "error", ev["message"], 0
                elif t == "done":
                    j["state"], j["path"], j["done"], j["speed"], j["error"] = "done", ev["path"], j["size"], 0, None
                    store.add_history({"path": ev["path"], "repo_id": j["repo_id"], "quant": j["quant"],
                                       "filename": j["filename"], "size": j["size"]})
                    self._persist()
                    self.on_event({"type": "downloaded", "job": dict(j)})
            now = time.monotonic()
            if t != "progress" or now - last_push > 0.4:
                last_push = now
                self._push()
        p.wait()
        with self.lock:
            if self.procs.get(job_id) is p:
                self.procs.pop(job_id, None)
                j = self._get(job_id)
                if j and j["state"] in ("running", "verifying"):
                    j["state"] = "error"
                    j["error"] = j.get("error") or f"Stopped unexpectedly (exit {p.returncode})."
                self._persist()
        self._pump()
        self._push()
