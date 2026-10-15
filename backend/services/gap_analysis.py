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


class PlayerCountGap(TypedDict):
    player_count: str
    games_supporting: int
    pct_of_collection: float
    is_gap: bool


class ComplexityGap(TypedDict):
    complexity_band: str
    count: int
    pct_of_collection: float
    is_gap: bool


class PlaytimeGap(TypedDict):
    playtime_band: str
    count: int
    pct_of_collection: float
    is_gap: bool


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

    results: list[CategoryGap] = []
    for key in CATEGORY_KEYS:
        count = counts[key]
        pct = round(count / total_games * 100, 1) if total_games else 0.0
        results.append(
            CategoryGap(
                category=key,
                count=count,
                pct_of_collection=pct,
                is_gap=total_games > 0 and pct < gap_threshold_pct,
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
        results.append(
            PlayerCountGap(
                player_count=bucket,
                games_supporting=count,
                pct_of_collection=pct,
                is_gap=total_games > 0 and count < gap_threshold,
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

    results: list[ComplexityGap] = []
    for band in COMPLEXITY_BUCKETS:
        count = counts[band]
        pct = round(count / total_games * 100, 1) if total_games else 0.0
        results.append(
            ComplexityGap(
                complexity_band=band,
                count=count,
                pct_of_collection=pct,
                is_gap=total_games > 0 and pct < gap_threshold_pct,
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

    results: list[PlaytimeGap] = []
    for band in PLAYTIME_BUCKETS:
        count = counts[band]
        pct = round(count / total_games * 100, 1) if total_games else 0.0
        results.append(
            PlaytimeGap(
                playtime_band=band,
                count=count,
                pct_of_collection=pct,
                is_gap=total_games > 0 and pct < gap_threshold_pct,
            )
        )
    return results


def annotate_candidate(game: Game, gaps: dict) -> dict:
    """Which currently-flagged gaps a candidate game (not yet owned) would help fill.

    `gaps` is the payload from compute_library_gaps(). Used to surface, next
    to each 'games to add' entry, why it might be worth buying.
    """
    category_is_gap = any(
        g["category"] == game.mana_meeple_category and g["is_gap"]
        for g in gaps["category_gaps"]
    )
    matching_player_count_gaps = [
        g["player_count"]
        for g in gaps["player_count_gaps"]
        if g["is_gap"]
        and _supports_player_count(
            game.players_min, game.players_max, 9 if g["player_count"] == "9+" else int(g["player_count"])
        )
    ]
    complexity_band = _complexity_bucket(game.complexity)
    complexity_is_gap = any(
        g["complexity_band"] == complexity_band and g["is_gap"]
        for g in gaps["complexity_gaps"]
    )
    playtime_band = _playtime_bucket(game.playtime_min, game.playtime_max)
    playtime_is_gap = any(
        g["playtime_band"] == playtime_band and g["is_gap"]
        for g in gaps["playtime_gaps"]
    )
    return {
        "category_is_gap": category_is_gap,
        "matching_player_count_gaps": matching_player_count_gaps,
        "complexity_is_gap": complexity_is_gap,
        "playtime_is_gap": playtime_is_gap,
    }


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
