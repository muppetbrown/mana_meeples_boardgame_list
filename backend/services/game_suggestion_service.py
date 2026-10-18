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
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from bgg_service import get_hot_games, search_bgg
from config import ANTHROPIC_API_KEY
from services.distro_availability import availability_for_titles
from models import BuyListGame, Game
from services.gap_analysis import COMPLEXITY_LABELS, PLAYTIME_LABELS, compute_library_gaps
from utils.helpers import CATEGORY_KEYS

logger = logging.getLogger(__name__)

SUGGESTION_MODEL = "claude-opus-5-5"
# Opus 5.5 always thinks, and thinking tokens count against max_tokens, so this
# has to cover the reasoning *and* the structured answer. At 4096 the reasoning
# could use the whole budget, leaving no text block and an empty suggestion list.
# Effort defaults to "medium" on this model; picking game titles doesn't need
# more, and lower effort keeps the (already 40s+) request shorter.
SUGGESTION_MAX_TOKENS = 16000
SUGGESTION_EFFORT = "low"
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


# How many BGG Hot List entries to mention in the prompt - context, not a
# target list of its own, so this stays small relative to the owned list.
MAX_TRENDING_IN_PROMPT = 15

# When filtering to distributor-available games, ask Claude for more than
# `count` since many suggestions won't be stocked; capped to keep the
# structured response within max_tokens.
AVAILABILITY_OVERFETCH_FACTOR = 3
MAX_CANDIDATES = 24


async def _build_prompt(db: Session, count: int) -> tuple[str, str]:
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

    try:
        trending = await get_hot_games(limit=MAX_TRENDING_IN_PROMPT)
    except Exception as e:
        logger.warning(f"BGG hot list fetch failed while building suggestion prompt: {e}")
        trending = []
    trending_lines = [
        f"#{g['rank']} {g['title']}" + (f" ({g['year']})" if g["year"] else "")
        for g in trending
    ]

    system = (
        "You are helping curate the board game library for Mana & Meeples, a board game cafe. "
        "The library is used for walk-in cafe play, gaming conventions, and corporate team-building "
        "events - every suggestion should genuinely suit at least one of those settings. "
        "Suggest only real, existing, published board games (never invent a title). Do not suggest "
        "a game that is already owned or already on the games-to-add list below. Prefer games that "
        "are well-regarded (generally BGG-rated 7.0+) and currently in print or easy to find, and "
        "favor games that would plausibly fill one of the collection's noted gaps, without ignoring "
        "strong games outside those gaps. Every suggestion is checked against the NZ distributor "
        "catalogues the cafe buys from, so strongly prefer games that are currently in print and "
        "stocked by NZ distributors. The current BoardGameGeek trending list is extra context, "
        "not a mandate - weigh it alongside fit for this library, don't just restate it."
    )

    user = (
        f"Suggest {count} board games worth adding to this library.\n\n"
        f"Collection size: {gaps['total_games']} owned games.\n\n"
        f"Under-represented categories (gaps): {', '.join(gap_categories) or 'none currently flagged'}\n"
        f"Thin player-count coverage (gaps): {', '.join(gap_player_counts) or 'none currently flagged'}\n"
        f"Thin complexity coverage (gaps): {', '.join(gap_complexity_bands) or 'none currently flagged'}\n"
        f"Thin playtime coverage (gaps): {', '.join(gap_playtime_bands) or 'none currently flagged'}\n\n"
        f"Currently trending on BoardGameGeek (recent community activity):\n"
        + ("\n".join(trending_lines) if trending_lines else "(trending data unavailable right now)")
        + f"\n\nAlready owned ({len(owned_rows)} games):\n"
        + "\n".join(owned_lines)
        + truncated_note
        + "\n\nAlready on the games-to-add list (do not re-suggest these): "
        + (", ".join(sorted(already_queued)) or "none")
    )

    return system, user


async def generate_suggestions(db: Session, count: int = 6, only_available: bool = True) -> List[dict]:
    """
    Ask Claude for `count` candidate games grounded in this library's actual
    collection and gap analysis, then best-effort resolve each to a BGG ID.

    Each result carries distro_availability (see services/distro_availability).
    With only_available, over-fetches candidates and drops any no distributor
    lists; if the distributor catalogue can't be read, nothing is dropped and
    distro_availability is None rather than guessing.
    """
    if not ANTHROPIC_API_KEY:
        raise SuggestionServiceError(
            "ANTHROPIC_API_KEY is not configured - set it in the backend environment to enable suggestions"
        )

    request_count = min(count * AVAILABILITY_OVERFETCH_FACTOR, MAX_CANDIDATES) if only_available else count
    system, user = await _build_prompt(db, request_count)
    # Everything below is a long (30-60s) wait on Claude and BGG that doesn't touch
    # the database (read-only so far, nothing to lose); give the connection back first so the pool doesn't hold it
    # idle until the cloud Postgres closes it ("SSL connection has been closed").
    db.rollback()
    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    try:
        response = await client.messages.parse(
            model=SUGGESTION_MODEL,
            max_tokens=SUGGESTION_MAX_TOKENS,
            output_config={"effort": SUGGESTION_EFFORT},
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=SuggestionResponse,
        )
    except anthropic.APIError as e:
        logger.error(f"Claude suggestion request failed: {e}")
        raise SuggestionServiceError(f"Claude API request failed: {e}") from e
    except ValidationError as e:
        # The SDK parses the text as it arrives; truncated or malformed JSON lands here.
        logger.error(f"Claude suggestion response didn't match the expected schema: {e}")
        raise SuggestionServiceError(
            "Claude's response was cut off or malformed - try again in a moment"
        ) from e

    parsed = response.parsed_output
    if parsed is None:
        # No usable text block: out of tokens mid-reasoning, or a refusal. Say so
        # rather than reporting an empty list as if Claude had nothing to suggest.
        logger.error(
            f"Claude returned no parsable suggestions (stop_reason={response.stop_reason!r}, "
            f"output_tokens={response.usage.output_tokens})"
        )
        raise SuggestionServiceError(
            "Claude didn't produce a usable answer "
            f"(stop reason: {response.stop_reason}) - try again in a moment"
        )
    suggestions = parsed.suggestions[:request_count]

    availability = availability_for_titles(s.title for s in suggestions)
    candidates_returned = len(suggestions)
    if availability is not None and only_available:
        suggestions = [s for s in suggestions if availability[s.title]["status"] != "not_listed"]
    logger.info(
        f"Suggestions: requested={request_count} returned={candidates_returned} "
        f"distributor_filter={'on' if availability is not None and only_available else 'off'} "
        f"kept={len(suggestions)}"
    )
    if candidates_returned and not suggestions:
        raise SuggestionServiceError(
            f"None of the {candidates_returned} games Claude suggested are listed by a distributor - "
            "try again for a different set"
        )
    suggestions = suggestions[:count]

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
                "distro_availability": availability[suggestion.title] if availability is not None else None,
            }
        )

    return results
