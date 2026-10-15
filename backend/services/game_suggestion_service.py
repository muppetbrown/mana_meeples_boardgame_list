# services/game_suggestion_service.py
"""
AI-assisted "games to add" suggestions.

Asks Claude for games that would plausibly suit this specific library,
grounded in its actual collection (owned titles + categories) and its gap
analysis, then best-effort resolves each suggestion to a BGG ID via BGG
search so the frontend can offer a one-click add.
"""
import logging
from typing import List, Optional

import anthropic
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from bgg_service import search_bgg
from config import ANTHROPIC_API_KEY
from models import BuyListGame, Game
from services.gap_analysis import COMPLEXITY_LABELS, PLAYTIME_LABELS, compute_library_gaps
from utils.helpers import CATEGORY_KEYS

logger = logging.getLogger(__name__)

SUGGESTION_MODEL = "claude-opus-5-5"
# Keep the prompt bounded even for a large collection - this is a supporting
# signal (what's already owned), not something every single row needs to
# individually inform.
MAX_OWNED_TITLES_IN_PROMPT = 500

CATEGORY_DESCRIPTIONS = {
    "COOP_ADVENTURE": "Co-op & Adventure - collaborative and story-driven games",
    "CORE_STRATEGY": "Core Strategy & Epics - medium-heavy games for experienced players",
    "GATEWAY_STRATEGY": "Gateway Strategy - accessible strategic games for new players",
    "KIDS_FAMILIES": "Kids & Families - age-appropriate games for all generations",
    "PARTY_ICEBREAKERS": "Party & Icebreakers - large group social games",
}


class SuggestedGame(BaseModel):
    title: str = Field(description="The board game's title, exactly as commonly listed on BoardGameGeek")
    year: Optional[int] = Field(default=None, description="Year first published, if known")
    category_key: Optional[str] = Field(
        default=None,
        description=f"Best-fit category key, one of {CATEGORY_KEYS}, or null if unclear",
    )
    reason: str = Field(description="One or two sentences on why this specific library should add it")


class SuggestionResponse(BaseModel):
    suggestions: List[SuggestedGame]


class SuggestionServiceError(Exception):
    """Raised when suggestions can't be generated (missing key, API failure)."""


