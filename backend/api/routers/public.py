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
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db, get_read_db
from exceptions import GameNotFoundError
from services import GameService, ImageService
from utils.helpers import game_to_dict
from utils.cache import cached_query

logger = logging.getLogger(__name__)

# Create router with prefix and tags
router = APIRouter(prefix="/api/public", tags=["public"])

# Import rate limiter from main
# (after router creation to avoid circular import)
from main import limiter  # noqa: E402


def _get_cached_games_key(
    search: Optional[str],
    category: Optional[str],
    designer: Optional[str],
    nz_designer: Optional[bool],
    players: Optional[int],
    complexity_min: Optional[float],
    complexity_max: Optional[float],
    recently_added: Optional[int],
    sort: str,
    page: int,
    page_size: int,
) -> str:
    """Generate cache key for game queries"""
    from utils.cache import make_cache_key
    return make_cache_key(
        search, category, designer, nz_designer,
        players, complexity_min, complexity_max, recently_added, sort, page, page_size
    )


def _get_games_from_db(
    db: Session,
    search: Optional[str],
    category: Optional[str],
    designer: Optional[str],
    nz_designer: Optional[bool],
    players: Optional[int],
    complexity_min: Optional[float],
    complexity_max: Optional[float],
    recently_added: Optional[int],
    sort: str,
    page: int,
    page_size: int,
):
    """
    Execute game query with caching.
    Sprint 12: Performance optimization for high-concurrency load.

    Uses simple TTL cache (5 seconds) to reduce database load during
    concurrent requests with identical parameters.
    """
    import time
    from utils.cache import _cache_store, _cache_timestamps

    # Generate cache key
    cache_params = _get_cached_games_key(
        search, category, designer, nz_designer,
        players, complexity_min, complexity_max, recently_added, sort, page, page_size
    )
    cache_key = f"games_query:{cache_params}"

    # Check cache (30 second TTL - optimized for performance at scale)
    current_time = time.time()
    if cache_key in _cache_store and cache_key in _cache_timestamps:
        if current_time - _cache_timestamps[cache_key] < 30:
            return _cache_store[cache_key]

    # Cache miss - query database
    service = GameService(db)
    result = service.get_filtered_games(
        search=search,
        category=category,
        designer=designer,
        nz_designer=nz_designer,
        players=players,
        complexity_min=complexity_min,
        complexity_max=complexity_max,
        recently_added_days=recently_added,
        sort=sort,
        page=page,
        page_size=page_size,
    )

    # Store in cache
    _cache_store[cache_key] = result
    _cache_timestamps[cache_key] = current_time

    return result


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
    complexity_min: Optional[float] = Query(
        None, ge=1, le=5, description="Minimum complexity rating (1-5)"
    ),
    complexity_max: Optional[float] = Query(
        None, ge=1, le=5, description="Maximum complexity rating (1-5)"
    ),
    recently_added: Optional[int] = Query(
        None, ge=1, description="Filter games added within last N days"
    ),
    db: Session = Depends(get_read_db),
):
    """Get paginated list of games with filtering and search"""
    # Convert nz_designer string to boolean
    nz_designer_bool = None
    if nz_designer is not None:
        if isinstance(nz_designer, str):
            nz_designer_bool = nz_designer.lower() in ["true", "1", "yes"]
        else:
            nz_designer_bool = bool(nz_designer)

    # Use cached query for better performance under load
    games, total = _get_games_from_db(
        db=db,
        search=q if q else None,
        category=category,
        designer=designer,
        nz_designer=nz_designer_bool,
        players=players,
        complexity_min=complexity_min,
        complexity_max=complexity_max,
        recently_added=recently_added,
        sort=sort,
        page=page,
        page_size=page_size,
    )

    # Convert to response format and add expansion player count info
    items = []
    for game in games:
        game_dict = game_to_dict(request, game)

        # Calculate player count with expansions for filtering
        if hasattr(game, "expansions") and game.expansions:
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

        items.append(game_dict)

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
    db: Session = Depends(get_read_db),
):
    """Get details for a specific game"""
    service = GameService(db)
    game = service.get_game_by_id(game_id)
    # Only show games that are owned (status is NULL or "OWNED")
    # Hide games on buy list or wishlist
    if not game or (game.status is not None and game.status != "OWNED"):
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
async def get_category_counts(request: Request, db: Session = Depends(get_read_db)):
    """Get counts for each category"""
    service = GameService(db)
    return service.get_category_counts()


