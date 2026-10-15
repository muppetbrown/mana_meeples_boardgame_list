# services/award_winners.py
"""
Curated list of major "game of the year" award winners - Spiel des Jahres,
Kennerspiel des Jahres, and Kinderspiel des Jahres - surfaced on the buy
list tab as a discovery signal alongside the BGG Hot List.

There's no BGG API endpoint for "every winner of award X" (the XML API only
exposes per-game honor links once you already know a bgg_id), so this list
is hand-maintained the same way the rest of this project curates content
(CATEGORY_KEYS, NZ designer flags): update AWARD_WINNERS once a year when
each award's new winner is announced (usually late July for all three).

No bgg_id is hardcoded for each entry - a wrong guessed numeric id would be
worse than none. Instead each title is best-effort matched against BGG by
name at request time, the same approach already used to resolve AI-suggested
games in game_suggestion_service.py.
"""
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from bgg_service import search_bgg
from models import BuyListGame, Game

logger = logging.getLogger(__name__)

AWARD_LABELS = {
    "spiel_des_jahres": "Spiel des Jahres",
    "kennerspiel_des_jahres": "Kennerspiel des Jahres",
    "kinderspiel_des_jahres": "Kinderspiel des Jahres",
}

# Most recent year first within each award. Add next year's three winners
# here once announced; no other code changes are needed.
AWARD_WINNERS: List[Dict[str, Any]] = [
    {"year": 2025, "award": "spiel_des_jahres", "title": "Bomb Busters"},
    {"year": 2025, "award": "kennerspiel_des_jahres", "title": "Endeavor: Deep Sea"},
    {"year": 2025, "award": "kinderspiel_des_jahres", "title": "Topp die Torte"},
    {"year": 2024, "award": "spiel_des_jahres", "title": "Sky Team"},
    {"year": 2024, "award": "kennerspiel_des_jahres", "title": "Daybreak"},
    {"year": 2024, "award": "kinderspiel_des_jahres", "title": "Magic Keys"},
    {"year": 2023, "award": "spiel_des_jahres", "title": "Dorfromantik: The Board Game"},
    {"year": 2023, "award": "kennerspiel_des_jahres", "title": "Challengers!"},
    {"year": 2023, "award": "kinderspiel_des_jahres", "title": "Mysterium Kids: Captain Echo's Treasure"},
    {"year": 2022, "award": "spiel_des_jahres", "title": "Cascadia"},
    {"year": 2022, "award": "kennerspiel_des_jahres", "title": "Living Forest"},
    {"year": 2022, "award": "kinderspiel_des_jahres", "title": "Magic Mountain"},
    {"year": 2021, "award": "spiel_des_jahres", "title": "MicroMacro: Crime City"},
    {"year": 2021, "award": "kennerspiel_des_jahres", "title": "Paleo"},
    {"year": 2021, "award": "kinderspiel_des_jahres", "title": "Dragomino"},
    {"year": 2020, "award": "spiel_des_jahres", "title": "Pictures"},
    {"year": 2020, "award": "kennerspiel_des_jahres", "title": "The Crew: The Quest for Planet Nine"},
    {"year": 2020, "award": "kinderspiel_des_jahres", "title": "Hedgehog Roll"},
    {"year": 2019, "award": "spiel_des_jahres", "title": "Just One"},
    {"year": 2019, "award": "kennerspiel_des_jahres", "title": "Wingspan"},
    {"year": 2019, "award": "kinderspiel_des_jahres", "title": "Valley of the Vikings"},
    {"year": 2018, "award": "spiel_des_jahres", "title": "Azul"},
    {"year": 2018, "award": "kennerspiel_des_jahres", "title": "The Quacks of Quedlinburg"},
    {"year": 2018, "award": "kinderspiel_des_jahres", "title": "Dragon's Breath"},
    {"year": 2017, "award": "spiel_des_jahres", "title": "Kingdomino"},
    {"year": 2017, "award": "kennerspiel_des_jahres", "title": "Exit: The Game – The Abandoned Cabin"},
    {"year": 2017, "award": "kinderspiel_des_jahres", "title": "Ice Cool"},
    {"year": 2016, "award": "spiel_des_jahres", "title": "Codenames"},
    {"year": 2016, "award": "kennerspiel_des_jahres", "title": "Isle of Skye: From Chieftain to King"},
    {"year": 2016, "award": "kinderspiel_des_jahres", "title": "Stone Age Jr."},
    {"year": 2015, "award": "spiel_des_jahres", "title": "Colt Express"},
    {"year": 2015, "award": "kennerspiel_des_jahres", "title": "Broom Service"},
    {"year": 2015, "award": "kinderspiel_des_jahres", "title": "Spinderella"},
]

