import os
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

import httpx
from fastapi import FastAPI, Depends, Header, HTTPException, Query, Request, BackgroundTasks, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session
from starlette.types import ASGIApp, Receive, Scope, Send

from database import SessionLocal, init_db
from models import Game
from bgg_service import fetch_bgg_thing

# ------------------------------------------------------------------------------
# Logging setup
# ------------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Config
# ------------------------------------------------------------------------------
PUBLIC_BASE_URL = (os.getenv("PUBLIC_BASE_URL") or "").rstrip("/")
ADMIN_TOKEN = (os.getenv("ADMIN_TOKEN") or "").strip()

THUMBS_DIR = os.getenv("THUMBS_DIR", "/data/thumbs")
os.makedirs(THUMBS_DIR, exist_ok=True)

# Single shared HTTP client
httpx_client = httpx.AsyncClient(follow_redirects=True, timeout=30)

# API base for thumbnails
API_BASE = PUBLIC_BASE_URL or "https://mana-meeples-boardgame-list.onrender.com"

# ------------------------------------------------------------------------------
# Category mapping - improved with better keyword matching
# ------------------------------------------------------------------------------
CATEGORY_KEYS = [
    "COOP_ADVENTURE",
    "CORE_STRATEGY", 
    "GATEWAY_STRATEGY",
    "KIDS_FAMILIES",
    "PARTY_ICEBREAKERS",
]

# More comprehensive category mapping with multiple keywords per category
CATEGORY_MAPPING = {
    "COOP_ADVENTURE": {
        "keywords": [
            "cooperative", "coop", "co-op", "adventure", "narrative", "campaign", 
            "story", "quest", "exploration", "dungeon", "rpg", "legacy"
        ],
        "exact_matches": [
            "cooperative game", "adventure", "narrative choice", "campaign game",
            "exploration", "storytelling"
        ]
    },
    "CORE_STRATEGY": {
        "keywords": [
            "wargame", "war", "strategy", "civilization", "economic", "engine", 
            "building", "area control", "area majority", "influence", "deck building",
            "bag building", "heavy", "complex"
        ],
        "exact_matches": [
            "wargame", "area majority / influence", "deck, bag, and pool building",
            "engine building", "civilization", "area control", "economic"
        ]
    },
    "GATEWAY_STRATEGY": {
        "keywords": [
            "abstract", "tile placement", "pattern", "family", "gateway", 
            "light strategy", "animals", "environmental", "nature"
        ],
        "exact_matches": [
            "abstract strategy", "animals", "environmental", "family game", 
            "tile placement", "pattern building"
        ]
    },
    "KIDS_FAMILIES": {
        "keywords": [
            "children", "kids", "family", "educational", "learning", "memory",
            "dexterity", "simple", "young"
        ],
        "exact_matches": [
            "children's game", "educational", "memory", "dexterity", "family game"
        ]
    },
    "PARTY_ICEBREAKERS": {
        "keywords": [
            "party", "social", "deduction", "humor", "funny", "word", "trivia",
            "communication", "bluffing", "guessing", "ice breaker"
        ],
        "exact_matches": [
            "party game", "humor", "social deduction", "word game", "bluffing",
            "communication"
        ]
    }
}

# ------------------------------------------------------------------------------
# App setup
# ------------------------------------------------------------------------------
app = FastAPI(title="Mana & Meeples API", version="2.0.0")

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

