from pydantic import BaseModel, validator
from typing import Dict, List, Optional


class Range(BaseModel):
    min: Optional[int] = None
    max: Optional[int] = None


class GameOut(BaseModel):
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

    class Config:
        orm_mode = True
        extra = "allow"


class PagedGames(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[GameOut]


class CategoryCounts(BaseModel):
    __root__: Dict[str, int]


class BGGGameImport(BaseModel):
    bgg_id: int

    @validator("bgg_id")
    def validate_bgg_id(cls, v):
        if v <= 0 or v > 999999:
            raise ValueError("BGG ID must be between 1 and 999999")
        return v


class CSVImport(BaseModel):
    csv_data: str

    @validator("csv_data")
    def validate_csv_data(cls, v):
        if not v.strip():
            raise ValueError("CSV data cannot be empty")
        return v


class AdminLogin(BaseModel):
    token: str

    @validator("token")
    def validate_token(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError("Token must be at least 10 characters")
        return v.strip()
