# main.py
import os
import pathlib
from typing import List, Dict, Optional

import httpx
from fastapi import FastAPI, Depends, Header, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from database import SessionLocal, init_db
from models import Game
from schemas import PagedGames, GameOut, CategoryCounts, Range
from bgg_service import fetch_bgg_thing

# -------------------------
# Configuration
# -------------------------
# Absolute public base for this API (used to build absolute URLs)
PUBLIC_BASE_URL = (os.getenv("PUBLIC_BASE_URL") or "").rstrip("/")

# Admin token for privileged endpoints
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "").strip()

# Where we store thumbnails on disk (persistent on Render if under /data)
THUMBS_DIR = os.getenv("THUMBS_DIR", "/data/thumbs")
os.makedirs(THUMBS_DIR, exist_ok=True)

# -------------------------
# App setup
# -------------------------
app = FastAPI(title="Mana & Meeples API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # front-end reads via your PHP proxy, but safe to allow
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve thumbnails directly
app.mount("/thumbs", StaticFiles(directory=THUMBS_DIR), name="thumbs")


# -------------------------
# DB dependency
# -------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------
# Utilities
# -------------------------
def _abs_thumb_from_file(filename: Optional[str]) -> Optional[str]:
    if not filename:
        return None
    # Prefer absolute URL so the browser on manaandmeeples.co.nz can load from Render
    if PUBLIC_BASE_URL:
        return f"{PUBLIC_BASE_URL}/thumbs/{filename}"
    # Fallback (works when calling API host directly)
    return f"/thumbs/{filename}"


async def _download_thumbnail(url: str, stem: str) -> Optional[str]:
    """
    Download a thumbnail to THUMBS_DIR.
    Returns the saved filename (basename only) or None on failure.
    """
    url = (url or "").strip()
    if not url:
        return None
    stem = "".join(c for c in stem.lower().replace(" ", "-") if c.isalnum() or c in "-_")[:64]

    # Pick extension from URL or default to .jpg
    ext = ".jpg"
    for cand in (".png", ".jpg", ".jpeg", ".webp"):
        if url.lower().endswith(cand):
            ext = cand
            break

    filename = f"{stem}{ext}"
    dest = os.path.join(THUMBS_DIR, filename)

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            r = await client.get(url)
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_bytes():
                    f.write(chunk)
        return filename
    except Exception:
        # Keep quiet — a missing thumb should not break inserts
        return None


def _game_to_out(g: Game) -> GameOut:
    # Categories are stored as comma-separated text in DB
    cats = [c.strip() for c in (g.categories or "").split(",") if c.strip()]

    # Determine thumbnail URL preference:
    # 1) stored absolute/path URL in DB (thumbnail_url)
    # 2) local file (thumbnail_file)
    thumb = (g.thumbnail_url or "").strip()
    if not thumb and g.thumbnail_file:
        thumb = _abs_thumb_from_file(g.thumbnail_file)

    # If DB has a leading-slash path, normalize to absolute
    if thumb and thumb.startswith("/") and PUBLIC_BASE_URL:
        thumb = f"{PUBLIC_BASE_URL}{thumb}"

    # Build the response with BOTH the new snake_case fields
    # and all legacy aliases the current frontend might reference.
    return GameOut(
        id=g.id,
        title=g.title or "",
        categories=cats,
        year=g.year,
        players_min=g.players_min,
        players_max=g.players_max,
        playtime_min=g.playtime_min,
        playtime_max=g.playtime_max,
        thumbnail_url=thumb,

        # flat mirrors (legacy)
        thumbnail=thumb,
        playersMin=g.players_min,
        playersMax=g.players_max,
        playtimeMin=g.playtime_min,
        playtimeMax=g.playtime_max,

        # additional common aliases and nested shapes
        imageUrl=thumb,
        image=thumb,
        imageURL=thumb,
        players=Range(min=g.players_min, max=g.players_max),
        playtime=Range(min=g.playtime_min, max=g.playtime_max),
    )


# -------------------------
# Health
# -------------------------
@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/health/db")
def health_db(db: Session = Depends(get_db)):
    try:
        # trivial round-trip
        db.execute(select(func.count()).select_from(Game))
        return {"db_ok": True}
    except Exception:
        return {"db_ok": False}


# -------------------------
# Public: list games with paging/filtering
# -------------------------
@app.get("/api/public/games", response_model=PagedGames)
def list_games(
    q: str = Query("", description="search in title"),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    sort: str = Query("title_asc", pattern="^(title_asc|title_desc)$"),
    db: Session = Depends(get_db),
):
    base = select(Game)
    if q:
        like = f"%{q.strip()}%"
        base = base.where(Game.title.ilike(like))

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0

    if sort == "title_desc":
        base = base.order_by(Game.title.desc())
    else:
        base = base.order_by(Game.title.asc())

    rows: List[Game] = db.execute(
        base.offset((page - 1) * page_size).limit(page_size)
    ).scalars().all() or []

    items = [_game_to_out(g) for g in rows]
    return {"total": int(total), "page": page, "page_size": page_size, "items": items}


@app.get("/api/public/category-counts", response_model=CategoryCounts)
def category_counts(db: Session = Depends(get_db)):
    """
    Simple counts of categories from DB.
    NOTE: Your UI's chips are custom; this returns BGG categories.
    """
    rows: List[Game] = db.execute(select(Game)).scalars().all() or []
    counts: Dict[str, int] = {}
    for g in rows:
        for c in [c.strip() for c in (g.categories or "").split(",") if c.strip()]:
            counts[c] = counts.get(c, 0) + 1
    return counts  # pydantic root model


# -------------------------
# Public: image proxy used by the frontend
# -------------------------
@app.get("/api/public/image-proxy")
async def image_proxy(url: str = Query(..., description="Absolute image URL")):
    """
    The frontend always wraps image URLs through this proxy.
    We support both:
      - our own thumbnails under /thumbs/
      - remote URLs (e.g. original BGG thumbnail, if ever used)
    """
    if not url:
        raise HTTPException(status_code=400, detail="missing url")

    # If it's one of our own /thumbs, serve from disk
    if PUBLIC_BASE_URL and url.startswith(f"{PUBLIC_BASE_URL}/thumbs/"):
        rel = url.replace(PUBLIC_BASE_URL, "").lstrip("/")
        abs_path = os.path.join(os.getcwd(), rel)
        if os.path.exists(abs_path):
            # Guess type from extension
            ext = pathlib.Path(abs_path).suffix.lower()
            mime = "image/png" if ext == ".png" else "image/jpeg"
            return StreamingResponse(open(abs_path, "rb"), media_type=mime)

    # Otherwise, fetch and stream
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        r = await client.get(url)
        r.raise_for_status()
        ctype = r.headers.get("content-type") or "application/octet-stream"
        return StreamingResponse(r.iter_bytes(), media_type=ctype)


# -------------------------
# Admin endpoints
# -------------------------
def _require_admin(x_admin_token: Optional[str]):
    if not ADMIN_TOKEN or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="invalid admin token")


