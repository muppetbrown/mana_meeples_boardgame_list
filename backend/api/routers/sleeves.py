from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from database import get_db
from models import Game, Sleeve
from api.dependencies import require_admin_auth

router = APIRouter(prefix="/api/admin/sleeves", tags=["admin-sleeves"])

class SleeveShoppingListRequest(BaseModel):
    game_ids: List[int]

class SleeveShoppingListItem(BaseModel):
    width_mm: int
    height_mm: int
    total_quantity: int
    games_count: int
    variations_grouped: int
    game_names: List[str]

@router.post("/shopping-list", dependencies=[Depends(require_admin_auth)])
def generate_sleeve_shopping_list(
    request: SleeveShoppingListRequest,
    db: Session = Depends(get_db)
) -> List[SleeveShoppingListItem]:
    """
    Generate a sleeve shopping list for selected games
    Groups sleeves by size and counts variations
    """
    from collections import defaultdict
    
    # Fetch all sleeves for selected games
    sleeves = db.query(Sleeve).filter(Sleeve.game_id.in_(request.game_ids)).all()
    
    # Group by size (with tolerance for slight variations)
    size_groups = defaultdict(list)
    
    for sleeve in sleeves:
        # Use exact size as key for now
        key = (sleeve.width_mm, sleeve.height_mm)
        size_groups[key].append(sleeve)
    
    # Build shopping list
    shopping_list = []
    
    for (width, height), sleeve_group in size_groups.items():
        # Count variations (slight size differences that got grouped)
        unique_sizes = set((s.width_mm, s.height_mm) for s in sleeve_group)
        variations = len(unique_sizes)
        
        # Get unique game names
        game_ids = set(s.game_id for s in sleeve_group)
        games = db.query(Game).filter(Game.id.in_(game_ids)).all()
        game_names = [g.title for g in games]
        
        # Sum quantities
        total_qty = sum(s.quantity for s in sleeve_group)
        
        shopping_list.append(SleeveShoppingListItem(
            width_mm=width,
            height_mm=height,
            total_quantity=total_qty,
            games_count=len(game_ids),
            variations_grouped=variations,
            game_names=game_names
        ))
    
    # Sort by size (width, then height)
    shopping_list.sort(key=lambda x: (x.width_mm, x.height_mm))
    
    return shopping_list

@router.get("/game/{game_id}", dependencies=[Depends(require_admin_auth)])
def get_game_sleeves(game_id: int, db: Session = Depends(get_db)):
    """Get all sleeve requirements for a specific game"""
    sleeves = db.query(Sleeve).filter(Sleeve.game_id == game_id).all()
    return sleeves