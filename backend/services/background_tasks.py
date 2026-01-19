# services/background_tasks.py
"""
Background task functions for async operations.
These are wrappers around service methods designed for FastAPI BackgroundTasks.
"""
import asyncio
import logging
from typing import Optional

from bgg_service import fetch_bgg_thing
from database import SessionLocal
from models import Game
from services.game_service import GameService
from services.image_service import ImageService

logger = logging.getLogger(__name__)


async def download_and_update_thumbnail(game_id: int, thumbnail_url: str):
    """
    DEPRECATED: Background task to download and update game thumbnail.
    
    This function is deprecated. Cloudinary now handles all image resizing on-demand.
    Local thumbnail caching is no longer needed.
    
    Wrapper around ImageService.download_and_update_game_thumbnail.

    Args:
        game_id: Database ID of the game
        thumbnail_url: URL of the thumbnail to download
    """
    logger.warning(
        "download_and_update_thumbnail is deprecated. "
        "Cloudinary handles all image resizing on-demand."
    )
    try:
        db = SessionLocal()
        image_service = ImageService(db)

        success = await image_service.download_and_update_game_thumbnail(
            game_id, thumbnail_url
        )

        if success:
            logger.info(f"Successfully downloaded thumbnail for game {game_id}")
        else:
            logger.warning(f"Failed to download thumbnail for game {game_id}")

    except Exception as e:
        logger.error(f"Error in background thumbnail download for game {game_id}: {e}")
    finally:
        db.close()


async def reimport_single_game(game_id: int, bgg_id: int, delay_seconds: float = 0):
    """
    Background task to re-import a single game with enhanced data from BGG.

    Args:
        game_id: Database ID of the game
        bgg_id: BoardGameGeek ID
        delay_seconds: Initial delay before processing (for rate limiting)
    """
    try:
        # Add delay to avoid overwhelming BGG API
        if delay_seconds > 0:
            await asyncio.sleep(delay_seconds)

        db = SessionLocal()
        game = db.get(Game, game_id)
        if not game:
            logger.warning(f"Game {game_id} not found for reimport")
            return

        # Fetch enhanced data from BGG
        bgg_data = await fetch_bgg_thing(bgg_id)

        # Use GameService to update from BGG data
        game_service = GameService(db)
        game_service.update_game_from_bgg_data(game, bgg_data, commit=True)

        logger.info(f"Re-imported game {game_id}: {game.title}")

    except Exception as e:
        logger.error(f"Failed to reimport game {game_id}: {e}")
    finally:
        db.close()
