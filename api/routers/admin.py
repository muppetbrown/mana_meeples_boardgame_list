# api/routers/admin.py
"""
Admin API endpoints for game management, authentication, and BGG import.
Includes CRUD operations and session management.
"""
import time
import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, Header, Cookie, Path, Query, Request, Response, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Game
from schemas import AdminLogin
from exceptions import GameNotFoundError, ValidationError
from bgg_service import fetch_bgg_thing
from api.dependencies import (
    require_admin_auth,
    get_client_ip,
    create_session,
    revoke_session
)
from utils.helpers import game_to_dict, parse_categories, categorize_game
from config import (
    ADMIN_TOKEN,
    RATE_LIMIT_ATTEMPTS,
    RATE_LIMIT_WINDOW,
    SESSION_TIMEOUT_SECONDS
)

logger = logging.getLogger(__name__)

# Import shared state from main
# TODO: Move to shared module
from main import admin_attempt_tracker, admin_sessions

# Create router with prefix and tags
router = APIRouter(prefix="/api/admin", tags=["admin"])


# ------------------------------------------------------------------------------
# Authentication endpoints
# ------------------------------------------------------------------------------

@router.post("/login")
async def admin_login(
    request: Request,
    credentials: AdminLogin,
    response: Response
):
    """
    Admin login endpoint - validates token and creates secure session cookie.
    This replaces the insecure localStorage-based authentication.
    """
    client_ip = get_client_ip(request)
    current_time = time.time()

    # Clean old attempts from tracker
    cutoff_time = current_time - RATE_LIMIT_WINDOW
    admin_attempt_tracker[client_ip] = [
        attempt_time for attempt_time in admin_attempt_tracker[client_ip]
        if attempt_time > cutoff_time
    ]

    # Check if rate limited
    if len(admin_attempt_tracker[client_ip]) >= RATE_LIMIT_ATTEMPTS:
        logger.warning(f"Rate limited admin login attempts from {client_ip}")
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Please try again later."
        )

    # Validate admin token
    if not ADMIN_TOKEN or credentials.token != ADMIN_TOKEN:
        admin_attempt_tracker[client_ip].append(current_time)
        logger.warning(f"Invalid admin login attempt from {client_ip}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create session
    session_token = create_session(client_ip)

    # Set httpOnly secure cookie
    response.set_cookie(
        key="admin_session",
        value=session_token,
        httponly=True,  # Prevents JavaScript access (XSS protection)
        secure=True,     # Only sent over HTTPS
        samesite="lax",  # CSRF protection
        max_age=SESSION_TIMEOUT_SECONDS,
        path="/"
    )

    logger.info(f"Successful admin login from {client_ip}")
    return {
        "success": True,
        "message": "Login successful",
        "expires_in": SESSION_TIMEOUT_SECONDS
    }


@router.post("/logout")
async def admin_logout(
    response: Response,
    admin_session: Optional[str] = Cookie(None)
):
    """
    Admin logout endpoint - revokes session and clears cookie.
    """
    # Revoke session
    revoke_session(admin_session)

    # Clear cookie
    response.delete_cookie(key="admin_session", path="/")

    logger.info("Admin logout")
    return {"success": True, "message": "Logged out successfully"}


@router.get("/validate")
async def validate_admin_token(
    request: Request,
    _: None = Depends(require_admin_auth)
):
    """Validate admin authentication (checks both session cookie and header token)"""
    return {"valid": True, "message": "Authentication valid"}


# ------------------------------------------------------------------------------
# Game CRUD endpoints
# ------------------------------------------------------------------------------

@router.post("/games")
async def create_game(
    game_data: Dict[str, Any],
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_auth)
):
    """Create a new game (admin only)"""
    # Import background task from main - TODO: move to services
    from main import _download_and_update_thumbnail

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
            game.designers = game_data.get("designers", [])
        if hasattr(game, 'publishers'):
            game.publishers = game_data.get("publishers", [])
        if hasattr(game, 'mechanics'):
            game.mechanics = game_data.get("mechanics", [])

        # Auto-categorize if no category provided
        if not game.mana_meeple_category:
            categories = parse_categories(game.categories)
            game.mana_meeple_category = categorize_game(categories)

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


@router.post("/import/bgg")
async def import_from_bgg(
    request: Request,
    bgg_id: int = Query(..., description="BGG game ID"),
    force: bool = Query(False, description="Force reimport if exists"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_auth)
):
    """Import game from BoardGameGeek (admin only)"""
    # Import background task from main - TODO: move to services
    from main import _download_and_update_thumbnail

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
                existing.designers = bgg_data.get("designers", [])
            if hasattr(existing, 'publishers'):
                existing.publishers = bgg_data.get("publishers", [])
            if hasattr(existing, 'mechanics'):
                existing.mechanics = bgg_data.get("mechanics", [])
            if hasattr(existing, 'artists'):
                existing.artists = bgg_data.get("artists", [])
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
            categories = parse_categories(categories_str)
            existing.mana_meeple_category = categorize_game(categories)

            db.add(existing)
            game = existing
        else:
            # Create new with enhanced data
            categories = parse_categories(categories_str)
            game = Game(
                title=bgg_data["title"],
                categories=categories_str,
                year=bgg_data.get("year"),
                players_min=bgg_data.get("players_min"),
                players_max=bgg_data.get("players_max"),
                playtime_min=bgg_data.get("playtime_min"),
                playtime_max=bgg_data.get("playtime_max"),
                bgg_id=bgg_id,
                mana_meeple_category=categorize_game(categories)
            )

            # Add enhanced fields if they exist in the model
            if hasattr(game, 'description'):
                game.description = bgg_data.get("description")
            if hasattr(game, 'designers'):
                game.designers = bgg_data.get("designers", [])
            if hasattr(game, 'publishers'):
                game.publishers = bgg_data.get("publishers", [])
            if hasattr(game, 'mechanics'):
                game.mechanics = bgg_data.get("mechanics", [])
            if hasattr(game, 'artists'):
                game.artists = bgg_data.get("artists", [])
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


@router.get("/games")
async def get_admin_games(
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_auth)
):
    """Get all games for admin interface"""
    games = db.execute(select(Game)).scalars().all()
    return [game_to_dict(request, game) for game in games]


@router.get("/games/{game_id}")
async def get_admin_game(
    request: Request,
    game_id: int = Path(..., description="Game ID"),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_auth)
):
    """Get single game for admin interface"""
    game = db.execute(select(Game).where(Game.id == game_id)).scalar_one_or_none()
    if not game:
        raise GameNotFoundError(f"Game {game_id} not found")

    return game_to_dict(request, game)


@router.put("/games/{game_id}")
async def update_admin_game(
    game_data: Dict[str, Any],
    request: Request,
    game_id: int = Path(..., description="Game ID"),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_auth)
):
    """Update game (admin only)"""
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
        return game_to_dict(request, game)

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update game {game_id}: {e}", extra={'game_id': game_id})
        raise HTTPException(status_code=500, detail="Failed to update game")


@router.post("/games/{game_id}/update")
async def update_admin_game_post(
    game_data: Dict[str, Any],
    request: Request,
    game_id: int = Path(..., description="Game ID"),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_auth)
):
    """Update game via POST (admin only) - alternative to PUT for proxy compatibility"""
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
        return game_to_dict(request, game)

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update game {game_id} via POST: {e}", extra={'game_id': game_id})
        raise HTTPException(status_code=500, detail="Failed to update game")


@router.delete("/games/{game_id}")
async def delete_admin_game(
    request: Request,
    game_id: int = Path(..., description="Game ID"),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_auth)
):
    """Delete game (admin only)"""
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
