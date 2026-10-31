import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

from config import GITHUB_TOKEN, GITHUB_REPO_OWNER, GITHUB_REPO_NAME
from database import get_db
from models import Game, Sleeve, SleeveProduct, SleeveProductDistroLink
from api.dependencies import require_admin_auth
from services.sleeve_matching import (
    run_matching_for_all_games,
    compute_to_sleeve_games,
    compute_to_order_list,
    pick_best_product,
    to_decimal,
)
from services.hl_stock_service import HLStockServiceError, fetch_distro_codes_by_key
from services.sleeve_distro import (
    auto_link_products,
    product_availability,
    unlisted_sleeves,
    with_stock_state,
)
from services.distro_availability import build_option

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/sleeves", tags=["admin-sleeves"])


# ============================================================================
# Pydantic Models
# ============================================================================

class SleeveShoppingListRequest(BaseModel):
    game_ids: List[int]

class SleeveShoppingListItem(BaseModel):
    width_mm: float
    height_mm: float
    total_quantity: int
    games_count: int
    variations_grouped: int
    game_names: List[str]

class SleeveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    game_id: int
    card_name: str | None
    width_mm: float
    height_mm: float
    quantity: int
    notes: str | None
    is_sleeved: bool
    matched_product_id: int | None = None
    matched_product_name: str | None = None
    matched_product_stock: int | None = None

class SleeveUpdateRequest(BaseModel):
    is_sleeved: bool

class SleeveEditRequest(BaseModel):
    card_name: str | None = None
    width_mm: float = Field(gt=0, le=9999.99)
    height_mm: float = Field(gt=0, le=9999.99)
    quantity: int = Field(gt=0)
    notes: str | None = None

class SleeveCreateRequest(BaseModel):
    card_name: str | None = None
    width_mm: float = Field(gt=0, le=9999.99)
    height_mm: float = Field(gt=0, le=9999.99)
    quantity: int = Field(gt=0)
    notes: str | None = None

class GameSleeveStatusUpdate(BaseModel):
    status: str  # "none" (no cards to sleeve) or "check" (reset to needs-investigation)

class SleeveDistroLink(BaseModel):
    distributor: str
    distro_code: str

class SleeveProductCreate(BaseModel):
    distributor: str
    item_id: str | None = None
    name: str
    width_mm: float = Field(gt=0, le=9999.99)
    height_mm: float = Field(gt=0, le=9999.99)
    card_width_mm: float | None = Field(default=None, gt=0, le=9999.99)
    card_height_mm: float | None = Field(default=None, gt=0, le=9999.99)
    sleeves_per_pack: int = Field(gt=0)
    price: float = Field(gt=0)
    in_stock: int = Field(default=0, ge=0)
    distro_link: SleeveDistroLink | None = None

class SleeveProductUpdate(BaseModel):
    distributor: str | None = None
    item_id: str | None = None
    name: str | None = None
    width_mm: float | None = Field(default=None, gt=0, le=9999.99)
    height_mm: float | None = Field(default=None, gt=0, le=9999.99)
    card_width_mm: float | None = Field(default=None, gt=0, le=9999.99)
    card_height_mm: float | None = Field(default=None, gt=0, le=9999.99)
    sleeves_per_pack: int | None = Field(default=None, gt=0)
    price: float | None = Field(default=None, gt=0)
    in_stock: int | None = Field(default=None, ge=0)

class SleeveProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    distributor: str
    item_id: str | None
    name: str
    width_mm: float
    height_mm: float
    card_width_mm: float | None = None
    card_height_mm: float | None = None
    sleeves_per_pack: int
    price: float
    in_stock: int
    # Live HL distro_codes rows (name, cost ex GST, distributor stock) for each linked code,
    # best supplier first; `distro` is the best active one.
    distros: List[dict] = []
    distro: dict | None = None


