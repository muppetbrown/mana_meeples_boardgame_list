# api/routers/public.py
"""
Public API endpoints for game catalogue browsing.
Includes filtering, search, pagination, and image proxying.
"""
import logging
from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, Path, Request, Response, HTTPException
from sqlalchemy import select, func, or_, and_, case
from sqlalchemy.orm import Session

from database import get_db
from models import Game
from exceptions import GameNotFoundError
from utils.helpers import game_to_dict, calculate_category_counts, CATEGORY_KEYS
from config import API_BASE

logger = logging.getLogger(__name__)

# Import rate limiter from main
# TODO: Move limiter to shared module
from main import limiter

# Create router with prefix and tags
router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/games")
@limiter.limit("100/minute")  # Allow 100 requests per minute per IP
async def get_public_games(
    request: Request,
    q: str = Query("", description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(24, ge=1, le=1000, description="Items per page"),
    sort: str = Query("title_asc", description="Sort order"),
    category: Optional[str] = Query(None, description="Category filter"),
    designer: Optional[str] = Query(None, description="Designer filter"),
    nz_designer: Optional[str] = Query(None, description="Filter by NZ designers"),
    players: Optional[int] = Query(None, ge=1, description="Filter by player count"),
    recently_added: Optional[int] = Query(None, ge=1, description="Filter games added within last N days"),
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

    # Apply player count filter
    if players is not None:
        # Filter games that support the specified player count
        # Game is suitable if players_min <= players <= players_max
        query = query.where(
            and_(
                or_(Game.players_min.is_(None), Game.players_min <= players),
                or_(Game.players_max.is_(None), Game.players_max >= players)
            )
        )

    # Apply recently added filter
    if recently_added is not None:
        cutoff_date = datetime.utcnow() - timedelta(days=recently_added)
        if hasattr(Game, 'date_added'):
            query = query.where(Game.date_added >= cutoff_date)

    # Apply sorting
    if sort == "title_desc":
        query = query.order_by(Game.title.desc())
    elif sort == "year_desc":
        query = query.order_by(Game.year.desc().nulls_last())
    elif sort == "year_asc":
        query = query.order_by(Game.year.asc().nulls_last())
    elif sort == "date_added_desc":
        if hasattr(Game, 'date_added'):
            query = query.order_by(Game.date_added.desc().nulls_last())
        else:
            query = query.order_by(Game.title.asc())
    elif sort == "date_added_asc":
        if hasattr(Game, 'date_added'):
            query = query.order_by(Game.date_added.asc().nulls_last())
        else:
            query = query.order_by(Game.title.asc())
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
    items = [game_to_dict(request, game) for game in page_games]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items
    }


@router.get("/games/{game_id}")
@limiter.limit("120/minute")  # Allow 120 game detail views per minute
async def get_public_game(
    request: Request,
    game_id: int = Path(..., description="Game ID"),
    db: Session = Depends(get_db)
):
    """Get details for a specific game"""
    game = db.get(Game, game_id)
    if not game:
        raise GameNotFoundError("Game not found")

    return game_to_dict(request, game)


@router.get("/category-counts")
@limiter.limit("60/minute")  # Category counts change infrequently
async def get_category_counts(request: Request, db: Session = Depends(get_db)):
    """Get counts for each category"""
    # Only select the columns we need to avoid missing column errors
    games = db.execute(select(Game.id, Game.mana_meeple_category)).all()
    return calculate_category_counts(games)


@router.get("/games/by-designer/{designer_name}")
@limiter.limit("60/minute")  # Designer searches
async def get_games_by_designer(request: Request, designer_name: str, db: Session = Depends(get_db)):
    """Get games by a specific designer"""
    try:
        designer_filter = f"%{designer_name}%"
        query = select(Game)
        if hasattr(Game, 'designers'):
            query = query.where(Game.designers.ilike(designer_filter))

        games = db.execute(query).scalars().all()
        return {"designer": designer_name, "games": [game_to_dict(request, game) for game in games]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch games by designer: {str(e)}")


@router.get("/image-proxy")
@limiter.limit("200/minute")  # Higher limit for image loading
async def image_proxy(request: Request, url: str = Query(..., description="Image URL to proxy")):
    """Proxy external images with caching headers"""
    # Import httpx_client from main - this is a temporary solution
    # TODO: Move httpx_client to a shared module
    from main import httpx_client

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

    except Exception as e:
        logger.error(f"Image proxy error for {url}: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch image: {str(e)}")
