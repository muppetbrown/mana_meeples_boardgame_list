# api/routers/bulk.py
"""
Bulk operations API endpoints for admin tasks.
Includes CSV-based import, categorization, and batch updates.
"""
import logging

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
)
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from api.dependencies import require_admin_auth
from bgg_service import fetch_bgg_thing
from database import get_db, SessionLocal
from models import Game, Sleeve
from utils.helpers import CATEGORY_KEYS, categorize_game, parse_categories

logger = logging.getLogger(__name__)

# Import background task from main - TODO: move to services
from main import (  # noqa: E402
    _download_and_update_thumbnail,
    _reimport_single_game,
)

# Create router with prefix and tags
router = APIRouter(prefix="/api/admin", tags=["bulk-operations"])


async def _fetch_sleeve_data_task(game_id: int, bgg_id: int, game_title: str):
    """Background task to fetch sleeve data for a single game"""
    from services.sleeve_scraper import scrape_sleeve_data

    try:
        db = SessionLocal()
        game = db.get(Game, game_id)
        if not game:
            logger.warning(f"Game {game_id} not found for sleeve fetch")
            return

        # Fetch sleeve data from BGG
        logger.info(f"Fetching sleeve data for '{game_title}' (BGG ID: {bgg_id})")
        sleeve_data = scrape_sleeve_data(bgg_id, game_title)

        if not sleeve_data:
            logger.warning(f"No sleeve data returned for {game_title}")
            return

        # Update has_sleeves status
        game.has_sleeves = sleeve_data.get('status', 'not_found')

        # Delete existing sleeve records
        db.execute(delete(Sleeve).where(Sleeve.game_id == game.id))

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
            logger.info(f"Saved {len(sleeve_data['card_types'])} sleeve types for {game_title}")
        else:
            db.commit()
            logger.info(f"No sleeve data found for {game_title} (status: {sleeve_data.get('status')})")

    except Exception as e:
        logger.error(f"Failed to fetch sleeve data for game {game_id}: {e}")
    finally:
        db.close()


@router.post("/bulk-import-csv")
async def bulk_import_csv(
    csv_data: dict,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_auth),
):
    """Bulk import games from CSV data (admin only)"""
    try:
        csv_text = csv_data.get("csv_data", "")
        if not csv_text.strip():
            raise HTTPException(status_code=400, detail="No CSV data provided")

        lines = [
            line.strip()
            for line in csv_text.strip().split("\n")
            if line.strip()
        ]
        if not lines:
            raise HTTPException(
                status_code=400, detail="No valid lines in CSV"
            )

        added = []
        skipped = []
        errors = []

        for line_num, line in enumerate(lines, 1):
            try:
                # Expected format: bgg_id,title (title is optional)
                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 1:
                    errors.append(f"Line {line_num}: No BGG ID provided")
                    continue

                # Try to parse BGG ID
                try:
                    bgg_id = int(parts[0])
                except ValueError:
                    errors.append(
                        f"Line {line_num}: Invalid BGG ID '{parts[0]}'"
                    )
                    continue

                # Check if already exists
                existing = db.execute(
                    select(Game).where(Game.bgg_id == bgg_id)
                ).scalar_one_or_none()
                if existing:
                    skipped.append(
                        f"BGG ID {bgg_id}: Already exists as "
                        f"'{existing.title}'"
                    )
                    continue

                # Import from BGG
                try:
                    bgg_data = await fetch_bgg_thing(bgg_id)
                    categories_str = ", ".join(bgg_data.get("categories", []))

                    # Create new game
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
                        mana_meeple_category=categorize_game(categories),
                    )

                    # Add enhanced fields if they exist in the model
                    if hasattr(game, "description"):
                        game.description = bgg_data.get("description")
                    if hasattr(game, "designers"):
                        game.designers = bgg_data.get("designers", [])
                    if hasattr(game, "publishers"):
                        game.publishers = bgg_data.get("publishers", [])
                    if hasattr(game, "mechanics"):
                        game.mechanics = bgg_data.get("mechanics", [])
                    if hasattr(game, "artists"):
                        game.artists = bgg_data.get("artists", [])
                    if hasattr(game, "average_rating"):
                        game.average_rating = bgg_data.get("average_rating")
                    if hasattr(game, "complexity"):
                        game.complexity = bgg_data.get("complexity")
                    if hasattr(game, "bgg_rank"):
                        game.bgg_rank = bgg_data.get("bgg_rank")
                    if hasattr(game, "users_rated"):
                        game.users_rated = bgg_data.get("users_rated")
                    if hasattr(game, "min_age"):
                        game.min_age = bgg_data.get("min_age")
                    if hasattr(game, "is_cooperative"):
                        game.is_cooperative = bgg_data.get("is_cooperative")
                    if hasattr(game, "game_type"):
                        game.game_type = bgg_data.get("game_type")
                    if hasattr(game, "image"):
                        # Store the full-size image URL
                        game.image = bgg_data.get("image")
                    if hasattr(game, "thumbnail_url"):
                        # Store the thumbnail URL separately
                        game.thumbnail_url = bgg_data.get("thumbnail")

                    db.add(game)
                    db.commit()
                    db.refresh(game)

                    added.append(f"BGG ID {bgg_id}: {game.title}")

                    # Download thumbnail in background
                    # Prioritize image over thumbnail
                    thumbnail_url = bgg_data.get("image") or bgg_data.get(
                        "thumbnail"
                    )
                    if thumbnail_url and background_tasks:
                        background_tasks.add_task(
                            _download_and_update_thumbnail,
                            game.id,
                            thumbnail_url,
                        )

                except Exception as e:
                    db.rollback()
                    errors.append(
                        f"Line {line_num}: Failed to import BGG ID "
                        f"{bgg_id} - {str(e)}"
                    )

            except Exception as e:
                errors.append(f"Line {line_num}: {str(e)}")

        return {
            "message": f"Processed {len(lines)} lines",
            "added": added,
            "skipped": skipped,
            "errors": errors,
        }

    except Exception as e:
        logger.error(f"Bulk import failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Bulk import failed: {str(e)}"
        )


