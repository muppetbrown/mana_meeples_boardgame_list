from pydantic import BaseModel
from typing import Optional, List, Dict

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

    # existing mirrors
    thumbnail: Optional[str] = None
    playersMin: Optional[int] = None
    playersMax: Optional[int] = None
    playtimeMin: Optional[int] = None
    playtimeMax: Optional[int] = None

    # added to match the frontend helpers & alternate shapes
    imageUrl: Optional[str] = None
    image: Optional[str] = None
    imageURL: Optional[str] = None
    players: Optional[Range] = None
    playtime: Optional[Range] = None

    class Config:
        orm_mode = True

class PagedGames(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[GameOut]

class CategoryCounts(BaseModel):
    __root__: Dict[str, int]
