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
