# api/routers/public.py
"""
Public API endpoints for game catalogue browsing.
Includes filtering, search, pagination, and image proxying.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, Path, Request, Response, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from exceptions import GameNotFoundError
from utils.helpers import game_to_dict
from services import GameService, ImageService

logger = logging.getLogger(__name__)

# Import rate limiter from shared module
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
    # Convert nz_designer string to boolean
    nz_designer_bool = None
    if nz_designer is not None:
        nz_designer_bool = nz_designer.lower() in ['true', '1', 'yes'] if isinstance(nz_designer, str) else bool(nz_designer)

    # Use service layer
    service = GameService(db)
    games, total = service.get_filtered_games(
        search=q if q else None,
        category=category,
        designer=designer,
        nz_designer=nz_designer_bool,
        players=players,
        recently_added_days=recently_added,
        sort=sort,
        page=page,
        page_size=page_size
    )

    # Convert to response format
    items = [game_to_dict(request, game) for game in games]

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
    service = GameService(db)
    game = service.get_game_by_id(game_id)
    if not game:
        raise GameNotFoundError("Game not found")

    return game_to_dict(request, game)


@router.get("/category-counts")
@limiter.limit("60/minute")  # Category counts change infrequently
async def get_category_counts(request: Request, db: Session = Depends(get_db)):
    """Get counts for each category"""
    service = GameService(db)
    return service.get_category_counts()


@router.get("/games/by-designer/{designer_name}")
@limiter.limit("60/minute")  # Designer searches
async def get_games_by_designer(request: Request, designer_name: str, db: Session = Depends(get_db)):
    """Get games by a specific designer"""
    try:
        service = GameService(db)
        games = service.get_games_by_designer(designer_name)
        return {"designer": designer_name, "games": [game_to_dict(request, game) for game in games]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch games by designer: {str(e)}")


@router.get("/image-proxy")
@limiter.limit("200/minute")  # Higher limit for image loading
async def image_proxy(request: Request, url: str = Query(..., description="Image URL to proxy"), db: Session = Depends(get_db)):
    """Proxy external images with caching headers"""
    # Import httpx_client from main
    from main import httpx_client

    try:
        # Determine cache max age based on URL
        from config import API_BASE
        cache_max_age = 31536000 if url.startswith(API_BASE + "/thumbs/") else 300

        # Use service layer for image proxying
        service = ImageService(db, http_client=httpx_client)
        content, content_type, cache_control = await service.proxy_image(url, cache_max_age)

        headers = {
            "Content-Type": content_type,
            "Cache-Control": cache_control
        }

        return Response(content=content, headers=headers)

    except Exception as e:
        logger.error(f"Image proxy error for {url}: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch image: {str(e)}")
