import os, re, httpx
from typing import Optional
from config import HTTP_TIMEOUT

# Use /tmp for Render free tier compatibility (ephemeral storage)
THUMBS_DIR = os.getenv("THUMBS_DIR", "/tmp/thumbs")

# File validation constants
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

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
    
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        # First, do a HEAD request to check content type and size
        try:
            head_response = await client.head(url)
            content_type = head_response.headers.get("content-type", "").lower()
            content_length = head_response.headers.get("content-length")
            
            # Validate content type
            if content_type and not any(allowed_type in content_type for allowed_type in ALLOWED_CONTENT_TYPES):
                return None
                
            # Validate file size
            if content_length and int(content_length) > MAX_FILE_SIZE:
                return None
        except:
            # If HEAD fails, continue with GET but validate after download
            pass
    
    # Determine extension based on URL or content type
    ext = ".jpg"
    if ".png" in url.lower() or "image/png" in url.lower():
        ext = ".png"
    elif ".webp" in url.lower() or "image/webp" in url.lower():
        ext = ".webp"
    
    filename = f"{safe_filename(basename)}{ext}"
    path = os.path.join(THUMBS_DIR, filename)
    
    # if exists, reuse (cache)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return filename
    
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.get(url)
        r.raise_for_status()
        
        # Validate file size after download
        if len(r.content) > MAX_FILE_SIZE:
            return None
            
        # Validate content type after download
        content_type = r.headers.get("content-type", "").lower()
        if content_type and not any(allowed_type in content_type for allowed_type in ALLOWED_CONTENT_TYPES):
            return None
        
        with open(path, "wb") as f:
            f.write(r.content)
    return filename