def _build_prompt(db: Session, count: int) -> tuple[str, str]:
    gaps = compute_library_gaps(db)

    owned_rows = db.execute(
        select(Game.title, Game.mana_meeple_category, Game.year)
        .where(Game.status == "OWNED")
        .order_by(Game.title)
    ).all()

    already_queued = {
        title
        for (title,) in db.execute(
            select(Game.title)
            .join(BuyListGame, BuyListGame.game_id == Game.id)
            .where(BuyListGame.on_buy_list == True)  # noqa: E712
        ).all()
    }

    gap_categories = [
        f"{CATEGORY_DESCRIPTIONS.get(g['category'], g['category'])} ({g['pct_of_collection']}% of collection)"
        for g in gaps["category_gaps"]
        if g["is_gap"]
    ]
    gap_player_counts = [
        f"{g['player_count']} players ({g['games_supporting']} games support it)"
        for g in gaps["player_count_gaps"]
        if g["is_gap"]
    ]
    gap_complexity_bands = [
        f"{COMPLEXITY_LABELS[g['complexity_band']]} ({g['pct_of_collection']}% of collection)"
        for g in gaps["complexity_gaps"]
        if g["is_gap"]
    ]
    gap_playtime_bands = [
        f"{PLAYTIME_LABELS[g['playtime_band']]} ({g['pct_of_collection']}% of collection)"
        for g in gaps["playtime_gaps"]
        if g["is_gap"]
    ]

    owned_lines = [
        f"- {title}" + (f" ({category})" if category else "") + (f" [{year}]" if year else "")
        for title, category, year in owned_rows[:MAX_OWNED_TITLES_IN_PROMPT]
    ]
    truncated_note = (
        f"\n(...and {len(owned_rows) - MAX_OWNED_TITLES_IN_PROMPT} more owned games, omitted for length)"
        if len(owned_rows) > MAX_OWNED_TITLES_IN_PROMPT
        else ""
    )

    system = (
        "You are helping curate the board game library for Mana & Meeples, a board game cafe. "
        "The library is used for walk-in cafe play, gaming conventions, and corporate team-building "
        "events - every suggestion should genuinely suit at least one of those settings. "
        "Suggest only real, existing, published board games (never invent a title). Do not suggest "
        "a game that is already owned or already on the games-to-add list below. Prefer games that "
        "are well-regarded (generally BGG-rated 7.0+) and currently in print or easy to find, and "
        "favor games that would plausibly fill one of the collection's noted gaps, without ignoring "
        "strong games outside those gaps."
    )

    user = (
        f"Suggest {count} board games worth adding to this library.\n\n"
        f"Collection size: {gaps['total_games']} owned games.\n\n"
        f"Under-represented categories (gaps): {', '.join(gap_categories) or 'none currently flagged'}\n"
        f"Thin player-count coverage (gaps): {', '.join(gap_player_counts) or 'none currently flagged'}\n"
        f"Thin complexity coverage (gaps): {', '.join(gap_complexity_bands) or 'none currently flagged'}\n"
        f"Thin playtime coverage (gaps): {', '.join(gap_playtime_bands) or 'none currently flagged'}\n\n"
        f"Already owned ({len(owned_rows)} games):\n"
        + "\n".join(owned_lines)
        + truncated_note
        + "\n\nAlready on the games-to-add list (do not re-suggest these): "
        + (", ".join(sorted(already_queued)) or "none")
    )

    return system, user


async def generate_suggestions(db: Session, count: int = 6) -> List[dict]:
    """
    Ask Claude for `count` candidate games grounded in this library's actual
    collection and gap analysis, then best-effort resolve each to a BGG ID.
    """
    if not ANTHROPIC_API_KEY:
        raise SuggestionServiceError(
            "ANTHROPIC_API_KEY is not configured - set it in the backend environment to enable suggestions"
        )

    system, user = _build_prompt(db, count)
    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    try:
        response = await client.messages.parse(
            model=SUGGESTION_MODEL,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=SuggestionResponse,
        )
    except anthropic.APIError as e:
        logger.error(f"Claude suggestion request failed: {e}")
        raise SuggestionServiceError(f"Claude API request failed: {e}") from e

    parsed = response.parsed_output
    suggestions = parsed.suggestions[:count] if parsed else []

    results = []
    for suggestion in suggestions:
        bgg_search_url = (
            "https://boardgamegeek.com/geeksearch.php?action=search&objecttype=boardgame&q="
            + suggestion.title.replace(" ", "+")
        )

        match = None
        try:
            candidates = await search_bgg(suggestion.title, limit=5)
        except Exception as e:
            logger.warning(f"BGG search failed while resolving suggestion '{suggestion.title}': {e}")
            candidates = []

        if candidates:
            # Prefer an exact (case-insensitive) title match; among ties (or if
            # no exact match), pick whichever is closest to the suggested year.
            exact = [c for c in candidates if c["title"].strip().lower() == suggestion.title.strip().lower()]
            pool = exact or candidates
            if suggestion.year:
                pool = sorted(pool, key=lambda c: abs((c["year"] or 0) - suggestion.year))
            match = pool[0]

        results.append(
            {
                "title": suggestion.title,
                "year": suggestion.year,
                "category_key": suggestion.category_key if suggestion.category_key in CATEGORY_KEYS else None,
                "reason": suggestion.reason,
                "suggested_bgg_id": match["bgg_id"] if match else None,
                "suggested_bgg_title": match["title"] if match else None,
                "suggested_bgg_year": match["year"] if match else None,
                "bgg_search_url": bgg_search_url,
            }
        )

    return results
