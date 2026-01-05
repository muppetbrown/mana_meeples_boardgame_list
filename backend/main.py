# main.py
"""
Main application entry point for Mana & Meeples Board Game Library API.
Handles app initialization, middleware setup, and router registration.
"""
import os
import json
import logging
import asyncio
import time
from typing import Dict, Any
from datetime import datetime, timezone
from collections import defaultdict
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import delete
from starlette.types import ASGIApp, Receive, Scope, Send
from shared.rate_limiting import (
    get_limiter,
    get_rate_limit_exception_handler,
    get_rate_limit_exception,
    admin_attempt_tracker,
    admin_sessions,
)

from database import SessionLocal, db_ping
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
from middleware.security import SecurityHeadersMiddleware
from middleware.cache import APICacheControlMiddleware

# ------------------------------------------------------------------------------
# Sentry initialization (Sprint 5: Enhanced with custom filtering)
# ------------------------------------------------------------------------------

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration


def before_send_sentry(event, hint):
    """
    Custom event filtering and enrichment for Sentry.
    Sprint 5: Error Handling & Monitoring

    Args:
        event: Sentry event dictionary
        hint: Additional context about the event

    Returns:
        Modified event or None to drop event
    """
    # Filter out development errors
    if os.getenv("ENVIRONMENT") == "development":
        return None

    # Filter out known non-issues
    if event.get("logger") == "uvicorn.access":
        return None

    # Filter out health check errors (noise)
    if "request" in hint:
        request = hint["request"]
        if hasattr(request, "url") and "/health" in str(request.url):
            return None

    # Enrich with custom context
    if "request" in hint:
        request = hint["request"]
        # Tag user type (admin vs public)
        if hasattr(request, "url"):
            url_path = str(request.url.path) if hasattr(request.url, "path") else str(request.url)
            event.setdefault("tags", {})
            event["tags"]["user_type"] = "admin" if "/admin/" in url_path else "public"
            event["tags"]["endpoint_type"] = (
                "api" if "/api/" in url_path else "static"
            )

    # Add environment info
    event.setdefault("tags", {})
    event["tags"]["python_version"] = os.getenv("PYTHON_VERSION", "unknown")

    # Add custom context for BGG-related errors
    if "exception" in event:
        for exc in event["exception"].get("values", []):
            if "BGG" in exc.get("type", ""):
                event.setdefault("contexts", {})
                event["contexts"]["bgg"] = {
                    "circuit_breaker_state": "available",  # Will be updated dynamically
                }

    return event


# Initialize Sentry for error tracking and performance monitoring
# Only initializes if SENTRY_DSN is configured
if os.getenv("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        environment=os.getenv("ENVIRONMENT", "production"),
        release=os.getenv("GIT_COMMIT_SHA", "unknown"),  # Track releases
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
        # Enable profiling for performance insights
        profiles_sample_rate=0.1,
        # Custom event filtering and enrichment
        before_send=before_send_sentry,
        # Attach stack traces to all messages
        attach_stacktrace=True,
        # Increase breadcrumbs for better debugging
        max_breadcrumbs=50,
        # Debug mode (off in production)
        debug=False,
    )

# ------------------------------------------------------------------------------
# Logging setup
# ------------------------------------------------------------------------------


class StructuredFormatter(logging.Formatter):
    """Enhanced logging with structured JSON format for production"""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
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
# Background task functions moved to services/background_tasks.py

# ------------------------------------------------------------------------------
# Lifespan event handler
# ------------------------------------------------------------------------------


