"""
Sleeve product matching service.

Matches game sleeve requirements to available sleeve products based on size tolerances.
Provides ordering recommendations and stock-based sleeving readiness checks.
"""
from collections import defaultdict
from decimal import Decimal
from sqlalchemy import select, and_
from sqlalchemy.orm import Session, joinedload

from models import Sleeve, SleeveProduct, Game


# Matching tolerances
WIDTH_TOLERANCE_MM = Decimal("1")   # Sleeve width must be >= card width and <= card width + 1mm
HEIGHT_TOLERANCE_MM = Decimal("5")  # Sleeve height must be >= card height and <= card height + 5mm


def to_decimal(value) -> Decimal:
    """Normalise int/float/Decimal/str measurements to Decimal (2dp) so mixed arithmetic is safe."""
    return Decimal(str(value)).quantize(Decimal("0.01"))


def size_waste(product: SleeveProduct, width_mm, height_mm) -> Decimal:
    """Total mm of slack between a product and a card size (lower is a tighter fit)."""
    return (to_decimal(product.width_mm) - to_decimal(width_mm)) + (
        to_decimal(product.height_mm) - to_decimal(height_mm)
    )


def find_matching_products(width_mm: float, height_mm: float, db: Session) -> list[SleeveProduct]:
    """Find all sleeve products that fit a given card size within tolerances."""
    width_mm = to_decimal(width_mm)
    height_mm = to_decimal(height_mm)
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


def best_match_for_order(width_mm: float, height_mm: float, db: Session) -> SleeveProduct | None:
    """Find the best-fitting product, using cheapest-per-sleeve as tiebreaker."""
    products = find_matching_products(width_mm, height_mm, db)
    if not products:
        return None
    # Best size fit first, then cheapest per sleeve for same-size products
    return min(products, key=lambda p: (
        size_waste(p, width_mm, height_mm),
        float(p.price) / p.sleeves_per_pack,
    ))


