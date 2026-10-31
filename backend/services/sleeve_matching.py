"""
Sleeve product matching service.

Matches game sleeve requirements to available sleeve products based on size tolerances.
Provides ordering recommendations and stock-based sleeving readiness checks.
"""
from collections import defaultdict
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from models import Sleeve, SleeveProduct, Game


# Matching tolerances. Applied to the sleeve's fits-card size when it has one, else its own size.
WIDTH_TOLERANCE_MM = Decimal("1")   # Width must be >= card width and <= card width + 1mm
HEIGHT_TOLERANCE_MM = Decimal("5")  # Height must be >= card height and <= card height + 5mm


def to_decimal(value) -> Decimal:
    """Normalise int/float/Decimal/str measurements to Decimal (2dp) so mixed arithmetic is safe."""
    return Decimal(str(value)).quantize(Decimal("0.01"))


def fit_size(product: SleeveProduct) -> tuple[Decimal, Decimal]:
    """The size used for matching: the card size the sleeve is rated to fit when
    known, otherwise the sleeve's own size."""
    w = product.card_width_mm if product.card_width_mm is not None else product.width_mm
    h = product.card_height_mm if product.card_height_mm is not None else product.height_mm
    return to_decimal(w), to_decimal(h)


def size_waste(product: SleeveProduct, width_mm, height_mm) -> Decimal:
    """Total mm of slack between a product and a card size (lower is a tighter fit)."""
    pw, ph = fit_size(product)
    return (pw - to_decimal(width_mm)) + (ph - to_decimal(height_mm))


def fits_card(product: SleeveProduct, width_mm, height_mm) -> bool:
    """Whether a product fits a card size within the matching tolerances."""
    sw, sh = to_decimal(width_mm), to_decimal(height_mm)
    pw, ph = fit_size(product)
    return sw <= pw <= sw + WIDTH_TOLERANCE_MM and sh <= ph <= sh + HEIGHT_TOLERANCE_MM


def _availability_rank(availability: dict | None, product: SleeveProduct) -> int:
    """Distributor stock for a linked product: 0 in stock, 1 unknown/unlinked, 2 out of stock."""
    option = (availability or {}).get(product.id)
    if option is None:
        return 1
    return {"in_stock": 0, "unknown": 1, "out_of_stock": 2}[option["stock_state"]]


