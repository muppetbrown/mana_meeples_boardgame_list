import os
import json
from typing import Optional, List, Dict, Tuple

import httpx
from fastapi import FastAPI, Depends, Header, HTTPException, Query, Request, BackgroundTasks, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from starlette.types import ASGIApp, Receive, Scope, Send

from database import SessionLocal, init_db
from models import Game
from bgg_service import fetch_bgg_thing

# ------------------------------------------------------------------------------
# Config
# ------------------------------------------------------------------------------
PUBLIC_BASE_URL = (os.getenv("PUBLIC_BASE_URL") or "").rstrip("/")
ADMIN_TOKEN = (os.getenv("ADMIN_TOKEN") or "").strip()

THUMBS_DIR = os.getenv("THUMBS_DIR", "/data/thumbs")
os.makedirs(THUMBS_DIR, exist_ok=True)

# Single shared client
httpx_client = httpx.AsyncClient(follow_redirects=True, timeout=20)

# Use your render base to recognize our own thumbs in the image-proxy
API_BASE = "https://mana-meeples-boardgame-list.onrender.com".rstrip("/")

# ------------------------------------------------------------------------------
# Category buckets (BGG -> enum KEY expected by frontend)
# Frontend keys are LOWERCASE with underscores. Labels are handled client-side.
# ------------------------------------------------------------------------------
CATEGORY_KEYS: Tuple[str, ...] = (
    "coop_adventure",
    "core_strategy",
    "gateway_strategy",
    "kids_families",
    "party_icebreakers",
)
# Map enum key -> set of lowercase BGG categories that should count toward it
BUCKET_MAP: Dict[str, set] = {
    "coop_adventure": {
        "cooperative game", "adventure", "narrative choice", "campaign game",
    },
    "core_strategy": {
        "wargame", "area majority / influence", "deck, bag, and pool building",
        "engine building", "civilization", "area control", "economic",
    },
    "gateway_strategy": {
        "abstract strategy", "animals", "environmental", "family game", "tile placement",
    },
    "kids_families": {
        "children's game", "educational", "memory", "dexterity",
    },
    "party_icebreakers": {
        "party game", "humor", "social deduction", "word game",
    },
}

# ------------------------------------------------------------------------------
# App + middleware
# ------------------------------------------------------------------------------
app = FastAPI(title="Mana & Meeples API", version="1.0.0")

class CacheThumbsMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                path = scope.get("path", "")
                if path.startswith("/thumbs/"):
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

# Serve static thumbs (e.g. /thumbs/1-azul.png)
app.mount("/thumbs", StaticFiles(directory=THUMBS_DIR), name="thumbs")

# ------------------------------------------------------------------------------
# DB session
# ------------------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
def _categories_to_list(raw) -> List[str]:
    """Accept DB value as list, JSON text, or comma-separated string; return list[str]."""
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(c).strip() for c in raw if str(c).strip()]
    s = str(raw).strip()
    if s.startswith("["):
        try:
            arr = json.loads(s)
            return [str(c).strip() for c in arr if str(c).strip()]
        except Exception:
            pass
    return [p.strip() for p in s.split(",") if p.strip()]

def _abs_url(request: Request, url: Optional[str]) -> Optional[str]:
    """Turn '/thumbs/x.png' into absolute 'https://host/thumbs/x.png'."""
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
        r = await httpx_client.get(url)
        r.raise_for_status()
        with open(dest, "wb") as f:
            f.write(r.content)
        return filename
    except Exception:
        return None

def _game_to_public_dict(request: Request, g: Game) -> Dict:
    """
    Shape the game object to include the names your bundle reads.
    Also emit an absolute image URL so the image-proxy can fetch it.
    """
    cats = _categories_to_list(getattr(g, "categories", None))

    thumb = (getattr(g, "thumbnail_url", None) or "").strip()
    if not thumb and getattr(g, "thumbnail_file", None):
        thumb = f"/thumbs/{g.thumbnail_file}"
    abs_thumb = _abs_url(request, thumb) if thumb else None

    year = getattr(g, "year", None)
    pmin = getattr(g, "players_min", None)
    pmax = getattr(g, "players_max", None)
    tmin = getattr(g, "playtime_min", None)
    tmax = getattr(g, "playtime_max", None)
    playing_time = tmin or tmax

    return {
        # canonical
        "id": g.id,
        "title": getattr(g, "title", "") or "",
        "categories": cats,
        "year": year,
        "players_min": pmin,
        "players_max": pmax,
        "playtime_min": tmin,
        "playtime_max": tmax,
        "thumbnail_url": abs_thumb,

        # aliases used by the public bundle
        "image_url": abs_thumb,
        "year_published": year,
        "min_players": pmin,
        "max_players": pmax,
        "playing_time": playing_time,

        # optionally include our enum category if we add it later
        "mana_meeple_category": getattr(g, "mana_meeple_category", None) if hasattr(g, "mana_meeple_category") else None,
        # add any extra fields your GameDetails page might read:
        "description": getattr(g, "description", None) if hasattr(g, "description") else None,
        "bgg_id": getattr(g, "bgg_id", None) if hasattr(g, "bgg_id") else None,
    }

