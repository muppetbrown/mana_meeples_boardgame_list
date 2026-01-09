# api/routers/printing.py
"""
Printing API endpoints for generating PDF game labels.
"""
import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.dependencies import require_admin_auth
from database import get_db
from models import Game
import schemas
from services.label_generator import LabelGenerator

logger = logging.getLogger(__name__)

# Create router with prefix and tags
router = APIRouter(prefix="/api/admin", tags=["printing"])


@router.post("/print-labels")
async def generate_labels(
    request: schemas.PrintLabelsRequest,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin_auth),
):
    """
    Generate PDF labels for selected games.

    Args:
        request: Contains list of game IDs to generate labels for
        db: Database session
        _admin: Admin authentication (dependency)

    Returns:
        StreamingResponse with PDF file

    Raises:
        HTTPException 404: If any game IDs are not found
        HTTPException 500: If PDF generation fails
    """
    try:
        logger.info(f"Generating labels for {len(request.game_ids)} games")

        # Query games from database
        stmt = select(Game).where(Game.id.in_(request.game_ids))
        games = db.execute(stmt).scalars().all()

        # Check if all games were found
        if len(games) != len(request.game_ids):
            found_ids = {game.id for game in games}
            missing_ids = set(request.game_ids) - found_ids
            logger.warning(f"Games not found: {missing_ids}")
            raise HTTPException(
                status_code=404,
                detail=f"Games not found: {list(missing_ids)}"
            )

        # Convert Game models to dictionaries
        game_dicts = []
        for game in games:
            game_dict = {
                'id': game.id,
                'title': game.title,
                'year': game.year,
                'players_min': game.players_min,
                'players_max': game.players_max,
                'playtime_min': game.playtime_min,
                'playtime_max': game.playtime_max,
                'min_age': game.min_age,
                'complexity': game.complexity,
                'game_type': game.game_type,
                'is_cooperative': game.is_cooperative,
                'mana_meeple_category': game.mana_meeple_category,
            }
            game_dicts.append(game_dict)

        # Generate PDF
        generator = LabelGenerator()
        pdf_buffer = generator.generate_pdf(game_dicts)

        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"board-game-labels-{timestamp}.pdf"

        logger.info(f"Successfully generated labels PDF: {filename}")

        # Return PDF as streaming response
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        logger.error(f"Error generating labels: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate labels: {str(e)}"
        )
