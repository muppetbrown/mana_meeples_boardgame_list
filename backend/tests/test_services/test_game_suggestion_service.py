# tests/test_services/test_game_suggestion_service.py
"""
Tests for services/game_suggestion_service.py - the AI-assisted "games to
add" suggestions feature (Claude API + best-effort BGG resolution).
"""
from unittest.mock import AsyncMock, patch

import anthropic
import httpx2
import pytest

from models import BuyListGame, Game
from services.game_suggestion_service import (
    SuggestedGame,
    SuggestionResponse,
    SuggestionServiceError,
    _build_prompt,
    generate_suggestions,
)


def _owned_game(db_session, **kwargs):
    defaults = {"status": "OWNED", "bgg_id": None}
    defaults.update(kwargs)
    game = Game(**defaults)
    db_session.add(game)
    return game


def _api_error(message="boom"):
    req = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    return anthropic.APIConnectionError(message=message, request=req)


class TestBuildPrompt:
    def test_includes_flagged_gaps_and_owned_titles(self, db_session):
        for i in range(10):
            _owned_game(db_session, title=f"Game {i}", bgg_id=i, mana_meeple_category="CORE_STRATEGY")
        db_session.commit()

        system, user = _build_prompt(db_session, count=5)

        assert "Mana & Meeples" in system
        assert "Game 0" in user
        assert "CORE_STRATEGY" in user  # owned-games list shows the category
        # Every category except CORE_STRATEGY has 0% share, so it's flagged as a gap
        assert "Gateway Strategy" in user

    def test_excludes_list_names_already_queued_games(self, db_session):
        _owned_game(db_session, title="Owned Game", bgg_id=1)
        candidate = Game(title="Candidate Game", bgg_id=2, status="BUY_LIST")
        db_session.add(candidate)
        db_session.flush()
        db_session.add(BuyListGame(game_id=candidate.id, on_buy_list=True))
        db_session.commit()

        _system, user = _build_prompt(db_session, count=5)

        assert "Owned Game" in user
        assert "Candidate Game" in user
        assert "do not re-suggest" in user.lower()

    def test_no_gaps_flagged_message(self, db_session):
        # No owned games at all -> compute_library_gaps flags nothing
        _system, user = _build_prompt(db_session, count=5)
        assert "none currently flagged" in user


class TestGenerateSuggestions:
    @pytest.mark.asyncio
    async def test_raises_when_api_key_missing(self, db_session):
        with patch("services.game_suggestion_service.ANTHROPIC_API_KEY", ""):
            with pytest.raises(SuggestionServiceError, match="ANTHROPIC_API_KEY"):
                await generate_suggestions(db_session, count=3)

    @pytest.mark.asyncio
    async def test_wraps_anthropic_api_errors(self, db_session):
        with patch("services.game_suggestion_service.ANTHROPIC_API_KEY", "test-key"):
            with patch("services.game_suggestion_service.anthropic.AsyncAnthropic") as mock_client_cls:
                mock_client = mock_client_cls.return_value
                mock_client.messages.parse = AsyncMock(side_effect=_api_error("rate limited"))

                with pytest.raises(SuggestionServiceError, match="Claude API request failed"):
                    await generate_suggestions(db_session, count=3)

    @pytest.mark.asyncio
    async def test_resolves_bgg_id_for_each_suggestion(self, db_session):
        parsed = SuggestionResponse(
            suggestions=[
                SuggestedGame(
                    title="Wingspan", year=2019, category_key="GATEWAY_STRATEGY",
                    reason="Fits the gateway strategy gap.",
                ),
                SuggestedGame(
                    title="Some Obscure Game", year=None, category_key="NOT_A_REAL_CATEGORY",
                    reason="Hard to resolve on BGG.",
                ),
            ]
        )
        mock_response = AsyncMock()
        mock_response.parsed_output = parsed

        async def fake_search(query, limit=5):
            if query == "Wingspan":
                return [{"bgg_id": 266192, "title": "Wingspan", "year": 2019}]
            return []

        with patch("services.game_suggestion_service.ANTHROPIC_API_KEY", "test-key"):
            with patch("services.game_suggestion_service.anthropic.AsyncAnthropic") as mock_client_cls:
                mock_client = mock_client_cls.return_value
                mock_client.messages.parse = AsyncMock(return_value=mock_response)

                with patch("services.game_suggestion_service.search_bgg", side_effect=fake_search):
                    results = await generate_suggestions(db_session, count=2)

        assert len(results) == 2

        wingspan = results[0]
        assert wingspan["title"] == "Wingspan"
        assert wingspan["suggested_bgg_id"] == 266192
        assert wingspan["category_key"] == "GATEWAY_STRATEGY"
        assert "boardgamegeek.com/geeksearch" in wingspan["bgg_search_url"]

        obscure = results[1]
        assert obscure["suggested_bgg_id"] is None
        # An invalid/hallucinated category key is dropped rather than passed through
        assert obscure["category_key"] is None
        assert "boardgamegeek.com/geeksearch" in obscure["bgg_search_url"]

    @pytest.mark.asyncio
    async def test_bgg_search_failure_does_not_fail_the_request(self, db_session):
        parsed = SuggestionResponse(
            suggestions=[SuggestedGame(title="Azul", year=2017, category_key=None, reason="Popular gateway game.")]
        )
        mock_response = AsyncMock()
        mock_response.parsed_output = parsed

        with patch("services.game_suggestion_service.ANTHROPIC_API_KEY", "test-key"):
            with patch("services.game_suggestion_service.anthropic.AsyncAnthropic") as mock_client_cls:
                mock_client = mock_client_cls.return_value
                mock_client.messages.parse = AsyncMock(return_value=mock_response)

                with patch(
                    "services.game_suggestion_service.search_bgg",
                    side_effect=RuntimeError("BGG unreachable"),
                ):
                    results = await generate_suggestions(db_session, count=1)

        assert len(results) == 1
        assert results[0]["title"] == "Azul"
        assert results[0]["suggested_bgg_id"] is None

    @pytest.mark.asyncio
    async def test_prefers_exact_title_match_closest_in_year(self, db_session):
        parsed = SuggestionResponse(
            suggestions=[SuggestedGame(title="Catan", year=1995, category_key=None, reason="Classic gateway game.")]
        )
        mock_response = AsyncMock()
        mock_response.parsed_output = parsed

        async def fake_search(query, limit=5):
            return [
                {"bgg_id": 999, "title": "Catan: Some Expansion", "year": 1995},
                {"bgg_id": 13, "title": "Catan", "year": 1995},
                {"bgg_id": 888, "title": "Catan", "year": 2015},
            ]

        with patch("services.game_suggestion_service.ANTHROPIC_API_KEY", "test-key"):
            with patch("services.game_suggestion_service.anthropic.AsyncAnthropic") as mock_client_cls:
                mock_client = mock_client_cls.return_value
                mock_client.messages.parse = AsyncMock(return_value=mock_response)

                with patch("services.game_suggestion_service.search_bgg", side_effect=fake_search):
                    results = await generate_suggestions(db_session, count=1)

        # Exact title match "Catan", and among the two exact matches the one
        # whose year is closest to the suggested year (1995) wins.
        assert results[0]["suggested_bgg_id"] == 13
