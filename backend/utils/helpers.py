# utils/helpers.py
"""
Shared helper functions for game processing, categorization,
and response formatting.
"""
import json
import logging
from datetime import datetime
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


def parse_categories(raw_categories) -> List[str]:
    """Parse categories from various formats into a clean list"""
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


def parse_json_field(field_value) -> List[str]:
    """Parse JSON field (designers, publishers, mechanics, etc.) into a list"""
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
    """Automatically categorize a game based on its BGG categories"""
    if not categories:
        return None

    # Normalize categories for comparison
    normalized_cats = [cat.lower().strip() for cat in categories]
    category_text = " ".join(normalized_cats)

    # Score each category based on keyword matches
    scores = {}
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
    """Convert relative URLs to absolute URLs"""
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url

    base = str(request.base_url).rstrip("/")
    return f"{base}{url}"


def game_to_dict(request: Request, game: Game) -> Dict[str, Any]:
    """Convert game model to dictionary for API response"""
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
        "nz_designer": getattr(game, "nz_designer", False),
        "game_type": getattr(game, "game_type", None),
    }


def calculate_category_counts(games) -> Dict[str, int]:
    """Calculate counts for each category"""
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
    """Standardized success response format"""
    response = {
        "success": True,
        "message": message,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    if data is not None:
        response["data"] = data
    return response


def error_response(
    message: str, error_code: str = "GENERAL_ERROR", details: Any = None
) -> Dict[str, Any]:
    """Standardized error response format"""
    response = {
        "success": False,
        "error": {"code": error_code, "message": message},
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    if details is not None:
        response["error"]["details"] = details
    return response