@router.post("/bulk-categorize-csv")
async def bulk_categorize_csv(
    csv_data: dict,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_auth),
):
    """Bulk categorize existing games from CSV data (admin only)"""
    try:
        csv_text = csv_data.get("csv_data", "")
        if not csv_text.strip():
            raise HTTPException(status_code=400, detail="No CSV data provided")

        lines = [
            line.strip()
            for line in csv_text.strip().split("\n")
            if line.strip()
        ]
        if not lines:
            raise HTTPException(
                status_code=400, detail="No valid lines in CSV"
            )

        updated = []
        not_found = []
        errors = []

        for line_num, line in enumerate(lines, 1):
            try:
                # Expected format: bgg_id,category[,title]
                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 2:
                    errors.append(
                        f"Line {line_num}: Must have at least "
                        f"bgg_id,category"
                    )
                    continue

                # Parse BGG ID
                try:
                    bgg_id = int(parts[0])
                except ValueError:
                    errors.append(
                        f"Line {line_num}: Invalid BGG ID '{parts[0]}'"
                    )
                    continue

                category = parts[1].strip()

                # Validate category (accept both keys and labels)
                category_key = None
                if category in CATEGORY_KEYS:
                    category_key = category
                else:
                    # Try to find by label (for backwards compatibility)
                    # This assumes CATEGORY_LABELS is available
                    try:
                        from constants.categories import (  # noqa: E402
                            CATEGORY_LABELS,
                        )

                        for key, label in CATEGORY_LABELS.items():
                            if label.lower() == category.lower():
                                category_key = key
                                break
                    except ImportError:
                        pass

                if not category_key:
                    errors.append(
                        f"Line {line_num}: Invalid category '{category}'. "
                        f"Use: {', '.join(CATEGORY_KEYS)}"
                    )
                    continue

                # Find and update game
                game = db.execute(
                    select(Game).where(Game.bgg_id == bgg_id)
                ).scalar_one_or_none()
                if not game:
                    not_found.append(f"BGG ID {bgg_id}: Game not found")
                    continue

                old_category = game.mana_meeple_category
                game.mana_meeple_category = category_key
                db.add(game)

                updated.append(
                    f"BGG ID {bgg_id} ({game.title}): "
                    f"{old_category or 'None'} → {category_key}"
                )

            except Exception as e:
                errors.append(f"Line {line_num}: {str(e)}")

        db.commit()

        return {
            "message": f"Processed {len(lines)} lines",
            "updated": updated,
            "not_found": not_found,
            "errors": errors,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Bulk categorize failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Bulk categorize failed: {str(e)}"
        )


@router.post("/reimport-all-games")
async def reimport_all_games(
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_auth),
):
    """Re-import all existing games to get enhanced BGG data"""
    games = (
        db.execute(select(Game).where(Game.bgg_id.isnot(None))).scalars().all()
    )

    for game in games:
        background_tasks.add_task(_reimport_single_game, game.id, game.bgg_id)

    return {
        "message": (
            f"Started re-importing {len(games)} games with enhanced data"
        )
    }


