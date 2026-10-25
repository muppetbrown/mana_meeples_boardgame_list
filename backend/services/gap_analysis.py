"""
Library gap analysis: flags where the owned collection is thin, so admin
curation (the "games to add" list) can be targeted rather than ad-hoc.

Four signals, all compared against an even split across their own buckets:
- category_gaps: how owned games are spread across the 5 Mana & Meeples
  categories (CATEGORY_KEYS).
- player_count_gaps: how many owned games support each player count,
  1 through 8, plus a "9+" bucket for large groups.
- complexity_gaps: how owned games are spread across BGG complexity bands
  (how long a game takes to learn).
- playtime_gaps: how owned games are spread across playtime bands.

A bucket is flagged as a gap when its share is below half of what an even
split across all buckets would give it. With no owned games, nothing is
flagged (there's no "thin" without a baseline to be thin against). Games
missing the relevant data (no complexity rating, no playtime) don't count
toward any bucket, the same way an uncategorized game doesn't count toward
any category - they just don't contribute a vote either way.
"""
import math
from typing import Optional, TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Game
from utils.helpers import CATEGORY_KEYS

PLAYER_COUNT_BUCKETS = ["1", "2", "3", "4", "5", "6", "7", "8", "9+"]

COMPLEXITY_BUCKETS = ["light", "medium", "heavy"]
COMPLEXITY_LABELS = {
    "light": "Light (under 2.0)",
    "medium": "Medium (2.0-3.0)",
    "heavy": "Heavy (3.0+)",
}

PLAYTIME_BUCKETS = ["quick", "standard", "long", "epic"]
PLAYTIME_LABELS = {
    "quick": "Quick (under 30 min)",
    "standard": "Standard (30-60 min)",
    "long": "Long (60-120 min)",
    "epic": "Epic (120+ min)",
}

# A bucket is a gap when its share of the collection is below this fraction
# of what an even split across all buckets would give it.
GAP_THRESHOLD_FRACTION = 0.5


class CategoryGap(TypedDict):
    category: str
    count: int
    pct_of_collection: float
    is_gap: bool
    games_needed: int


class PlayerCountGap(TypedDict):
    player_count: str
    games_supporting: int
    pct_of_collection: float
    is_gap: bool
    games_needed: int


class ComplexityGap(TypedDict):
    complexity_band: str
    count: int
    pct_of_collection: float
    is_gap: bool
    games_needed: int


class PlaytimeGap(TypedDict):
    playtime_band: str
    count: int
    pct_of_collection: float
    is_gap: bool
    games_needed: int


def _supports_player_count(players_min: Optional[int], players_max: Optional[int], n: int) -> bool:
    """Whether a game with this min/max range supports n players.

    A missing players_max is treated as unbounded (some party/large-group
    games are listed on BGG without an upper limit).
    """
    if players_min is None:
        return False
    return players_min <= n and (players_max is None or players_max >= n)


def _complexity_bucket(complexity: Optional[float]) -> Optional[str]:
    """Which complexity band a BGG weight (1-5) falls into, or None if unrated."""
    if complexity is None:
        return None
    if complexity < 2.0:
        return "light"
    if complexity < 3.0:
        return "medium"
    return "heavy"


def _playtime_bucket(playtime_min: Optional[int], playtime_max: Optional[int]) -> Optional[str]:
    """Which playtime band a game falls into, or None if neither field is set.

    Uses the upper bound when available (the worst case a table needs to plan
    around), falling back to the lower bound rather than guessing further.
    """
    minutes = playtime_max if playtime_max is not None else playtime_min
    if minutes is None:
        return None
    if minutes < 30:
        return "quick"
    if minutes < 60:
        return "standard"
    if minutes < 120:
        return "long"
    return "epic"


