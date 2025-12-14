# main.py
"""
Main application entry point for Mana & Meeples Board Game Library API.
Handles app initialization, middleware setup, and router registration.
"""
import os
import json
import logging
from typing import Dict, Any
from datetime import datetime
from collections import defaultdict

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.types import ASGIApp, Receive, Scope, Send
from shared.rate_limiting import (
    get_limiter,
    get_rate_limit_exception_handler,
    get_rate_limit_exception,
    admin_attempt_tracker,
    admin_sessions,
)

from database import SessionLocal, db_ping, run_migrations
from models import Game
from bgg_service import fetch_bgg_thing
from exceptions import (
    GameServiceError,
    GameNotFoundError,
    BGGServiceError,
    ValidationError,
    DatabaseError,
)
from config import HTTP_TIMEOUT, CORS_ORIGINS
from middleware.logging import RequestLoggingMiddleware

# ------------------------------------------------------------------------------
# Sentry initialization
# ------------------------------------------------------------------------------

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

# Initialize Sentry for error tracking and performance monitoring
# Only initializes if SENTRY_DSN is configured
if os.getenv("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        environment=os.getenv("ENVIRONMENT", "production"),
        # Performance monitoring
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        # Set traces_sample_rate to 1.0 to capture 100% of transactions for performance monitoring.
        # Adjust this value in production to reduce volume
        traces_sample_rate=(
            0.1 if os.getenv("ENVIRONMENT") == "production" else 1.0
        ),
        # Filter out development errors
        before_send=lambda event, hint: (
            None if os.getenv("ENVIRONMENT") == "development" else event
        ),
    )

# ------------------------------------------------------------------------------
# Logging setup
# ------------------------------------------------------------------------------


class StructuredFormatter(logging.Formatter):
    """Enhanced logging with structured JSON format for production"""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields if they exist
        for field in ["user_id", "request_id", "bgg_id", "game_id"]:
            if hasattr(record, field):
                log_entry[field] = getattr(record, field)

        return json.dumps(log_entry)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

# Use structured logging in production
if os.getenv("ENVIRONMENT") == "production":
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    logging.getLogger().handlers = [handler]

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------

# Thumbnail storage directory (ephemeral on Render free tier)
THUMBS_DIR = os.getenv("THUMBS_DIR", "/tmp/thumbs")

# Single shared HTTP client
httpx_client = httpx.AsyncClient(follow_redirects=True, timeout=HTTP_TIMEOUT)

# Session storage and rate limiting moved to shared/rate_limiting.py

# ------------------------------------------------------------------------------
# Background task functions
# TODO: Move to services/ module
# ------------------------------------------------------------------------------


async def _download_thumbnail(url: str, filename_prefix: str) -> str:
    """Download thumbnail from URL and save to local storage"""
    try:
        response = await httpx_client.get(url)
        response.raise_for_status()

        # Generate filename
        ext = url.split(".")[-1].split("?")[0]  # Handle query params
        if ext not in ["jpg", "jpeg", "png", "webp"]:
            ext = "jpg"
        filename = f"{filename_prefix}.{ext}"
        filepath = os.path.join(THUMBS_DIR, filename)

        # Save file
        with open(filepath, "wb") as f:
            f.write(response.content)

        logger.info(f"Downloaded thumbnail: {filename}")
        return filename

    except Exception as e:
        logger.error(f"Failed to download thumbnail from {url}: {e}")
        return None


async def _download_and_update_thumbnail(game_id: int, thumbnail_url: str):
    """Background task to download and update game thumbnail"""
    try:
        db = SessionLocal()
        game = db.get(Game, game_id)
        if not game:
            return

        filename = await _download_thumbnail(
            thumbnail_url, f"{game_id}-{game.title}"
        )
        if filename:
            if hasattr(game, "thumbnail_file"):
                game.thumbnail_file = filename
            if hasattr(game, "thumbnail_url"):
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

        # Fetch enhanced data from BGG (including sleeve data)
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
        for field in [
            "description",
            "designers",
            "publishers",
            "mechanics",
            "artists",
            "average_rating",
            "complexity",
            "bgg_rank",
            "users_rated",
            "min_age",
            "is_cooperative",
            "game_type",
            "image",
            "thumbnail_url",
        ]:
            if hasattr(game, field):
                setattr(game, field, bgg_data.get(field))

        db.add(game)
        db.commit()

        # Save sleeve data if available
        from models import Sleeve
        sleeve_data = bgg_data.get('sleeve_data')
        if sleeve_data:
            # Update has_sleeves status
            game.has_sleeves = sleeve_data.get('status', 'not_found')

            # Delete existing sleeve records for this game
            db.query(Sleeve).filter(Sleeve.game_id == game.id).delete()

            # Save new sleeve records if found
            if sleeve_data.get('status') == 'found' and sleeve_data.get('card_types'):
                notes = sleeve_data.get('notes')
                for card_type in sleeve_data['card_types']:
                    # Ensure quantity is never None (fallback to 0)
                    quantity = card_type.get('quantity') or 0
                    sleeve = Sleeve(
                        game_id=game.id,
                        card_name=card_type.get('name'),
                        width_mm=card_type['width_mm'],
                        height_mm=card_type['height_mm'],
                        quantity=quantity,
                        notes=notes
                    )
                    db.add(sleeve)

                db.commit()
                logger.info(f"Saved {len(sleeve_data['card_types'])} sleeve types for {game.title}")

        logger.info(f"Re-imported game {game_id}: {game.title}")

    except Exception as e:
        logger.error(f"Failed to reimport game {game_id}: {e}")
    finally:
        db.close()