def warm_cache():
    """
    Warm up cache with popular queries on startup.
    Sprint 12: Performance Optimization - Cache Warming

    Pre-loads frequently accessed data to eliminate cold start delays:
    - Category counts (used in filter buttons)
    - First page of games (default landing page)
    - Popular category filters
    """
    from database import SessionLocal
    from services import GameService

    logger.info("Starting cache warming...")
    start_time = time.time()

    try:
        db = SessionLocal()
        service = GameService(db)

        # 1. Warm category counts (most common query, shown on every page load)
        try:
            counts = service.get_category_counts()
            logger.info(f"✓ Warmed category counts: {len(counts)} categories")
        except Exception as e:
            logger.warning(f"Failed to warm category counts: {e}")

        # 2. Warm first page of games (default landing page query)
        # This uses the same code path as the public API endpoint
        try:
            games, total = service.get_filtered_games(
                search=None,
                category=None,
                designer=None,
                nz_designer=None,
                players=None,
                complexity_min=None,
                complexity_max=None,
                recently_added_days=None,
                sort="title_asc",
                page=1,
                page_size=24  # Default page size
            )
            logger.info(f"✓ Warmed first page: {len(games)}/{total} games")
        except Exception as e:
            logger.warning(f"Failed to warm first page: {e}")

        # 3. Warm popular category filters (each category's first page)
        from utils.helpers import CATEGORY_KEYS
        for category in CATEGORY_KEYS[:3]:  # Warm top 3 categories only
            try:
                games, total = service.get_filtered_games(
                    search=None,
                    category=category,
                    designer=None,
                    nz_designer=None,
                    players=None,
                    complexity_min=None,
                    complexity_max=None,
                    recently_added_days=None,
                    sort="title_asc",
                    page=1,
                    page_size=24
                )
                logger.info(f"✓ Warmed category '{category}': {len(games)}/{total} games")
            except Exception as e:
                logger.warning(f"Failed to warm category '{category}': {e}")

        db.close()

        elapsed = time.time() - start_time
        logger.info(f"Cache warming complete in {elapsed:.2f}s")

    except Exception as e:
        logger.error(f"Cache warming failed: {e}")
        # Don't raise - allow app to start even if cache warming fails


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Replaces deprecated @app.on_event() decorators.
    """
    # Startup
    logger.info("Starting Mana & Meeples API...")
    logger.info("Verifying database connection...")

    # Verify database connection
    if not db_ping():
        logger.error("Database connection failed!")
        raise RuntimeError("Cannot connect to PostgreSQL database")

    logger.info("Database connection verified")

    # Database migrations are now handled by Alembic
    # Run `alembic upgrade head` before starting the application
    # See: backend/alembic/ for migration files

    os.makedirs(THUMBS_DIR, exist_ok=True)
    logger.info(f"Thumbnails directory: {THUMBS_DIR}")

    # Sprint 12: Warm cache for popular queries
    warm_cache()

    logger.info("API startup complete")

    yield

    # Shutdown
    logger.info("Shutting down API...")
    await httpx_client.aclose()
    logger.info("API shutdown complete")


# ------------------------------------------------------------------------------
# FastAPI app initialization
# ------------------------------------------------------------------------------

app = FastAPI(
    lifespan=lifespan,
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


# CORS configuration - Must be set up BEFORE adding middleware
# Parse CORS origins from environment or use defaults
cors_origins_from_env = CORS_ORIGINS
cors_origins = cors_origins_from_env if cors_origins_from_env else [
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
        "http://localhost:5173",  # Vite default port
        "http://127.0.0.1:5173",  # Vite default port
    ]

logger.info(f"CORS origins from environment: {cors_origins_from_env}")
logger.info(f"CORS origins configured: {cors_origins}")

# Add middleware in reverse order (last added = first executed)
# IMPORTANT: CORS must be added LAST to execute FIRST and handle preflight requests
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CacheThumbsMiddleware)
app.add_middleware(APICacheControlMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# CORS middleware MUST be added last to wrap all other middleware
# This ensures preflight OPTIONS requests are handled correctly
# NOTE: When allow_credentials=True, we must use explicit headers (not wildcards)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    allow_headers=[
        "content-type",
        "authorization",
        "accept",
        "origin",
        "user-agent",
        "dnt",
        "cache-control",
        "x-requested-with",
        "x-admin-token",
        "accept-language",
        "accept-encoding",
    ],
    expose_headers=[
        "content-length",
        "content-type",
        "x-total-count",
        "access-control-allow-origin",
        "access-control-allow-credentials",
    ],
    max_age=3600,  # Cache preflight requests for 1 hour
)
logger.info("CORS middleware configured and added to application")

# ------------------------------------------------------------------------------
# Static files
# ------------------------------------------------------------------------------

os.makedirs(THUMBS_DIR, exist_ok=True)
app.mount("/thumbs", StaticFiles(directory=THUMBS_DIR), name="thumbs")

# ------------------------------------------------------------------------------
# Router registration with API versioning
# ------------------------------------------------------------------------------

from api.routers.public import router as public_router
from api.routers.admin import router as admin_router
from api.routers.bulk import router as bulk_router
from api.routers.health import health_router, debug_router
from api.routers.buy_list import router as buy_list_router
from api.routers.sleeves import router as sleeves_router
from api.versioning import version_info

# Register API routers (currently using /api prefix without versioning)
# Note: Explicit /api/v1 versioning disabled due to CORS middleware inheritance issues
app.include_router(public_router)
app.include_router(admin_router)
app.include_router(bulk_router)
app.include_router(buy_list_router)
app.include_router(sleeves_router)
app.include_router(health_router)
app.include_router(debug_router)

# ------------------------------------------------------------------------------
# Root endpoint
# ------------------------------------------------------------------------------


@app.get("/")
async def root():
    """
    Root endpoint - API information and version discovery.

    Returns API version information and available endpoints.
    """
    return {
        "message": "Mana & Meeples Board Game Library API",
        "app_version": "2.0.0",
        "endpoints": {
            "documentation": "/docs",
            "health_check": "/api/health",
            "public_games": "/api/public/games",
            "admin_panel": "/api/admin",
        },
        "base_url": "/api",
    }


# ------------------------------------------------------------------------------
# Development server
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
