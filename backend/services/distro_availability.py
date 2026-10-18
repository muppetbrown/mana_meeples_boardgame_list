# services/distro_availability.py
"""
Which NZ distributors can supply a given game, by fuzzy-matching its title
against the HL Timaru distro_codes catalogue.

A match is a suggestion for staff to confirm, same as hl_stock_matching: the
matched distributor product name and score are always returned alongside it.
Matching is deliberately stricter than the HL-product matcher (token_sort_ratio
rather than WRatio) because the catalogue is full of expansions and bundles
that WRatio's partial matching would treat as the base game ("Wingspan" vs
"Wingspan Oceania Expansion").
"""
import logging
import re
import threading
import time
import unicodedata
from typing import Any, Dict, Iterable, List, Optional

from rapidfuzz import fuzz, process

from services.hl_stock_service import HLStockServiceError, fetch_distro_catalogue

logger = logging.getLogger(__name__)

DISTRO_MATCH_THRESHOLD = 88
MAX_OPTIONS_PER_GAME = 5
CATALOGUE_TTL_SECONDS = 600

# Words that appear on distributor listings but not in BGG titles.
_NOISE = re.compile(r"\b(the|board game|card game|boardgame|game)\b")

_cache_lock = threading.Lock()
_cache: Dict[str, Any] = {"loaded_at": 0.0, "rows": None}


def normalize_title(title: str) -> str:
    text = unicodedata.normalize("NFKD", title or "").encode("ascii", "ignore").decode()
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = _NOISE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def _load_catalogue() -> Optional[List[dict]]:
    """Catalogue rows with a precomputed normalised name, cached briefly.
    None if HL isn't configured/reachable (callers treat that as 'unknown')."""
    with _cache_lock:
        if _cache["rows"] is not None and time.monotonic() - _cache["loaded_at"] < CATALOGUE_TTL_SECONDS:
            return _cache["rows"]
        try:
            rows = fetch_distro_catalogue()
        except HLStockServiceError as e:
            logger.warning(f"Distributor availability unavailable: {e}")
            return None
        for row in rows:
            row["norm"] = normalize_title(row["name"])
        rows = [r for r in rows if r["norm"]]
        _cache.update(loaded_at=time.monotonic(), rows=rows)
        return rows


def _stock_rank(qty: Optional[int]) -> int:
    # in stock (0) < stock unknown (1) < out of stock (2)
    if qty is None:
        return 1
    return 0 if qty > 0 else 2


def _summarise(options: List[dict]) -> str:
    if not options:
        return "not_listed"
    ranks = {_stock_rank(o["qty_available"]) for o in options}
    if 0 in ranks:
        return "in_stock"
    if 1 in ranks:
        return "listed"
    return "out_of_stock"


def availability_for_titles(titles: Iterable[str]) -> Optional[Dict[str, dict]]:
    """Map each title to {"status", "options"}; None if the catalogue is
    unavailable or empty (so callers don't mislabel everything 'not listed').

    status: in_stock | listed (stock unknown) | out_of_stock | not_listed
    options: best match per distributor, in-stock first then cheapest.
    """
    catalogue = _load_catalogue()
    if not catalogue:
        return None

    choices = [r["norm"] for r in catalogue]
    result: Dict[str, dict] = {}
    for title in titles:
        norm = normalize_title(title)
        best_per_distributor: Dict[str, dict] = {}
        if norm:
            matches = process.extract(
                norm, choices, scorer=fuzz.token_sort_ratio,
                score_cutoff=DISTRO_MATCH_THRESHOLD, limit=None,
            )
            for _, score, idx in matches:
                row = catalogue[idx]
                option = {
                    "distributor": row["distributor"],
                    "distro_code": row["distro_code"],
                    "distro_product_name": row["name"],
                    "cost_price_ex_gst": (
                        float(row["cost_price_ex_gst"]) if row["cost_price_ex_gst"] is not None else None
                    ),
                    "qty_available": row["qty_available"],
                    "qty_updated_at": row["qty_updated_at"].isoformat() if row["qty_updated_at"] else None,
                    "match_score": round(score, 1),
                }
                current = best_per_distributor.get(row["distributor"])
                if current is None or (-score, _stock_rank(row["qty_available"])) < (
                    -current["match_score"], _stock_rank(current["qty_available"])
                ):
                    best_per_distributor[row["distributor"]] = option

        options = sorted(
            best_per_distributor.values(),
            key=lambda o: (
                _stock_rank(o["qty_available"]),
                o["cost_price_ex_gst"] if o["cost_price_ex_gst"] is not None else float("inf"),
            ),
        )[:MAX_OPTIONS_PER_GAME]
        result[title] = {"status": _summarise(options), "options": options}
    return result
