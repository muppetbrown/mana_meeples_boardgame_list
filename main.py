import os
import json
import logging
import time
from typing import Optional, List, Dict, Any
from datetime import datetime
from collections import defaultdict

import httpx
from fastapi import FastAPI, Depends, Header, HTTPException, Query, Request, BackgroundTasks, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import case, select, func, and_, or_, text
from sqlalchemy.orm import Session
from starlette.types import ASGIApp, Receive, Scope, Send

from database import SessionLocal, init_db, engine
from models import Game
from bgg_service import fetch_bgg_thing
from schemas import BGGGameImport, CSVImport
from exceptions import GameServiceError, GameNotFoundError, BGGServiceError, ValidationError, DatabaseError
from config import HTTP_TIMEOUT, HTTP_RETRIES, RATE_LIMIT_ATTEMPTS, RATE_LIMIT_WINDOW

# ------------------------------------------------------------------------------
# Logging setup with structured logging
# ------------------------------------------------------------------------------

# Enhanced logging with structured format
class StructuredFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if they exist
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'bgg_id'):
            log_entry['bgg_id'] = record.bgg_id
        if hasattr(record, 'game_id'):
            log_entry['game_id'] = record.game_id
            
        return json.dumps(log_entry)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

# Use structured logging in production
if os.getenv('ENVIRONMENT') == 'production':
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    logging.getLogger().handlers = [handler]

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Config
# ------------------------------------------------------------------------------
PUBLIC_BASE_URL = (os.getenv("PUBLIC_BASE_URL") or "").rstrip("/")
ADMIN_TOKEN = (os.getenv("ADMIN_TOKEN") or "").strip()

# Rate limiting for admin authentication attempts
admin_attempt_tracker = defaultdict(list)

THUMBS_DIR = os.getenv("THUMBS_DIR", "/data/thumbs")
os.makedirs(THUMBS_DIR, exist_ok=True)

# Single shared HTTP client
httpx_client = httpx.AsyncClient(follow_redirects=True, timeout=HTTP_TIMEOUT)


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

# Exception handlers
@app.exception_handler(GameNotFoundError)
async def game_not_found_handler(request: Request, exc: GameNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})

@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})

@app.exception_handler(BGGServiceError)
async def bgg_service_error_handler(request: Request, exc: BGGServiceError):
    return JSONResponse(status_code=503, content={"detail": f"BGG service error: {str(exc)}"})

@app.exception_handler(DatabaseError)
async def database_error_handler(request: Request, exc: DatabaseError):
    return JSONResponse(status_code=500, content={"detail": "Database operation failed"})

import time
import uuid
from collections import defaultdict, deque

# Performance monitoring
class PerformanceMonitor:
    def __init__(self):
        self.request_times = deque(maxlen=1000)  # Keep last 1000 requests
        self.endpoint_stats = defaultdict(lambda: {"count": 0, "total_time": 0, "errors": 0})
        self.slow_queries = deque(maxlen=100)  # Keep last 100 slow queries
    
    def record_request(self, path: str, method: str, duration: float, status_code: int):
        self.request_times.append(duration)
        endpoint_key = f"{method} {path}"
        stats = self.endpoint_stats[endpoint_key]
        stats["count"] += 1
        stats["total_time"] += duration
        if status_code >= 400:
            stats["errors"] += 1
        
        # Record slow queries (>2 seconds)
        if duration > 2.0:
            self.slow_queries.append({
                "path": path,
                "method": method,
                "duration": duration,
                "timestamp": time.time()
            })
    
    def get_stats(self):
        if not self.request_times:
            return {"message": "No requests recorded yet"}
        
        total_requests = len(self.request_times)
        avg_response_time = sum(self.request_times) / total_requests
        
        return {
            "total_requests": total_requests,
            "avg_response_time_ms": round(avg_response_time * 1000, 2),
            "slowest_endpoints": sorted([
                {
                    "endpoint": endpoint,
                    "avg_time_ms": round((stats["total_time"] / stats["count"]) * 1000, 2),
                    "requests": stats["count"],
                    "errors": stats["errors"]
                }
                for endpoint, stats in self.endpoint_stats.items()
            ], key=lambda x: x["avg_time_ms"], reverse=True)[:10],
            "recent_slow_queries": list(self.slow_queries)[-10:]
        }

performance_monitor = PerformanceMonitor()

class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]
        status_code = 200  # Default
        
        # Add request ID to scope for downstream handlers
        scope["request_id"] = request_id
        
        path = scope.get("path", "")
        method = scope.get("method", "")
        
        logger.info(f"Request started: {method} {path}", extra={'request_id': request_id})
        
        # Capture status code from response
        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            duration = time.time() - start_time
            status_code = 500
            performance_monitor.record_request(path, method, duration, status_code)
            logger.error(
                f"Request failed: {method} {path} - {str(e)} ({duration:.3f}s)", 
                extra={'request_id': request_id}
            )
            raise
        else:
            duration = time.time() - start_time
            performance_monitor.record_request(path, method, duration, status_code)
            logger.info(
                f"Request completed: {method} {path} ({duration:.3f}s)", 
                extra={'request_id': request_id}
            )

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

app.add_middleware(RequestLoggingMiddleware)
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