def order_cost(product: SleeveProduct, total_needed: int) -> float:
    """Cost of buying whole packs to cover what's still missing after current stock."""
    deficit = max(0, total_needed - product.in_stock)
    packs = -(-deficit // product.sleeves_per_pack)
    return float(product.price) * packs


def rank_products(
    products: list[SleeveProduct],
    width_mm,
    height_mm,
    quantity: int | None = None,
    availability: dict | None = None,
) -> list[SleeveProduct]:
    """THE ranking used everywhere a sleeve/card size is matched to a product.

    Every product within tolerance of the card size, best first:
      1. supply: we can get it. Either stock we hold covers `quantity`, or the
         distributor (HL, see services/sleeve_distro.py) has it in stock. These
         are equal, so a tighter fit we'd have to order beats a looser one we
         hold. Then unknown distributor stock, then out of stock.
      2. tightest size fit
      3. cheapest whole-pack order for what's still missing (needs `quantity`)
      4. cheapest per sleeve

    `quantity` is the sleeve quantity when matching a single requirement, or the
    total for a size group when building the order list. Without it, held stock
    is ignored (rule 1 uses distributor stock only) and rule 3 is skipped.
    """
    def supply_rank(p: SleeveProduct) -> int:
        if quantity is not None and p.in_stock >= quantity:
            return 0
        return _availability_rank(availability, p)

    def key(p: SleeveProduct):
        cost = order_cost(p, quantity) if quantity is not None else 0.0
        return (
            supply_rank(p),
            size_waste(p, width_mm, height_mm),
            cost,
            float(p.price) / p.sleeves_per_pack,
        )

    return sorted((p for p in products if fits_card(p, width_mm, height_mm)), key=key)


def pick_best_product(
    products: list[SleeveProduct], width_mm, height_mm, quantity: int | None = None,
    availability: dict | None = None,
) -> SleeveProduct | None:
    """The single best product for a card size from a pre-loaded product list."""
    ranked = rank_products(products, width_mm, height_mm, quantity, availability)
    return ranked[0] if ranked else None


def find_matching_products(width_mm: float, height_mm: float, db: Session) -> list[SleeveProduct]:
    """All sleeve products that fit a card size within tolerances (unranked)."""
    products = db.execute(select(SleeveProduct)).scalars().all()
    return [p for p in products if fits_card(p, width_mm, height_mm)]


def run_matching_for_all_games(
    db: Session, commit: bool = True, availability: dict | None = None
) -> dict:
    """
    Batch match: set matched_product_id on every unsleeved Sleeve record.
    `availability` is live distributor stock per product id (see
    services/sleeve_distro.product_availability); the same ranking as the order list.
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
        best = pick_best_product(
            all_products, sleeve.width_mm, sleeve.height_mm, sleeve.quantity, availability
        )
        if best:
            sleeve.matched_product_id = best.id
            matched += 1
        else:
            sleeve.matched_product_id = None
            unmatched += 1

    if commit:
        db.commit()
    else:
        db.flush()
    return {"matched": matched, "unmatched": unmatched, "total": matched + unmatched}


def compute_to_sleeve_games(db: Session) -> list[dict]:
    """
    Returns games that have at least one sleeve requirement coverable by stock.
    Each sleeve is marked as ready or not, so partial sleeving is supported.
    Games are sorted: fully coverable first, then by number of ready sleeves descending.
    """
    games = db.execute(
        select(Game).where(
            Game.has_sleeves.in_(("found", "manual")),
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


def _order_quote(product: SleeveProduct, total_needed: int, option: dict | None) -> dict:
    deficit = max(0, total_needed - product.in_stock)
    packs = -(-deficit // product.sleeves_per_pack)
    return {
        "product_id": product.id,
        "product_name": product.name,
        "distributor": product.distributor,
        "item_id": product.item_id,
        "sleeves_per_pack": product.sleeves_per_pack,
        "price_per_pack": float(product.price),
        "price_per_sleeve": round(float(product.price) / product.sleeves_per_pack, 3),
        "packs_to_buy": packs,
        "total_cost": round(float(product.price) * packs, 2),
        "current_stock": product.in_stock,
        # Live from HL when the product is linked to a distro code, else None.
        "distributor_stock": option["qty_available"] if option else None,
        "distributor_stock_state": option["stock_state"] if option else None,
        "distributor_cost_ex_gst": option["cost_price_ex_gst"] if option else None,
        "distro_code": option["distro_code"] if option else None,
        # Distributor of the best supplier, plus every linked supplier (best first).
        "distro_distributor": option.get("distributor") if option else None,
        "distro_options": option.get("options", []) if option else [],
    }


def compute_to_order_list(db: Session, availability: dict | None = None) -> list[dict]:
    """
    Returns what to order, grouped by matched product.

    `availability` maps product id -> live HL distro option (see
    services/sleeve_distro.product_availability). When given, products whose
    distributor is out of stock lose to ones that can ship, and each row lists
    the other products that would also fit as `alternatives`.

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

    all_products = db.execute(select(SleeveProduct)).scalars().all()

    # Bucket sizes by the product they'd be ordered from. Unmatched sizes get
    # their own bucket keyed by size.
    buckets: dict = {}
    for (width, height), group_sleeves in sorted(size_groups.items()):
        size_needed = sum(s.quantity for s in group_sleeves)
        ranked = rank_products(all_products, width, height, size_needed, availability)
        product = ranked[0] if ranked else None
        key = ("product", product.id) if product else ("size", width, height)
        bucket = buckets.setdefault(key, {"product": product, "sizes": [], "sleeves": [], "fitting": None})
        fitting = {p.id: p for p in ranked}
        bucket["fitting"] = fitting if bucket["fitting"] is None else {
            pid: p for pid, p in bucket["fitting"].items() if pid in fitting
        }
        bucket["sizes"].append((float(width), float(height)))
        bucket["sleeves"].extend(group_sleeves)

    order_list = []

    for bucket in buckets.values():
        product = bucket["product"]
        group_sleeves = bucket["sleeves"]
        total_needed = sum(s.quantity for s in group_sleeves)
        product_info = None

        if product:
            deficit = max(0, total_needed - product.in_stock)

            if deficit <= 0:
                continue  # Already have enough stock

            product_info = _order_quote(product, total_needed, (availability or {}).get(product.id))
            product_info["alternatives"] = [
                _order_quote(alt, total_needed, (availability or {}).get(alt.id))
                for alt in rank_products(
                    [a for pid, a in bucket["fitting"].items() if pid != product.id],
                    *bucket["sizes"][0], total_needed, availability,
                )
            ]
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
