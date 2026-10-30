# services/sleeve_distro.py
"""
Connects sleeve products to the HL Timaru distro_codes catalogue.

A SleeveProduct optionally stores a (hl_distributor, hl_distro_code) key; name,
cost and distributor stock are read live from HL. This module also mines the
rest of the catalogue for sleeves that aren't in sleeve_products yet and works
out which of them would fit a size we currently need sleeves for.

Sizes and pack counts for catalogue rows are parsed from the listing name, so
they are best-effort: anything that can't be parsed confidently is left None
rather than guessed.
"""
import logging
import re
from collections import defaultdict
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Game, Sleeve, SleeveProduct
from services.distro_availability import build_option
from services.hl_stock_service import HLStockServiceError, fetch_distro_codes_by_key, fetch_sleeve_catalogue

logger = logging.getLogger(__name__)

# Same tolerances as services/sleeve_matching.py (kept literal to avoid a circular import).
WIDTH_TOLERANCE_MM = Decimal("1")
HEIGHT_TOLERANCE_MM = Decimal("5")

MIN_CARD_MM = 20
MAX_CARD_MM = 400

_MM_SIZE = re.compile(r"(\d{2,3}(?:\.\d+)?)\s*(?:mm)?\s*[x×]\s*(\d{2,3}(?:\.\d+)?)\s*mm", re.IGNORECASE)
# Geek Culture codes carry the size, e.g. 03BCW1-BG-59X92 (also rescues names truncated mid-size).
_CODE_SIZE = re.compile(r"(?<!\d)(\d{2,3})X(\d{2,3})(?!\d)")
_PACK_PATTERNS = (
    re.compile(r"(\d{1,4})\s*sleeves?\s*per\s*pack", re.IGNORECASE),
    re.compile(r"\b(\d{1,4})\s*(?:ct|count|pcs|pk)\b", re.IGNORECASE),
    re.compile(r"\((\d{2,4})\)"),
    re.compile(r"^\s*(\d{2,4})\s+[A-Za-z]"),
)


def _valid_size(a: float, b: float) -> Optional[Tuple[float, float]]:
    if not (MIN_CARD_MM <= a <= MAX_CARD_MM and MIN_CARD_MM <= b <= MAX_CARD_MM):
        return None
    return (min(a, b), max(a, b))


def parse_size_mm(name: str, code: str = "") -> Optional[Tuple[float, float]]:
    """(width, height) in mm from a listing name or code, width <= height; None if not found."""
    m = _MM_SIZE.search(name or "")
    if m:
        size = _valid_size(float(m.group(1)), float(m.group(2)))
        if size:
            return size
    m = _CODE_SIZE.search((code or "").upper())
    if m:
        return _valid_size(float(m.group(1)), float(m.group(2)))
    return None


def parse_pack_size(name: str) -> Optional[int]:
    """Sleeves per pack from a listing name, if it states one."""
    for pattern in _PACK_PATTERNS:
        m = pattern.search(name or "")
        if m:
            n = int(m.group(1))
            if n > 0:
                return n
    return None


def stock_state(qty: Optional[int]) -> str:
    """in_stock | unknown | out_of_stock. Distributors report 0 or negatives for none."""
    if qty is None:
        return "unknown"
    return "in_stock" if qty > 0 else "out_of_stock"


def with_stock_state(option: dict) -> dict:
    option["stock_state"] = stock_state(option["qty_available"])
    return option


def product_availability(products: Iterable[SleeveProduct]) -> Optional[Dict[int, dict]]:
    """Live HL option (name, cost, distributor stock) per linked product id.

    None when HL can't be read, so callers fall back to ordering without
    distributor stock rather than failing. Products with no link, or whose code
    is no longer active in HL, are simply absent from the result.
    """
    keyed = [p for p in products if p.hl_distributor and p.hl_distro_code]
    if not keyed:
        return {}
    try:
        rows = fetch_distro_codes_by_key([(p.hl_distributor, p.hl_distro_code) for p in keyed])
    except HLStockServiceError as e:
        logger.warning(f"Sleeve distributor availability unavailable: {e}")
        return None
    by_key = {(r["distributor"], r["distro_code"]): r for r in rows}
    return {
        p.id: with_stock_state(build_option(by_key[(p.hl_distributor, p.hl_distro_code)], None))
        for p in keyed
        if (p.hl_distributor, p.hl_distro_code) in by_key
    }