def _parse_json_field(field_value) -> List[str]:
    """Parse JSON field (designers, publishers, mechanics, etc.) into a list"""
    if not field_value:
        return []
    
    if isinstance(field_value, list):
        return field_value
    
    try:
        parsed = json.loads(field_value)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []

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
    
    # Parse JSON fields safely
    designers = _parse_json_field(getattr(game, 'designers', None))
    publishers = _parse_json_field(getattr(game, 'publishers', None))
    mechanics = _parse_json_field(getattr(game, 'mechanics', None))
    artists = _parse_json_field(getattr(game, 'artists', None))
    
    # Handle thumbnail URL - prioritize larger image over thumbnail
    thumbnail_url = None
    if hasattr(game, 'thumbnail_file') and game.thumbnail_file:
        thumbnail_url = _make_absolute_url(request, f"/thumbs/{game.thumbnail_file}")
    elif hasattr(game, 'image') and game.image:  # Use the larger image first
        thumbnail_url = game.image
    elif hasattr(game, 'thumbnail_url') and game.thumbnail_url:
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
        "designers": designers,
        "publishers": publishers,  
        "mechanics": mechanics,
        "artists": artists,
        "average_rating": getattr(game, "average_rating", None),
        "complexity": getattr(game, "complexity", None),
        "bgg_rank": getattr(game, "bgg_rank", None),
        "min_age": getattr(game, "min_age", None),
        "is_cooperative": getattr(game, "is_cooperative", None),
        "users_rated": getattr(game, "users_rated", None),
        "bgg_id": getattr(game, "bgg_id", None),
        "created_at": game.created_at.isoformat() if hasattr(game, "created_at") and game.created_at else None,
        "nz_designer": getattr(game, "nz_designer", False),
        "game_type": getattr(game, "game_type", None),
    }

def _calculate_category_counts(games) -> Dict[str, int]:
    """Calculate counts for each category"""
    counts = {"all": len(games), "uncategorized": 0}
    
    # Initialize category counts
    for key in CATEGORY_KEYS:
        counts[key] = 0
    
    # Count games by category
    for game in games:
        # Handle both Game objects and tuples from select queries
        if hasattr(game, 'mana_meeple_category'):
            category = game.mana_meeple_category
        else:
            # Assume it's a tuple (id, mana_meeple_category)
            category = game[1]
            
        if category and category in CATEGORY_KEYS:
            counts[category] += 1
        else:
            counts["uncategorized"] += 1
    
    return counts

def _get_client_ip(request: Request) -> str:
    """Extract client IP from request"""
    if request.client:
        return request.client.host
    # Check for forwarded headers in case of proxy
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    return "unknown"

def _success_response(data: Any = None, message: str = "Success") -> Dict[str, Any]:
    """Standardized success response format"""
    response = {
        "success": True,
        "message": message,
        "timestamp": datetime.utcnow().isoformat() + 'Z'
    }
    if data is not None:
        response["data"] = data
    return response

def _error_response(message: str, error_code: str = "GENERAL_ERROR", details: Any = None) -> Dict[str, Any]:
    """Standardized error response format"""
    response = {
        "success": False,
        "error": {
            "code": error_code,
            "message": message
        },
        "timestamp": datetime.utcnow().isoformat() + 'Z'
    }
    if details is not None:
        response["error"]["details"] = details
    return response

def _require_admin_token(token: Optional[str], client_ip: str = "unknown"):
    """Validate admin token with rate limiting"""
    current_time = time.time()
    
    # Clean old attempts from tracker (older than rate limit window)
    cutoff_time = current_time - RATE_LIMIT_WINDOW
    admin_attempt_tracker[client_ip] = [
        attempt_time for attempt_time in admin_attempt_tracker[client_ip] 
        if attempt_time > cutoff_time
    ]
    
    # Check if rate limited
    if len(admin_attempt_tracker[client_ip]) >= RATE_LIMIT_ATTEMPTS:
        logger.warning(f"Rate limited admin token attempts from {client_ip}")
        raise HTTPException(
            status_code=429, 
            detail="Too many failed authentication attempts. Please try again later."
        )
    
    # Validate token
    if not ADMIN_TOKEN or token != ADMIN_TOKEN:
        # Record failed attempt
        admin_attempt_tracker[client_ip].append(current_time)
        logger.warning(f"Invalid admin token attempt from {client_ip}")
        raise HTTPException(status_code=401, detail="Invalid admin token")

async def _download_and_update_thumbnail(game_id: int, thumbnail_url: str):
    """Background task to download and update game thumbnail"""
    try:
        db = SessionLocal()
        game = db.get(Game, game_id)
        if not game:
            return
        
        filename = await _download_thumbnail(thumbnail_url, f"{game_id}-{game.title}")
        if filename:
            if hasattr(game, 'thumbnail_file'):
                game.thumbnail_file = filename
            if hasattr(game, 'thumbnail_url'):
                game.thumbnail_url = f"/thumbs/{filename}"
            db.add(game)
            db.commit()
            logger.info(f"Updated thumbnail for game {game_id}: {filename}")
        
    except Exception as e:
        logger.error(f"Failed to download thumbnail for game {game_id}: {e}")
    finally:
        db.close()

