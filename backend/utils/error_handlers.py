# utils/error_handlers.py
"""
Centralized error handling utilities for API endpoints.
Converts database and validation errors into user-friendly HTTP exceptions.
"""
from typing import Dict
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError


def handle_integrity_error(e: IntegrityError) -> HTTPException:
    """
    Convert SQLAlchemy IntegrityError to user-friendly HTTPException.

    Extracts constraint names from PostgreSQL error messages and maps them
    to human-readable error messages.

    Args:
        e: SQLAlchemy IntegrityError exception

    Returns:
        HTTPException with appropriate status code and user-friendly message

    Example:
        try:
            db.add(game)
            db.commit()
        except IntegrityError as e:
            raise handle_integrity_error(e)
    """
    error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)

    # Map constraint names to user-friendly error messages
    constraint_messages: Dict[str, str] = {
        # Player count constraints
        "players_max_gte_min": "Maximum players must be greater than or equal to minimum players",
        "valid_min_players": "Minimum players must be at least 1",

        # Playtime constraints
        "playtime_max_gte_min": "Maximum playtime must be greater than or equal to minimum playtime",
        "valid_playtime_min": "Playtime must be greater than 0",

        # Year constraints
        "valid_year": "Year must be between 1900 and 2100",

        # Rating constraints
        "valid_rating": "Rating must be between 0 and 10",
        "valid_complexity": "Complexity must be between 1 and 5",

        # Age constraints
        "valid_min_age": "Minimum age must be between 0 and 100",

        # Status constraints
        "valid_status": "Status must be one of: OWNED, BUY_LIST, WISHLIST",

        # Unique constraints
        "boardgames_bgg_id_key": "A game with this BoardGameGeek ID already exists",
        "buy_list_games_game_id_key": "This game is already on the buy list",

        # Foreign key constraints
        "boardgames_base_game_id_fkey": "Referenced base game does not exist",
    }

    # Check each constraint pattern
    for constraint, message in constraint_messages.items():
        if constraint in error_msg:
            return HTTPException(status_code=400, detail=message)

    # Generic constraint violation if no specific match
    # Don't expose internal database details to users
    return HTTPException(
        status_code=400,
        detail="Data validation failed. Please check your input and try again."
    )


def handle_validation_error(e: Exception) -> HTTPException:
    """
    Convert validation errors (ValueError, ValidationError) to HTTPException.

    Args:
        e: Validation exception (ValueError, ValidationError, etc.)

    Returns:
        HTTPException with 422 status code and error message

    Example:
        try:
            if year < 1900:
                raise ValueError("Year too old")
        except ValueError as e:
            raise handle_validation_error(e)
    """
    return HTTPException(status_code=422, detail=str(e))


def handle_not_found_error(resource_type: str, resource_id: any) -> HTTPException:
    """
    Create a consistent 404 HTTPException for missing resources.

    Args:
        resource_type: Type of resource (e.g., "Game", "User")
        resource_id: ID of the missing resource

    Returns:
        HTTPException with 404 status code

    Example:
        if not game:
            raise handle_not_found_error("Game", game_id)
    """
    return HTTPException(
        status_code=404,
        detail=f"{resource_type} with ID {resource_id} not found"
    )


def handle_generic_error(e: Exception, operation: str) -> HTTPException:
    """
    Convert generic exceptions to HTTPException with logging.

    Use this for unexpected errors that should be logged and reported to Sentry.

    Args:
        e: The exception that occurred
        operation: Description of the operation that failed (for logging)

    Returns:
        HTTPException with 500 status code and generic message

    Example:
        try:
            complex_operation()
        except Exception as e:
            logger.error(f"Failed to do thing: {e}", exc_info=True)
            raise handle_generic_error(e, "complex operation")
    """
    import logging
    logger = logging.getLogger(__name__)

    # Log the error with full stack trace
    logger.error(f"Failed to {operation}: {e}", exc_info=True)

    # Don't expose internal error details to users
    return HTTPException(
        status_code=500,
        detail=f"An error occurred while processing your request. Please try again later."
    )