# CORS middleware
cors_origins = [
    "https://manaandmeeples.co.nz",
    "https://www.manaandmeeples.co.nz",
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static thumbs
app.mount("/thumbs", StaticFiles(directory=THUMBS_DIR), name="thumbs")

# ------------------------------------------------------------------------------
# Database dependency
# ------------------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------------------
def _parse_categories(raw_categories) -> List[str]:
    """Parse categories from various formats into a clean list"""
    if not raw_categories:
        return []
    
    if isinstance(raw_categories, list):
        return [str(c).strip() for c in raw_categories if str(c).strip()]
    
    raw_str = str(raw_categories).strip()
    if not raw_str:
        return []
    
    # Handle JSON array format
    if raw_str.startswith("[") and raw_str.endswith("]"):
        try:
            parsed = json.loads(raw_str)
            return [str(c).strip() for c in parsed if str(c).strip()]
        except json.JSONDecodeError:
            pass
    
    # Handle comma-separated format
    return [c.strip() for c in raw_str.split(",") if c.strip()]

def _categorize_game(categories: List[str]) -> Optional[str]:
    """Automatically categorize a game based on its BGG categories"""
    if not categories:
        return None
    
    # Normalize categories for comparison
    normalized_cats = [cat.lower().strip() for cat in categories]
    category_text = " ".join(normalized_cats)
    
    # Score each category based on keyword matches
    scores = {}
    for category_key, mapping in CATEGORY_MAPPING.items():
        score = 0
        
        # Check exact matches first (higher weight)
        for exact_match in mapping["exact_matches"]:
            if exact_match.lower() in normalized_cats:
                score += 10
        
        # Check keyword matches
        for keyword in mapping["keywords"]:
            if keyword in category_text:
                score += 1
        
        if score > 0:
            scores[category_key] = score
    
    # Return the category with the highest score
    if scores:
        return max(scores, key=scores.get)
    
    return None

def _make_absolute_url(request: Request, url: Optional[str]) -> Optional[str]:
    """Convert relative URLs to absolute URLs"""
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    
    base = str(request.base_url).rstrip("/")
    return f"{base}{url}"

async def _download_thumbnail(url: str, filename_base: str) -> Optional[str]:
    """Download thumbnail image and save to disk"""
    if not url or not url.startswith("http"):
        return None
    
    try:
        # Create safe filename
        safe_name = "".join(c for c in filename_base.lower().replace(" ", "-") 
                           if c.isalnum() or c in "-_")[:50]
        
        # Determine extension
        ext = ".jpg"
        for candidate in [".png", ".jpg", ".jpeg", ".webp"]:
            if url.lower().endswith(candidate):
                ext = candidate
                break
        
        filename = f"{safe_name}{ext}"
        filepath = os.path.join(THUMBS_DIR, filename)
        
        # Download image
        response = await httpx_client.get(url)
        response.raise_for_status()
        
        with open(filepath, "wb") as f:
            f.write(response.content)
        
        logger.info(f"Downloaded thumbnail: {filename}")
        return filename
        
    except Exception as e:
        logger.error(f"Failed to download thumbnail from {url}: {e}")
        return None

def _game_to_dict(request: Request, game: Game) -> Dict[str, Any]:
    """Convert game model to dictionary for API response"""
    categories = _parse_categories(game.categories)
    
    # Handle thumbnail URL
    thumbnail_url = None
    if game.thumbnail_file:
        thumbnail_url = _make_absolute_url(request, f"/thumbs/{game.thumbnail_file}")
    elif game.thumbnail_url:
        thumbnail_url = game.thumbnail_url
    
    return {
        "id": game.id,
        "title": game.title or "",
        "categories": categories,
        "year": game.year,
        "year_published": game.year,  # Alias for frontend
        "players_min": game.players_min,
        "players_max": game.players_max,
        "min_players": game.players_min,  # Alias for frontend
        "max_players": game.players_max,  # Alias for frontend
        "playtime_min": game.playtime_min,
        "playtime_max": game.playtime_max,
        "playing_time": game.playtime_min or game.playtime_max,  # Alias for frontend
        "thumbnail_url": thumbnail_url,
        "image_url": thumbnail_url,  # Alias for frontend
        "mana_meeple_category": getattr(game, "mana_meeple_category", None),
        "description": getattr(game, "description", None),
        "bgg_id": getattr(game, "bgg_id", None),
        "created_at": game.created_at.isoformat() if hasattr(game, "created_at") and game.created_at else None,
    }

def _calculate_category_counts(games: List[Game]) -> Dict[str, int]:
    """Calculate counts for each category"""
    counts = {"all": len(games), "uncategorized": 0}
    
    # Initialize category counts
    for key in CATEGORY_KEYS:
        counts[key] = 0
    
    # Count games by category
    for game in games:
        category = getattr(game, "mana_meeple_category", None)
        if category and category in CATEGORY_KEYS:
            counts[category] += 1
        else:
            counts["uncategorized"] += 1
    
    return counts

def _require_admin_token(token: Optional[str]):
    """Validate admin token"""
    if not ADMIN_TOKEN or token != ADMIN_TOKEN:
        logger.warning(f"Invalid admin token attempt: {token}")
        raise HTTPException(status_code=401, detail="Invalid admin token")

# ------------------------------------------------------------------------------
# Health endpoints
# ------------------------------------------------------------------------------
@app.get("/api/health")
async def health_check():
    """Basic health check"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/api/health/db")
async def health_check_db(db: Session = Depends(get_db)):
    """Database health check"""
    try:
        count = db.execute(select(func.count()).select_from(Game)).scalar()
        return {"status": "healthy", "game_count": count}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(status_code=503, detail="Database unavailable")

# ------------------------------------------------------------------------------
# Debug endpoints
# ------------------------------------------------------------------------------
@app.get("/api/debug/categories")
async def debug_categories(db: Session = Depends(get_db)):
    """Debug endpoint to see all unique categories in the database"""
    games = db.execute(select(Game)).scalars().all()
    all_categories = []
    
    for game in games:
        categories = _parse_categories(game.categories)
        all_categories.extend(categories)
    
    unique_categories = sorted(list(set(all_categories)))
    
    return {
        "total_games": len(games),
        "unique_categories": unique_categories,
        "category_count": len(unique_categories)
    }

# ------------------------------------------------------------------------------
# Public API endpoints
# ------------------------------------------------------------------------------
@app.get("/api/public/games")
async def get_public_games(
    request: Request,
    q: str = Query("", description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(24, ge=1, le=100, description="Items per page"),
    sort: str = Query("title_asc", description="Sort order"),
    category: Optional[str] = Query(None, description="Category filter"),
    db: Session = Depends(get_db)
):
    """Get paginated list of games with filtering and search"""
    
    # Build base query
    query = select(Game)
    
    # Apply search filter
    if q.strip():
        search_term = f"%{q.strip()}%"
        query = query.where(Game.title.ilike(search_term))
    
    # Apply sorting
    if sort == "title_desc":
        query = query.order_by(Game.title.desc())
    elif sort == "year_desc":
        query = query.order_by(Game.year.desc().nulls_last())
    elif sort == "year_asc":
        query = query.order_by(Game.year.asc().nulls_last())
    else:  # Default to title_asc
        query = query.order_by(Game.title.asc())
    
    # Get all matching games first
    all_games = db.execute(query).scalars().all()
    
    # Apply category filtering (server-side for known categories)
    filtered_games = all_games
    if category and category != "all":
        if category == "uncategorized":
            filtered_games = [g for g in all_games if not getattr(g, "mana_meeple_category", None)]
        elif category in CATEGORY_KEYS:
            filtered_games = [g for g in all_games if getattr(g, "mana_meeple_category", None) == category]
    
    # Calculate pagination
    total = len(filtered_games)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_games = filtered_games[start_idx:end_idx]
    
    # Convert to response format
    items = [_game_to_dict(request, game) for game in page_games]
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items
    }

@app.get("/api/public/games/{game_id}")
async def get_public_game(
    request: Request,
    game_id: int = Path(..., description="Game ID"),
    db: Session = Depends(get_db)
):
    """Get details for a specific game"""
    game = db.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    return _game_to_dict(request, game)

@app.get("/api/public/category-counts")
async def get_category_counts(db: Session = Depends(get_db)):
    """Get counts for each category"""
    games = db.execute(select(Game)).scalars().all()
    return _calculate_category_counts(games)

@app.get("/api/public/image-proxy")
async def image_proxy(url: str = Query(..., description="Image URL to proxy")):
    """Proxy external images with caching headers"""
    try:
        response = await httpx_client.get(url)
        response.raise_for_status()
        
        content_type = response.headers.get("content-type", "application/octet-stream")
        
        # Set cache headers based on URL
        cache_control = "public, max-age=300"  # 5 minutes default
        if url.startswith(API_BASE + "/thumbs/"):
            cache_control = "public, max-age=31536000, immutable"  # 1 year for our own images
        
        headers = {
            "Content-Type": content_type,
            "Cache-Control": cache_control
        }
        
        return Response(content=response.content, headers=headers)
        
    except httpx.HTTPError as e:
        logger.error(f"Image proxy error for {url}: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch image: {str(e)}")

# ------------------------------------------------------------------------------
# Admin API endpoints
# ------------------------------------------------------------------------------
@app.post("/api/admin/games")
async def create_game(
    game_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    x_admin_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Create a new game (admin only)"""
    _require_admin_token(x_admin_token)
    
    try:
        # Check if game already exists by BGG ID
        bgg_id = game_data.get("bgg_id")
        if bgg_id:
            existing = db.execute(select(Game).where(Game.bgg_id == bgg_id)).scalar_one_or_none()
            if existing:
                raise HTTPException(status_code=400, detail="Game already exists")
        
        # Create game
        game = Game(
            title=game_data.get("title", ""),
            categories=",".join(game_data.get("categories", [])),
            year=game_data.get("year"),
            players_min=game_data.get("players_min"),
            players_max=game_data.get("players_max"),
            playtime_min=game_data.get("playtime_min"),
            playtime_max=game_data.get("playtime_max"),
            bgg_id=bgg_id,
            mana_meeple_category=game_data.get("mana_meeple_category")
        )
        
        # Auto-categorize if no category provided
        if not game.mana_meeple_category:
            categories = _parse_categories(game.categories)
            game.mana_meeple_category = _categorize_game(categories)
        
        db.add(game)
        db.commit()
        db.refresh(game)
        
        # Download thumbnail in background if provided
        thumbnail_url = game_data.get("thumbnail_url") or game_data.get("image_url")
        if thumbnail_url:
            background_tasks.add_task(_download_and_update_thumbnail, game.id, thumbnail_url)
        
        logger.info(f"Created game: {game.title} (ID: {game.id})")
        return {"id": game.id, "title": game.title}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create game: {e}")
        raise HTTPException(status_code=500, detail="Failed to create game")

async def _download_and_update_thumbnail(game_id: int, thumbnail_url: str):
    """Background task to download and update game thumbnail"""
    try:
        db = SessionLocal()
        game = db.get(Game, game_id)
        if not game:
            return
        
        filename = await _download_thumbnail(thumbnail_url, f"{game_id}-{game.title}")
        if filename:
            game.thumbnail_file = filename
            game.thumbnail_url = f"/thumbs/{filename}"
            db.add(game)
            db.commit()
            logger.info(f"Updated thumbnail for game {game_id}: {filename}")
        
    except Exception as e:
        logger.error(f"Failed to download thumbnail for game {game_id}: {e}")
    finally:
        db.close()

@app.post("/api/admin/import/bgg")
async def import_from_bgg(
    bgg_id: int = Query(..., description="BGG game ID"),
    force: bool = Query(False, description="Force reimport if exists"),
    x_admin_token: Optional[str] = Header(None),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """Import game from BoardGameGeek (admin only)"""
    _require_admin_token(x_admin_token)
    
    try:
        # Check if already exists
        existing = db.execute(select(Game).where(Game.bgg_id == bgg_id)).scalar_one_or_none()
        if existing and not force:
            return {"id": existing.id, "title": existing.title, "cached": True}
        
        # Fetch from BGG
        bgg_data = await fetch_bgg_thing(bgg_id)
        categories_str = ", ".join(bgg_data.get("categories", []))
        
        if existing:
            # Update existing
            existing.title = bgg_data["title"]
            existing.categories = categories_str
            existing.year = bgg_data.get("year")
            existing.players_min = bgg_data.get("players_min")
            existing.players_max = bgg_data.get("players_max")
            existing.playtime_min = bgg_data.get("playtime_min")
            existing.playtime_max = bgg_data.get("playtime_max")
            
            # Re-categorize
            categories = _parse_categories(categories_str)
            existing.mana_meeple_category = _categorize_game(categories)
            
            db.add(existing)
            game = existing
        else:
            # Create new
            categories = _parse_categories(categories_str)
            game = Game(
                title=bgg_data["title"],
                categories=categories_str,
                year=bgg_data.get("year"),
                players_min=bgg_data.get("players_min"),
                players_max=bgg_data.get("players_max"),
                playtime_min=bgg_data.get("playtime_min"),
                playtime_max=bgg_data.get("playtime_max"),
                bgg_id=bgg_id,
                mana_meeple_category=_categorize_game(categories)
            )
            db.add(game)
        
        db.commit()
        db.refresh(game)
        
        # Download thumbnail in background
        thumbnail_url = bgg_data.get("thumbnail")
        if thumbnail_url and background_tasks:
            background_tasks.add_task(_download_and_update_thumbnail, game.id, thumbnail_url)
        
        logger.info(f"Imported from BGG: {game.title} (BGG ID: {bgg_id})")
        return {"id": game.id, "title": game.title, "cached": bool(existing)}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to import BGG game {bgg_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to import game: {str(e)}")

# ------------------------------------------------------------------------------
# Startup
# ------------------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    """Initialize database and create thumbs directory"""
    logger.info("Starting Mana & Meeples API...")
    init_db()
    os.makedirs(THUMBS_DIR, exist_ok=True)
    logger.info(f"Thumbnails directory: {THUMBS_DIR}")
    logger.info("API startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down API...")
    await httpx_client.aclose()
    logger.info("API shutdown complete")

# ------------------------------------------------------------------------------
# Root redirect
# ------------------------------------------------------------------------------
@app.get("/")
async def root():
    """Root endpoint - redirect to API docs"""
    return {"message": "Mana & Meeples API", "docs": "/docs", "health": "/api/health"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