async def _reimport_single_game(game_id: int, bgg_id: int):
    """Background task to re-import a single game with enhanced data"""
    try:
        db = SessionLocal()
        game = db.get(Game, game_id)
        if not game:
            logger.warning(f"Game {game_id} not found for reimport")
            return
        
        # Fetch enhanced data from BGG
        bgg_data = await fetch_bgg_thing(bgg_id)
        
        # Update game with enhanced data
        game.title = bgg_data.get("title", game.title)
        game.categories = ", ".join(bgg_data.get("categories", []))
        game.year = bgg_data.get("year", game.year)
        game.players_min = bgg_data.get("players_min", game.players_min)
        game.players_max = bgg_data.get("players_max", game.players_max)
        game.playtime_min = bgg_data.get("playtime_min", game.playtime_min)
        game.playtime_max = bgg_data.get("playtime_max", game.playtime_max)
        
        # Update enhanced fields if they exist in the model
        if hasattr(game, 'description'):
            game.description = bgg_data.get("description")
        if hasattr(game, 'designers'):
            game.designers = json.dumps(bgg_data.get("designers", []))
        if hasattr(game, 'publishers'):
            game.publishers = json.dumps(bgg_data.get("publishers", []))
        if hasattr(game, 'mechanics'):
            game.mechanics = json.dumps(bgg_data.get("mechanics", []))
        if hasattr(game, 'artists'):
            game.artists = json.dumps(bgg_data.get("artists", []))
        if hasattr(game, 'average_rating'):
            game.average_rating = bgg_data.get("average_rating")
        if hasattr(game, 'complexity'):
            game.complexity = bgg_data.get("complexity")
        if hasattr(game, 'bgg_rank'):
            game.bgg_rank = bgg_data.get("bgg_rank")
        if hasattr(game, 'users_rated'):
            game.users_rated = bgg_data.get("users_rated")
        if hasattr(game, 'min_age'):
            game.min_age = bgg_data.get("min_age")
        if hasattr(game, 'is_cooperative'):
            game.is_cooperative = bgg_data.get("is_cooperative")
        if hasattr(game, 'game_type'):
            game.game_type = bgg_data.get("game_type")
        if hasattr(game, 'image'):
            game.image = bgg_data.get("image")  # Store the full-size image URL
        if hasattr(game, 'thumbnail_url'):
            game.thumbnail_url = bgg_data.get("thumbnail")  # Store the thumbnail URL separately
        
        # Re-categorize based on new data
        categories = _parse_categories(game.categories)
        game.mana_meeple_category = _categorize_game(categories)
        
        db.add(game)
        db.commit()
        
        # Download new thumbnail if available
        thumbnail_url = bgg_data.get("image") or bgg_data.get("thumbnail")  # Use larger image first
        if thumbnail_url:
            await _download_and_update_thumbnail(game_id, thumbnail_url)
        
        logger.info(f"Successfully reimported game {game_id}: {game.title}")
        
    except Exception as e:
        logger.error(f"Failed to reimport game {game_id}: {e}")
        if 'db' in locals():
            db.rollback()
    finally:
        if 'db' in locals():
            db.close()

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
    # Only select the columns we need to avoid missing column errors
    games = db.execute(select(Game.id, Game.categories)).all()
    all_categories = []
    
    for game in games:
        # Handle tuple from select query
        categories = _parse_categories(game[1])
        all_categories.extend(categories)
    
    unique_categories = sorted(list(set(all_categories)))
    
    return {
        "total_games": len(games),
        "unique_categories": unique_categories,
        "category_count": len(unique_categories)
    }

@app.get("/api/debug/database-info")
async def debug_database_info(
    limit: Optional[int] = Query(None, description="Number of games to return (default: all)"),
    db: Session = Depends(get_db)
):
    """Debug endpoint to see database structure and sample data"""
    # Select all columns from your schema
    query = select(
        Game.id, Game.title, Game.categories, Game.year, 
        Game.players_min, Game.players_max, Game.playtime_min, Game.playtime_max,
        Game.thumbnail_url, Game.image, Game.created_at, Game.bgg_id,
        Game.thumbnail_file, Game.mana_meeple_category, Game.description,
        Game.designers, Game.publishers, Game.mechanics, Game.artists,
        Game.average_rating, Game.complexity, Game.bgg_rank, Game.users_rated,
        Game.min_age, Game.is_cooperative, Game.nz_designer, Game.game_type
    )
    
    games = db.execute(query).all()
    
    # Apply limit if specified, otherwise return all
    if limit is not None:
        games = games[:limit]
    
    return {
        "total_games_in_db": db.execute(select(func.count()).select_from(Game)).scalar(),
        "games_returned": len(games),
        "sample_games": [
            {
                "id": g[0],
                "title": g[1],
                "categories": g[2],
                "year": g[3],
                "players_min": g[4],
                "players_max": g[5],
                "playtime_min": g[6],
                "playtime_max": g[7],
                "thumbnail_url": g[8],
                "image": g[9],
                "created_at": g[10].isoformat() if g[10] else None,
                "bgg_id": g[11],
                "thumbnail_file": g[12],
                "mana_meeple_category": g[13],
                "description": g[14],
                "designers": g[15],
                "publishers": g[16],
                "mechanics": g[17],
                "artists": g[18],
                "average_rating": g[19],
                "complexity": g[20],
                "bgg_rank": g[21],
                "users_rated": g[22],
                "min_age": g[23],
                "is_cooperative": g[24],
                "nz_designer": g[25],
                "game_type": g[26]
            }
            for g in games
        ]
    }