@router.post("/fetch-all-sleeve-data")
async def fetch_all_sleeve_data(
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_auth),
):
    """
    Trigger GitHub Action to fetch sleeve data for all games

    This triggers the GitHub workflow 'fetch_sleeves.yml' which runs the scraper
    with Chrome installed in the GitHub Actions environment.
    """
    import os
    import httpx

    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        raise HTTPException(
            status_code=500,
            detail="GITHUB_TOKEN not configured. Cannot trigger GitHub Action."
        )

    # Get total games for response
    games = list(
        db.execute(select(Game).where(Game.bgg_id.isnot(None))).scalars().all()
    )
    total_games = len(games)

    # Trigger GitHub workflow
    github_api_url = "https://api.github.com/repos/muppetbrown/mana_meeples_boardgame_list/actions/workflows/fetch_sleeves.yml/dispatches"

    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    payload = {
        "ref": "main"  # or "master" depending on your default branch
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(github_api_url, json=payload, headers=headers)

        if response.status_code == 204:
            return {
                "message": f"Triggered GitHub Action to fetch sleeve data for {total_games} games",
                "total_games": total_games,
                "note": "Check GitHub Actions tab for progress. Results will be committed when complete."
            }
        else:
            logger.error(f"GitHub API error: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to trigger GitHub Action: {response.status_code}"
            )
    except Exception as e:
        logger.error(f"Failed to trigger GitHub Action: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger GitHub Action: {str(e)}"
        )


@router.post("/bulk-update-nz-designers")
async def bulk_update_nz_designers(
    csv_data: dict,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_auth),
):
    """Bulk update NZ designer status from CSV (admin only)"""
    try:
        csv_text = csv_data.get("csv_data", "")
        if not csv_text.strip():
            raise HTTPException(status_code=400, detail="No CSV data provided")

        lines = [
            line.strip()
            for line in csv_text.strip().split("\n")
            if line.strip()
        ]
        updated = []
        not_found = []
        errors = []

        for line_num, line in enumerate(lines, 1):
            try:
                # Expected format: bgg_id,true/false or
                # game_title,true/false
                parts = [p.strip() for p in line.split(",")]
                if len(parts) != 2:
                    errors.append(
                        f"Line {line_num}: Must have format "
                        f"'identifier,true/false'"
                    )
                    continue

                identifier = parts[0]
                nz_status = parts[1].lower() in ["true", "1", "yes", "y"]

                # Try to find by BGG ID first, then by title
                game = None
                try:
                    bgg_id = int(identifier)
                    game = db.execute(
                        select(Game).where(Game.bgg_id == bgg_id)
                    ).scalar_one_or_none()
                except ValueError:
                    # Not a number, try by title
                    game = db.execute(
                        select(Game).where(Game.title.ilike(f"%{identifier}%"))
                    ).scalar_one_or_none()

                if not game:
                    not_found.append(f"'{identifier}': Game not found")
                    continue

                old_status = game.nz_designer
                game.nz_designer = nz_status
                db.add(game)

                updated.append(f"{game.title}: {old_status} → {nz_status}")

            except Exception as e:
                errors.append(f"Line {line_num}: {str(e)}")

        db.commit()

        return {
            "message": f"Processed {len(lines)} lines",
            "updated": updated,
            "not_found": not_found,
            "errors": errors,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Bulk NZ designer update failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Bulk update failed: {str(e)}"
        )


@router.post("/bulk-update-aftergame-ids")
async def bulk_update_aftergame_ids(
    csv_data: dict,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_auth),
):
    """Bulk update AfterGame game IDs from CSV (admin only)"""
    try:
        csv_text = csv_data.get("csv_data", "")
        if not csv_text.strip():
            raise HTTPException(status_code=400, detail="No CSV data provided")

        lines = [
            line.strip()
            for line in csv_text.strip().split("\n")
            if line.strip()
        ]
        updated = []
        not_found = []
        errors = []

        for line_num, line in enumerate(lines, 1):
            try:
                # Expected format: bgg_id,aftergame_game_id[,title]
                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 2:
                    errors.append(
                        f"Line {line_num}: Must have at least "
                        f"bgg_id,aftergame_game_id"
                    )
                    continue

                # Parse BGG ID
                try:
                    bgg_id = int(parts[0])
                except ValueError:
                    errors.append(
                        f"Line {line_num}: Invalid BGG ID '{parts[0]}'"
                    )
                    continue

                aftergame_id = parts[1].strip() if parts[1].strip() else None

                # Basic UUID validation (optional but recommended)
                if aftergame_id and len(aftergame_id) != 36:
                    logger.warning(
                        f"Line {line_num}: AfterGame ID '{aftergame_id}' "
                        f"doesn't match expected UUID format (36 chars)"
                    )

                # Find and update game
                game = db.execute(
                    select(Game).where(Game.bgg_id == bgg_id)
                ).scalar_one_or_none()
                if not game:
                    not_found.append(f"BGG ID {bgg_id}: Game not found")
                    continue

                old_aftergame_id = game.aftergame_game_id
                game.aftergame_game_id = aftergame_id
                db.add(game)

                updated.append(
                    f"BGG ID {bgg_id} ({game.title}): "
                    f"{old_aftergame_id or 'None'} → {aftergame_id or 'None'}"
                )

            except Exception as e:
                errors.append(f"Line {line_num}: {str(e)}")

        db.commit()

        return {
            "message": f"Processed {len(lines)} lines",
            "updated": updated,
            "not_found": not_found,
            "errors": errors,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Bulk AfterGame ID update failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Bulk AfterGame ID update failed: {str(e)}"
        )
