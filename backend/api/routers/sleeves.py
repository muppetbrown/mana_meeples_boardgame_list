from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, ConfigDict

from database import get_db
from models import Game, Sleeve, SleeveProduct
from api.dependencies import require_admin_auth
from services.sleeve_matching import (
    run_matching_for_all_games,
    compute_to_sleeve_games,
    compute_to_order_list,
)

router = APIRouter(prefix="/api/admin/sleeves", tags=["admin-sleeves"])


# ============================================================================
# Pydantic Models
# ============================================================================

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
    matched_product_id: int | None = None
    matched_product_name: str | None = None
    matched_product_stock: int | None = None

class SleeveUpdateRequest(BaseModel):
    is_sleeved: bool

class SleeveProductCreate(BaseModel):
    distributor: str
    item_id: str | None = None
    name: str
    width_mm: int
    height_mm: int
    sleeves_per_pack: int
    price: float
    in_stock: int = 0
    ordered: int = 0

class SleeveProductUpdate(BaseModel):
    distributor: str | None = None
    item_id: str | None = None
    name: str | None = None
    width_mm: int | None = None
    height_mm: int | None = None
    sleeves_per_pack: int | None = None
    price: float | None = None
    in_stock: int | None = None
    ordered: int | None = None

class SleeveProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    distributor: str
    item_id: str | None
    name: str
    width_mm: int
    height_mm: int
    sleeves_per_pack: int
    price: float
    in_stock: int
    ordered: int
    ordered_sleeves: int = 0  # Computed: ordered * sleeves_per_pack


# ============================================================================
# Existing Endpoints (unchanged behavior, enhanced response)
# ============================================================================

@router.post("/shopping-list", dependencies=[Depends(require_admin_auth)])
def generate_sleeve_shopping_list(
    request: SleeveShoppingListRequest,
    db: Session = Depends(get_db)
) -> List[SleeveShoppingListItem]:
    """
    Generate a sleeve shopping list for selected games.
    Groups sleeves by size and counts variations.
    Excludes games that are already fully sleeved and individual sleeved sleeve types.
    """
    from collections import defaultdict

    sleeves = db.execute(
        select(Sleeve).join(Game, Sleeve.game_id == Game.id).where(
            Sleeve.game_id.in_(request.game_ids),
            (Sleeve.is_sleeved == False) | (Sleeve.is_sleeved.is_(None)),
            (Game.is_sleeved == False) | (Game.is_sleeved.is_(None))
        )
    ).scalars().all()

    size_groups = defaultdict(list)
    for sleeve in sleeves:
        key = (sleeve.width_mm, sleeve.height_mm)
        size_groups[key].append(sleeve)

    shopping_list = []
    for (width, height), sleeve_group in size_groups.items():
        unique_sizes = set((s.width_mm, s.height_mm) for s in sleeve_group)
        variations = len(unique_sizes)

        game_ids = set(s.game_id for s in sleeve_group)
        games = db.execute(
            select(Game).where(Game.id.in_(game_ids))
        ).scalars().all()
        game_names = [g.title for g in games]

        total_qty = sum(s.quantity for s in sleeve_group)

        shopping_list.append(SleeveShoppingListItem(
            width_mm=width,
            height_mm=height,
            total_quantity=total_qty,
            games_count=len(game_ids),
            variations_grouped=variations,
            game_names=game_names
        ))

    shopping_list.sort(key=lambda x: (x.width_mm, x.height_mm))
    return shopping_list