def compute_category_gaps(db: Session) -> list[CategoryGap]:
    """Category balance across the owned collection."""
    rows = db.execute(
        select(Game.mana_meeple_category).where(Game.status == "OWNED")
    ).all()
    total_games = len(rows)

    counts = {key: 0 for key in CATEGORY_KEYS}
    for (category,) in rows:
        if category in counts:
            counts[category] += 1

    average_share_pct = 100 / len(CATEGORY_KEYS) if CATEGORY_KEYS else 0
    gap_threshold_pct = average_share_pct * GAP_THRESHOLD_FRACTION
    # Same threshold, expressed as a game count against the current collection
    # size, so a gap's "games_needed" doesn't require re-deriving it per-bucket.
    gap_threshold_count = gap_threshold_pct / 100 * total_games

    results: list[CategoryGap] = []
    for key in CATEGORY_KEYS:
        count = counts[key]
        pct = round(count / total_games * 100, 1) if total_games else 0.0
        is_gap = total_games > 0 and pct < gap_threshold_pct
        results.append(
            CategoryGap(
                category=key,
                count=count,
                pct_of_collection=pct,
                is_gap=is_gap,
                games_needed=max(0, math.ceil(gap_threshold_count - count)) if is_gap else 0,
            )
        )
    return results


def compute_player_count_gaps(db: Session) -> list[PlayerCountGap]:
    """Player-count coverage across the owned collection."""
    rows = db.execute(
        select(Game.players_min, Game.players_max).where(Game.status == "OWNED")
    ).all()
    total_games = len(rows)

    counts: dict[str, int] = {}
    for bucket in PLAYER_COUNT_BUCKETS:
        n = 9 if bucket == "9+" else int(bucket)
        counts[bucket] = sum(
            1 for players_min, players_max in rows
            if _supports_player_count(players_min, players_max, n)
        )

    average_count = sum(counts.values()) / len(PLAYER_COUNT_BUCKETS)
    gap_threshold = average_count * GAP_THRESHOLD_FRACTION

    results: list[PlayerCountGap] = []
    for bucket in PLAYER_COUNT_BUCKETS:
        count = counts[bucket]
        pct = round(count / total_games * 100, 1) if total_games else 0.0
        is_gap = total_games > 0 and count < gap_threshold
        results.append(
            PlayerCountGap(
                player_count=bucket,
                games_supporting=count,
                pct_of_collection=pct,
                is_gap=is_gap,
                games_needed=max(0, math.ceil(gap_threshold - count)) if is_gap else 0,
            )
        )
    return results


def compute_complexity_gaps(db: Session) -> list[ComplexityGap]:
    """Complexity-band balance across the owned collection."""
    rows = db.execute(
        select(Game.complexity).where(Game.status == "OWNED")
    ).all()
    total_games = len(rows)

    counts = {band: 0 for band in COMPLEXITY_BUCKETS}
    for (complexity,) in rows:
        band = _complexity_bucket(complexity)
        if band in counts:
            counts[band] += 1

    average_share_pct = 100 / len(COMPLEXITY_BUCKETS)
    gap_threshold_pct = average_share_pct * GAP_THRESHOLD_FRACTION
    gap_threshold_count = gap_threshold_pct / 100 * total_games

    results: list[ComplexityGap] = []
    for band in COMPLEXITY_BUCKETS:
        count = counts[band]
        pct = round(count / total_games * 100, 1) if total_games else 0.0
        is_gap = total_games > 0 and pct < gap_threshold_pct
        results.append(
            ComplexityGap(
                complexity_band=band,
                count=count,
                pct_of_collection=pct,
                is_gap=is_gap,
                games_needed=max(0, math.ceil(gap_threshold_count - count)) if is_gap else 0,
            )
        )
    return results


def compute_playtime_gaps(db: Session) -> list[PlaytimeGap]:
    """Playtime-band balance across the owned collection."""
    rows = db.execute(
        select(Game.playtime_min, Game.playtime_max).where(Game.status == "OWNED")
    ).all()
    total_games = len(rows)

    counts = {band: 0 for band in PLAYTIME_BUCKETS}
    for playtime_min, playtime_max in rows:
        band = _playtime_bucket(playtime_min, playtime_max)
        if band in counts:
            counts[band] += 1

    average_share_pct = 100 / len(PLAYTIME_BUCKETS)
    gap_threshold_pct = average_share_pct * GAP_THRESHOLD_FRACTION
    gap_threshold_count = gap_threshold_pct / 100 * total_games

    results: list[PlaytimeGap] = []
    for band in PLAYTIME_BUCKETS:
        count = counts[band]
        pct = round(count / total_games * 100, 1) if total_games else 0.0
        is_gap = total_games > 0 and pct < gap_threshold_pct
        results.append(
            PlaytimeGap(
                playtime_band=band,
                count=count,
                pct_of_collection=pct,
                is_gap=is_gap,
                games_needed=max(0, math.ceil(gap_threshold_count - count)) if is_gap else 0,
            )
        )
    return results


