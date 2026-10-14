# services/background_tasks.py
"""
Background task functions for async operations.
These are wrappers around service methods designed for FastAPI BackgroundTasks.
"""
import asyncio
import logging

from bgg_service import fetch_bgg_thing
import database
SessionLocal = database.SessionLocal  # alias for test patching
from models import Game
from services.game_service import GameService

logger = logging.getLogger(__name__)


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
