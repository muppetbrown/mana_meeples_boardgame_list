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


@pytest.fixture(autouse=True)
def mock_hot_games():
    """
    _build_prompt calls get_hot_games for trending context on every call;
    default to no trending data so tests don't make real network calls.
    Override per-test with mock_hot_games.return_value = [...].
    """
    with patch(
        "services.game_suggestion_service.get_hot_games", new_callable=AsyncMock, return_value=[]
    ) as mock:
        yield mock


class TestBuildPrompt:
    @pytest.mark.asyncio
    async def test_includes_flagged_gaps_and_owned_titles(self, db_session):
        for i in range(10):
            _owned_game(db_session, title=f"Game {i}", bgg_id=i, mana_meeple_category="CORE_STRATEGY")
        db_session.commit()

        system, user = await _build_prompt(db_session, count=5)

        assert "Mana & Meeples" in system
        assert "Game 0" in user
        assert "CORE_STRATEGY" in user  # owned-games list shows the category
        # Every category except CORE_STRATEGY has 0% share, so it's flagged as a gap
        assert "Gateway Strategy" in user

    @pytest.mark.asyncio
    async def test_excludes_list_names_already_queued_games(self, db_session):
        _owned_game(db_session, title="Owned Game", bgg_id=1)
        candidate = Game(title="Candidate Game", bgg_id=2, status="BUY_LIST")
        db_session.add(candidate)
        db_session.flush()
        db_session.add(BuyListGame(game_id=candidate.id, on_buy_list=True))
        db_session.commit()

        _system, user = await _build_prompt(db_session, count=5)

        assert "Owned Game" in user
        assert "Candidate Game" in user
        assert "do not re-suggest" in user.lower()

    @pytest.mark.asyncio
    async def test_no_gaps_flagged_message(self, db_session):
        # No owned games at all -> compute_library_gaps flags nothing
        _system, user = await _build_prompt(db_session, count=5)
        assert "none currently flagged" in user

    @pytest.mark.asyncio
    async def test_includes_complexity_and_playtime_gaps(self, db_session):
        # 10 heavy, epic-length games -> light/medium complexity and
        # quick/standard/long playtime bands are all flagged as gaps
        for i in range(10):
            _owned_game(
                db_session, title=f"Game {i}", bgg_id=i,
                complexity=4.0, playtime_min=180, playtime_max=180,
            )
        db_session.commit()

        _system, user = await _build_prompt(db_session, count=5)

        assert "Thin complexity coverage" in user
        assert "Light (under 2.0)" in user
        assert "Thin playtime coverage" in user
        assert "Quick (under 30 min)" in user

    @pytest.mark.asyncio
    async def test_includes_trending_games(self, db_session, mock_hot_games):
        mock_hot_games.return_value = [
            {"bgg_id": 174430, "rank": 1, "title": "Gloomhaven", "year": 2017, "thumbnail_url": None},
            {"bgg_id": 266192, "rank": 2, "title": "Wingspan", "year": 2019, "thumbnail_url": None},
        ]

        system, user = await _build_prompt(db_session, count=5)

        assert "trending" in system.lower()
        assert "Currently trending on BoardGameGeek" in user
        assert "#1 Gloomhaven (2017)" in user
        assert "#2 Wingspan (2019)" in user

    @pytest.mark.asyncio
    async def test_trending_unavailable_message_when_empty(self, db_session):
        _system, user = await _build_prompt(db_session, count=5)
        assert "(trending data unavailable right now)" in user

    @pytest.mark.asyncio
    async def test_trending_fetch_failure_does_not_break_prompt(self, db_session, mock_hot_games):
        mock_hot_games.side_effect = RuntimeError("BGG unreachable")

        _system, user = await _build_prompt(db_session, count=5)

        assert "(trending data unavailable right now)" in user


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