@router.patch("/sleeve/{sleeve_id}", dependencies=[Depends(require_admin_auth)])
def update_sleeve_status(
    sleeve_id: int,
    request: SleeveUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Update the sleeved status of a specific sleeve record.
    When marking as sleeved: deducts stock from matched product.
    When unmarking: restores stock to matched product.
    """
    sleeve = db.execute(
        select(Sleeve).where(Sleeve.id == sleeve_id)
    ).scalar_one_or_none()

    if not sleeve:
        raise HTTPException(status_code=404, detail="Sleeve not found")

    old_status = sleeve.is_sleeved
    new_status = request.is_sleeved

    stock_info = None

    # Stock deduction/restoration when status changes
    if old_status != new_status and sleeve.matched_product_id:
        # Lock the product row to prevent race conditions
        product = db.execute(
            select(SleeveProduct)
            .where(SleeveProduct.id == sleeve.matched_product_id)
            .with_for_update()
        ).scalar_one_or_none()

        if product:
            if new_status:
                # Marking as sleeved -> deduct stock
                if product.in_stock < sleeve.quantity:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Insufficient stock for {product.name}: have {product.in_stock}, need {sleeve.quantity}"
                    )
                product.in_stock -= sleeve.quantity
            else:
                # Unmarking -> restore stock
                product.in_stock += sleeve.quantity

            stock_info = {
                "product_id": product.id,
                "product_name": product.name,
                "new_stock": product.in_stock,
            }

    sleeve.is_sleeved = new_status
    db.commit()
    db.refresh(sleeve)

    return {
        "success": True,
        "sleeve_id": sleeve_id,
        "is_sleeved": sleeve.is_sleeved,
        "stock_info": stock_info,
    }


@router.get("/game/{game_id}", dependencies=[Depends(require_admin_auth)])
def get_game_sleeves(game_id: int, db: Session = Depends(get_db)) -> List[SleeveResponse]:
    """Get all sleeve requirements for a specific game with sleeved status and matched product info."""
    sleeves = db.execute(
        select(Sleeve).where(Sleeve.game_id == game_id)
    ).scalars().all()

    result = []
    for s in sleeves:
        product_name = None
        product_stock = None
        if s.matched_product_id:
            product = db.get(SleeveProduct, s.matched_product_id)
            if product:
                product_name = product.name
                product_stock = product.in_stock

        result.append(SleeveResponse(
            id=s.id,
            game_id=s.game_id,
            card_name=s.card_name,
            width_mm=s.width_mm,
            height_mm=s.height_mm,
            quantity=s.quantity,
            notes=s.notes,
            is_sleeved=s.is_sleeved or False,
            matched_product_id=s.matched_product_id,
            matched_product_name=product_name,
            matched_product_stock=product_stock,
        ))

    return result


# ============================================================================
# Sleeve Products CRUD
# ============================================================================

@router.get("/products", dependencies=[Depends(require_admin_auth)])
def list_sleeve_products(
    distributor: Optional[str] = None,
    db: Session = Depends(get_db),
) -> List[SleeveProductResponse]:
    """List all sleeve products, optionally filtered by distributor."""
    query = select(SleeveProduct)
    if distributor:
        query = query.where(SleeveProduct.distributor == distributor)
    query = query.order_by(SleeveProduct.distributor, SleeveProduct.width_mm, SleeveProduct.height_mm)

    products = db.execute(query).scalars().all()
    return [
        SleeveProductResponse(
            id=p.id,
            distributor=p.distributor,
            item_id=p.item_id,
            name=p.name,
            width_mm=p.width_mm,
            height_mm=p.height_mm,
            sleeves_per_pack=p.sleeves_per_pack,
            price=float(p.price),
            in_stock=p.in_stock,
            ordered=p.ordered,
            ordered_sleeves=p.ordered * p.sleeves_per_pack,
        )
        for p in products
    ]


@router.post("/products", dependencies=[Depends(require_admin_auth)])
def create_sleeve_product(
    data: SleeveProductCreate,
    db: Session = Depends(get_db),
) -> SleeveProductResponse:
    """Create a new sleeve product."""
    product = SleeveProduct(
        distributor=data.distributor,
        item_id=data.item_id,
        name=data.name,
        width_mm=data.width_mm,
        height_mm=data.height_mm,
        sleeves_per_pack=data.sleeves_per_pack,
        price=Decimal(str(data.price)),
        in_stock=data.in_stock,
        ordered=data.ordered,
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    return SleeveProductResponse(
        id=product.id,
        distributor=product.distributor,
        item_id=product.item_id,
        name=product.name,
        width_mm=product.width_mm,
        height_mm=product.height_mm,
        sleeves_per_pack=product.sleeves_per_pack,
        price=float(product.price),
        in_stock=product.in_stock,
        ordered=product.ordered,
        ordered_sleeves=product.ordered * product.sleeves_per_pack,
    )


@router.put("/products/{product_id}", dependencies=[Depends(require_admin_auth)])
def update_sleeve_product(
    product_id: int,
    data: SleeveProductUpdate,
    db: Session = Depends(get_db),
) -> SleeveProductResponse:
    """Update an existing sleeve product."""
    product = db.get(SleeveProduct, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Sleeve product not found")

    update_data = data.model_dump(exclude_unset=True)
    if "price" in update_data:
        update_data["price"] = Decimal(str(update_data["price"]))

    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)

    return SleeveProductResponse(
        id=product.id,
        distributor=product.distributor,
        item_id=product.item_id,
        name=product.name,
        width_mm=product.width_mm,
        height_mm=product.height_mm,
        sleeves_per_pack=product.sleeves_per_pack,
        price=float(product.price),
        in_stock=product.in_stock,
        ordered=product.ordered,
        ordered_sleeves=product.ordered * product.sleeves_per_pack,
    )


@router.delete("/products/{product_id}", dependencies=[Depends(require_admin_auth)])
def delete_sleeve_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    """Delete a sleeve product. Clears matched_product_id on any linked sleeves."""
    product = db.get(SleeveProduct, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Sleeve product not found")

    # Clear references in sleeves table
    linked_sleeves = db.execute(
        select(Sleeve).where(Sleeve.matched_product_id == product_id)
    ).scalars().all()
    for s in linked_sleeves:
        s.matched_product_id = None

    db.delete(product)
    db.commit()

    return {"success": True, "cleared_sleeve_links": len(linked_sleeves)}


# ============================================================================
# Matching & Reports
# ============================================================================

@router.post("/match-all", dependencies=[Depends(require_admin_auth)])
def match_all_sleeves(db: Session = Depends(get_db)):
    """Run matching across all unsleeved games, persist matched_product_id."""
    result = run_matching_for_all_games(db)
    return result


@router.get("/to-order", dependencies=[Depends(require_admin_auth)])
def get_to_order_list(db: Session = Depends(get_db)):
    """Aggregated list of sleeves to order, grouped by size/product."""
    return compute_to_order_list(db)


@router.get("/to-sleeve", dependencies=[Depends(require_admin_auth)])
def get_to_sleeve_list(db: Session = Depends(get_db)):
    """List of games ready to sleeve (all requirements covered by stock)."""
    return compute_to_sleeve_games(db)
