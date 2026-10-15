"""
Library gap analysis: flags where the owned collection is thin, so admin
curation (the "games to add" list) can be targeted rather than ad-hoc.

Two signals, both compared against an even split across their own buckets:
- category_gaps: how owned games are spread across the 5 Mana & Meeples
  categories (CATEGORY_KEYS).
- player_count_gaps: how many owned games support each player count,
  1 through 8, plus a "9+" bucket for large groups.

A bucket is flagged as a gap when its share is below half of what an even
split across all buckets would give it. With no owned games, nothing is
flagged (there's no "thin" without a baseline to be thin against).
"""
from typing import Optional, TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Game
from utils.helpers import CATEGORY_KEYS

PLAYER_COUNT_BUCKETS = ["1", "2", "3", "4", "5", "6", "7", "8", "9+"]

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


def _supports_player_count(players_min: Optional[int], players_max: Optional[int], n: int) -> bool:
    """Whether a game with this min/max range supports n players.

    A missing players_max is treated as unbounded (some party/large-group
    games are listed on BGG without an upper limit).
    """
    if players_min is None:
        return False
    return players_min <= n and (players_max is None or players_max >= n)


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
    return {
        "category_is_gap": category_is_gap,
        "matching_player_count_gaps": matching_player_count_gaps,
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
    }
