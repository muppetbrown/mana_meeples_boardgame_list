from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, ConfigDict

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

class SleeveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    game_id: int
    card_name: str | None
    width_mm: int
    height_mm: int
    quantity: int
    notes: str | None
    is_sleeved: bool

@router.post("/shopping-list", dependencies=[Depends(require_admin_auth)])
def generate_sleeve_shopping_list(
    request: SleeveShoppingListRequest,
    db: Session = Depends(get_db)
) -> List[SleeveShoppingListItem]:
    """
    Generate a sleeve shopping list for selected games
    Groups sleeves by size and counts variations
    Excludes games that are already fully sleeved (Game.is_sleeved=True)
    Also excludes individual sleeve types that are marked as sleeved (Sleeve.is_sleeved=True)
    """
    from collections import defaultdict

    # Fetch all UNSLEEVED sleeves for selected UNSLEEVED games
    # Exclude both: games marked as sleeved AND individual sleeve types marked as sleeved
    sleeves = db.execute(
        select(Sleeve).join(Game, Sleeve.game_id == Game.id).where(
            Sleeve.game_id.in_(request.game_ids),
            (Sleeve.is_sleeved == False) | (Sleeve.is_sleeved.is_(None)),
            (Game.is_sleeved == False) | (Game.is_sleeved.is_(None))
        )
    ).scalars().all()
    
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
        games = db.execute(
            select(Game).where(Game.id.in_(game_ids))
        ).scalars().all()
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

class SleeveUpdateRequest(BaseModel):
    is_sleeved: bool

@router.patch("/sleeve/{sleeve_id}", dependencies=[Depends(require_admin_auth)])
def update_sleeve_status(
    sleeve_id: int,
    request: SleeveUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update the sleeved status of a specific sleeve record"""
    sleeve = db.execute(
        select(Sleeve).where(Sleeve.id == sleeve_id)
    ).scalar_one_or_none()

    if not sleeve:
        raise HTTPException(status_code=404, detail="Sleeve not found")

    sleeve.is_sleeved = request.is_sleeved
    db.commit()
    db.refresh(sleeve)

    return {"success": True, "sleeve_id": sleeve_id, "is_sleeved": sleeve.is_sleeved}

@router.get("/game/{game_id}", dependencies=[Depends(require_admin_auth)])
def get_game_sleeves(game_id: int, db: Session = Depends(get_db)) -> List[SleeveResponse]:
    """Get all sleeve requirements for a specific game with sleeved status"""
    sleeves = db.execute(
        select(Sleeve).where(Sleeve.game_id == game_id)
    ).scalars().all()

    return [
        SleeveResponse(
            id=s.id,
            game_id=s.game_id,
            card_name=s.card_name,
            width_mm=s.width_mm,
            height_mm=s.height_mm,
            quantity=s.quantity,
            notes=s.notes,
            is_sleeved=s.is_sleeved or False
        )
        for s in sleeves
    ]