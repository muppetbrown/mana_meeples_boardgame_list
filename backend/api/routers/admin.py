# api/routers/admin.py
"""
Admin API endpoints for game management, authentication, and BGG import.
Includes CRUD operations and session management.
"""
import logging
import time
from typing import Any, Dict, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Cookie,
    Depends,
    HTTPException,
    Path,
    Query,
    Request,
    Response,
)
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.dependencies import (
    create_session,
    get_client_ip,
    require_admin_auth,
    revoke_session,
)
from bgg_service import fetch_bgg_thing
from config import (
    ADMIN_TOKEN,
    JWT_EXPIRATION_DAYS,
    RATE_LIMIT_ATTEMPTS,
    RATE_LIMIT_WINDOW,
    SESSION_TIMEOUT_SECONDS,
)
from utils.jwt_utils import generate_jwt_token
from database import get_db
from exceptions import GameNotFoundError, ValidationError
import schemas
from services import GameService, ImageService
from shared.rate_limiting import admin_attempt_tracker
from utils.helpers import game_to_dict

logger = logging.getLogger(__name__)

# Create router with prefix and tags
router = APIRouter(prefix="/api/admin", tags=["admin"])


# ------------------------------------------------------------------------------
# Authentication endpoints
# ------------------------------------------------------------------------------


@router.post("/login")
async def admin_login(
    request: Request, credentials: schemas.AdminLogin, response: Response
):
    """
    Admin login endpoint - validates token and returns JWT.
    JWT tokens are stateless and persist across server restarts.
    """
    client_ip = get_client_ip(request)
    current_time = time.time()

    # Clean old attempts from tracker
    cutoff_time = current_time - RATE_LIMIT_WINDOW
    admin_attempt_tracker[client_ip] = [
        attempt_time
        for attempt_time in admin_attempt_tracker[client_ip]
        if attempt_time > cutoff_time
    ]

    # Check if rate limited
    if len(admin_attempt_tracker[client_ip]) >= RATE_LIMIT_ATTEMPTS:
        logger.warning(f"Rate limited admin login attempts from {client_ip}")
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Please try again later.",
        )

    # Validate admin token
    if not ADMIN_TOKEN or credentials.token != ADMIN_TOKEN:
        admin_attempt_tracker[client_ip].append(current_time)
        logger.warning(f"Invalid admin login attempt from {client_ip}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Generate JWT token
    jwt_token = generate_jwt_token(client_ip)

    logger.info(f"Successful admin login from {client_ip}")
    return {
        "success": True,
        "message": "Login successful",
        "token": jwt_token,
        "expires_in_days": JWT_EXPIRATION_DAYS,
    }


@router.post("/logout")
async def admin_logout(response: Response):
    """
    Admin logout endpoint - with JWT, logout is client-side (token deletion).
    This endpoint is kept for API consistency.
    """
    logger.info("Admin logout")
    return {"success": True, "message": "Logged out successfully"}


@router.get("/validate")
async def validate_admin_token(
    request: Request, _: None = Depends(require_admin_auth)
):
    """
    Validate admin authentication (checks both session cookie and
    header token)
    """
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
    _: None = Depends(require_admin_auth),
):
    """Create a new game (admin only)"""
    # Import httpx_client from main
    from main import httpx_client

    try:
        # Use service layer
        game_service = GameService(db)
        game = game_service.create_game(game_data)

        # Download thumbnail in background if provided
        thumbnail_url = (
            game_data.get("image")
            or game_data.get("thumbnail_url")
            or game_data.get("image_url")
        )
        if thumbnail_url:

            async def download_task():
                image_service = ImageService(db, http_client=httpx_client)
                await image_service.download_and_update_game_thumbnail(
                    game.id, thumbnail_url
                )

            background_tasks.add_task(download_task)

        return {"id": game.id, "title": game.title}

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
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
    _: None = Depends(require_admin_auth),
):
    """Import game from BoardGameGeek (admin only)"""
    # Import httpx_client from main
    from main import httpx_client

    try:
        # Fetch from BGG
        bgg_data = await fetch_bgg_thing(bgg_id)

        # Use service layer - consolidates all the duplication!
        game_service = GameService(db)
        game, was_cached = game_service.create_or_update_from_bgg(
            bgg_id=bgg_id, bgg_data=bgg_data, force_update=force
        )

        # Download thumbnail in background
        thumbnail_url = bgg_data.get("image") or bgg_data.get("thumbnail")
        if thumbnail_url and background_tasks:

            async def download_task():
                image_service = ImageService(db, http_client=httpx_client)
                await image_service.download_and_update_game_thumbnail(
                    game.id, thumbnail_url
                )

            background_tasks.add_task(download_task)

        # Fetch sleeve data in background to avoid blocking the import
        if background_tasks:

            def sleeve_task():
                """Background task to fetch and save sleeve data"""
                from services.sleeve_scraper import scrape_sleeve_data
                from database import SessionLocal

                # Create a new database session for the background task
                db_session = SessionLocal()
                try:
                    logger.info(
                        f"Background task: Fetching sleeve data for '{game.title}' (BGG ID: {bgg_id})"
                    )
                    sleeve_result = scrape_sleeve_data(bgg_id, game.title)
                    logger.info(
                        f"Background task: Sleeve data fetch result: {sleeve_result['status']}"
                    )

                    # Save sleeve data using game service
                    game_service = GameService(db_session)
                    # Fetch the game in this session
                    from models import Game

                    game_in_session = db_session.query(Game).get(game.id)
                    if game_in_session:
                        # Create a fake bgg_data dict with just sleeve data
                        sleeve_bgg_data = {"sleeve_data": sleeve_result}
                        game_service._save_sleeve_data(
                            game_in_session, sleeve_bgg_data
                        )
                        db_session.commit()
                        logger.info(
                            f"Background task: Successfully saved sleeve data for '{game.title}'"
                        )
                except Exception as e:
                    logger.error(
                        f"Background task: Failed to fetch/save sleeve data for {game.title}: {e}",
                        exc_info=True,
                    )
                    db_session.rollback()
                finally:
                    db_session.close()

            background_tasks.add_task(sleeve_task)

        return {"id": game.id, "title": game.title, "cached": was_cached}

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to import BGG game {bgg_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to import game: {str(e)}"
        )


