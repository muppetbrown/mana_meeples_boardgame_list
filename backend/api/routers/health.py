# api/routers/health.py
"""
Health check and debug endpoints for monitoring and troubleshooting.
Includes database health checks, category debugging, and performance metrics.
"""
import logging
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from database import get_db
from models import Game
from api.dependencies import require_admin_auth
from utils.helpers import parse_categories
from middleware.performance import performance_monitor
from bgg_service import fetch_bgg_thing, BGGServiceError

logger = logging.getLogger(__name__)

# Create routers for different prefixes
health_router = APIRouter(prefix="/api/health", tags=["health"])
debug_router = APIRouter(prefix="/api/debug", tags=["debug"])


# ------------------------------------------------------------------------------
# Health check endpoints (public)
# ------------------------------------------------------------------------------


@health_router.get("")
async def health_check():
    """Basic health check"""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@health_router.get("/db")
async def health_check_db(db: Session = Depends(get_db)):
    """Database health check"""
    try:
        count = db.execute(select(func.count()).select_from(Game)).scalar()
        return {"status": "healthy", "game_count": count}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(status_code=503, detail="Database unavailable")


@health_router.get("/redis")
async def health_check_redis():
    """
    Redis health check.
    Sprint 8: Monitor Redis connectivity for session storage and rate limiting.
    """
    try:
        from redis_client import get_redis_client
        from config import REDIS_ENABLED

        if not REDIS_ENABLED:
            return {
                "status": "disabled",
                "message": "Redis is disabled, using in-memory storage",
            }

        redis_client = get_redis_client()
        if redis_client.ping():
            return {
                "status": "healthy",
                "message": "Redis is connected and responding",
            }
        else:
            return {
                "status": "unhealthy",
                "message": "Redis is not responding",
            }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {
            "status": "error",
            "message": f"Redis health check error: {str(e)}",
        }


# ------------------------------------------------------------------------------
# Debug endpoints (admin only)
# ------------------------------------------------------------------------------


@debug_router.get("/categories")
async def debug_categories(
    db: Session = Depends(get_db), _: None = Depends(require_admin_auth)
):
    """Debug endpoint to see all unique categories in the database"""
    # Only select the columns we need to avoid missing column errors
    games = db.execute(select(Game.id, Game.categories)).all()
    all_categories = []

    for game in games:
        # Handle tuple from select query
        categories = parse_categories(game[1])
        all_categories.extend(categories)

    unique_categories = sorted(list(set(all_categories)))

    return {
        "total_games": len(games),
        "unique_categories": unique_categories,
        "category_count": len(unique_categories),
    }


@debug_router.get("/database-info")
async def debug_database_info(
    limit: Optional[int] = Query(
        None, description="Number of games to return (default: all)"
    ),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_auth),
):
    """Debug endpoint to see database structure and sample data"""
    # Select all columns from your schema
    query = select(
        Game.id,
        Game.title,
        Game.categories,
        Game.year,
        Game.players_min,
        Game.players_max,
        Game.playtime_min,
        Game.playtime_max,
        Game.image,
        Game.created_at,
        Game.bgg_id,
        Game.mana_meeple_category,
        Game.description,
        Game.designers,
        Game.publishers,
        Game.mechanics,
        Game.artists,
        Game.average_rating,
        Game.complexity,
        Game.bgg_rank,
        Game.users_rated,
        Game.min_age,
        Game.is_cooperative,
        Game.nz_designer,
        Game.game_type,
    )

    games = db.execute(query).all()

    # Apply limit if specified, otherwise return all
    if limit is not None:
        games = games[:limit]

    return {
        "total_games_in_db": db.execute(
            select(func.count()).select_from(Game)
        ).scalar(),
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
                "image": g[8],
                "created_at": g[9].isoformat() if g[9] else None,
                "bgg_id": g[10],
                "mana_meeple_category": g[11],
                "description": g[12],
                "designers": g[13],
                "publishers": g[14],
                "mechanics": g[15],
                "artists": g[16],
                "average_rating": g[17],
                "complexity": g[18],
                "bgg_rank": g[19],
                "users_rated": g[20],
                "min_age": g[21],
                "is_cooperative": g[22],
                "nz_designer": g[23],
                "game_type": g[24],
            }
            for g in games
        ],
    }


@debug_router.get("/performance")
async def get_performance_stats(_: None = Depends(require_admin_auth)):
    """Get performance monitoring stats (admin only)"""
    return performance_monitor.get_stats()


@debug_router.get("/bgg-test/{bgg_id}")
async def debug_bgg_api_call(
    bgg_id: int, _: None = Depends(require_admin_auth)
):
    """Debug endpoint to test BGG API calls with detailed logging"""
    logger.info(f"Starting BGG debug test for game ID {bgg_id}")

    try:
        game_data = await fetch_bgg_thing(bgg_id)
        logger.info(f"Successfully fetched BGG data for game {bgg_id}")

        return {
            "status": "success",
            "bgg_id": bgg_id,
            "game_data": game_data,
            "message": (
                "BGG API call successful - check logs for detailed "
                "response info"
            ),
        }

    except BGGServiceError as e:
        logger.error(f"BGG service error for game {bgg_id}: {str(e)}")
        return {
            "status": "bgg_error",
            "bgg_id": bgg_id,
            "error": str(e),
            "message": (
                "BGG service error occurred - check logs for detailed "
                "debugging info"
            ),
        }

    except Exception as e:
        logger.error(
            f"Unexpected error during BGG debug test for game "
            f"{bgg_id}: {str(e)}"
        )
        return {
            "status": "error",
            "bgg_id": bgg_id,
            "error": str(e),
            "message": "Unexpected error occurred - check logs for details",
        }