def _bucket_matches(cats_lower: List[str], bucket_key: str) -> bool:
    """True if any of the game's categories belong to the given bucket key."""
    keys = BUCKET_MAP.get(bucket_key, set())
    return any(c in keys for c in cats_lower)

def _require_admin(token: Optional[str]):
    if not ADMIN_TOKEN or token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="invalid admin token")

# ------------------------------------------------------------------------------
# Health
# ------------------------------------------------------------------------------
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

# ------------------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------------------
@app.get("/api/public/games")
def public_games(
    request: Request,
    q: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    sort: str = Query("title_asc"),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Returns paged games. If 'category' is one of CATEGORY_KEYS, filter on-the-fly
    using BUCKET_MAP; 'all' => no filter; 'uncategorized' handled client-side.
    """
    qry = db.query(Game)

    if q:
        qry = qry.filter(Game.title.ilike(f"%{q}%"))

    # Sorting
    if sort == "title_desc":
        qry = qry.order_by(Game.title.desc())
    else:
        qry = qry.order_by(Game.title.asc())

    # Run once to get total (before paging) since we may client-filter below
    all_rows = qry.all()
    # Category filtering (server-side) for our 5 buckets; 'uncategorized' is client-side
    if category and category not in ("all", "uncategorized") and category in CATEGORY_KEYS:
        filtered = []
        for g in all_rows:
            cats = [c.lower() for c in _categories_to_list(getattr(g, "categories", None))]
            if _bucket_matches(cats, category):
                filtered.append(g)
        total = len(filtered)
        rows = filtered
    else:
        total = len(all_rows)
        rows = all_rows

    # Pagination
    start = (page - 1) * page_size
    end = start + page_size
    page_rows = rows[start:end]

    items = [_game_to_public_dict(request, g) for g in page_rows]
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }

@app.get("/api/public/games/{game_id}")
def public_game_details(
    request: Request,
    game_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    g = db.get(Game, game_id)
    if not g:
        raise HTTPException(404, "game not found")
    return _game_to_public_dict(request, g)

@app.get("/api/public/category-counts")
def public_category_counts(db: Session = Depends(get_db)):
    """
    Return counts keyed by the enum KEYS the frontend uses:
    {
      "all": N,
      "gateway_strategy": X,
      "kids_families": Y,
      "coop_adventure": Z,
      "party_icebreakers": ...,
      "core_strategy": ...,
      "uncategorized": U
    }
    """
    rows = db.execute(select(Game)).scalars().all() or []
    counts: Dict[str, int] = {"all": len(rows), "uncategorized": 0}
    for key in CATEGORY_KEYS:
        counts[key] = 0

    for g in rows:
        cats = [c.lower() for c in _categories_to_list(getattr(g, "categories", None))]
        matched = False
        for key in CATEGORY_KEYS:
            if _bucket_matches(cats, key):
                counts[key] += 1
                matched = True
        if not matched:
            counts["uncategorized"] += 1

    return counts

@app.get("/api/public/image-proxy")
async def image_proxy(url: str):
    """
    Proxies an image URL. If it's our own /thumbs/*, send a long-lived cache header.
    Otherwise, set a short cache.
    """
    try:
        r = await httpx_client.get(url)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Upstream error: {e!s}")

    content_type = r.headers.get("content-type", "application/octet-stream")
    headers = {"Content-Type": content_type}
    try:
        if url.startswith(API_BASE + "/thumbs/"):
            headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            headers["Cache-Control"] = "public, max-age=300"
    except Exception:
        headers["Cache-Control"] = "public, max-age=300"

    return Response(content=r.content, status_code=r.status_code, headers=headers)

# ------------------------------------------------------------------------------
# Admin API
# ------------------------------------------------------------------------------
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

    data = await fetch_bgg_thing(bgg_id)
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

# ------------------------------------------------------------------------------
# Startup
# ------------------------------------------------------------------------------
@app.on_event("startup")
def _startup():
    init_db()
    os.makedirs(THUMBS_DIR, exist_ok=True)
