# main.py
import os
import pathlib
from typing import Optional, List, Dict

import httpx
from fastapi import FastAPI, Depends, Header, HTTPException, Query, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from starlette.types import ASGIApp, Receive, Scope, Send

from database import SessionLocal, init_db
from models import Game
from bgg_service import fetch_bgg_thing

# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------
PUBLIC_BASE_URL = (os.getenv("PUBLIC_BASE_URL") or "").rstrip("/")
ADMIN_TOKEN = (os.getenv("ADMIN_TOKEN") or "").strip()

THUMBS_DIR = os.getenv("THUMBS_DIR", "/data/thumbs")
os.makedirs(THUMBS_DIR, exist_ok=True)

# ---------------------------------------------------------------------
# App
# ---------------------------------------------------------------------
app = FastAPI(title="Mana & Meeples API", version="1.0.0")

class CacheThumbsMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                path = scope.get("path", "")
                if path.startswith("/thumbs/"):
                    # append Cache-Control header
                    headers = message.setdefault("headers", [])
                    headers.append((b"cache-control", b"public, max-age=31536000, immutable"))
            await send(message)

        await self.app(scope, receive, send_wrapper)

app.add_middleware(CacheThumbsMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# serve thumbnails (e.g. https://.../thumbs/1-azul.png)
app.mount("/thumbs", StaticFiles(directory=THUMBS_DIR), name="thumbs")


# ---------------------------------------------------------------------
# DB session
# ---------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _categories_to_list(raw) -> List[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [c.strip() for c in raw if c and str(c).strip()]
    # assume comma-separated text
    return [c.strip() for c in str(raw).split(",") if c.strip()]


def _abs_url(request: Request, url: Optional[str]) -> Optional[str]:
    """Turn '/thumbs/x.png' into absolute https://host/thumbs/x.png for the proxy."""
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    base = str(request.base_url).rstrip("/")
    return f"{base}{url}"


async def _download_to_thumbs(url: str, name_stem: str) -> Optional[str]:
    """Download image to THUMBS_DIR; return basename or None."""
    url = (url or "").strip()
    if not url:
        return None

    safe = "".join(c for c in name_stem.lower().replace(" ", "-") if c.isalnum() or c in "-_")[:64]
    ext = ".jpg"
    for cand in (".png", ".jpg", ".jpeg", ".webp"):
        if url.lower().endswith(cand):
            ext = cand
            break

    filename = f"{safe}{ext}"
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
        return None


def _game_row_to_dict(request: Request, g: Game) -> Dict:
    """
    Return a dict that includes BOTH your original public fields and
    the alias keys the shipped frontend reads.
    """
    cats = _categories_to_list(getattr(g, "categories", None))

    # Prefer explicit thumbnail_url; otherwise use local file if present
    thumb = (getattr(g, "thumbnail_url", None) or "").strip()
    if not thumb and getattr(g, "thumbnail_file", None):
        thumb = f"/thumbs/{g.thumbnail_file}"

    # Absolute for the image proxy
    abs_thumb = _abs_url(request, thumb) if thumb else None

    year = getattr(g, "year", None)
    pmin = getattr(g, "players_min", None)
    pmax = getattr(g, "players_max", None)
    tmin = getattr(g, "playtime_min", None)
    tmax = getattr(g, "playtime_max", None)

    # single number the bundle expects; fall back smartly
    playing_time = tmin or tmax

    return {
        # --- your existing public fields (keep unchanged) ---
        "id": g.id,
        "title": getattr(g, "title", "") or "",
        "categories": cats,
        "year": year,
        "players_min": pmin,
        "players_max": pmax,
        "playtime_min": tmin,
        "playtime_max": tmax,
        "thumbnail_url": abs_thumb,  # keep absolute; helps when browsing raw JSON

        # --- aliases the shipped bundle reads on the public catalogue ---
        "image_url": abs_thumb,
        "year_published": year,
        "min_players": pmin,
        "max_players": pmax,
        "playing_time": playing_time,

        # optional custom category used by chips, if you later store it
        "mana_meeple_category": getattr(g, "mana_meeple_category", None),
    }


def _require_admin(token: Optional[str]):
    if not ADMIN_TOKEN or token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="invalid admin token")


