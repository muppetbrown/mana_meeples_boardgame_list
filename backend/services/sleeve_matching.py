"""
Sleeve product matching service.

Matches game sleeve requirements to available sleeve products based on size tolerances.
Provides ordering recommendations and stock-based sleeving readiness checks.
"""
from collections import defaultdict
from decimal import Decimal
from sqlalchemy import select, and_, func
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


def find_matching_products(width_mm: float, height_mm: float, db: Session) -> list[SleeveProduct]:
    """Find all sleeve products that fit a given card size within tolerances."""
    width_mm = to_decimal(width_mm)
    height_mm = to_decimal(height_mm)
    fit_w = func.coalesce(SleeveProduct.card_width_mm, SleeveProduct.width_mm)
    fit_h = func.coalesce(SleeveProduct.card_height_mm, SleeveProduct.height_mm)
    return db.execute(
        select(SleeveProduct).where(
            and_(
                fit_w >= width_mm,
                fit_w <= width_mm + WIDTH_TOLERANCE_MM,
                fit_h >= height_mm,
                fit_h <= height_mm + HEIGHT_TOLERANCE_MM,
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


def rank_products_for_order(
    width_mm, height_mm, db: Session, availability: dict | None = None,
    total_needed: int | None = None,
) -> list[SleeveProduct]:
    """Every product that fits a card size, best one to order first.

    Distributor stock (from HL, see services/sleeve_distro.py) outranks fit and
    price: all candidates are within tolerance, and a sleeve nobody can supply
    is a worse buy than a slightly looser one that ships. Among equally good
    fits, when `total_needed` is known the cheapest actual order wins (so stock
    already held of a product, and pack-size rounding, are taken into account);
    otherwise cheapest per sleeve.
    """
    def cost(p: SleeveProduct) -> float:
        return order_cost(p, total_needed) if total_needed is not None else 0.0

    return sorted(
        find_matching_products(width_mm, height_mm, db),
        key=lambda p: (
            _availability_rank(availability, p),
            size_waste(p, width_mm, height_mm),
            cost(p),
            float(p.price) / p.sleeves_per_pack,
        ),
    )


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


def pick_best_product(
    products: list[SleeveProduct], width_mm, height_mm, quantity: int | None = None
) -> SleeveProduct | None:
    """Pick the best product for a card size from a pre-loaded product list.

    Uses the same tolerances as find_matching_products: an exact size match
    (e.g. 59 x 91 card, 59 x 91 sleeve) always qualifies. When `quantity` is
    given, a product whose stock already covers it wins first, so the sleeve
    shows as ready to sleeve instead of being matched to a tighter fit with
    no stock. Then best size fit, then prefer in-stock, then cheapest per sleeve.
    """
    sw = to_decimal(width_mm)
    sh = to_decimal(height_mm)
    candidates = [
        p for p in products
        if sw <= fit_size(p)[0] <= sw + WIDTH_TOLERANCE_MM
        and sh <= fit_size(p)[1] <= sh + HEIGHT_TOLERANCE_MM
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda p: (
        0 if quantity is None or p.in_stock >= quantity else 1,
        size_waste(p, sw, sh),
        0 if p.in_stock > 0 else 1,
        float(p.price) / p.sleeves_per_pack,
    ))


def run_matching_for_all_games(db: Session, commit: bool = True) -> dict:
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
        best = pick_best_product(all_products, sleeve.width_mm, sleeve.height_mm, sleeve.quantity)
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

    # Bucket sizes by the product they'd be ordered from. Unmatched sizes get
    # their own bucket keyed by size.
    buckets: dict = {}
    for (width, height), group_sleeves in sorted(size_groups.items()):
        size_needed = sum(s.quantity for s in group_sleeves)
        ranked = rank_products_for_order(width, height, db, availability, size_needed)
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
                for alt in sorted(
                    (a for pid, a in bucket["fitting"].items() if pid != product.id),
                    key=lambda a: (
                        _availability_rank(availability, a),
                        order_cost(a, total_needed),
                        float(a.price) / a.sleeves_per_pack,
                    ),
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