# ------------------------------------------------------------------------------
# FastAPI app initialization
# ------------------------------------------------------------------------------

app = FastAPI(
    title="Mana & Meeples Board Game Library API",
    version="2.0.0",
    description="""
    Public board game catalogue and admin management API for Mana & Meeples café.

    ## Features

    * 🎲 **Public Game Browsing**: Search and filter 400+ board games
    * 🔍 **Advanced Search**: Filter by category, designer, players, complexity
    * 🇳🇿 **NZ Designer Spotlight**: Highlight New Zealand game designers
    * 📊 **BoardGameGeek Integration**: Automatic metadata sync from BGG
    * 🖼️ **Image Optimization**: Cached and optimized game images
    * 🔐 **Admin Interface**: Secure game management and bulk operations

    ## Public Endpoints

    * `GET /api/public/games` - Browse games with filters and pagination
    * `GET /api/public/games/{id}` - Get detailed game information
    * `GET /api/public/category-counts` - Category statistics

    ## Admin Endpoints

    Require `X-Admin-Token` header for authentication.

    * `POST /api/admin/login` - Create admin session
    * `POST /api/admin/import/bgg` - Import game from BoardGameGeek
    * `POST /api/admin/bulk-import-csv` - Bulk import games from CSV

    ## Rate Limits

    * Public endpoints: 100 requests/minute
    * Admin endpoints: Limited by authentication
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "public",
            "description": "Public game browsing endpoints (no authentication required)",
        },
        {
            "name": "admin",
            "description": "Admin game management (requires X-Admin-Token header)",
        },
        {
            "name": "bulk",
            "description": "Bulk operations for managing multiple games",
        },
        {
            "name": "health",
            "description": "Health check and monitoring endpoints",
        },
        {"name": "debug", "description": "Debug and diagnostic endpoints"},
    ],
)

# ------------------------------------------------------------------------------
# Rate limiting
# ------------------------------------------------------------------------------

limiter = get_limiter()
app.state.limiter = limiter
app.add_exception_handler(
    get_rate_limit_exception(), get_rate_limit_exception_handler()
)

# ------------------------------------------------------------------------------
# Exception handlers
# ------------------------------------------------------------------------------


@app.exception_handler(GameNotFoundError)
async def game_not_found_handler(request: Request, exc: GameNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(BGGServiceError)
async def bgg_service_error_handler(request: Request, exc: BGGServiceError):
    return JSONResponse(
        status_code=503, content={"detail": f"BGG service error: {str(exc)}"}
    )


@app.exception_handler(DatabaseError)
async def database_error_handler(request: Request, exc: DatabaseError):
    return JSONResponse(
        status_code=500, content={"detail": "Database operation failed"}
    )


# ------------------------------------------------------------------------------
# Middleware
# ------------------------------------------------------------------------------


# Cache headers for thumbnail images
class CacheThumbsMiddleware:
    """Add cache headers to thumbnail responses"""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                path = scope.get("path", "")
                if path.startswith("/thumbs/"):
                    headers = message.setdefault("headers", [])
                    headers.append(
                        (
                            b"cache-control",
                            b"public, max-age=31536000, immutable",
                        )
                    )
            await send(message)

        await self.app(scope, receive, send_wrapper)


# Add middleware in reverse order (last added = first executed)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CacheThumbsMiddleware)

# CORS configuration
cors_origins = CORS_ORIGINS or [
    "https://manaandmeeples.co.nz",
    "https://www.manaandmeeples.co.nz",
    "https://library.manaandmeeples.co.nz",
    "https://mana-meeples-library-web.onrender.com",
]

# Always add localhost for development
if "http://localhost:3000" not in cors_origins:
    cors_origins = cors_origins + [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

logger.info(f"CORS origins configured: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------------------
# Static files
# ------------------------------------------------------------------------------

os.makedirs(THUMBS_DIR, exist_ok=True)
app.mount("/thumbs", StaticFiles(directory=THUMBS_DIR), name="thumbs")

# ------------------------------------------------------------------------------
# Router registration
# ------------------------------------------------------------------------------

from api.routers.public import router as public_router
from api.routers.admin import router as admin_router
from api.routers.bulk import router as bulk_router
from api.routers.health import health_router, debug_router
from api.routers.buy_list import router as buy_list_router
from api.routers.sleeves import router as sleeves_router

# Register all routers
app.include_router(public_router)
app.include_router(admin_router)
app.include_router(bulk_router)
app.include_router(buy_list_router)
app.include_router(sleeves_router)
app.include_router(health_router)
app.include_router(debug_router)

# ------------------------------------------------------------------------------
# Startup and shutdown events
# ------------------------------------------------------------------------------


@app.on_event("startup")
async def startup_event():
    """Initialize database and create thumbs directory"""
    logger.info("Starting Mana & Meeples API...")
    logger.info("Verifying database connection...")

    # Verify database connection
    if not db_ping():
        logger.error("Database connection failed!")
        raise RuntimeError("Cannot connect to PostgreSQL database")

    logger.info("Database connection verified")

    # Run migrations to update schema
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
# Root endpoint
# ------------------------------------------------------------------------------


@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "message": "Mana & Meeples API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }


# ------------------------------------------------------------------------------
# Development server
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