def annotate_candidate(game: Game, gaps: dict) -> dict:
    """Which currently-flagged gaps a candidate game (not yet owned) would help fill.

    `gaps` is the payload from compute_library_gaps(). Used to surface, next
    to each 'games to add' entry, why it might be worth buying - including,
    per matched gap, how many more owned games (beyond this one) it would
    still take to clear that gap entirely (`*_games_needed`), so ties on
    total gaps filled can be told apart by how close each one gets you.
    """
    category_gap = next(
        (g for g in gaps["category_gaps"] if g["category"] == game.mana_meeple_category and g["is_gap"]),
        None,
    )

    matching_player_count_gaps = []
    player_count_games_needed = {}
    for g in gaps["player_count_gaps"]:
        if not g["is_gap"]:
            continue
        n = 9 if g["player_count"] == "9+" else int(g["player_count"])
        if _supports_player_count(game.players_min, game.players_max, n):
            matching_player_count_gaps.append(g["player_count"])
            player_count_games_needed[g["player_count"]] = g.get("games_needed", 0)

    complexity_band = _complexity_bucket(game.complexity)
    complexity_gap = next(
        (g for g in gaps["complexity_gaps"] if g["complexity_band"] == complexity_band and g["is_gap"]),
        None,
    )

    playtime_band = _playtime_bucket(game.playtime_min, game.playtime_max)
    playtime_gap = next(
        (g for g in gaps["playtime_gaps"] if g["playtime_band"] == playtime_band and g["is_gap"]),
        None,
    )

    return {
        "category_is_gap": category_gap is not None,
        "category_games_needed": category_gap.get("games_needed", 0) if category_gap else 0,
        "matching_player_count_gaps": matching_player_count_gaps,
        "player_count_games_needed": player_count_games_needed,
        "complexity_is_gap": complexity_gap is not None,
        "complexity_games_needed": complexity_gap.get("games_needed", 0) if complexity_gap else 0,
        "playtime_is_gap": playtime_gap is not None,
        "playtime_games_needed": playtime_gap.get("games_needed", 0) if playtime_gap else 0,
    }


def games_needed_values(gap_match: Optional[dict]) -> list[int]:
    """games_needed for each gap a candidate's gap_match actually fills - i.e.
    how many more owned games it would still take, per matched gap, to clear
    it. Used to break ties on total gaps filled: a candidate that would fully
    close a gap on its own (a 0 or 1 here) is worth more than one chipping
    away at a gap that needs several more games yet.
    """
    if not gap_match:
        return []
    values = []
    if gap_match.get("category_is_gap"):
        values.append(gap_match.get("category_games_needed", 0))
    player_count_needed = gap_match.get("player_count_games_needed") or {}
    for count in gap_match.get("matching_player_count_gaps") or []:
        values.append(player_count_needed.get(count, 0))
    if gap_match.get("complexity_is_gap"):
        values.append(gap_match.get("complexity_games_needed", 0))
    if gap_match.get("playtime_is_gap"):
        values.append(gap_match.get("playtime_games_needed", 0))
    return values


def compute_library_gaps(db: Session) -> dict:
    """Full gap-analysis payload for the admin 'games to add' dashboard."""
    total_games = db.execute(
        select(Game.id).where(Game.status == "OWNED")
    ).all()
    return {
        "total_games": len(total_games),
        "category_gaps": compute_category_gaps(db),
        "player_count_gaps": compute_player_count_gaps(db),
        "complexity_gaps": compute_complexity_gaps(db),
        "playtime_gaps": compute_playtime_gaps(db),
    }