@app.get("/api/debug/performance")
async def get_performance_stats(request: Request, x_admin_token: Optional[str] = Header(None)):
    """Get performance monitoring stats (admin only)"""
    client_ip = request.client.host if request.client else "unknown"
    _require_admin_token(x_admin_token, client_ip)
    return performance_monitor.get_stats()

# ------------------------------------------------------------------------------
# Public API endpoints
# ------------------------------------------------------------------------------
@app.get("/api/public/games")
async def get_public_games(
    request: Request,
    q: str = Query("", description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(24, ge=1, le=1000, description="Items per page"),
    sort: str = Query("title_asc", description="Sort order"),
    category: Optional[str] = Query(None, description="Category filter"),
    designer: Optional[str] = Query(None, description="Designer filter"),
    nz_designer: Optional[str] = Query(None, description="Filter by NZ designers"),
    db: Session = Depends(get_db)
):
    """Get paginated list of games with filtering and search"""
    
    # Build base query
    query = select(Game)
    
    # Apply search filter - search across title, designers, and description (keywords)
    if q.strip():
        search_term = f"%{q.strip()}%"
        search_conditions = [
            Game.title.ilike(search_term)
        ]

        # Add designer search if the field exists and has data
        if hasattr(Game, 'designers'):
            search_conditions.append(Game.designers.ilike(search_term))

        # Add description search for keyword functionality
        if hasattr(Game, 'description'):
            search_conditions.append(Game.description.ilike(search_term))

        # Combine all search conditions with OR
        query = query.where(or_(*search_conditions))
    
    # Apply designer filter
    if designer and designer.strip():
        designer_filter = f"%{designer.strip()}%"
        if hasattr(Game, 'designers'):
            query = query.where(Game.designers.ilike(designer_filter))

    # Apply NZ designer filter
    if nz_designer is not None:
        # Convert string parameter to boolean for database comparison
        nz_designer_bool = nz_designer.lower() in ['true', '1', 'yes'] if isinstance(nz_designer, str) else bool(nz_designer)
        query = query.where(Game.nz_designer == nz_designer_bool)
    
    # Apply sorting
    if sort == "title_desc":
        query = query.order_by(Game.title.desc())
    elif sort == "year_desc":
        query = query.order_by(Game.year.desc().nulls_last())
    elif sort == "year_asc":
        query = query.order_by(Game.year.asc().nulls_last())
    elif sort == "rating_desc":
        if hasattr(Game, 'average_rating'):
            query = query.order_by(Game.average_rating.desc().nulls_last())
        else:
            # Fallback to title if rating field doesn't exist
            query = query.order_by(Game.title.asc())
    elif sort == "rating_asc":
        if hasattr(Game, 'average_rating'):
            query = query.order_by(Game.average_rating.asc().nulls_last())
        else:
            # Fallback to title if rating field doesn't exist
            query = query.order_by(Game.title.asc())
    elif sort == "time_asc":
        # Sort by average playing time (min + max) / 2, ascending
        avg_time = case(
            [
                # Both min and max exist
                (and_(Game.playtime_min.isnot(None), Game.playtime_max.isnot(None)), 
                 (Game.playtime_min + Game.playtime_max) / 2),
                # Only min exists, use min
                (Game.playtime_min.isnot(None), Game.playtime_min),
                # Only max exists, use max
                (Game.playtime_max.isnot(None), Game.playtime_max),
            ],
            else_=999999  # Put games with no time data at the end
        )
        query = query.order_by(avg_time.asc())
    elif sort == "time_desc":
        # Sort by average playing time (min + max) / 2, descending
        avg_time = case(
            [
                # Both min and max exist
                (and_(Game.playtime_min.isnot(None), Game.playtime_max.isnot(None)), 
                 (Game.playtime_min + Game.playtime_max) / 2),
                # Only min exists, use min
                (Game.playtime_min.isnot(None), Game.playtime_min),
                # Only max exists, use max
                (Game.playtime_max.isnot(None), Game.playtime_max),
            ],
            else_=0  # Put games with no time data at the end
        )
        query = query.order_by(avg_time.desc())
    else:  # Default to title_asc
        query = query.order_by(Game.title.asc())
    
    # Apply category filtering at database level for better performance
    if category and category != "all":
        if category == "uncategorized":
            query = query.where(Game.mana_meeple_category.is_(None))
        elif category in CATEGORY_KEYS:
            query = query.where(Game.mana_meeple_category == category)
    
    # Get total count for pagination
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar()
    
    # Apply pagination at database level
    page_games = db.execute(
        query.offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    
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
        raise GameNotFoundError("Game not found")
    
    return _game_to_dict(request, game)

@app.get("/api/public/category-counts")
async def get_category_counts(db: Session = Depends(get_db)):
    """Get counts for each category"""
    # Only select the columns we need to avoid missing column errors
    games = db.execute(select(Game.id, Game.mana_meeple_category)).all()
    return _calculate_category_counts(games)

@app.get("/api/public/games/by-designer/{designer_name}")
async def get_games_by_designer(designer_name: str, db: Session = Depends(get_db)):
    """Get games by a specific designer"""
    try:
        designer_filter = f"%{designer_name}%"
        query = select(Game)
        if hasattr(Game, 'designers'):
            query = query.where(Game.designers.ilike(designer_filter))
        
        games = db.execute(query).scalars().all()
        return {"designer": designer_name, "games": [_game_to_dict(request, game) for game in games]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch games by designer: {str(e)}")

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
        
        # Create game with basic fields
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
        
        # Add enhanced fields if they exist in the model
        if hasattr(game, 'description'):
            game.description = game_data.get("description")
        if hasattr(game, 'designers'):
            game.designers = json.dumps(game_data.get("designers", []))
        if hasattr(game, 'publishers'):
            game.publishers = json.dumps(game_data.get("publishers", []))
        if hasattr(game, 'mechanics'):
            game.mechanics = json.dumps(game_data.get("mechanics", []))
        
        # Auto-categorize if no category provided
        if not game.mana_meeple_category:
            categories = _parse_categories(game.categories)
            game.mana_meeple_category = _categorize_game(categories)
        
        db.add(game)
        db.commit()
        db.refresh(game)
        
        # Download thumbnail in background if provided
        thumbnail_url = game_data.get("image") or game_data.get("thumbnail_url") or game_data.get("image_url")
        if thumbnail_url:
            background_tasks.add_task(_download_and_update_thumbnail, game.id, thumbnail_url)
        
        logger.info(f"Created game: {game.title} (ID: {game.id})")
        return {"id": game.id, "title": game.title}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create game: {e}")
        raise HTTPException(status_code=500, detail="Failed to create game")

@app.post("/api/admin/import/bgg")
async def import_from_bgg(
    request: Request,
    bgg_id: int = Query(..., description="BGG game ID"),
    force: bool = Query(False, description="Force reimport if exists"),
    x_admin_token: Optional[str] = Header(None),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """Import game from BoardGameGeek (admin only)"""
    _require_admin_token(x_admin_token, _get_client_ip(request))
    
    # Validate BGG ID
    if bgg_id <= 0 or bgg_id > 999999:
        raise ValidationError("BGG ID must be between 1 and 999999")
    
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
            
            # Update enhanced fields if they exist
            if hasattr(existing, 'description'):
                existing.description = bgg_data.get("description")
            if hasattr(existing, 'designers'):
                existing.designers = json.dumps(bgg_data.get("designers", []))
            if hasattr(existing, 'publishers'):
                existing.publishers = json.dumps(bgg_data.get("publishers", []))
            if hasattr(existing, 'mechanics'):
                existing.mechanics = json.dumps(bgg_data.get("mechanics", []))
            if hasattr(existing, 'artists'):
                existing.artists = json.dumps(bgg_data.get("artists", []))
            if hasattr(existing, 'average_rating'):
                existing.average_rating = bgg_data.get("average_rating")
            if hasattr(existing, 'complexity'):
                existing.complexity = bgg_data.get("complexity")
            if hasattr(existing, 'bgg_rank'):
                existing.bgg_rank = bgg_data.get("bgg_rank")
            if hasattr(existing, 'users_rated'):
                existing.users_rated = bgg_data.get("users_rated")
            if hasattr(existing, 'min_age'):
                existing.min_age = bgg_data.get("min_age")
            if hasattr(existing, 'is_cooperative'):
                existing.is_cooperative = bgg_data.get("is_cooperative")
            if hasattr(existing, 'game_type'):
                existing.game_type = bgg_data.get("game_type")

            # Re-categorize
            categories = _parse_categories(categories_str)
            existing.mana_meeple_category = _categorize_game(categories)
            
            db.add(existing)
            game = existing
        else:
            # Create new with enhanced data
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
            
            # Add enhanced fields if they exist in the model
            if hasattr(game, 'description'):
                game.description = bgg_data.get("description")
            if hasattr(game, 'designers'):
                game.designers = json.dumps(bgg_data.get("designers", []))
            if hasattr(game, 'publishers'):
                game.publishers = json.dumps(bgg_data.get("publishers", []))
            if hasattr(game, 'mechanics'):
                game.mechanics = json.dumps(bgg_data.get("mechanics", []))
            if hasattr(game, 'artists'):
                game.artists = json.dumps(bgg_data.get("artists", []))
            if hasattr(game, 'average_rating'):
                game.average_rating = bgg_data.get("average_rating")
            if hasattr(game, 'complexity'):
                game.complexity = bgg_data.get("complexity")
            if hasattr(game, 'bgg_rank'):
                game.bgg_rank = bgg_data.get("bgg_rank")
            if hasattr(game, 'users_rated'):
                game.users_rated = bgg_data.get("users_rated")
            if hasattr(game, 'min_age'):
                game.min_age = bgg_data.get("min_age")
            if hasattr(game, 'is_cooperative'):
                game.is_cooperative = bgg_data.get("is_cooperative")
            if hasattr(game, 'game_type'):
                game.game_type = bgg_data.get("game_type")
            if hasattr(game, 'image'):
                game.image = bgg_data.get("image")  # Store the full-size image URL
            if hasattr(game, 'thumbnail_url'):
                game.thumbnail_url = bgg_data.get("thumbnail")  # Store the thumbnail URL separately
            
            db.add(game)

        db.commit()
        db.refresh(game)
        
        # Download thumbnail in background
        thumbnail_url = bgg_data.get("image") or bgg_data.get("thumbnail")  # Prioritize image over thumbnail
        if thumbnail_url and background_tasks:
            background_tasks.add_task(_download_and_update_thumbnail, game.id, thumbnail_url)
        
        logger.info(f"Imported from BGG: {game.title} (BGG ID: {bgg_id})")
        return {"id": game.id, "title": game.title, "cached": bool(existing)}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to import BGG game {bgg_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to import game: {str(e)}")

@app.post("/api/admin/bulk-import-csv")
async def bulk_import_csv(
    csv_data: dict,
    background_tasks: BackgroundTasks,
    request: Request,
    x_admin_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Bulk import games from CSV data (admin only)"""
    _require_admin_token(x_admin_token, _get_client_ip(request))
    
    try:
        csv_text = csv_data.get("csv_data", "")
        if not csv_text.strip():
            raise HTTPException(status_code=400, detail="No CSV data provided")
        
        lines = [line.strip() for line in csv_text.strip().split('\n') if line.strip()]
        if not lines:
            raise HTTPException(status_code=400, detail="No valid lines in CSV")
        
        added = []
        skipped = []
        errors = []
        
        for line_num, line in enumerate(lines, 1):
            try:
                # Expected format: bgg_id,title (title is optional)
                parts = [p.strip() for p in line.split(',')]
                if len(parts) < 1:
                    errors.append(f"Line {line_num}: No BGG ID provided")
                    continue
                
                # Try to parse BGG ID
                try:
                    bgg_id = int(parts[0])
                except ValueError:
                    errors.append(f"Line {line_num}: Invalid BGG ID '{parts[0]}'")
                    continue
                
                # Check if already exists
                existing = db.execute(select(Game).where(Game.bgg_id == bgg_id)).scalar_one_or_none()
                if existing:
                    skipped.append(f"BGG ID {bgg_id}: Already exists as '{existing.title}'")
                    continue
                
                # Import from BGG
                try:
                    bgg_data = await fetch_bgg_thing(bgg_id)
                    categories_str = ", ".join(bgg_data.get("categories", []))
                    
                    # Create new game
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
                    
                    # Add enhanced fields if they exist in the model
                    if hasattr(game, 'description'):
                        game.description = bgg_data.get("description")
                    if hasattr(game, 'designers'):
                        game.designers = json.dumps(bgg_data.get("designers", []))
                    if hasattr(game, 'publishers'):
                        game.publishers = json.dumps(bgg_data.get("publishers", []))
                    if hasattr(game, 'mechanics'):
                        game.mechanics = json.dumps(bgg_data.get("mechanics", []))
                    if hasattr(game, 'artists'):
                        game.artists = json.dumps(bgg_data.get("artists", []))
                    if hasattr(game, 'average_rating'):
                        game.average_rating = bgg_data.get("average_rating")
                    if hasattr(game, 'complexity'):
                        game.complexity = bgg_data.get("complexity")
                    if hasattr(game, 'bgg_rank'):
                        game.bgg_rank = bgg_data.get("bgg_rank")
                    if hasattr(game, 'users_rated'):
                        game.users_rated = bgg_data.get("users_rated")
                    if hasattr(game, 'min_age'):
                        game.min_age = bgg_data.get("min_age")
                    if hasattr(game, 'is_cooperative'):
                        game.is_cooperative = bgg_data.get("is_cooperative")
                    if hasattr(game, 'game_type'):
                        game.game_type = bgg_data.get("game_type")
                    if hasattr(game, 'image'):
                        game.image = bgg_data.get("image")  # Store the full-size image URL
                    if hasattr(game, 'thumbnail_url'):
                        game.thumbnail_url = bgg_data.get("thumbnail")  # Store the thumbnail URL separately
                    
                    db.add(game)
                    db.commit()
                    db.refresh(game)
                    
                    added.append(f"BGG ID {bgg_id}: {game.title}")
                    
                    # Download thumbnail in background
                    thumbnail_url = bgg_data.get("image") or bgg_data.get("thumbnail")  # Prioritize image over thumbnail
                    if thumbnail_url and background_tasks:
                        background_tasks.add_task(_download_and_update_thumbnail, game.id, thumbnail_url)
                    
                except Exception as e:
                    db.rollback()
                    errors.append(f"Line {line_num}: Failed to import BGG ID {bgg_id} - {str(e)}")
                    
            except Exception as e:
                errors.append(f"Line {line_num}: {str(e)}")
        
        return {
            "message": f"Processed {len(lines)} lines",
            "added": added,
            "skipped": skipped,
            "errors": errors
        }
        
    except Exception as e:
        logger.error(f"Bulk import failed: {e}")
        raise HTTPException(status_code=500, detail=f"Bulk import failed: {str(e)}")


@app.post("/api/admin/bulk-categorize-csv")
async def bulk_categorize_csv(
    csv_data: dict,
    request: Request,
    x_admin_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Bulk categorize existing games from CSV data (admin only)"""
    _require_admin_token(x_admin_token, _get_client_ip(request))
    
    try:
        csv_text = csv_data.get("csv_data", "")
        if not csv_text.strip():
            raise HTTPException(status_code=400, detail="No CSV data provided")
        
        lines = [line.strip() for line in csv_text.strip().split('\n') if line.strip()]
        if not lines:
            raise HTTPException(status_code=400, detail="No valid lines in CSV")
        
        updated = []
        not_found = []
        errors = []
        
        for line_num, line in enumerate(lines, 1):
            try:
                # Expected format: bgg_id,category[,title]
                parts = [p.strip() for p in line.split(',')]
                if len(parts) < 2:
                    errors.append(f"Line {line_num}: Must have at least bgg_id,category")
                    continue
                
                # Parse BGG ID
                try:
                    bgg_id = int(parts[0])
                except ValueError:
                    errors.append(f"Line {line_num}: Invalid BGG ID '{parts[0]}'")
                    continue
                
                category = parts[1].strip()
                
                # Validate category (accept both keys and labels)
                category_key = None
                if category in CATEGORY_KEYS:
                    category_key = category
                else:
                    # Try to find by label
                    from constants.categories import CATEGORY_LABELS
                    for key, label in CATEGORY_LABELS.items():
                        if label.lower() == category.lower():
                            category_key = key
                            break
                
                if not category_key:
                    errors.append(f"Line {line_num}: Invalid category '{category}'. Use: {', '.join(CATEGORY_KEYS)}")
                    continue
                
                # Find and update game
                game = db.execute(select(Game).where(Game.bgg_id == bgg_id)).scalar_one_or_none()
                if not game:
                    not_found.append(f"BGG ID {bgg_id}: Game not found")
                    continue
                
                old_category = game.mana_meeple_category
                game.mana_meeple_category = category_key
                db.add(game)
                
                updated.append(f"BGG ID {bgg_id} ({game.title}): {old_category or 'None'} → {category_key}")
                
            except Exception as e:
                errors.append(f"Line {line_num}: {str(e)}")
        
        db.commit()
        
        return {
            "message": f"Processed {len(lines)} lines",
            "updated": updated,
            "not_found": not_found,
            "errors": errors
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Bulk categorize failed: {e}")
        raise HTTPException(status_code=500, detail=f"Bulk categorize failed: {str(e)}")


@app.post("/api/admin/reimport-all-games")
async def reimport_all_games(
    background_tasks: BackgroundTasks,
    request: Request,
    x_admin_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Re-import all existing games to get enhanced BGG data"""
    _require_admin_token(x_admin_token, _get_client_ip(request))
    
    games = db.execute(select(Game).where(Game.bgg_id.isnot(None))).scalars().all()
    
    for game in games:
        background_tasks.add_task(_reimport_single_game, game.id, game.bgg_id)
    
    return {"message": f"Started re-importing {len(games)} games with enhanced data"}

@app.post("/api/admin/bulk-update-nz-designers")
async def bulk_update_nz_designers(
    csv_data: dict,
    request: Request,
    x_admin_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Bulk update NZ designer status from CSV (admin only)"""
    _require_admin_token(x_admin_token, _get_client_ip(request))
    
    try:
        csv_text = csv_data.get("csv_data", "")
        if not csv_text.strip():
            raise HTTPException(status_code=400, detail="No CSV data provided")
        
        lines = [line.strip() for line in csv_text.strip().split('\n') if line.strip()]
        updated = []
        not_found = []
        errors = []
        
        for line_num, line in enumerate(lines, 1):
            try:
                # Expected format: bgg_id,true/false or game_title,true/false
                parts = [p.strip() for p in line.split(',')]
                if len(parts) != 2:
                    errors.append(f"Line {line_num}: Must have format 'identifier,true/false'")
                    continue
                
                identifier = parts[0]
                nz_status = parts[1].lower() in ['true', '1', 'yes', 'y']
                
                # Try to find by BGG ID first, then by title
                game = None
                try:
                    bgg_id = int(identifier)
                    game = db.execute(select(Game).where(Game.bgg_id == bgg_id)).scalar_one_or_none()
                except ValueError:
                    # Not a number, try by title
                    game = db.execute(select(Game).where(Game.title.ilike(f"%{identifier}%"))).scalar_one_or_none()
                
                if not game:
                    not_found.append(f"'{identifier}': Game not found")
                    continue
                
                old_status = game.nz_designer
                game.nz_designer = nz_status
                db.add(game)
                
                updated.append(f"{game.title}: {old_status} → {nz_status}")
                
            except Exception as e:
                errors.append(f"Line {line_num}: {str(e)}")
        
        db.commit()
        
        return {
            "message": f"Processed {len(lines)} lines",
            "updated": updated,
            "not_found": not_found,
            "errors": errors
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Bulk NZ designer update failed: {e}")
        raise HTTPException(status_code=500, detail=f"Bulk update failed: {str(e)}")


@app.get("/api/admin/games")
async def get_admin_games(
    request: Request,
    x_admin_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Get all games for admin interface"""
    _require_admin_token(x_admin_token, _get_client_ip(request))
    
    games = db.execute(select(Game)).scalars().all()
    return [_game_to_dict(None, game) for game in games]


@app.get("/api/admin/games/{game_id}")
async def get_admin_game(
    request: Request,
    game_id: int = Path(..., description="Game ID"),
    x_admin_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Get single game for admin interface"""
    _require_admin_token(x_admin_token, _get_client_ip(request))
    
    game = db.execute(select(Game).where(Game.id == game_id)).scalar_one_or_none()
    if not game:
        raise GameNotFoundError(f"Game {game_id} not found")
    
    return _game_to_dict(None, game)


@app.put("/api/admin/games/{game_id}")
async def update_admin_game(
    game_data: Dict[str, Any],
    request: Request,
    game_id: int = Path(..., description="Game ID"),
    x_admin_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Update game (admin only)"""
    _require_admin_token(x_admin_token, _get_client_ip(request))
    
    game = db.execute(select(Game).where(Game.id == game_id)).scalar_one_or_none()
    if not game:
        raise GameNotFoundError(f"Game {game_id} not found")
    
    try:
        # Update allowed fields
        if "title" in game_data:
            game.title = game_data["title"]
        if "year" in game_data:
            game.year = game_data["year"]
        if "description" in game_data and hasattr(game, 'description'):
            game.description = game_data["description"]
        if "mana_meeple_category" in game_data:
            game.mana_meeple_category = game_data["mana_meeple_category"]
        if "players_min" in game_data:
            game.players_min = game_data["players_min"]
        if "players_max" in game_data:
            game.players_max = game_data["players_max"]
        if "playtime_min" in game_data:
            game.playtime_min = game_data["playtime_min"]
        if "playtime_max" in game_data:
            game.playtime_max = game_data["playtime_max"]
        if "min_age" in game_data and hasattr(game, 'min_age'):
            game.min_age = game_data["min_age"]
        if "nz_designer" in game_data:
            game.nz_designer = game_data["nz_designer"]
        
        db.commit()
        db.refresh(game)
        
        logger.info(f"Updated game: {game.title} (ID: {game.id})", extra={'game_id': game.id})
        return _game_to_dict(None, game)
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update game {game_id}: {e}", extra={'game_id': game_id})
        raise HTTPException(status_code=500, detail="Failed to update game")


@app.post("/api/admin/games/{game_id}/update")
async def update_admin_game_post(
    game_data: Dict[str, Any],
    request: Request,
    game_id: int = Path(..., description="Game ID"),
    x_admin_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Update game via POST (admin only) - alternative to PUT for proxy compatibility"""
    _require_admin_token(x_admin_token, _get_client_ip(request))

    game = db.execute(select(Game).where(Game.id == game_id)).scalar_one_or_none()
    if not game:
        raise GameNotFoundError(f"Game {game_id} not found")

    try:
        # Update allowed fields
        if "title" in game_data:
            game.title = game_data["title"]
        if "year" in game_data:
            game.year = game_data["year"]
        if "description" in game_data and hasattr(game, 'description'):
            game.description = game_data["description"]
        if "mana_meeple_category" in game_data:
            game.mana_meeple_category = game_data["mana_meeple_category"]
        if "players_min" in game_data:
            game.players_min = game_data["players_min"]
        if "players_max" in game_data:
            game.players_max = game_data["players_max"]
        if "playtime_min" in game_data:
            game.playtime_min = game_data["playtime_min"]
        if "playtime_max" in game_data:
            game.playtime_max = game_data["playtime_max"]
        if "min_age" in game_data and hasattr(game, 'min_age'):
            game.min_age = game_data["min_age"]

        db.commit()
        db.refresh(game)

        logger.info(f"Updated game via POST: {game.title} (ID: {game.id})", extra={'game_id': game.id})
        return _game_to_dict(None, game)

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update game {game_id} via POST: {e}", extra={'game_id': game_id})
        raise HTTPException(status_code=500, detail="Failed to update game")


@app.delete("/api/admin/games/{game_id}")
async def delete_admin_game(
    request: Request,
    game_id: int = Path(..., description="Game ID"),
    x_admin_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Delete game (admin only)"""
    _require_admin_token(x_admin_token, _get_client_ip(request))

    game = db.execute(select(Game).where(Game.id == game_id)).scalar_one_or_none()
    if not game:
        raise GameNotFoundError(f"Game {game_id} not found")

    try:
        game_title = game.title
        db.delete(game)
        db.commit()

        logger.info(f"Deleted game: {game_title} (ID: {game_id})", extra={'game_id': game_id})
        return {"message": f"Game '{game_title}' deleted successfully"}

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete game {game_id}: {e}", extra={'game_id': game_id})
        raise HTTPException(status_code=500, detail="Failed to delete game")

def run_migrations():
    """Run database migrations to ensure schema is up to date."""
    try:
        with engine.connect() as conn:
            # Check existing columns
            result = conn.execute(text("PRAGMA table_info(games)"))
            columns = [row[1] for row in result]
            
            # Add image column if missing
            if 'image' not in columns:
                logger.info("Adding missing 'image' column to games table...")
                conn.execute(text("ALTER TABLE games ADD COLUMN image VARCHAR(512)"))
                conn.commit()
                logger.info("Successfully added 'image' column to games table")
            
            # Add nz_designer column if missing
            if 'nz_designer' not in columns:
                logger.info("Adding missing 'nz_designer' column to games table...")
                conn.execute(text("ALTER TABLE games ADD COLUMN nz_designer BOOLEAN DEFAULT FALSE"))
                conn.commit()
                logger.info("Successfully added 'nz_designer' column to games table")

            # Add game_type column if missing
            if 'game_type' not in columns:
                logger.info("Adding missing 'game_type' column to games table...")
                conn.execute(text("ALTER TABLE games ADD COLUMN game_type VARCHAR(255)"))
                conn.commit()
                logger.info("Successfully added 'game_type' column to games table")

            logger.info("Database schema is up to date")
                
    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        raise

# ------------------------------------------------------------------------------
# Startup
# ------------------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    """Initialize database and create thumbs directory"""
    logger.info("Starting Mana & Meeples API...")
    init_db()
    run_migrations()
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