def _product_response(p: SleeveProduct, distro: dict | None = None) -> SleeveProductResponse:
    return SleeveProductResponse(
        id=p.id,
        distributor=p.distributor,
        item_id=p.item_id,
        name=p.name,
        width_mm=p.width_mm,
        height_mm=p.height_mm,
        card_width_mm=p.card_width_mm,
        card_height_mm=p.card_height_mm,
        sleeves_per_pack=p.sleeves_per_pack,
        price=float(p.price),
        in_stock=p.in_stock,
        distros=(distro or {}).get("options", []),
        distro=None if (distro is None or distro.get("inactive")) else {k: v for k, v in distro.items() if k != "options"},
    )


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
        key = (to_decimal(sleeve.width_mm), to_decimal(sleeve.height_mm))
        size_groups[key].append(sleeve)

    shopping_list = []
    for (width, height), sleeve_group in size_groups.items():
        unique_sizes = set((to_decimal(s.width_mm), to_decimal(s.height_mm)) for s in sleeve_group)
        variations = len(unique_sizes)

        game_ids = set(s.game_id for s in sleeve_group)
        games = db.execute(
            select(Game).where(Game.id.in_(game_ids))
        ).scalars().all()
        game_names = [g.title for g in games]

        total_qty = sum(s.quantity for s in sleeve_group)

        shopping_list.append(SleeveShoppingListItem(
            width_mm=float(width),
            height_mm=float(height),
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
                # Marking as sleeved -> deduct stock (use all available if insufficient)
                product.in_stock = max(0, product.in_stock - sleeve.quantity)
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


def _sleeve_response(s: Sleeve, db: Session) -> SleeveResponse:
    product = db.get(SleeveProduct, s.matched_product_id) if s.matched_product_id else None
    return SleeveResponse(
        id=s.id,
        game_id=s.game_id,
        card_name=s.card_name,
        width_mm=s.width_mm,
        height_mm=s.height_mm,
        quantity=s.quantity,
        notes=s.notes,
        is_sleeved=s.is_sleeved or False,
        matched_product_id=s.matched_product_id,
        matched_product_name=product.name if product else None,
        matched_product_stock=product.in_stock if product else None,
    )


def _live_availability(db: Session) -> dict | None:
    """Live distributor stock per product id, or None if HL can't be read (ranking then ignores it)."""
    products = db.execute(
        select(SleeveProduct).options(selectinload(SleeveProduct.distro_links))
    ).scalars().all()
    return product_availability(products)


def _auto_match_sleeve(sleeve: Sleeve, db: Session) -> None:
    """Match one unsleeved sleeve requirement to the best product (same rules as batch matching)."""
    products = db.execute(select(SleeveProduct)).scalars().all()
    best = pick_best_product(
        products, sleeve.width_mm, sleeve.height_mm, sleeve.quantity, _live_availability(db)
    )
    sleeve.matched_product_id = best.id if best else None


@router.get("/game/{game_id}", dependencies=[Depends(require_admin_auth)])
def get_game_sleeves(game_id: int, db: Session = Depends(get_db)) -> List[SleeveResponse]:
    """Get all sleeve requirements for a specific game with sleeved status and matched product info."""
    sleeves = db.execute(
        select(Sleeve).where(Sleeve.game_id == game_id).order_by(Sleeve.id)
    ).scalars().all()
    return [_sleeve_response(s, db) for s in sleeves]


@router.post("/game/{game_id}", dependencies=[Depends(require_admin_auth)])
def create_game_sleeve(
    game_id: int,
    data: SleeveCreateRequest,
    db: Session = Depends(get_db),
) -> SleeveResponse:
    """Manually add a sleeve requirement for a game (no BGG scrape needed)."""
    game = db.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Reflect that this game's sleeve data includes a manual entry, so the
    # public "needs investigation" badge clears once an admin has looked at it.
    game.has_sleeves = "manual"

    sleeve = Sleeve(
        game_id=game_id,
        card_name=data.card_name,
        width_mm=to_decimal(data.width_mm),
        height_mm=to_decimal(data.height_mm),
        quantity=data.quantity,
        notes=data.notes,
        is_sleeved=False,
    )
    _auto_match_sleeve(sleeve, db)

    db.add(sleeve)
    db.commit()
    db.refresh(sleeve)
    return _sleeve_response(sleeve, db)


@router.put("/sleeve/{sleeve_id}", dependencies=[Depends(require_admin_auth)])
def edit_game_sleeve(
    sleeve_id: int,
    data: SleeveEditRequest,
    db: Session = Depends(get_db),
) -> SleeveResponse:
    """Correct a sleeve requirement (name, size, quantity, notes) and re-match it to a product."""
    sleeve = db.get(Sleeve, sleeve_id)
    if not sleeve:
        raise HTTPException(status_code=404, detail="Sleeve not found")

    sleeve.card_name = data.card_name
    sleeve.width_mm = to_decimal(data.width_mm)
    sleeve.height_mm = to_decimal(data.height_mm)
    sleeve.quantity = data.quantity
    sleeve.notes = data.notes
    if not sleeve.is_sleeved:
        _auto_match_sleeve(sleeve, db)

    db.commit()
    db.refresh(sleeve)
    return _sleeve_response(sleeve, db)


@router.delete("/sleeve/{sleeve_id}", dependencies=[Depends(require_admin_auth)])
def delete_game_sleeve(
    sleeve_id: int,
    db: Session = Depends(get_db),
):
    """Delete a manually or automatically added sleeve requirement record."""
    sleeve = db.get(Sleeve, sleeve_id)
    if not sleeve:
        raise HTTPException(status_code=404, detail="Sleeve not found")

    db.delete(sleeve)
    db.commit()

    return {"success": True}


@router.patch("/game/{game_id}/status", dependencies=[Depends(require_admin_auth)])
def update_game_sleeve_status(
    game_id: int,
    data: GameSleeveStatusUpdate,
    db: Session = Depends(get_db),
):
    """
    Manually set a game's sleeve-investigation status without a BGG scrape.
    Use "none" for games that genuinely have no cards to sleeve (this clears
    any existing sleeve requirement rows, since they'd be contradictory).
    Use "check" to reset back to "needs investigation" - e.g. to undo an
    accidental "none", or to clear a bad "manual"/"error" state.
    """
    if data.status not in ("none", "check"):
        raise HTTPException(status_code=400, detail="status must be 'none' or 'check'")

    game = db.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if data.status == "none":
        db.execute(delete(Sleeve).where(Sleeve.game_id == game_id))
        game.has_sleeves = "none"
    else:
        game.has_sleeves = None

    db.commit()

    return {"success": True, "game_id": game_id, "has_sleeves": game.has_sleeves}


# ============================================================================
# Sleeve Products CRUD
# ============================================================================

def _live_option(product: SleeveProduct) -> dict | None:
    return (product_availability([product]) or {}).get(product.id)


def _add_distro_link(product: SleeveProduct, row: dict) -> None:
    """Attach a catalogue row to a product unless it's already linked."""
    key = (row["distributor"], row["distro_code"])
    if any((l.hl_distributor, l.hl_distro_code) == key for l in product.distro_links):
        return
    product.distro_links.append(SleeveProductDistroLink(hl_distributor=key[0], hl_distro_code=key[1]))


def _validated_distro_row(link: SleeveDistroLink) -> dict:
    try:
        rows = fetch_distro_codes_by_key([(link.distributor, link.distro_code)])
    except HLStockServiceError as e:
        raise HTTPException(status_code=503, detail=str(e))
    if not rows:
        raise HTTPException(status_code=404, detail="Distributor code not found (or inactive) in HL catalogue")
    return rows[0]


@router.get("/products", dependencies=[Depends(require_admin_auth)])
def list_sleeve_products(
    distributor: Optional[str] = None,
    db: Session = Depends(get_db),
) -> List[SleeveProductResponse]:
    """List all sleeve products, optionally filtered by distributor."""
    query = select(SleeveProduct).options(selectinload(SleeveProduct.distro_links))
    if distributor:
        query = query.where(SleeveProduct.distributor == distributor)
    query = query.order_by(SleeveProduct.distributor, SleeveProduct.width_mm, SleeveProduct.height_mm)

    products = db.execute(query).scalars().all()
    availability = product_availability(products) or {}
    return [_product_response(p, availability.get(p.id)) for p in products]


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
        width_mm=to_decimal(data.width_mm),
        height_mm=to_decimal(data.height_mm),
        card_width_mm=to_decimal(data.card_width_mm) if data.card_width_mm is not None else None,
        card_height_mm=to_decimal(data.card_height_mm) if data.card_height_mm is not None else None,
        sleeves_per_pack=data.sleeves_per_pack,
        price=Decimal(str(data.price)),
        in_stock=data.in_stock,
    )
    if data.distro_link:
        _add_distro_link(product, _validated_distro_row(data.distro_link))
    db.add(product)
    db.flush()
    run_matching_for_all_games(db, commit=False, availability=_live_availability(db))
    db.commit()
    db.refresh(product)

    return _product_response(product, _live_option(product))


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
    for dim in ("width_mm", "height_mm", "card_width_mm", "card_height_mm"):
        if update_data.get(dim) is not None:
            update_data[dim] = to_decimal(update_data[dim])

    for field, value in update_data.items():
        setattr(product, field, value)

    db.flush()
    # Size or stock changes can alter which product best fits each sleeve
    run_matching_for_all_games(db, commit=False, availability=_live_availability(db))
    db.commit()
    db.refresh(product)

    return _product_response(product, _live_option(product))


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
    db.flush()
    # Sleeves that lost their product may fit another one
    run_matching_for_all_games(db, commit=False, availability=_live_availability(db))
    db.commit()

    return {"success": True, "cleared_sleeve_links": len(linked_sleeves)}


# ============================================================================
# HL Timaru distro_codes link
# ============================================================================

@router.post("/products/{product_id}/distro-links", dependencies=[Depends(require_admin_auth)])
def link_product_to_distro_code(
    product_id: int,
    data: SleeveDistroLink,
    db: Session = Depends(get_db),
) -> SleeveProductResponse:
    """Add a distributor code from the HL catalogue to a sleeve product (several allowed)."""
    product = db.get(SleeveProduct, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Sleeve product not found")
    _add_distro_link(product, _validated_distro_row(data))
    db.commit()
    db.refresh(product)
    return _product_response(product, _live_option(product))


@router.delete("/products/{product_id}/distro-links/{link_id}", dependencies=[Depends(require_admin_auth)])
def unlink_product_from_distro_code(
    product_id: int, link_id: int, db: Session = Depends(get_db)
) -> SleeveProductResponse:
    link = db.get(SleeveProductDistroLink, link_id)
    if not link or link.sleeve_product_id != product_id:
        raise HTTPException(status_code=404, detail="Distro link not found")
    product = db.get(SleeveProduct, product_id)
    db.delete(link)
    db.commit()
    db.refresh(product)
    return _product_response(product, _live_option(product))


@router.post("/distro/auto-link", dependencies=[Depends(require_admin_auth)])
def auto_link_distro_codes(db: Session = Depends(get_db)):
    """Link every product with no distro link to the HL catalogue by (distributor, item_id), then by exact name."""
    try:
        return auto_link_products(db)
    except HLStockServiceError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/catalogue/unlisted", dependencies=[Depends(require_admin_auth)])
def get_unlisted_catalogue_sleeves(include_all: bool = False, db: Session = Depends(get_db)):
    """Sleeves in the HL distributor catalogue that aren't in sleeve inventory,
    with the currently-needed sizes each would fit (see services/sleeve_distro.py)."""
    try:
        items = unlisted_sleeves(db, include_all=include_all)
    except HLStockServiceError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {"count": len(items), "items": items}


# ============================================================================
# Matching & Reports
# ============================================================================

@router.post("/match-all", dependencies=[Depends(require_admin_auth)])
def match_all_sleeves(db: Session = Depends(get_db)):
    """Run matching across all unsleeved games, persist matched_product_id."""
    result = run_matching_for_all_games(db, availability=_live_availability(db))
    return result


@router.get("/to-order", dependencies=[Depends(require_admin_auth)])
def get_to_order_list(db: Session = Depends(get_db)):
    """Aggregated list of sleeves to order, grouped by size/product."""
    products = db.execute(
        select(SleeveProduct).options(selectinload(SleeveProduct.distro_links))
    ).scalars().all()
    return compute_to_order_list(db, availability=product_availability(products))


@router.get("/to-sleeve", dependencies=[Depends(require_admin_auth)])
def get_to_sleeve_list(db: Session = Depends(get_db)):
    """List of games ready to sleeve (all requirements covered by stock)."""
    return compute_to_sleeve_games(db)


# ============================================================================
# Fetch Status (visibility into the GitHub Actions sleeve scrape)
# ============================================================================

@router.get("/fetch-status", dependencies=[Depends(require_admin_auth)])
async def get_sleeve_fetch_status(db: Session = Depends(get_db)):
    """
    Report the status of the most recent 'Fetch Sleeve Data' GitHub Actions
    run, plus a DB-wide coverage snapshot. Both the "fetch all" and
    "fetch selected games" buttons dispatch the same workflow via the
    GitHub API, which only returns a 204 with no run ID - so this looks up
    the most recent run rather than tracking a specific one. That's a
    reasonable approximation since this workflow isn't run concurrently.
    """
    import httpx

    coverage_rows = db.execute(
        select(Game.has_sleeves, func.count()).group_by(Game.has_sleeves)
    ).all()
    coverage = {(status or "null"): count for status, count in coverage_rows}

    if not GITHUB_TOKEN:
        return {
            "workflow_configured": False,
            "message": "GITHUB_TOKEN not configured - cannot check workflow run status.",
            "coverage": coverage,
        }

    url = (
        f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}"
        f"/actions/workflows/fetch_sleeves.yml/runs?per_page=1"
    )
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=headers)
        response.raise_for_status()
        runs = response.json().get("workflow_runs", [])
    except Exception as e:
        logger.error(f"Failed to fetch sleeve workflow run status: {e}")
        return {
            "workflow_configured": True,
            "message": "Failed to reach GitHub Actions API - check server logs.",
            "coverage": coverage,
        }

    if not runs:
        return {
            "workflow_configured": True,
            "message": "No sleeve fetch runs found yet.",
            "coverage": coverage,
        }

    run = runs[0]
    return {
        "workflow_configured": True,
        "status": run.get("status"),  # queued | in_progress | completed
        "conclusion": run.get("conclusion"),  # success | failure | cancelled | null
        "html_url": run.get("html_url"),
        "run_started_at": run.get("run_started_at"),
        "updated_at": run.get("updated_at"),
        "coverage": coverage,
    }
