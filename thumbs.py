import os, re, httpx
from typing import Optional

THUMBS_DIR = "/data/thumbs"

def ensure_dir():
    os.makedirs(THUMBS_DIR, exist_ok=True)

def safe_filename(name: str) -> str:
    # keep it deterministic and filesystem-safe
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9._-]+", "-", name)
    name = re.sub(r"-{2,}", "-", name).strip("-")
    return name or "thumb"

async def download_thumbnail(url: str, basename: str) -> Optional[str]:
    if not url:
        return None
    ensure_dir()
    ext = ".jpg"
    if ".png" in url.lower():
        ext = ".png"
    filename = f"{safe_filename(basename)}{ext}"
    path = os.path.join(THUMBS_DIR, filename)
    # if exists, reuse (cache)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return filename
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url)
        r.raise_for_status()
        with open(path, "wb") as f:
            f.write(r.content)
    return filename