class TestAvailabilityFiltering:
    def _parsed(self):
        return SuggestionResponse(
            suggestions=[
                SuggestedGame(title="Wingspan", year=2019, category_key=None, reason="a"),
                SuggestedGame(title="Out Of Print Game", year=2001, category_key=None, reason="b"),
            ]
        )

    async def _run(self, db_session, availability, **kwargs):
        mock_response = AsyncMock()
        mock_response.parsed_output = self._parsed()
        with patch("services.game_suggestion_service.ANTHROPIC_API_KEY", "test-key"):
            with patch("services.game_suggestion_service.anthropic.AsyncAnthropic") as mock_client_cls:
                parse = AsyncMock(return_value=mock_response)
                mock_client_cls.return_value.messages.parse = parse
                with patch("services.game_suggestion_service.search_bgg", new_callable=AsyncMock, return_value=[]):
                    with patch(
                        "services.game_suggestion_service.availability_for_titles", return_value=availability
                    ):
                        results = await generate_suggestions(db_session, **kwargs)
        return results, parse

    @pytest.mark.asyncio
    async def test_drops_unavailable_and_overfetches(self, db_session):
        availability = {
            "Wingspan": {"status": "in_stock", "options": []},
            "Out Of Print Game": {"status": "not_listed", "options": []},
        }
        results, parse = await self._run(db_session, availability, count=2)

        assert [r["title"] for r in results] == ["Wingspan"]
        assert results[0]["distro_availability"]["status"] == "in_stock"
        assert "Suggest 6 board games" in parse.call_args.kwargs["messages"][0]["content"]

    @pytest.mark.asyncio
    async def test_only_available_false_keeps_everything(self, db_session):
        availability = {
            "Wingspan": {"status": "in_stock", "options": []},
            "Out Of Print Game": {"status": "not_listed", "options": []},
        }
        results, _ = await self._run(db_session, availability, count=2, only_available=False)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_no_filtering_when_catalogue_unavailable(self, db_session):
        results, _ = await self._run(db_session, None, count=2)
        assert len(results) == 2
        assert all(r["distro_availability"] is None for r in results)


class TestUnusableResponses:
    """An unusable Claude response must surface as an error, not as 'no suggestions'."""

    async def _run(self, db_session, *, parse_result=None, parse_error=None, availability=None, **kwargs):
        with patch("services.game_suggestion_service.ANTHROPIC_API_KEY", "test-key"):
            with patch("services.game_suggestion_service.anthropic.AsyncAnthropic") as mock_client_cls:
                parse = AsyncMock(return_value=parse_result, side_effect=parse_error)
                mock_client_cls.return_value.messages.parse = parse
                with patch("services.game_suggestion_service.search_bgg", new_callable=AsyncMock, return_value=[]):
                    with patch(
                        "services.game_suggestion_service.availability_for_titles", return_value=availability
                    ):
                        return await generate_suggestions(db_session, **kwargs), parse

    @pytest.mark.asyncio
    async def test_no_parsed_output_raises_with_stop_reason(self, db_session):
        response = AsyncMock()
        response.parsed_output = None
        response.stop_reason = "max_tokens"
        response.usage.output_tokens = 4096

        with pytest.raises(SuggestionServiceError, match="max_tokens"):
            await self._run(db_session, parse_result=response, count=3)

    @pytest.mark.asyncio
    async def test_truncated_json_raises_friendly_error(self, db_session):
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as truncated:
            SuggestionResponse.model_validate_json('{"suggestions": [{"title": "Wing')

        with pytest.raises(SuggestionServiceError, match="cut off or malformed"):
            await self._run(db_session, parse_error=truncated.value, count=3)

    @pytest.mark.asyncio
    async def test_everything_filtered_out_raises_instead_of_returning_empty(self, db_session):
        response = AsyncMock()
        response.parsed_output = SuggestionResponse(
            suggestions=[SuggestedGame(title="Out Of Print Game", year=2001, category_key=None, reason="x")]
        )
        availability = {"Out Of Print Game": {"status": "not_listed", "options": []}}

        with pytest.raises(SuggestionServiceError, match="None of the 1 games"):
            await self._run(db_session, parse_result=response, availability=availability, count=3)

    @pytest.mark.asyncio
    async def test_request_leaves_room_for_thinking(self, db_session):
        response = AsyncMock()
        response.parsed_output = SuggestionResponse(
            suggestions=[SuggestedGame(title="Wingspan", year=2019, category_key=None, reason="x")]
        )
        _, parse = await self._run(db_session, parse_result=response, count=1)

        kwargs = parse.call_args.kwargs
        assert kwargs["max_tokens"] >= 16000
        assert kwargs["output_config"] == {"effort": "low"}