@router.get("/games/by-designer/{designer_name}")
@limiter.limit("60/minute")  # Designer searches
async def get_games_by_designer(
    request: Request, designer_name: str, db: Session = Depends(get_read_db)
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
@limiter.limit("300/minute")  # Allow higher rate for pages with many images
async def image_proxy(
    request: Request,
    url: str = Query(..., description="Image URL to proxy"),
    width: Optional[int] = Query(None, description="Target width for resize"),
    height: Optional[int] = Query(None, description="Target height for resize"),
    db: Session = Depends(get_read_db),
):
    """
    Proxy external images with Cloudinary CDN and caching.

    If Cloudinary is enabled:
    - Automatically uploads BGG images to Cloudinary on first request
    - Returns optimized Cloudinary URL with WebP/AVIF support
    - Supports width/height parameters for responsive images

    If Cloudinary is disabled:
    - Falls back to direct proxy with caching headers

    Rate limit: 300 requests/minute to support pages with many images.
    Security: Only proxies images from trusted sources (BGG, local storage).
    """
    # Import dependencies
    from main import httpx_client  # noqa: E402
    from config import API_BASE, CLOUDINARY_ENABLED  # noqa: E402
    from services.cloudinary_service import cloudinary_service  # noqa: E402

    try:
        # Validate URL - only allow trusted sources
        trusted_domains = [
            'cf.geekdo-images.com',  # BGG CDN
            'cf.geekdo-static.com',  # BGG static
            API_BASE,  # Our own API base
        ]

        # Check if URL is from a trusted domain
        is_trusted = any(domain in url for domain in trusted_domains)
        if not is_trusted:
            logger.warning(f"Attempted to proxy untrusted URL: {url}")
            raise HTTPException(
                status_code=400,
                detail="Image proxy only supports BoardGameGeek images"
            )

        # FAST PATH: Check if we have a pre-generated Cloudinary URL cached in database
        # This eliminates the upload check and redirect latency (50-150ms savings)
        if CLOUDINARY_ENABLED and 'cf.geekdo-images.com' in url:
            from models import Game  # noqa: E402
            from sqlalchemy import or_  # noqa: E402

            try:
                # Quick database lookup for cached Cloudinary URL
                # Check both image and thumbnail_url fields
                cached_game = db.execute(
                    select(Game).where(
                        or_(
                            Game.image == url,
                            Game.thumbnail_url == url
                        )
                    ).where(
                        Game.cloudinary_url.isnot(None)
                    )
                ).scalar_one_or_none()

                if cached_game and cached_game.cloudinary_url:
                    logger.debug(f"Using cached Cloudinary URL for game {cached_game.id}")
                    return Response(
                        status_code=302,
                        headers={
                            "Location": cached_game.cloudinary_url,
                            "Cache-Control": "public, max-age=31536000, immutable"
                        }
                    )
            except Exception as e:
                logger.debug(f"Cached Cloudinary URL lookup failed: {e}, continuing to upload path")

        # If Cloudinary is enabled, try to upload and return Cloudinary URL
        if CLOUDINARY_ENABLED and 'cf.geekdo-images.com' in url:
            try:
                # Try to upload image to Cloudinary (will skip if already exists)
                # This ensures the Cloudinary URL actually works
                upload_result = await cloudinary_service.upload_from_url(
                    url,
                    httpx_client
                )

                # If upload succeeded, generate and redirect to Cloudinary URL
                if upload_result:
                    # Get optimized URL without size transformations
                    # Don't pass width/height - use base Cloudinary URL only
                    cloudinary_url = cloudinary_service.get_image_url(url)

                    # Only redirect to Cloudinary if we got a valid URL that differs from original
                    if cloudinary_url and cloudinary_url != url:
                        logger.debug(f"Redirecting to Cloudinary URL: {cloudinary_url}")
                        return Response(
                            status_code=302,
                            headers={
                                "Location": cloudinary_url,
                                "Cache-Control": "public, max-age=31536000, immutable"
                            }
                        )

                # Upload failed or returned original URL - fall through to direct proxy
                logger.debug(f"Cloudinary upload/URL failed for {url}, using direct proxy")

            except Exception as e:
                # If Cloudinary fails for any reason, fall through to direct proxy
                logger.warning(f"Cloudinary error for {url}: {e}, falling back to direct proxy")

        # Fallback to direct proxy if Cloudinary fails or is disabled
        # Determine cache max age based on URL
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

    except HTTPException:
        # Re-raise HTTPExceptions (like validation errors) without modification
        raise
    except Exception as e:
        logger.error(f"Image proxy error for {url}: {e}")
        raise HTTPException(
            status_code=502, detail=f"Failed to fetch image: {str(e)}"
        )