def best_match_in_stock(width_mm: float, height_mm: float, db: Session) -> SleeveProduct | None:
    """Find the best-fitting in-stock product for the given card size."""
    products = find_matching_products(width_mm, height_mm, db)
    in_stock = [p for p in products if p.in_stock > 0]
    if not in_stock:
        return None
    # Best size fit first, then highest stock for same-size products
    return min(in_stock, key=lambda p: (
        size_waste(p, width_mm, height_mm),
        -p.in_stock,
        float(p.price) / p.sleeves_per_pack,
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
        sw = to_decimal(sleeve.width_mm)
        sh = to_decimal(sleeve.height_mm)
        candidates = [
            p for p in all_products
            if to_decimal(p.width_mm) >= sw
            and to_decimal(p.width_mm) <= sw + WIDTH_TOLERANCE_MM
            and to_decimal(p.height_mm) >= sh
            and to_decimal(p.height_mm) <= sh + HEIGHT_TOLERANCE_MM
        ]

        if candidates:
            # Best size fit, then prefer in-stock, then cheapest per sleeve
            best = min(candidates, key=lambda p: (
                size_waste(p, sleeve.width_mm, sleeve.height_mm),
                0 if p.in_stock > 0 else 1,
                float(p.price) / p.sleeves_per_pack,
            ))
            sleeve.matched_product_id = best.id
            matched += 1
        else:
            sleeve.matched_product_id = None
            unmatched += 1

    db.commit()
    return {"matched": matched, "unmatched": unmatched, "total": matched + unmatched}


def compute_to_sleeve_games(db: Session) -> list[dict]:
    """
    Returns games that have at least one sleeve requirement coverable by stock.
    Each sleeve is marked as ready or not, so partial sleeving is supported.
    Games are sorted: fully coverable first, then by number of ready sleeves descending.
    """
    games = db.execute(
        select(Game).where(
            Game.has_sleeves == "found",
            (Game.is_sleeved == False) | (Game.is_sleeved.is_(None)),
            Game.status == "OWNED",
        ).options(joinedload(Game.sleeves))
    ).unique().scalars().all()

    ready_games = []

    for game in games:
        unsleeved = [s for s in game.sleeves if not s.is_sleeved]
        if not unsleeved:
            continue

        sleeve_details = []
        any_ready = False

        for sleeve in unsleeved:
            if not sleeve.matched_product_id:
                sleeve_details.append({
                    "sleeve_id": sleeve.id,
                    "card_name": sleeve.card_name,
                    "width_mm": float(sleeve.width_mm),
                    "height_mm": float(sleeve.height_mm),
                    "quantity": sleeve.quantity,
                    "product_id": None,
                    "product_name": None,
                    "product_stock": None,
                    "ready": False,
                })
                continue

            product = db.get(SleeveProduct, sleeve.matched_product_id)
            has_stock = product is not None and product.in_stock >= sleeve.quantity
            if has_stock:
                any_ready = True

            sleeve_details.append({
                "sleeve_id": sleeve.id,
                "card_name": sleeve.card_name,
                "width_mm": float(sleeve.width_mm),
                "height_mm": float(sleeve.height_mm),
                "quantity": sleeve.quantity,
                "product_id": product.id if product else None,
                "product_name": product.name if product else None,
                "product_stock": product.in_stock if product else None,
                "ready": has_stock,
            })

        if any_ready:
            ready_count = sum(1 for s in sleeve_details if s["ready"])
            ready_games.append({
                "game_id": game.id,
                "game_title": game.title,
                "sleeves": sleeve_details,
                "all_ready": ready_count == len(sleeve_details),
                "ready_count": ready_count,
                "total_count": len(sleeve_details),
            })

    # Fully coverable games first, then by ready count descending
    ready_games.sort(key=lambda g: (-int(g["all_ready"]), -g["ready_count"]))
    return ready_games


def compute_to_order_list(db: Session) -> list[dict]:
    """
    Returns what to order, grouped by matched product.

    Several card sizes can resolve to the same product; those are merged into a
    single row so the product's stock/on-order quantities are counted once and
    packs are rounded up once. Sizes with no matching product are listed
    individually (there is no product to group them under).
    """
    # Get all unsleeved sleeve records
    sleeves = db.execute(
        select(Sleeve).join(Game, Sleeve.game_id == Game.id).where(
            (Sleeve.is_sleeved == False) | (Sleeve.is_sleeved.is_(None)),
            (Game.is_sleeved == False) | (Game.is_sleeved.is_(None)),
            Game.status == "OWNED",
        )
    ).scalars().all()

    # Group by card size
    size_groups = defaultdict(list)
    for sleeve in sleeves:
        size_groups[(to_decimal(sleeve.width_mm), to_decimal(sleeve.height_mm))].append(sleeve)

    # Bucket sizes by the product they'd be ordered from. Unmatched sizes get
    # their own bucket keyed by size.
    buckets: dict = {}
    for (width, height), group_sleeves in sorted(size_groups.items()):
        product = best_match_for_order(width, height, db)
        key = ("product", product.id) if product else ("size", width, height)
        bucket = buckets.setdefault(key, {"product": product, "sizes": [], "sleeves": []})
        bucket["sizes"].append((float(width), float(height)))
        bucket["sleeves"].extend(group_sleeves)

    order_list = []

    for bucket in buckets.values():
        product = bucket["product"]
        group_sleeves = bucket["sleeves"]
        total_needed = sum(s.quantity for s in group_sleeves)
        product_info = None

        if product:
            ordered_sleeves = product.ordered * product.sleeves_per_pack
            deficit = max(0, total_needed - product.in_stock - ordered_sleeves)

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
                "current_stock": product.in_stock,
                "ordered_packs": product.ordered,
                "ordered_sleeves": ordered_sleeves,
            }
        else:
            deficit = total_needed

        game_ids = set(s.game_id for s in group_sleeves)
        games = db.execute(select(Game.title).where(Game.id.in_(game_ids))).scalars().all()

        sizes = bucket["sizes"]
        order_list.append({
            # First (smallest) size kept for backwards compatibility / size-group classification
            "width_mm": sizes[0][0],
            "height_mm": sizes[0][1],
            "sizes": [{"width_mm": w, "height_mm": h} for w, h in sizes],
            "total_needed": total_needed,
            "deficit": deficit,
            "games_count": len(game_ids),
            "game_names": sorted(games),
            "product": product_info,
        })

    return order_list