@app.post("/api/admin/seed")
def admin_seed(x_admin_token: Optional[str] = Header(None), db: Session = Depends(get_db)):
    _require_admin(x_admin_token)

    samples = [
        Game(title="Azul", categories="Abstract Strategy, Renaissance"),
        Game(title="Cascadia", categories="Animals, Environmental"),
        Game(title="Wingspan", categories="Animals, Card Game, Educational"),
    ]
    inserted = 0
    for g in samples:
        db.add(g)
        inserted += 1
    db.commit()
    return {"inserted": inserted}


@app.post("/api/admin/import/bgg")
async def admin_import_bgg(
    bgg_id: int,
    force: int = 0,
    x_admin_token: Optional[str] = Header(None),
    background: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    _require_admin(x_admin_token)

    existing = db.execute(select(Game).where(Game.bgg_id == bgg_id)).scalar_one_or_none()

    data = await fetch_bgg_thing(bgg_id)
    cats = ", ".join(data.get("categories") or [])

    if existing and not force:
        return {"ok": True, "id": existing.id, "cached": True}

    if existing and force:
        g = existing
        g.title = data["title"]
        g.categories = cats
        g.year = data.get("year")
        g.players_min = data.get("players_min")
        g.players_max = data.get("players_max")
        g.playtime_min = data.get("playtime_min")
        g.playtime_max = data.get("playtime_max")
        # clear old thumbs to allow refresh
        g.thumbnail_file = None
        g.thumbnail_url = None
        db.add(g)
        db.commit()
        db.refresh(g)
    else:
        g = Game(
            title=data["title"],
            categories=cats,
            year=data.get("year"),
            players_min=data.get("players_min"),
            players_max=data.get("players_max"),
            playtime_min=data.get("playtime_min"),
            playtime_max=data.get("playtime_max"),
            bgg_id=bgg_id,
        )
        db.add(g)
        db.commit()
        db.refresh(g)

    # async thumb download & DB update
    async def _dl_and_set():
        try:
            fname = await _download_thumbnail(data.get("thumbnail") or "", f"{g.id}-{g.title}")
            if fname:
                db2 = SessionLocal()
                try:
                    g2 = db2.get(Game, g.id)
                    if g2:
                        g2.thumbnail_file = fname
                        g2.thumbnail_url = _abs_thumb_from_file(fname)
                        db2.add(g2)
                        db2.commit()
                finally:
                    db2.close()
        except Exception:
            pass

    if background is not None:
        background.add_task(_dl_and_set)

    return {"ok": True, "id": g.id, "cached": existing is not None and not bool(force)}


# -------------------------
# Startup
# -------------------------
@app.on_event("startup")
def _on_startup():
    # Ensure DB tables exist
    init_db()
    # Ensure thumbs dir exists (Render persistent disk)
    os.makedirs(THUMBS_DIR, exist_ok=True)
