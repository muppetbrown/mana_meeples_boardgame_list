# api/routers/public.py
"""
Public API endpoints for game catalogue browsing.
Includes filtering, search, pagination, and image proxying.
"""
import logging
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Query,
    Request,
    Response,
)
from sqlalchemy.orm import Session

from database import get_db
from exceptions import GameNotFoundError
from services import GameService, ImageService
from utils.helpers import game_to_dict

logger = logging.getLogger(__name__)

# Create router with prefix and tags
router = APIRouter(prefix="/api/public", tags=["public"])

# Import rate limiter from main
# (after router creation to avoid circular import)
from main import limiter  # noqa: E402


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
    nz_designer: Optional[str] = Query(
        None, description="Filter by NZ designers"
    ),
    players: Optional[int] = Query(
        None, ge=1, description="Filter by player count"
    ),
    recently_added: Optional[int] = Query(
        None, ge=1, description="Filter games added within last N days"
    ),
    db: Session = Depends(get_db),
):
    """Get paginated list of games with filtering and search"""
    # Convert nz_designer string to boolean
    nz_designer_bool = None
    if nz_designer is not None:
        if isinstance(nz_designer, str):
            nz_designer_bool = nz_designer.lower() in ["true", "1", "yes"]
        else:
            nz_designer_bool = bool(nz_designer)

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
        page_size=page_size,
    )

    # Convert to response format
    items = [game_to_dict(request, game) for game in games]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


@router.get("/games/{game_id}")
@limiter.limit("120/minute")  # Allow 120 game detail views per minute
async def get_public_game(
    request: Request,
    game_id: int = Path(..., description="Game ID"),
    db: Session = Depends(get_db),
):
    """Get details for a specific game"""
    service = GameService(db)
    game = service.get_game_by_id(game_id)
    if not game or game.status != "OWNED":
        raise GameNotFoundError("Game not found")

    # Build detailed response with expansions and base game info
    game_dict = game_to_dict(request, game)

    # Add expansions if this is a base game
    if hasattr(game, "expansions") and game.expansions:
        game_dict["expansions"] = [
            game_to_dict(request, exp) for exp in game.expansions
        ]

        # Calculate player count with expansions
        max_with_exp = game.players_max or 0
        min_with_exp = game.players_min or 0
        has_player_expansion = False

        for exp in game.expansions:
            if exp.modifies_players_max and exp.modifies_players_max > max_with_exp:
                max_with_exp = exp.modifies_players_max
                has_player_expansion = True
            if exp.modifies_players_min and exp.modifies_players_min < min_with_exp:
                min_with_exp = exp.modifies_players_min

        game_dict["players_max_with_expansions"] = max_with_exp
        game_dict["players_min_with_expansions"] = min_with_exp
        game_dict["has_player_expansion"] = has_player_expansion
    else:
        game_dict["expansions"] = []

    # Add base game info if this is an expansion
    if game.base_game_id and hasattr(game, "base_game") and game.base_game:
        game_dict["base_game"] = {
            "id": game.base_game.id,
            "title": game.base_game.title,
            "thumbnail_url": game.base_game.image or game.base_game.thumbnail_url,
        }

    return game_dict


@router.get("/category-counts")
@limiter.limit("60/minute")  # Category counts change infrequently
async def get_category_counts(request: Request, db: Session = Depends(get_db)):
    """Get counts for each category"""
    service = GameService(db)
    return service.get_category_counts()


@router.get("/games/by-designer/{designer_name}")
@limiter.limit("60/minute")  # Designer searches
async def get_games_by_designer(
    request: Request, designer_name: str, db: Session = Depends(get_db)
):
    """Get games by a specific designer"""
    try:
        service = GameService(db)
        games = service.get_games_by_designer(designer_name)
        return {
            "designer": designer_name,
            "games": [game_to_dict(request, game) for game in games],
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch games by designer: {str(e)}",
        )


@router.get("/image-proxy")
@limiter.limit("200/minute")  # Higher limit for image loading
async def image_proxy(
    request: Request,
    url: str = Query(..., description="Image URL to proxy"),
    db: Session = Depends(get_db),
):
    """Proxy external images with caching headers"""
    # Import httpx_client from main
    from main import httpx_client  # noqa: E402

    try:
        # Determine cache max age based on URL
        from config import API_BASE  # noqa: E402

        cache_max_age = (
            31536000 if url.startswith(API_BASE + "/thumbs/") else 300
        )

        # Use service layer for image proxying
        service = ImageService(db, http_client=httpx_client)
        content, content_type, cache_control = await service.proxy_image(
            url, cache_max_age
        )

        headers = {
            "Content-Type": content_type,
            "Cache-Control": cache_control,
        }

        return Response(content=content, headers=headers)

    except Exception as e:
        logger.error(f"Image proxy error for {url}: {e}")
        raise HTTPException(
            status_code=502, detail=f"Failed to fetch image: {str(e)}"
        )
