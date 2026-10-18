# services/hl_signal_fit.py
"""
Scores HL Timaru stock signals against the library's gaps, so the "Selling
Well at HL Timaru" list can be ordered by how well each product fills what
the collection is thin on, not just by sales.

A product already matched to a library game is scored from that game. An
unmatched one has no player count / complexity / playtime / category, so it is
looked up on BGG once and the result cached on its HLStockLink. BGG is
rate-limited (~10 requests/minute) so lookups run in a background task and the
list scores whatever is cached so far; each refresh picks up more.
"""
import logging
from datetime import timedelta
from types import SimpleNamespace
from typing import Any, Dict, Optional

from rapidfuzz import fuzz
from sqlalchemy import select

from bgg_service import BGGServiceError, fetch_bgg_thing, search_bgg
from models import HLStockLink, Game, utc_now
from services.gap_analysis import annotate_candidate
from utils.helpers import categorize_game

logger = logging.getLogger(__name__)

# BGG search result must resemble the (often abbreviated) HL product name at
# least this much (rapidfuzz WRatio, 0-100) to be trusted. Looser than the
# library matcher because HL names are abbreviated, so the matched BGG title
# and score are always shown for staff to sanity-check.
BGG_MATCH_THRESHOLD = 75
# A product BGG couldn't place is retried after this long.
BGG_RETRY_AFTER = timedelta(days=7)
# Only the best sellers are scored/ranked, which bounds BGG lookups.
SCORING_POOL_SIZE = 30

_in_flight: set[int] = set()


def needs_bgg_lookup(link: HLStockLink) -> bool:
    if link.game_id is not None or link.dismissed:
        return False
    if link.bgg_enriched_at is None:
        return True
    # The column is tz-naive; compare naive-to-naive whatever utc_now() returns.
    age = utc_now().replace(tzinfo=None) - link.bgg_enriched_at.replace(tzinfo=None)
    return link.bgg_id is None and age > BGG_RETRY_AFTER


def gaps_filled(gap_match: Optional[Dict[str, Any]]) -> int:
    """How many library gaps a gap_match would fill (same counting as the buy list)."""
    gap_match = gap_match or {}
    count = 1 if gap_match.get("category_is_gap") else 0
    count += len(gap_match.get("matching_player_count_gaps") or [])
    count += 1 if gap_match.get("complexity_is_gap") else 0
    count += 1 if gap_match.get("playtime_is_gap") else 0
    return count


def fit_for_link(link: HLStockLink, game: Optional[Game], gaps: Dict[str, Any]) -> Dict[str, Any]:
    """Gap fit for one HL product: from its library game if linked, else from
    its cached BGG lookup, else unscored."""
    if game is not None:
        gap_match = annotate_candidate(game, gaps)
        return {"scored": True, "source": "library", "gaps_filled": gaps_filled(gap_match),
                "gap_match": gap_match, "bgg": None}

    if link.bgg_enriched_at is not None and link.bgg_id is not None:
        candidate = SimpleNamespace(
            mana_meeple_category=link.bgg_category,
            players_min=link.bgg_players_min,
            players_max=link.bgg_players_max,
            complexity=link.bgg_complexity,
            playtime_min=link.bgg_playtime_min,
            playtime_max=link.bgg_playtime_max,
        )
        gap_match = annotate_candidate(candidate, gaps)
        return {
            "scored": True,
            "source": "bgg",
            "gaps_filled": gaps_filled(gap_match),
            "gap_match": gap_match,
            "bgg": {
                "bgg_id": link.bgg_id,
                "title": link.bgg_title,
                "year": link.bgg_year,
                "match_score": link.bgg_match_score,
            },
        }

    return {"scored": False, "source": None, "gaps_filled": None, "gap_match": None, "bgg": None}


async def _enrich_link(link: HLStockLink) -> None:
    """Look one HL product up on BGG and cache the result on the link. Leaves
    bgg_enriched_at unset if BGG errored (so it's retried next time)."""
    candidates = await search_bgg(link.hl_product_name, limit=5)

    best, best_score = None, 0.0
    for candidate in candidates:
        score = fuzz.WRatio(link.hl_product_name, candidate["title"])
        if score > best_score:
            best, best_score = candidate, score

    if best is None or best_score < BGG_MATCH_THRESHOLD:
        link.bgg_id = None
        link.bgg_match_score = best_score or None
        link.bgg_enriched_at = utc_now()
        return

    data = await fetch_bgg_thing(best["bgg_id"])
    link.bgg_id = best["bgg_id"]
    link.bgg_title = data.get("title") or best["title"]
    link.bgg_year = data.get("year") or best.get("year")
    link.bgg_match_score = best_score
    link.bgg_players_min = data.get("players_min")
    link.bgg_players_max = data.get("players_max")
    link.bgg_playtime_min = data.get("playtime_min")
    link.bgg_playtime_max = data.get("playtime_max")
    link.bgg_complexity = data.get("complexity")
    link.bgg_category = categorize_game(data.get("categories") or [])
    link.bgg_enriched_at = utc_now()


async def enrich_links_task(hl_internal_ids: list[int]) -> None:
    """Background task: BGG-enrich the given HL products, best seller first.
    Skips products another run is already handling, and stops early if BGG is
    unavailable. Commits per product so progress survives a later failure."""
    # Local import so a test session patched over database.SessionLocal is picked up.
    from database import SessionLocal

    db = SessionLocal()
    try:
        for hl_internal_id in hl_internal_ids:
            if hl_internal_id in _in_flight:
                continue
            _in_flight.add(hl_internal_id)
            try:
                link = db.execute(
                    select(HLStockLink).where(HLStockLink.hl_internal_id == hl_internal_id)
                ).scalar_one_or_none()
                if link is None or not needs_bgg_lookup(link):
                    continue
                try:
                    await _enrich_link(link)
                    db.commit()
                except BGGServiceError as e:
                    logger.warning(f"BGG unavailable, stopping HL enrichment: {e}")
                    db.rollback()
                    return
                except Exception as e:
                    logger.error(f"BGG enrichment failed for HL product {hl_internal_id}: {e}")
                    db.rollback()
            finally:
                _in_flight.discard(hl_internal_id)
    finally:
        db.close()
