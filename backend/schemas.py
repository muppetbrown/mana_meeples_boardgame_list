from pydantic import BaseModel, field_validator, ConfigDict, Field, model_validator
from typing import List, Optional, Any
from datetime import datetime
import json


class Range(BaseModel):
    min: Optional[int] = None
    max: Optional[int] = None


class GameOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")

    id: int
    title: str
    categories: List[str]
    year: Optional[int] = None
    players_min: Optional[int] = None
    players_max: Optional[int] = None
    playtime_min: Optional[int] = None
    playtime_max: Optional[int] = None
    thumbnail_url: Optional[str] = None
    game_type: Optional[str] = None


class AdminLogin(BaseModel):
    token: str

    @field_validator("token")
    @classmethod
    def validate_token(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError("Token must be at least 10 characters")
        return v.strip()


class FixSequenceRequest(BaseModel):
    """Schema for fix-sequence endpoint validation"""

    table_name: str = "boardgames"

    @field_validator("table_name")
    @classmethod
    def validate_table_name(cls, v):
        # Whitelist allowed tables to prevent SQL injection
        allowed_tables = {
            "boardgames",
            "buy_list_games",
            "sleeves"
        }
        if v not in allowed_tables:
            raise ValueError(f"Invalid table name. Allowed: {', '.join(allowed_tables)}")
        # Additional safety: ensure only alphanumeric and underscore
        if not v.replace("_", "").isalnum():
            raise ValueError("Table name contains invalid characters")
        return v


# ------------------------------------------------------------------------------
# Printing Schemas
# ------------------------------------------------------------------------------


class PrintLabelsRequest(BaseModel):
    """Schema for generating game labels"""

    game_ids: List[int] = Field(..., min_length=1, max_length=100)

    @field_validator("game_ids")
    @classmethod
    def validate_game_ids(cls, v):
        if not v:
            raise ValueError("At least one game ID required")
        if len(v) > 100:
            raise ValueError("Maximum 100 games per request")
        if any(game_id <= 0 for game_id in v):
            raise ValueError("All game IDs must be positive integers")
        return v


# ------------------------------------------------------------------------------
# Buy List Schemas
# ------------------------------------------------------------------------------


class BuyListGameCreate(BaseModel):
    """Schema for adding a game to the 'games to add' list by BGG ID"""

    bgg_id: int
    rank: Optional[int] = None
    notes: Optional[str] = None

    @field_validator("bgg_id")
    @classmethod
    def validate_bgg_id(cls, v):
        if v <= 0 or v > 999999:
            raise ValueError("BGG ID must be between 1 and 999999")
        return v


class BuyListGameUpdate(BaseModel):
    """Schema for updating a 'games to add' entry"""

    rank: Optional[int] = None
    notes: Optional[str] = None
    on_buy_list: Optional[bool] = None


class SuggestGamesRequest(BaseModel):
    """Schema for requesting AI-generated 'games to add' suggestions."""

    count: int = Field(default=6, ge=1, le=12)


class BuyListReorderRequest(BaseModel):
    """Schema for re-ranking 'games to add' entries from a given display order.

    ordered_ids lists buy-list entry IDs in the desired priority order (first
    = highest priority); each one's rank is set to its 1-based position.
    """

    ordered_ids: List[int]

    @field_validator("ordered_ids")
    @classmethod
    def validate_not_empty(cls, v):
        if not v:
            raise ValueError("ordered_ids must not be empty")
        return v


class HLStockSignalLinkRequest(BaseModel):
    """Schema for confirming/correcting the link between an HL Timaru stock
    product and an existing game in this library."""

    game_id: int


# ------------------------------------------------------------------------------
# Phase 1 Performance Optimization Schemas
# ------------------------------------------------------------------------------


class GameListItemResponse(BaseModel):
    """
    Minimal game data for list views - reduces payload size.

    This schema excludes heavy fields like mechanics, publishers,
    and artists to reduce response size for list endpoints.
    Includes description and designers for expanded card preview.
    """

    model_config = ConfigDict(from_attributes=True)

    # Essential fields
    id: int
    title: str
    year: Optional[int] = None

    # Display fields
    thumbnail_url: Optional[str] = None
    image: Optional[str] = None
    cloudinary_url: Optional[str] = None
    image_url: Optional[str] = None  # Alias for frontend compatibility (computed from thumbnail_url/image)

    # Filtering/sorting fields
    players_min: Optional[int] = None
    players_max: Optional[int] = None
    playtime_min: Optional[int] = None
    playtime_max: Optional[int] = None
    average_rating: Optional[float] = None
    complexity: Optional[float] = None
    mana_meeple_category: Optional[str] = None
    nz_designer: Optional[bool] = None

    # Metadata
    bgg_id: Optional[int] = None
    aftergame_game_id: Optional[str] = None
    status: Optional[str] = None

    # Expansion info (minimal)
    is_expansion: Optional[bool] = None
    expansion_type: Optional[str] = None

    # Card preview fields (shown in expanded card state)
    description: Optional[str] = None
    designers: Optional[List[str]] = None

    @field_validator('designers', mode='before')
    @classmethod
    def parse_designers_json(cls, v):
        """Handle JSON field that might come as string"""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return v

    @model_validator(mode='before')
    @classmethod
    def add_image_url_alias(cls, data: Any) -> Any:
        """Add image_url as an alias for frontend compatibility

        IMPORTANT: Always use original BGG URL (image > thumbnail_url), NOT cloudinary_url
        The cloudinary_url is only used internally by the backend image proxy endpoint.
        Sending cloudinary_url to the frontend would cause a double-proxy loop.
        """
        # If data is a SQLAlchemy model object
        if hasattr(data, '__dict__'):
            # Use main image field (Cloudinary handles all resizing)
            # NOT cloudinary_url to avoid double-proxy
            image = getattr(data, 'image', None)

            # Compute image_url field - use original BGG URL only
            image_url = image
            data.image_url = image_url

        return data


class GameDetailResponse(BaseModel):
    """
    Full game data for detail views - includes all fields.

    This schema is used when fetching a single game's details,
    where we want comprehensive information.
    """

    model_config = ConfigDict(from_attributes=True)

    # All fields from GameListItemResponse
    id: int
    title: str
    year: Optional[int] = None
    thumbnail_url: Optional[str] = None
    image: Optional[str] = None
    cloudinary_url: Optional[str] = None
    image_url: Optional[str] = None  # Alias for frontend compatibility
    players_min: Optional[int] = None
    players_max: Optional[int] = None
    average_rating: Optional[float] = None
    complexity: Optional[float] = None
    mana_meeple_category: Optional[str] = None
    nz_designer: Optional[bool] = None
    bgg_id: Optional[int] = None
    aftergame_game_id: Optional[str] = None
    status: Optional[str] = None

    # Additional detail fields
    description: Optional[str] = None
    designers: Optional[List[str]] = None
    publishers: Optional[List[str]] = None
    mechanics: Optional[List[str]] = None
    artists: Optional[List[str]] = None
    categories: Optional[str] = None

    playtime_min: Optional[int] = None
    playtime_max: Optional[int] = None
    min_age: Optional[int] = None

    bgg_rank: Optional[int] = None
    users_rated: Optional[int] = None
    is_cooperative: Optional[bool] = None
    game_type: Optional[str] = None

    # Expansion data
    is_expansion: Optional[bool] = None
    expansion_type: Optional[str] = None
    base_game_id: Optional[int] = None
    expansions: List['GameListItemResponse'] = Field(default_factory=list)
    base_game: Optional[dict] = None

    # Player count modifications (for expansions)
    modifies_players_min: Optional[int] = None
    modifies_players_max: Optional[int] = None

    # Computed player counts with expansions (calculated from expansions relationship)
    players_min_with_expansions: Optional[int] = None
    players_max_with_expansions: Optional[int] = None
    has_player_expansion: Optional[bool] = None

    # Sleeve data
    has_sleeves: Optional[str] = None
    fully_sleeved: Optional[bool] = None

    # Metadata (Pydantic automatically serializes datetime to ISO format)
    date_added: Optional[datetime] = None
    created_at: Optional[datetime] = None

    @field_validator('designers', 'publishers', 'mechanics', 'artists', mode='before')
    @classmethod
    def parse_json_field(cls, v):
        """Handle JSON fields that might come as strings from SQLite"""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return v

    @field_validator('base_game', mode='before')
    @classmethod
    def serialize_base_game(cls, v):
        """Serialize base_game object to dict"""
        if v is None:
            return None
        if hasattr(v, '__dict__'):
            return {
                'id': v.id,
                'title': v.title,
                'image_url': getattr(v, 'image', None),  # Use main image field
            }
        return v

    @field_validator('expansions', mode='before')
    @classmethod
    def ensure_expansions_list(cls, v):
        """Ensure expansions is always a list (empty if none)"""
        if v is None:
            return []
        return v

    @model_validator(mode='before')
    @classmethod
    def calculate_expansion_player_counts(cls, data: Any) -> Any:
        """
        Calculate player count ranges with expansions.

        This runs before validation and calculates three fields based on the game's expansions:
        - players_min_with_expansions: Minimum player count across all expansions
        - players_max_with_expansions: Maximum player count across all expansions
        - has_player_expansion: True if any expansion modifies player counts
        """
        # If data is a SQLAlchemy model object (has expansions attribute)
        if hasattr(data, 'expansions'):
            expansions = getattr(data, 'expansions', [])

            min_players = None
            max_players = None
            has_modification = False

            # Check each expansion for player count modifications
            for expansion in expansions:
                exp_min = getattr(expansion, 'modifies_players_min', None)
                exp_max = getattr(expansion, 'modifies_players_max', None)

                if exp_min is not None:
                    min_players = exp_min if min_players is None else min(min_players, exp_min)
                    has_modification = True
                if exp_max is not None:
                    max_players = exp_max if max_players is None else max(max_players, exp_max)
                    has_modification = True

            # Store computed values on the object so they get picked up during validation
            # Use setattr if possible, otherwise we'll handle in dict form
            if hasattr(data, '__dict__'):
                data.players_min_with_expansions = min_players
                data.players_max_with_expansions = max_players
                data.has_player_expansion = has_modification

        # Also add image_url alias for frontend compatibility
        # IMPORTANT: Use original BGG URL only (NOT cloudinary_url to avoid double-proxy)
        if hasattr(data, '__dict__'):
            # Use main image field (Cloudinary handles all resizing)
            image = getattr(data, 'image', None)

            # Compute image_url field - use original BGG URL only
            data.image_url = image

        return data

# Update forward references for circular dependency
GameDetailResponse.model_rebuild()