def auto_link_products(db: Session) -> dict:
    """Link unlinked sleeve products to catalogue rows.

    Match order: (distributor, item_id) exactly (case-insensitive distributor),
    then an exact case-insensitive name within the same distributor when that
    name is unambiguous. Never overwrites an existing link.
    """
    catalogue = fetch_sleeve_catalogue()
    by_code = {(r["distributor"].upper(), r["distro_code"]): r for r in catalogue}
    names: Dict[Tuple[str, str], List[dict]] = defaultdict(list)
    for r in catalogue:
        names[(r["distributor"].upper(), r["name"].strip().lower())].append(r)

    products = db.execute(select(SleeveProduct)).scalars().all()
    linked, already, unmatched = [], 0, []
    for p in products:
        if p.hl_distributor and p.hl_distro_code:
            already += 1
            continue
        dist = (p.distributor or "").strip().upper()
        row = by_code.get((dist, (p.item_id or "").strip()))
        if row is None:
            candidates = names.get((dist, p.name.strip().lower()), [])
            row = candidates[0] if len(candidates) == 1 else None
        if row is None:
            unmatched.append({"id": p.id, "name": p.name, "distributor": p.distributor})
            continue
        p.hl_distributor, p.hl_distro_code = row["distributor"], row["distro_code"]
        linked.append({"id": p.id, "name": p.name, "distro_code": row["distro_code"]})
    db.commit()
    return {"linked": len(linked), "already_linked": already, "unmatched": unmatched, "linked_items": linked}


def needed_sizes(db: Session) -> List[dict]:
    """Card sizes still needing sleeves for owned, not-yet-sleeved games, with demand."""
    rows = db.execute(
        select(Sleeve.width_mm, Sleeve.height_mm, Sleeve.quantity, Sleeve.game_id)
        .join(Game, Sleeve.game_id == Game.id)
        .where(
            (Sleeve.is_sleeved == False) | (Sleeve.is_sleeved.is_(None)),  # noqa: E712
            (Game.is_sleeved == False) | (Game.is_sleeved.is_(None)),  # noqa: E712
            Game.status == "OWNED",
        )
    ).all()
    groups: Dict[Tuple[Decimal, Decimal], dict] = {}
    for w, h, qty, game_id in rows:
        g = groups.setdefault((Decimal(str(w)), Decimal(str(h))), {"quantity": 0, "games": set()})
        g["quantity"] += qty
        g["games"].add(game_id)
    return [
        {"width_mm": w, "height_mm": h, "total_needed": g["quantity"], "games_count": len(g["games"])}
        for (w, h), g in sorted(groups.items())
    ]


def _fits(size: Tuple[float, float], need_w: Decimal, need_h: Decimal) -> bool:
    w, h = Decimal(str(size[0])), Decimal(str(size[1]))
    return need_w <= w <= need_w + WIDTH_TOLERANCE_MM and need_h <= h <= need_h + HEIGHT_TOLERANCE_MM


def _covered_sizes(products: Iterable[SleeveProduct]) -> set:
    return {
        (Decimal(str(p.card_width_mm if p.card_width_mm is not None else p.width_mm)),
         Decimal(str(p.card_height_mm if p.card_height_mm is not None else p.height_mm)))
        for p in products
    }


def unlisted_sleeves(db: Session, include_all: bool = False) -> List[dict]:
    """Catalogue sleeves that aren't linked to a sleeve product.

    Each row carries the sizes we currently need that it would fit. By default
    only rows with a parseable size that fits a needed size are returned;
    include_all adds every sleeve with a parseable size (e.g. to browse ahead
    of games being added). Sorted: fills a size nothing in inventory covers
    first, then in stock at the distributor, then cheapest per sleeve.
    """
    catalogue = fetch_sleeve_catalogue()
    products = db.execute(select(SleeveProduct)).scalars().all()
    linked = {(p.hl_distributor, p.hl_distro_code) for p in products if p.hl_distributor and p.hl_distro_code}
    needs = needed_sizes(db)

    # A need counts as covered when some product's fit size satisfies it.
    def covered(need: dict) -> bool:
        return any(
            _fits((float(w), float(h)), need["width_mm"], need["height_mm"]) for (w, h) in _covered_sizes(products)
        )

    result = []
    for row in catalogue:
        if (row["distributor"], row["distro_code"]) in linked:
            continue
        size = parse_size_mm(row["name"], row["distro_code"])
        if size is None:
            continue
        fits = [
            {
                "width_mm": float(n["width_mm"]),
                "height_mm": float(n["height_mm"]),
                "total_needed": n["total_needed"],
                "games_count": n["games_count"],
                "uncovered": not covered(n),
            }
            for n in needs
            if _fits(size, n["width_mm"], n["height_mm"])
        ]
        if not fits and not include_all:
            continue
        pack = parse_pack_size(row["name"])
        cost = float(row["cost_price_ex_gst"]) if row["cost_price_ex_gst"] is not None else None
        option = with_stock_state(build_option(row, None))
        option.update(
            {
                "width_mm": size[0],
                "height_mm": size[1],
                "sleeves_per_pack": pack,
                "cost_per_sleeve": round(cost / pack, 3) if cost is not None and pack else None,
                "hl_internal_id": row["hl_internal_id"],
                "hl_stock": row["hl_stock"],
                "fits": fits,
                "fills_gap": any(f["uncovered"] for f in fits),
            }
        )
        result.append(option)

    result.sort(
        key=lambda o: (
            not o["fills_gap"],
            {"in_stock": 0, "unknown": 1, "out_of_stock": 2}[o["stock_state"]],
            o["cost_per_sleeve"] if o["cost_per_sleeve"] is not None else float("inf"),
            o["distro_product_name"],
        )
    )
    return result
