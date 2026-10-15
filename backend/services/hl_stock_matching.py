# services/hl_stock_matching.py
"""
Fuzzy-matches HL Timaru product names against this library's board-game
titles, to tell apart already-tracked games from true new candidates.

Confirmed matches are persisted on HLStockLink.game_id (see
api/routers/buy_list.py) so a linked product is never re-matched; this
module is only consulted for a newly-seen hl_internal_id. Retail POS names
are often abbreviated or reordered relative to BGG-style titles (e.g.
"Wingspan Euro Exp" vs. "Wingspan: European Expansion"), so a match here is
always a suggestion for staff to confirm - never auto-trusted into the data
model - the caller always surfaces the score alongside the match.
"""
from rapidfuzz import fuzz, process
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Game

# rapidfuzz WRatio score (0-100) below which a candidate is treated as
# unmatched rather than a suggested link.
MATCH_CONFIDENCE_THRESHOLD = 85


def find_best_title_match(db: Session, hl_product_name: str) -> tuple[Game | None, float]:
    """Best match for hl_product_name among every game in the library (any
    status - OWNED, BUY_LIST, WISHLIST - since the goal is "is this already
    tracked", not just "already owned").

    Returns (Game, score) if the best match clears the threshold, otherwise
    (None, score) - score is still returned so an unmatched candidate's
    near-miss is visible rather than discarded.
    """
    titles = db.execute(select(Game.id, Game.title)).all()
    if not titles:
        return None, 0.0

    choices = {row.id: row.title for row in titles}
    result = process.extractOne(hl_product_name, choices, scorer=fuzz.WRatio)
    if result is None:
        return None, 0.0

    _, score, game_id = result
    if score < MATCH_CONFIDENCE_THRESHOLD:
        return None, score

    return db.get(Game, game_id), score
