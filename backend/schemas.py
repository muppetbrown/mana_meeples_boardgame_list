from pydantic import BaseModel, field_validator, ConfigDict, RootModel
from typing import Dict, List, Optional


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


class PagedGames(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[GameOut]


class CategoryCounts(RootModel[Dict[str, int]]):
    root: Dict[str, int]


class BGGGameImport(BaseModel):
    bgg_id: int

    @field_validator("bgg_id")
    @classmethod
    def validate_bgg_id(cls, v):
        if v <= 0 or v > 999999:
            raise ValueError("BGG ID must be between 1 and 999999")
        return v


class CSVImport(BaseModel):
    csv_data: str

    @field_validator("csv_data")
    @classmethod
    def validate_csv_data(cls, v):
        if not v.strip():
            raise ValueError("CSV data cannot be empty")
        return v


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
            "price_snapshots",
            "price_offers",
            "sleeves"
        }
        if v not in allowed_tables:
            raise ValueError(f"Invalid table name. Allowed: {', '.join(allowed_tables)}")
        # Additional safety: ensure only alphanumeric and underscore
        if not v.replace("_", "").isalnum():
            raise ValueError("Table name contains invalid characters")
        return v


# ------------------------------------------------------------------------------
# Buy List Schemas
# ------------------------------------------------------------------------------


class BuyListGameCreate(BaseModel):
    """Schema for adding a game to the buy list by BGG ID"""

    bgg_id: int
    rank: Optional[int] = None
    bgo_link: Optional[str] = None
    lpg_rrp: Optional[float] = None
    lpg_status: Optional[str] = None

    @field_validator("bgg_id")
    @classmethod
    def validate_bgg_id(cls, v):
        if v <= 0 or v > 999999:
            raise ValueError("BGG ID must be between 1 and 999999")
        return v


class BuyListGameUpdate(BaseModel):
    """Schema for updating buy list game details"""

    rank: Optional[int] = None
    bgo_link: Optional[str] = None
    lpg_rrp: Optional[float] = None
    lpg_status: Optional[str] = None
    on_buy_list: Optional[bool] = None


class PriceSnapshotOut(BaseModel):
    """Schema for price snapshot output"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    game_id: int
    checked_at: str
    low_price: Optional[float] = None
    mean_price: Optional[float] = None
    best_price: Optional[float] = None
    best_store: Optional[str] = None
    discount_pct: Optional[float] = None
    delta: Optional[float] = None


class BuyListGameOut(BaseModel):
    """Schema for buy list game output with game details and latest prices"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    game_id: int
    rank: Optional[int] = None
    bgo_link: Optional[str] = None
    lpg_rrp: Optional[float] = None
    lpg_status: Optional[str] = None
    on_buy_list: bool
    created_at: str
    updated_at: str
    # Game details
    title: str
    thumbnail_url: Optional[str] = None
    bgg_id: Optional[int] = None
    # Latest price data
    latest_price: Optional[PriceSnapshotOut] = None
    # Computed field
    buy_filter: Optional[bool] = None
