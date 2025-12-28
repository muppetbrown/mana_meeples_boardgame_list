# utils/helpers.py
"""
Shared helper functions for game processing, categorization,
and response formatting.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import Request
from models import Game

logger = logging.getLogger(__name__)

# Category constants
CATEGORY_KEYS = [
    "COOP_ADVENTURE",
    "CORE_STRATEGY",
    "GATEWAY_STRATEGY",
    "KIDS_FAMILIES",
    "PARTY_ICEBREAKERS",
]

# Category mapping for auto-categorization
CATEGORY_MAPPING = {
    "COOP_ADVENTURE": {
        "keywords": [
            "cooperative",
            "coop",
            "co-op",
            "adventure",
            "narrative",
            "campaign",
            "story",
            "quest",
            "exploration",
            "dungeon",
            "rpg",
            "legacy",
        ],
        "exact_matches": [
            "cooperative game",
            "adventure",
            "narrative choice",
            "campaign game",
            "exploration",
            "storytelling",
        ],
    },
    "CORE_STRATEGY": {
        "keywords": [
            "wargame",
            "war",
            "strategy",
            "civilization",
            "economic",
            "engine",
            "building",
            "area control",
            "area majority",
            "influence",
            "deck building",
            "bag building",
            "heavy",
            "complex",
        ],
        "exact_matches": [
            "wargame",
            "area majority / influence",
            "deck, bag, and pool building",
            "engine building",
            "civilization",
            "area control",
            "economic",
        ],
    },
    "GATEWAY_STRATEGY": {
        "keywords": [
            "abstract",
            "tile placement",
            "pattern",
            "family",
            "gateway",
            "light strategy",
            "animals",
            "environmental",
            "nature",
        ],
        "exact_matches": [
            "abstract strategy",
            "animals",
            "environmental",
            "family game",
            "tile placement",
            "pattern building",
        ],
    },
    "KIDS_FAMILIES": {
        "keywords": [
            "children",
            "kids",
            "family",
            "educational",
            "learning",
            "memory",
            "dexterity",
            "simple",
            "young",
        ],
        "exact_matches": [
            "children's game",
            "educational",
            "memory",
            "dexterity",
            "family game",
        ],
    },
    "PARTY_ICEBREAKERS": {
        "keywords": [
            "party",
            "social",
            "deduction",
            "humor",
            "funny",
            "word",
            "trivia",
            "communication",
            "bluffing",
            "guessing",
            "ice breaker",
        ],
        "exact_matches": [
            "party game",
            "humor",
            "social deduction",
            "word game",
            "bluffing",
            "communication",
        ],
    },
}


def parse_categories(raw_categories: Optional[Any]) -> List[str]:
    """
    Parse categories from various formats into a clean list.

    Handles multiple input formats:
    - List of strings
    - JSON array string
    - Comma-separated string

    Args:
        raw_categories: Categories in string, list, or JSON format

    Returns:
        List of category strings (empty list if no valid categories)

    Examples:
        >>> parse_categories("Action, Strategy")
        ['Action', 'Strategy']
        >>> parse_categories(['Action', 'Strategy'])
        ['Action', 'Strategy']
        >>> parse_categories('["Action", "Strategy"]')
        ['Action', 'Strategy']
    """
    if not raw_categories:
        return []

    if isinstance(raw_categories, list):
        return [str(c).strip() for c in raw_categories if str(c).strip()]

    raw_str = str(raw_categories).strip()
    if not raw_str:
        return []

    # Handle JSON array format
    if raw_str.startswith("[") and raw_str.endswith("]"):
        try:
            parsed = json.loads(raw_str)
            return [str(c).strip() for c in parsed if str(c).strip()]
        except json.JSONDecodeError:
            pass

    # Handle comma-separated format
    return [c.strip() for c in raw_str.split(",") if c.strip()]


def parse_json_field(field_value: Optional[Any]) -> List[str]:
    """
    Parse JSON field (designers, publishers, mechanics, etc.) into a list.

    Args:
        field_value: JSON string or list to parse

    Returns:
        List of strings (empty list if parsing fails or no data)

    Examples:
        >>> parse_json_field('["Designer A", "Designer B"]')
        ['Designer A', 'Designer B']
        >>> parse_json_field(['Designer A', 'Designer B'])
        ['Designer A', 'Designer B']
        >>> parse_json_field(None)
        []
    """
    if not field_value:
        return []

    if isinstance(field_value, list):
        return field_value

    try:
        parsed = json.loads(field_value)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def categorize_game(categories: List[str]) -> Optional[str]:
    """
    Automatically categorize a game based on its BGG categories.

    Uses keyword matching and scoring to assign one of the predefined
    Mana & Meeples categories. Exact matches score higher (10 points)
    than keyword matches (1 point each).

    Args:
        categories: List of BGG category strings

    Returns:
        Category key (one of CATEGORY_KEYS) or None if no match

    Examples:
        >>> categorize_game(['cooperative game', 'adventure'])
        'COOP_ADVENTURE'
        >>> categorize_game(['party game', 'humor'])
        'PARTY_ICEBREAKERS'
        >>> categorize_game([])
        None
    """
    if not categories:
        return None

    # Normalize categories for comparison
    normalized_cats = [cat.lower().strip() for cat in categories]
    category_text = " ".join(normalized_cats)

    # Score each category based on keyword matches
    scores: Dict[str, int] = {}
    for category_key, mapping in CATEGORY_MAPPING.items():
        score = 0

        # Check exact matches first (higher weight)
        for exact_match in mapping["exact_matches"]:
            if exact_match.lower() in normalized_cats:
                score += 10

        # Check keyword matches
        for keyword in mapping["keywords"]:
            if keyword in category_text:
                score += 1

        if score > 0:
            scores[category_key] = score

    # Return the category with the highest score
    if scores:
        return max(scores, key=scores.get)

    return None


def make_absolute_url(request: Request, url: Optional[str]) -> Optional[str]:
    """
    Convert relative URLs to absolute URLs using request base URL.

    Args:
        request: FastAPI Request object
        url: URL string (relative or absolute)

    Returns:
        Absolute URL string or None if url is None

    Examples:
        >>> # Assuming request.base_url is "https://example.com"
        >>> make_absolute_url(request, "/thumbs/image.jpg")
        'https://example.com/thumbs/image.jpg'
        >>> make_absolute_url(request, "https://external.com/image.jpg")
        'https://external.com/image.jpg'
    """
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url

    base = str(request.base_url).rstrip("/")
    return f"{base}{url}"


def game_to_dict(request: Request, game: Game) -> Dict[str, Any]:
    """
    Convert game model to dictionary for API response.

    Handles all game fields including optional enhanced data from BGG.
    Provides field aliases for frontend compatibility.
    Prioritizes BGG image URLs over local files (for ephemeral filesystems).

    Args:
        request: FastAPI Request object (for building absolute URLs)
        game: Game model instance

    Returns:
        Dictionary representation of game with all fields

    Note:
        - Image priority: BGG large image > BGG thumbnail > local file
        - Includes field aliases (e.g., year_published, min_players)
        - Handles missing optional fields gracefully with getattr
    """
    categories = parse_categories(game.categories)

    # Parse JSON fields safely
    designers = parse_json_field(getattr(game, "designers", None))
    publishers = parse_json_field(getattr(game, "publishers", None))
    mechanics = parse_json_field(getattr(game, "mechanics", None))
    artists = parse_json_field(getattr(game, "artists", None))

    # Handle thumbnail URL - prioritize BGG URLs over local files (Render has ephemeral filesystem)
    thumbnail_url = None
    if hasattr(game, "image") and game.image:  # Use the larger BGG image first
        thumbnail_url = game.image
    elif (
        hasattr(game, "thumbnail_url") and game.thumbnail_url
    ):  # Fall back to BGG thumbnail
        thumbnail_url = game.thumbnail_url
    elif hasattr(game, "thumbnail_file") and game.thumbnail_file:
        # Only use local files if they're external URLs (not local paths starting with /thumbs/)
        if not game.thumbnail_file.startswith("/thumbs/"):
            thumbnail_url = make_absolute_url(
                request, f"/thumbs/{game.thumbnail_file}"
            )

    return {
        "id": game.id,
        "title": game.title or "",
        "categories": categories,
        "year": game.year,
        "year_published": game.year,  # Alias for frontend
        "players_min": game.players_min,
        "players_max": game.players_max,
        "min_players": game.players_min,  # Alias for frontend
        "max_players": game.players_max,  # Alias for frontend
        "playtime_min": game.playtime_min,
        "playtime_max": game.playtime_max,
        "playing_time": game.playtime_min
        or game.playtime_max,  # Alias for frontend
        "thumbnail_url": thumbnail_url,
        "image_url": thumbnail_url,  # Alias for frontend
        "mana_meeple_category": getattr(game, "mana_meeple_category", None),
        "description": getattr(game, "description", None),
        "designers": designers,
        "publishers": publishers,
        "mechanics": mechanics,
        "artists": artists,
        "average_rating": getattr(game, "average_rating", None),
        "complexity": getattr(game, "complexity", None),
        "bgg_rank": getattr(game, "bgg_rank", None),
        "min_age": getattr(game, "min_age", None),
        "is_cooperative": getattr(game, "is_cooperative", None),
        "users_rated": getattr(game, "users_rated", None),
        "bgg_id": getattr(game, "bgg_id", None),
        "created_at": (
            game.created_at.isoformat()
            if hasattr(game, "created_at") and game.created_at
            else None
        ),
        "date_added": (
            game.date_added.isoformat()
            if hasattr(game, "date_added") and game.date_added
            else None
        ),
        "status": getattr(game, "status", "OWNED"),  # Default to OWNED for backward compatibility
        "nz_designer": getattr(game, "nz_designer", False),
        "game_type": getattr(game, "game_type", None),
        # Expansion fields
        "is_expansion": getattr(game, "is_expansion", False),
        "base_game_id": getattr(game, "base_game_id", None),
        "expansion_type": getattr(game, "expansion_type", None),
        "modifies_players_min": getattr(game, "modifies_players_min", None),
        "modifies_players_max": getattr(game, "modifies_players_max", None),
        # AfterGame integration
        "aftergame_game_id": getattr(game, "aftergame_game_id", None),
    }


def calculate_category_counts(games: Any) -> Dict[str, int]:
    """
    Calculate counts for each category from a list of games.

    Args:
        games: List of Game objects or tuples from select queries
               (supports both ORM objects and raw query results)

    Returns:
        Dictionary mapping category keys to counts, including:
        - "all": Total count
        - CATEGORY_KEYS: Individual category counts
        - "uncategorized": Games without assigned category

    Examples:
        >>> games = [game1, game2, game3]  # Game objects
        >>> counts = calculate_category_counts(games)
        >>> counts['all']
        3
        >>> counts['COOP_ADVENTURE']
        1
    """
    counts = {"all": len(games), "uncategorized": 0}

    # Initialize category counts
    for key in CATEGORY_KEYS:
        counts[key] = 0

    # Count games by category
    for game in games:
        # Handle both Game objects and tuples from select queries
        if hasattr(game, "mana_meeple_category"):
            category = game.mana_meeple_category
        else:
            # Assume it's a tuple (id, mana_meeple_category)
            category = game[1]

        if category and category in CATEGORY_KEYS:
            counts[category] += 1
        else:
            counts["uncategorized"] += 1

    return counts


def success_response(
    data: Any = None, message: str = "Success"
) -> Dict[str, Any]:
    """
    Create a standardized success response format.

    Args:
        data: Response data (optional)
        message: Success message (default: "Success")

    Returns:
        Standardized success response dictionary with:
        - success: True
        - message: Success message
        - timestamp: ISO 8601 timestamp
        - data: Response data (if provided)

    Examples:
        >>> success_response({"id": 123}, "Game created")
        {'success': True, 'message': 'Game created', 'timestamp': '...', 'data': {'id': 123}}
    """
    response = {
        "success": True,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
    }
    if data is not None:
        response["data"] = data
    return response


def error_response(
    message: str, error_code: str = "GENERAL_ERROR", details: Any = None
) -> Dict[str, Any]:
    """
    Create a standardized error response format.

    Args:
        message: Error message
        error_code: Error code string (default: "GENERAL_ERROR")
        details: Additional error details (optional)

    Returns:
        Standardized error response dictionary with:
        - success: False
        - error: Object containing code, message, and optional details
        - timestamp: ISO 8601 timestamp

    Examples:
        >>> error_response("Game not found", "NOT_FOUND", {"game_id": 123})
        {'success': False, 'error': {'code': 'NOT_FOUND', 'message': '...'}, 'timestamp': '...'}
    """
    response = {
        "success": False,
        "error": {"code": error_code, "message": message},
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
    }
    if details is not None:
        response["error"]["details"] = details
    return response