@router.get("/games")
async def get_admin_games(
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_auth),
):
    """Get all games for admin interface"""
    game_service = GameService(db)
    games = game_service.get_all_games()
    return [game_to_dict(request, game) for game in games]


@router.get("/games/{game_id}")
async def get_admin_game(
    request: Request,
    game_id: int = Path(..., description="Game ID"),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_auth),
):
    """Get single game for admin interface"""
    game_service = GameService(db)
    game = game_service.get_game_by_id(game_id)
    if not game:
        raise GameNotFoundError(f"Game {game_id} not found")

    return game_to_dict(request, game)


@router.put("/games/{game_id}")
async def update_admin_game(
    game_data: Dict[str, Any],
    request: Request,
    game_id: int = Path(..., description="Game ID"),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_auth),
):
    """Update game (admin only)"""
    try:
        game_service = GameService(db)
        game = game_service.update_game(game_id, game_data)
        return game_to_dict(request, game)

    except GameNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(
            f"Failed to update game {game_id}: {e}", extra={"game_id": game_id}
        )
        raise HTTPException(status_code=500, detail="Failed to update game")


@router.post("/games/{game_id}/update")
async def update_admin_game_post(
    game_data: Dict[str, Any],
    request: Request,
    game_id: int = Path(..., description="Game ID"),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_auth),
):
    """
    Update game via POST (admin only) - alternative to PUT for
    proxy compatibility
    """
    try:
        game_service = GameService(db)
        game = game_service.update_game(game_id, game_data)
        logger.info(
            f"Updated game via POST: {game.title} (ID: {game.id})",
            extra={"game_id": game.id},
        )
        return game_to_dict(request, game)

    except GameNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(
            f"Failed to update game {game_id} via POST: {e}",
            extra={"game_id": game_id},
        )
        raise HTTPException(status_code=500, detail="Failed to update game")


@router.delete("/games/{game_id}")
async def delete_admin_game(
    request: Request,
    game_id: int = Path(..., description="Game ID"),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_auth),
):
    """Delete game (admin only)"""
    try:
        game_service = GameService(db)
        game_title = game_service.delete_game(game_id)
        return {"message": f"Game '{game_title}' deleted successfully"}

    except GameNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(
            f"Failed to delete game {game_id}: {e}", extra={"game_id": game_id}
        )
        raise HTTPException(status_code=500, detail="Failed to delete game")


@router.post("/fix-sequence")
async def fix_sequence(
    request: Request,
    body: schemas.FixSequenceRequest = schemas.FixSequenceRequest(),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_auth),
):
    """
    Fix PostgreSQL sequence for table ID column.
    This resolves 'duplicate key value violates unique constraint' errors
    when importing new records.

    Security: Input validation ensures only whitelisted tables can be accessed.
    """
    try:
        table_name = body.table_name

        # Get the current maximum ID from the table
        # Note: table_name is validated by Pydantic schema (whitelist + alphanumeric check)
        result = db.execute(text(f"SELECT MAX(id) FROM {table_name}"))
        max_id = result.scalar()

        if max_id is None:
            max_id = 0

        # Determine sequence name (PostgreSQL naming convention)
        sequence_name = f"{table_name}_id_seq"

        # Reset the sequence to max_id (with is_called=true, so next value will be max_id + 1)
        # Using 'true' (or default) means the sequence has been "called" and will increment on next use
        # Use parameter binding to prevent SQL injection on max_id
        db.execute(
            text(f"SELECT setval('{sequence_name}', :max_id, true)"),
            {"max_id": max_id}
        )
        db.commit()

        logger.info(
            f"Successfully reset {table_name} sequence to {max_id} (next will be {max_id + 1})",
            extra={"table_name": table_name, "max_id": max_id}
        )
        return {
            "message": "Sequence fixed successfully",
            "table_name": table_name,
            "max_id": max_id,
            "next_id": max_id + 1
        }

    except ValueError as e:
        # Validation error from Pydantic
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(
            f"Failed to fix sequence for {body.table_name}: {e}",
            extra={"table_name": body.table_name},
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Failed to fix sequence: {str(e)}")