# ---------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/health/db")
def health_db(db: Session = Depends(get_db)):
    try:
        db.execute(select(func.count()).select_from(Game))
        return {"db_ok": True}
    except Exception:
        return {"db_ok": False}


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------
@app.get("/api/public/games")  # no response_model => we can include alias keys freely
def list_games(
    request: Request,
    q: str = Query("", description="search title"),
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

    rows = db.execute(
        base.offset((page - 1) * page_size).limit(page_size)
    ).scalars().all() or []

    items = [_game_row_to_dict(request, g) for g in rows]
    return {"total": int(total), "page": page, "page_size": page_size, "items": items}


@app.get("/api/public/category-counts")
def category_counts(db: Session = Depends(get_db)):
    rows = db.execute(select(Game)).scalars().all() or []
    counts: Dict[str, int] = {}
    for g in rows:
        for c in _categories_to_list(getattr(g, "categories", None)):
            counts[c] = counts.get(c, 0) + 1
    return counts


@app.get("/api/public/image-proxy")
async def image_proxy(url: str = Query(..., description="Absolute image URL")):
    if not url:
        raise HTTPException(status_code=400, detail="missing url")

    # serve our own thumbs directly
    if PUBLIC_BASE_URL and url.startswith(f"{PUBLIC_BASE_URL}/thumbs/"):
        rel = url.replace(PUBLIC_BASE_URL, "").lstrip("/")
        abs_path = os.path.join(os.getcwd(), rel)
        if os.path.exists(abs_path):
            ext = pathlib.Path(abs_path).suffix.lower()
            mime = "image/png" if ext == ".png" else "image/jpeg"
            return StreamingResponse(open(abs_path, "rb"), media_type=mime)

    # otherwise proxy
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        r = await client.get(url)
        r.raise_for_status()
        ctype = r.headers.get("content-type") or "application/octet-stream"
        return StreamingResponse(r.iter_bytes(), media_type=ctype)


# ---------------------------------------------------------------------
# Admin API
# ---------------------------------------------------------------------
@app.post("/api/admin/seed")
def admin_seed(x_admin_token: Optional[str] = Header(None), db: Session = Depends(get_db)):
    _require_admin(x_admin_token)
    samples = [
        Game(title="Azul", categories="Abstract Strategy, Renaissance"),
        Game(title="Cascadia", categories="Animals, Environmental"),
        Game(title="Wingspan", categories="Animals, Card Game, Educational"),
    ]
    for g in samples:
        db.add(g)
    db.commit()
    return {"inserted": len(samples)}


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

    data = await fetch_bgg_thing(bgg_id)  # expects: title, categories(list), year, players_min, players_max, playtime_min, playtime_max, thumbnail
    cats = ", ".join(data.get("categories") or [])

    if existing and not force:
        return {"ok": True, "id": existing.id, "cached": True}

    if existing:
        g = existing
        g.title = data["title"]
        g.categories = cats
        g.year = data.get("year")
        g.players_min = data.get("players_min")
        g.players_max = data.get("players_max")
        g.playtime_min = data.get("playtime_min")
        g.playtime_max = data.get("playtime_max")
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

    async def _dl_and_set():
        try:
            fname = await _download_to_thumbs(data.get("thumbnail") or "", f"{g.id}-{g.title}")
            if fname:
                db2 = SessionLocal()
                try:
                    g2 = db2.get(Game, g.id)
                    if g2:
                        g2.thumbnail_file = fname
                        g2.thumbnail_url = f"/thumbs/{fname}"
                        db2.add(g2)
                        db2.commit()
                finally:
                    db2.close()
        except Exception:
            pass

    if background is not None:
        background.add_task(_dl_and_set)

    return {"ok": True, "id": g.id, "cached": bool(existing and not force)}


# ---------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------
@app.on_event("startup")
def _startup():
    init_db()
    os.makedirs(THUMBS_DIR, exist_ok=True)
