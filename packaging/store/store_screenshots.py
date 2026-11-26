"""Replace the Microsoft Store listing screenshots for Capstan through the Store submission API.

The Microsoft Store Developer CLI (msstore) has no command for listing images of an MSIX app, so this
script talks to the API directly, reusing the credentials `msstore reconfigure` already saved:
tenant, seller and client IDs from the CLI's settings.json, and the client secret from Windows
Credential Manager (read in memory only, never printed or written).

    python store_screenshots.py --check        # read-only: sign in, show the live screenshots
    python store_screenshots.py                # new submission: swap screenshots, upload, commit

A new submission copies the last published one, so only the screenshots change. The API allows one
pending submission at a time: wait until the previous one is published.
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wt
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

PRODUCT_ID = "9PDMZQ06VL6B"
API = "https://manage.devcenter.microsoft.com/v1.0/my/applications/" + PRODUCT_ID
ROOT = Path(__file__).resolve().parents[2]
SHOTS = [  # (file in the repo, name inside the ZIP, caption)
    (ROOT / "docs/screenshot-search.png", "screenshots/search.png",
     "Search the Hub live, or paste any model link."),
    (ROOT / "docs/screenshot-repo.png", "screenshots/repo.png",
     "Every quant gets a fit light for this PC, at your context length."),
]
SETTINGS = Path(os.environ["LOCALAPPDATA"]) / (
    "Packages/Microsoft.MicrosoftStoreCLI_8wekyb3d8bbwe/LocalCache/Local/Microsoft/MSStore.CLI/settings.json")


class CREDENTIAL(ctypes.Structure):
    _fields_ = [("Flags", wt.DWORD), ("Type", wt.DWORD), ("TargetName", wt.LPWSTR),
                ("Comment", wt.LPWSTR), ("LastWritten", wt.FILETIME),
                ("CredentialBlobSize", wt.DWORD), ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
                ("Persist", wt.DWORD), ("AttributeCount", wt.DWORD), ("Attributes", ctypes.c_void_p),
                ("TargetAlias", wt.LPWSTR), ("UserName", wt.LPWSTR)]


def client_secret(client_id: str) -> str:
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    ptr = ctypes.POINTER(CREDENTIAL)()
    if not advapi.CredReadW(f"MicrosoftStoreCli:user={client_id}", 1, 0, ctypes.byref(ptr)):
        sys.exit("No msstore credential in Credential Manager: run `msstore reconfigure` first.")
    try:
        cred = ptr.contents
        raw = bytes(cred.CredentialBlob[: cred.CredentialBlobSize])
    finally:
        advapi.CredFree(ptr)
    for enc in ("utf-16-le", "utf-8"):
        try:
            text = raw.decode(enc)
            if text.isprintable():
                return text
        except UnicodeDecodeError:
            pass
    sys.exit("Could not read the msstore credential.")


def call(method: str, url: str, token: str | None = None, body=None, headers=None, raw: bytes | None = None):
    h = dict(headers or {})
    data = raw
    if token:
        h["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            text = r.read().decode() or "{}"
            return json.loads(text) if text.strip().startswith(("{", "[")) else {}
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {url.split('?')[0]} -> HTTP {e.code}: {e.read().decode(errors='replace')[:800]}")


def sign_in() -> str:
    cfg = json.loads(SETTINGS.read_text(encoding="utf-8-sig"))
    form = urllib.parse.urlencode({
        "grant_type": "client_credentials", "client_id": cfg["ClientId"],
        "client_secret": client_secret(cfg["ClientId"]),
        "resource": "https://manage.devcenter.microsoft.com"}).encode()
    tok = call("POST", f"https://login.microsoftonline.com/{cfg['TenantId']}/oauth2/token",
               raw=form, headers={"Content-Type": "application/x-www-form-urlencoded"})
    return tok["access_token"]


def screenshots(sub: dict) -> list[str]:
    out = []
    for lang, listing in sub.get("listings", {}).items():
        for im in listing.get("baseListing", {}).get("images", []):
            if im.get("imageType") == "Screenshot":
                out.append(f"  {lang}: {im.get('fileName')}  [{im.get('fileStatus')}]  {im.get('description', '')}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="read-only: sign in and show the live screenshots")
    args = ap.parse_args()
    for path, _, _ in SHOTS:
        if not path.is_file():
            sys.exit(f"Missing {path}")

    token = sign_in()
    app = call("GET", API, token)
    pending = app.get("pendingApplicationSubmission")
    published = app.get("lastPublishedApplicationSubmission")
    print(f"Signed in. Last published submission: {published and published.get('id')}; "
          f"pending: {pending and pending.get('id')}")
    if published:
        live = call("GET", f"{API}/submissions/{published['id']}", token)
        print("Screenshots on the live listing:")
        print("\n".join(screenshots(live)) or "  (none)")

    if args.check:
        return
    if pending:
        sys.exit("A submission is still pending (in certification or a draft). Wait until it is published.")

    sub = call("POST", f"{API}/submissions", token)
    sid = sub["id"]
    print(f"Created submission {sid}")
    for listing in sub.get("listings", {}).values():
        base = listing.setdefault("baseListing", {})
        images = base.setdefault("images", [])
        for im in images:
            if im.get("imageType") == "Screenshot":
                im["fileStatus"] = "PendingDelete"
        images += [{"fileName": name, "fileStatus": "PendingUpload", "imageType": "Screenshot",
                    "description": caption} for _, name, caption in SHOTS]
    sub = call("PUT", f"{API}/submissions/{sid}", token, body=sub)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for path, name, _ in SHOTS:
            z.write(path, name)
    call("PUT", sub["fileUploadUrl"], raw=buf.getvalue(),
         headers={"x-ms-blob-type": "BlockBlob", "Content-Type": "application/zip"})
    print(f"Uploaded {len(buf.getvalue()) // 1024} KB of screenshots")

    call("POST", f"{API}/submissions/{sid}/commit", token)
    for _ in range(30):
        st = call("GET", f"{API}/submissions/{sid}/status", token)
        if st.get("status") != "CommitStarted":
            break
        time.sleep(10)
    print(f"Submission {sid} status: {st.get('status')}")
    details = st.get("statusDetails") or {}
    for kind in ("errors", "warnings", "certificationReports"):
        for item in details.get(kind) or []:
            print(f"  {kind}: {item}")
    if st.get("status") in ("CommitFailed", "PreProcessingFailed"):
        sys.exit(1)


if __name__ == "__main__":
    main()
