"""
Sleeve product matching service.

Matches game sleeve requirements to available sleeve products based on size tolerances.
Provides ordering recommendations and stock-based sleeving readiness checks.
"""
from collections import defaultdict
from sqlalchemy import select, and_
from sqlalchemy.orm import Session, joinedload

from models import Sleeve, SleeveProduct, Game


# Matching tolerances
WIDTH_TOLERANCE_MM = 1   # Sleeve width must be >= card width and <= card width + 1mm
HEIGHT_TOLERANCE_MM = 5  # Sleeve height must be >= card height and <= card height + 5mm


def find_matching_products(width_mm: int, height_mm: int, db: Session) -> list[SleeveProduct]:
    """Find all sleeve products that fit a given card size within tolerances."""
    return db.execute(
        select(SleeveProduct).where(
            and_(
                SleeveProduct.width_mm >= width_mm,
                SleeveProduct.width_mm <= width_mm + WIDTH_TOLERANCE_MM,
                SleeveProduct.height_mm >= height_mm,
                SleeveProduct.height_mm <= height_mm + HEIGHT_TOLERANCE_MM,
            )
        )
    ).scalars().all()


def best_match_for_order(width_mm: int, height_mm: int, db: Session) -> SleeveProduct | None:
    """Find the cheapest-per-sleeve product that fits the given card size."""
    products = find_matching_products(width_mm, height_mm, db)
    if not products:
        return None
    # Sort by price per sleeve (lowest first)
    return min(products, key=lambda p: float(p.price) / p.sleeves_per_pack)


def best_match_in_stock(width_mm: int, height_mm: int, db: Session) -> SleeveProduct | None:
    """Find the best-fitting in-stock product for the given card size."""
    products = find_matching_products(width_mm, height_mm, db)
    in_stock = [p for p in products if p.in_stock > 0]
    if not in_stock:
        return None
    # Sort by best size fit (smallest overshoot), then highest stock
    return min(in_stock, key=lambda p: (
        (p.width_mm - width_mm) + (p.height_mm - height_mm),
        -p.in_stock,
    ))


def run_matching_for_all_games(db: Session) -> dict:
    """
    Batch match: set matched_product_id on every unsleeved Sleeve record.
    Returns summary of matches made.
    """
    sleeves = db.execute(
        select(Sleeve).where(
            (Sleeve.is_sleeved == False) | (Sleeve.is_sleeved.is_(None))
        )
    ).scalars().all()

    # Pre-load all products for efficiency
    all_products = db.execute(select(SleeveProduct)).scalars().all()

    matched = 0
    unmatched = 0

    for sleeve in sleeves:
        # Find matching products from pre-loaded list
        candidates = [
            p for p in all_products
            if p.width_mm >= sleeve.width_mm
            and p.width_mm <= sleeve.width_mm + WIDTH_TOLERANCE_MM
            and p.height_mm >= sleeve.height_mm
            and p.height_mm <= sleeve.height_mm + HEIGHT_TOLERANCE_MM
        ]

        if candidates:
            # Pick cheapest per sleeve
            best = min(candidates, key=lambda p: float(p.price) / p.sleeves_per_pack)
            sleeve.matched_product_id = best.id
            matched += 1
        else:
            sleeve.matched_product_id = None
            unmatched += 1

    db.commit()
    return {"matched": matched, "unmatched": unmatched, "total": matched + unmatched}


def compute_to_sleeve_games(db: Session) -> list[dict]:
    """
    Returns games where ALL sleeve requirements have a matched product with sufficient stock.
    Each game includes its sleeve requirements and matched products.
    """
    # Get all unsleeved games that have sleeve data
    games = db.execute(
        select(Game).where(
            Game.has_sleeves == "found",
            (Game.is_sleeved == False) | (Game.is_sleeved.is_(None)),
        ).options(joinedload(Game.sleeves))
    ).unique().scalars().all()

    ready_games = []

    for game in games:
        unsleeved = [s for s in game.sleeves if not s.is_sleeved]
        if not unsleeved:
            continue

        # Check if ALL unsleeved requirements have a matched product with enough stock
        all_covered = True
        sleeve_details = []

        for sleeve in unsleeved:
            if not sleeve.matched_product_id:
                all_covered = False
                break

            product = db.get(SleeveProduct, sleeve.matched_product_id)
            if not product or product.in_stock < sleeve.quantity:
                all_covered = False
                break

            sleeve_details.append({
                "sleeve_id": sleeve.id,
                "card_name": sleeve.card_name,
                "width_mm": sleeve.width_mm,
                "height_mm": sleeve.height_mm,
                "quantity": sleeve.quantity,
                "product_id": product.id,
                "product_name": product.name,
                "product_stock": product.in_stock,
            })

        if all_covered and sleeve_details:
            ready_games.append({
                "game_id": game.id,
                "game_title": game.title,
                "sleeves": sleeve_details,
            })

    return ready_games


def compute_to_order_list(db: Session) -> list[dict]:
    """
    Returns sleeve sizes where stock is insufficient, grouped by matched product.
    Shows recommended product, price, distributor, quantity needed, and packs to buy.
    """
    # Get all unsleeved sleeve records
    sleeves = db.execute(
        select(Sleeve).join(Game, Sleeve.game_id == Game.id).where(
            (Sleeve.is_sleeved == False) | (Sleeve.is_sleeved.is_(None)),
            (Game.is_sleeved == False) | (Game.is_sleeved.is_(None)),
        )
    ).scalars().all()

    # Group by card size
    size_groups = defaultdict(list)
    for sleeve in sleeves:
        size_groups[(sleeve.width_mm, sleeve.height_mm)].append(sleeve)

    order_list = []

    for (width, height), group_sleeves in sorted(size_groups.items()):
        total_needed = sum(s.quantity for s in group_sleeves)

        # Find best product for ordering (cheapest per sleeve)
        product = best_match_for_order(width, height, db)

        current_stock = 0
        product_info = None

        if product:
            current_stock = product.in_stock
            ordered_sleeves = product.ordered * product.sleeves_per_pack
            deficit = max(0, total_needed - current_stock - ordered_sleeves)

            if deficit <= 0:
                continue  # Already have enough stock + ordered

            packs_to_buy = -(-deficit // product.sleeves_per_pack)  # Ceiling division

            product_info = {
                "product_id": product.id,
                "product_name": product.name,
                "distributor": product.distributor,
                "item_id": product.item_id,
                "sleeves_per_pack": product.sleeves_per_pack,
                "price_per_pack": float(product.price),
                "price_per_sleeve": round(float(product.price) / product.sleeves_per_pack, 3),
                "packs_to_buy": packs_to_buy,
                "total_cost": round(float(product.price) * packs_to_buy, 2),
                "current_stock": current_stock,
                "ordered_packs": product.ordered,
                "ordered_sleeves": ordered_sleeves,
            }
        else:
            deficit = total_needed

        game_ids = set(s.game_id for s in group_sleeves)
        games = db.execute(select(Game.title).where(Game.id.in_(game_ids))).scalars().all()

        order_list.append({
            "width_mm": width,
            "height_mm": height,
            "total_needed": total_needed,
            "deficit": deficit,
            "games_count": len(game_ids),
            "game_names": list(games),
            "product": product_info,
        })

    return order_list
