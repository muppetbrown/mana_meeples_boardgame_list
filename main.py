from fastapi import FastAPI, Header, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from typing import List

from config import CORS_ORIGINS, ADMIN_TOKEN
from database import db_ping, SessionLocal, init_db
from models import Game
from schemas import GameOut, PagedGames

app = FastAPI(title="Mana & Meeples API", version="0.2")

# CORS: your domains only
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS or [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/api/health")
def health():
    return {"ok": True}

@app.get("/api/health/db")
def health_db():
    return {"db_ok": db_ping()}

# ---------- PUBLIC ----------

@app.get("/api/public/games", response_model=PagedGames)
def list_games(
    q: str = Query("", description="search in title"),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    sort: str = Query("title_asc", pattern="^(title_asc|title_desc)$"),
    db: Session = Depends(get_db),
):
    query = select(Game)
    if q:
        like = f"%{q.strip()}%"
        query = query.where(Game.title.ilike(like))

    # total
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

    # sort
    if sort == "title_desc":
        query = query.order_by(Game.title.desc())
    else:
        query = query.order_by(Game.title.asc())

    # pagination
    offset = (page - 1) * page_size
    rows: List[Game] = db.execute(query.offset(offset).limit(page_size)).scalars().all()

    def to_out(g: Game) -> GameOut:
        cats = [c.strip() for c in (g.categories or "").split(",") if c.strip()]
        return GameOut(
            id=g.id, title=g.title, categories=cats, year=g.year,
            players_min=g.players_min, players_max=g.players_max,
            playtime_min=g.playtime_min, playtime_max=g.playtime_max,
            thumbnail_url=g.thumbnail_url,
        )

    items = [to_out(g) for g in rows]
    return {"total": total, "page": page, "page_size": page_size, "items": items}

@app.get("/api/public/category-counts")
def category_counts(db: Session = Depends(get_db)):
    rows = db.execute(select(Game.categories)).all()
    counts: dict[str, int] = {}
    for (cats_str,) in rows:
        for c in [x.strip() for x in (cats_str or "").split(",") if x.strip()]:
            counts[c] = counts.get(c, 0) + 1
    counts["all"] = len(rows)
    counts["uncategorized"] = sum(1 for (cats_str,) in rows if not (cats_str or "").strip())
    return counts

# ---------- ADMIN (seed for quick testing) ----------

@app.post("/api/admin/seed")
def admin_seed(x_admin_token: str = Header(None), db: Session = Depends(get_db)):
    if not ADMIN_TOKEN or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="invalid admin token")
    samples = [
        Game(title="Azul", categories="Abstract,Family", year=2017, players_min=2, players_max=4, playtime_min=30, playtime_max=45),
        Game(title="Wingspan", categories="Engine Building,Card Game", year=2019, players_min=1, players_max=5, playtime_min=40, playtime_max=70),
        Game(title="Cascadia", categories="Tile Placement,Family", year=2021, players_min=1, players_max=4, playtime_min=30, playtime_max=45),
    ]
    db.add_all(samples)
    db.commit()
    return {"inserted": len(samples)}