# In-process cache of BGG search resolutions, keyed by (title, year). Avoids
# re-hitting BGG for the same unowned winner on every dashboard refresh;
# cleared on restart, same lifetime as the circuit breaker/rate limiter
# state bgg_service.py already keeps in-process.
_bgg_match_cache: Dict[tuple, Optional[Dict[str, Any]]] = {}


def _award_winners_since(years: Optional[int]) -> List[Dict[str, Any]]:
    if years is None:
        return list(AWARD_WINNERS)
    cutoff = max(w["year"] for w in AWARD_WINNERS) - years + 1
    return [w for w in AWARD_WINNERS if w["year"] >= cutoff]


async def _resolve_bgg_match(title: str, year: Optional[int]) -> Optional[Dict[str, Any]]:
    cache_key = (title, year)
    if cache_key in _bgg_match_cache:
        return _bgg_match_cache[cache_key]

    try:
        candidates = await search_bgg(title, limit=5)
    except Exception as e:
        logger.warning(f"BGG search failed while resolving award winner {title!r}: {e}")
        candidates = []

    match = None
    if candidates:
        exact = [c for c in candidates if c["title"].strip().lower() == title.strip().lower()]
        pool = exact or candidates
        if year:
            pool = sorted(pool, key=lambda c: abs((c["year"] or 0) - year))
        match = pool[0]

    _bgg_match_cache[cache_key] = match
    return match


async def get_award_winners(db: Session, years: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Curated award winners, annotated with whether each is already owned or
    already on the games-to-add list, and best-effort resolved to a bgg_id
    when not already in this library (for the one-click add action).
    """
    entries = _award_winners_since(years)
    titles = [e["title"] for e in entries]

    games_by_title = {
        game.title.strip().lower(): game
        for game in db.execute(select(Game).where(Game.title.in_(titles))).scalars().all()
    }
    game_ids = [game.id for game in games_by_title.values()]
    queued_game_ids = set()
    if game_ids:
        queued_game_ids = {
            game_id
            for (game_id,) in db.execute(
                select(BuyListGame.game_id).where(
                    BuyListGame.on_buy_list == True,  # noqa: E712
                    BuyListGame.game_id.in_(game_ids),
                )
            ).all()
        }

    results = []
    for entry in entries:
        game = games_by_title.get(entry["title"].strip().lower())
        bgg_id = None
        thumbnail_url = None

        if game and game.status == "OWNED":
            status = "owned"
            bgg_id = game.bgg_id
            thumbnail_url = game.image
        elif game and game.id in queued_game_ids:
            status = "on_buy_list"
            bgg_id = game.bgg_id
            thumbnail_url = game.image
        else:
            status = "new"
            match = await _resolve_bgg_match(entry["title"], entry["year"])
            if match:
                bgg_id = match["bgg_id"]

        results.append({
            "year": entry["year"],
            "award": entry["award"],
            "award_label": AWARD_LABELS.get(entry["award"], entry["award"]),
            "title": entry["title"],
            "bgg_id": bgg_id,
            "thumbnail_url": thumbnail_url,
            "status": status,
            "bgg_search_url": (
                "https://boardgamegeek.com/geeksearch.php?action=search&objecttype=boardgame&q="
                + entry["title"].replace(" ", "+")
            ),
        })

    return results
