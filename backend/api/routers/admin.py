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
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.dependencies import (
    get_client_ip,
    require_admin_auth,
)
from utils.error_handlers import (
    handle_integrity_error,
    handle_validation_error,
    handle_generic_error,
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
from shared.rate_limiting import rate_limit_tracker
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
    attempts = rate_limit_tracker.get_attempts(client_ip)
    attempts = [
        attempt_time
        for attempt_time in attempts
        if attempt_time > cutoff_time
    ]

    # Check if rate limited
    if len(attempts) >= RATE_LIMIT_ATTEMPTS:
        logger.warning(f"Rate limited admin login attempts from {client_ip}")
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Please try again later.",
        )

    # Validate admin token
    if not ADMIN_TOKEN or credentials.token != ADMIN_TOKEN:
        attempts.append(current_time)
        rate_limit_tracker.set_attempts(client_ip, attempts, RATE_LIMIT_WINDOW)
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


@router.post("/games", status_code=201)
async def create_game(
    game_data: Dict[str, Any],
    request: Request,
    response: Response,
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

        return game_to_dict(request, game)

    except IntegrityError as e:
        db.rollback()
        raise handle_integrity_error(e)
    except (ValidationError, ValueError) as e:
        raise handle_validation_error(e)
    except Exception as e:
        db.rollback()
        raise handle_generic_error(e, "create game")


@router.post("/import/bgg")
async def import_from_bgg(
    request: Request,
    response: Response,
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
        game_service = GameService(db)

        # Check if game exists and return cached version if force=false
        if not force:
            existing = game_service.get_game_by_bgg_id(bgg_id)
            if existing:
                response.status_code = 200
                return game_to_dict(request, existing)

        # Fetch from BGG (only if force=true or game doesn't exist)
        bgg_data = await fetch_bgg_thing(bgg_id)

        # Use service layer - consolidates all the duplication!
        game, was_cached = game_service.create_or_update_from_bgg(
            bgg_id=bgg_id, bgg_data=bgg_data, force_update=force
        )

        # Upload image to Cloudinary in background (PROACTIVE vs on-demand during page loads)
        # This improves customer experience by pre-processing images during import
        thumbnail_url = bgg_data.get("image") or bgg_data.get("thumbnail")
        if thumbnail_url and background_tasks:
            from config import CLOUDINARY_ENABLED
            from services.cloudinary_service import cloudinary_service

            async def cloudinary_upload_task():
                """Upload image to Cloudinary immediately during import"""
                if CLOUDINARY_ENABLED:
                    try:
                        # Upload to Cloudinary (will compress to WebP at 1200px)
                        upload_result = await cloudinary_service.upload_from_url(
                            thumbnail_url, httpx_client, game_id=game.id
                        )

                        if upload_result:
                            # Generate base Cloudinary URL (without transformations)
                            cloudinary_url = cloudinary_service.get_image_url(thumbnail_url)

                            # Save to database for fast-path serving
                            from models import Game
                            stmt = select(Game).where(Game.id == game.id)
                            db_game = db.execute(stmt).scalars().first()
                            if db_game:
                                db_game.cloudinary_url = cloudinary_url
                                db.commit()
                                logger.info(f"✓ Cloudinary upload completed for game {game.id}: {game.title}")
                        else:
                            logger.warning(f"Cloudinary upload failed for game {game.id}, will use direct proxy fallback")
                    except Exception as e:
                        logger.error(f"Cloudinary upload task failed for game {game.id}: {e}")
                        # Non-critical - image proxy will handle it on-demand if needed
                else:
                    # Cloudinary disabled - download thumbnail locally (legacy behavior)
                    image_service = ImageService(db, http_client=httpx_client)
                    await image_service.download_and_update_game_thumbnail(
                        game.id, thumbnail_url
                    )

            background_tasks.add_task(cloudinary_upload_task)

        # Note: Sleeve data is fetched via GitHub Actions workflow (not on Render server)
        # Users can select games in Manage Library and trigger sleeve fetch for selected games

        # Set appropriate status code: 201 for new, 200 for update
        response.status_code = 201 if not was_cached else 200
        return game_to_dict(request, game)

    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to import BGG game {bgg_id}: {e}", exc_info=True)
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
    except IntegrityError as e:
        db.rollback()
        raise handle_integrity_error(e)
    except (ValidationError, ValueError) as e:
        raise handle_validation_error(e)
    except Exception as e:
        db.rollback()
        logger.error(
            f"Failed to update game {game_id}: {e}", extra={"game_id": game_id}, exc_info=True
        )
        raise handle_generic_error(e, f"update game {game_id}")


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

    Security: Explicit whitelist mapping prevents SQL injection.
    """
    try:
        table_name = body.table_name

        # SECURITY: Explicit whitelist of valid table->sequence mappings
        # This prevents SQL injection even if Pydantic validation is bypassed
        VALID_SEQUENCES = {
            "boardgames": "boardgames_id_seq",
            "buy_list_games": "buy_list_games_id_seq",
            "price_snapshots": "price_snapshots_id_seq",
            "price_offers": "price_offers_id_seq",
            "sleeves": "sleeves_id_seq",
        }

        if table_name not in VALID_SEQUENCES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid table name. Allowed: {', '.join(VALID_SEQUENCES.keys())}"
            )

        sequence_name = VALID_SEQUENCES[table_name]

        # SECURITY FIX: Use SQLAlchemy's identifier quoting to prevent SQL injection
        # Even though we have a whitelist, using proper identifier quoting is defense-in-depth
        from sqlalchemy import inspect, func
        from sqlalchemy.sql import quoted_name

        # Option 1: Use SQLAlchemy's table inspection for safety
        inspector = inspect(db.get_bind())
        if table_name not in inspector.get_table_names():
            raise HTTPException(
                status_code=400,
                detail=f"Table {table_name} does not exist in database"
            )

        # Get the current maximum ID using SQLAlchemy's func
        # This is safer than raw SQL with f-strings
        from models import Base

        # Map table names to model classes for type-safe queries
        table_models = {
            "boardgames": __import__('models', fromlist=['Game']).Game,
            "buy_list_games": __import__('models', fromlist=['BuyListGame']).BuyListGame,
            "price_snapshots": __import__('models', fromlist=['PriceSnapshot']).PriceSnapshot,
            "price_offers": __import__('models', fromlist=['PriceOffer']).PriceOffer,
            "sleeves": __import__('models', fromlist=['Sleeve']).Sleeve,
        }

        if table_name not in table_models:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid table name. Allowed: {', '.join(table_models.keys())}"
            )

        model_class = table_models[table_name]

        # Type-safe query using SQLAlchemy ORM
        stmt = select(func.max(model_class.id))
        max_id = db.execute(stmt).scalar()

        if max_id is None:
            max_id = 0

        # Reset the sequence using func.setval (safer than raw SQL)
        # Note: PostgreSQL's setval() requires literal sequence name, not a parameter
        # We use the whitelisted sequence_name from VALID_SEQUENCES
        # This is safe because sequence_name comes from a hardcoded dict, not user input
        db.execute(
            select(func.setval(sequence_name, max_id, True))
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

    except HTTPException:
        raise
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


@router.post("/trigger-sleeve-fetch")
async def trigger_sleeve_fetch(
    request: Request,
    game_ids: list[int],
    _: None = Depends(require_admin_auth),
):
    """
    Trigger GitHub Actions workflow to fetch sleeve data for selected games.
    Requires GITHUB_TOKEN to be configured in environment variables.
    """
    from config import GITHUB_TOKEN, GITHUB_REPO_OWNER, GITHUB_REPO_NAME
    import httpx

    if not GITHUB_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="GitHub token not configured. Cannot trigger workflow.",
        )

    if not game_ids:
        raise HTTPException(
            status_code=400, detail="At least one game ID must be provided"
        )

    # Prepare workflow dispatch request
    workflow_name = "fetch_sleeves.yml"
    game_ids_str = ",".join(str(gid) for gid in game_ids)

    url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/actions/workflows/{workflow_name}/dispatches"

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    payload = {
        "ref": "main",  # or master, depending on your default branch
        "inputs": {"game_ids": game_ids_str},
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)

            if response.status_code == 204:
                # Success - workflow dispatched
                logger.info(
                    f"Successfully triggered sleeve fetch workflow for {len(game_ids)} game(s)"
                )
                return {
                    "success": True,
                    "message": f"Sleeve fetch workflow triggered for {len(game_ids)} game(s)",
                    "game_ids": game_ids,
                }
            else:
                error_detail = response.text
                logger.error(
                    f"Failed to trigger workflow. Status: {response.status_code}, Error: {error_detail}"
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"GitHub API error: {error_detail}",
                )

    except httpx.HTTPError as e:
        logger.error(f"HTTP error triggering workflow: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to trigger workflow: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error triggering workflow: {e}")
        raise HTTPException(
            status_code=500, detail=f"Unexpected error: {str(e)}"
        )


# ------------------------------------------------------------------------------
# Error Monitoring Endpoints (Sprint 5)
# ------------------------------------------------------------------------------


@router.get("/monitoring/background-failures")
async def get_background_task_failures(
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_auth),
    resolved: Optional[bool] = Query(None, description="Filter by resolved status"),
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    limit: int = Query(50, ge=1, le=500, description="Number of results"),
):
    """
    Get recent background task failures for monitoring.
    Sprint 5: Error Handling & Monitoring

    Returns failure data including:
    - Task type (thumbnail_download, bgg_import, etc.)
    - Error messages and stack traces
    - Associated game IDs
    - Retry counts
    - Resolution status
    """
    from models import BackgroundTaskFailure

    try:
        # Build query
        stmt = select(BackgroundTaskFailure)

        # Apply filters
        if resolved is not None:
            stmt = stmt.where(BackgroundTaskFailure.resolved == resolved)

        if task_type:
            stmt = stmt.where(BackgroundTaskFailure.task_type == task_type)

        # Order by most recent first
        stmt = stmt.order_by(BackgroundTaskFailure.created_at.desc())

        # Limit results
        failures = db.execute(stmt.limit(limit)).scalars().all()

        # Get summary statistics
        total_failures = db.execute(
            select(func.count()).select_from(BackgroundTaskFailure)
        ).scalar()
        unresolved_failures = db.execute(
            select(func.count())
            .select_from(BackgroundTaskFailure)
            .where(BackgroundTaskFailure.resolved == False)
        ).scalar()

        # Get failure counts by task type
        task_type_counts = db.execute(
            select(
                BackgroundTaskFailure.task_type,
                func.count(BackgroundTaskFailure.id).label("count"),
            )
            .where(BackgroundTaskFailure.resolved == False)
            .group_by(BackgroundTaskFailure.task_type)
        ).all()

        return {
            "total_failures": total_failures,
            "unresolved_failures": unresolved_failures,
            "task_type_counts": {
                task_type: count for task_type, count in task_type_counts
            },
            "failures": [
                {
                    "id": f.id,
                    "task_type": f.task_type,
                    "game_id": f.game_id,
                    "error_message": f.error_message,
                    "error_type": f.error_type,
                    "retry_count": f.retry_count,
                    "url": f.url,
                    "resolved": f.resolved,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                    "resolved_at": (
                        f.resolved_at.isoformat() if f.resolved_at else None
                    ),
                }
                for f in failures
            ],
        }

    except Exception as e:
        logger.error(f"Failed to get background task failures: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve background task failures: {str(e)}",
        )


@router.post("/monitoring/background-failures/{failure_id}/resolve")
async def resolve_background_failure(
    request: Request,
    failure_id: int = Path(..., description="ID of the failure to resolve"),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_auth),
):
    """
    Mark a background task failure as resolved.
    Sprint 5: Error Handling & Monitoring
    """
    from models import BackgroundTaskFailure
    from datetime import datetime, timezone

    try:
        failure = db.execute(
            select(BackgroundTaskFailure).where(
                BackgroundTaskFailure.id == failure_id
            )
        ).scalar_one_or_none()

        if not failure:
            raise HTTPException(status_code=404, detail="Failure record not found")

        failure.resolved = True
        failure.resolved_at = datetime.now(timezone.utc)

        db.commit()

        logger.info(f"Marked background failure {failure_id} as resolved")

        return {
            "success": True,
            "message": f"Background failure {failure_id} marked as resolved",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve background failure: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resolve background failure: {str(e)}",
        )


@router.get("/monitoring/circuit-breaker-status")
async def get_circuit_breaker_status(
    request: Request,
    _: None = Depends(require_admin_auth),
):
    """
    Get BGG circuit breaker status for monitoring.
    Sprint 5: Error Handling & Monitoring

    Returns:
    - Circuit breaker state (closed, open, half_open)
    - Failure count
    - Last failure time
    """
    from bgg_service import bgg_circuit_breaker, _is_bgg_available

    try:
        state = bgg_circuit_breaker.current_state

        return {
            "circuit_breaker": "BGG API",
            "state": state,
            "is_available": _is_bgg_available(),
            "failure_count": bgg_circuit_breaker.fail_counter,
            "description": {
                "closed": "Service is healthy and accepting requests",
                "open": "Service is down, requests are failing fast",
                "half_open": "Service is recovering, testing with limited requests",
            }.get(state, "Unknown state"),
        }

    except Exception as e:
        logger.error(f"Failed to get circuit breaker status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve circuit breaker status: {str(e)}",
        )
