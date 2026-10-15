# tests/test_services/test_award_winners.py
"""
Tests for services/award_winners.py - the curated Spiel des Jahres /
Kennerspiel des Jahres / Kinderspiel des Jahres list and its best-effort
BGG resolution for titles not already in the library.
"""
from unittest.mock import AsyncMock, patch

import pytest

from models import BuyListGame, Game
from services.award_winners import AWARD_WINNERS, _bgg_match_cache, get_award_winners


@pytest.fixture(autouse=True)
def clear_bgg_match_cache():
    """The module-level resolution cache must not leak between tests."""
    _bgg_match_cache.clear()
    yield
    _bgg_match_cache.clear()


class TestAwardWinnersData:
    def test_every_entry_has_year_award_and_title(self):
        assert len(AWARD_WINNERS) > 0
        for entry in AWARD_WINNERS:
            assert isinstance(entry["year"], int)
            assert entry["award"] in (
                "spiel_des_jahres",
                "kennerspiel_des_jahres",
                "kinderspiel_des_jahres",
            )
            assert entry["title"]


class TestGetAwardWinners:
    @pytest.mark.asyncio
    async def test_owned_winner_is_annotated_owned(self, db_session):
        owned_year = max(w["year"] for w in AWARD_WINNERS if w["award"] == "spiel_des_jahres")
        owned_title = next(
            w["title"] for w in AWARD_WINNERS
            if w["award"] == "spiel_des_jahres" and w["year"] == owned_year
        )
        game = Game(title=owned_title, bgg_id=111222, status="OWNED", image="http://example.com/t.jpg")
        db_session.add(game)
        db_session.commit()

        with patch("services.award_winners.search_bgg", new_callable=AsyncMock, return_value=[]):
            results = await get_award_winners(db_session, years=1)

        match = next(r for r in results if r["title"] == owned_title)
        assert match["status"] == "owned"
        assert match["bgg_id"] == 111222
        assert match["thumbnail_url"] == "http://example.com/t.jpg"

    @pytest.mark.asyncio
    async def test_queued_winner_is_annotated_on_buy_list(self, db_session):
        year = max(w["year"] for w in AWARD_WINNERS if w["award"] == "kennerspiel_des_jahres")
        title = next(
            w["title"] for w in AWARD_WINNERS
            if w["award"] == "kennerspiel_des_jahres" and w["year"] == year
        )
        game = Game(title=title, bgg_id=333444, status="BUY_LIST")
        db_session.add(game)
        db_session.flush()
        db_session.add(BuyListGame(game_id=game.id, on_buy_list=True))
        db_session.commit()

        with patch("services.award_winners.search_bgg", new_callable=AsyncMock, return_value=[]):
            results = await get_award_winners(db_session, years=1)

        match = next(r for r in results if r["title"] == title)
        assert match["status"] == "on_buy_list"
        assert match["bgg_id"] == 333444

    @pytest.mark.asyncio
    async def test_unowned_winner_resolves_bgg_id_via_search(self, db_session):
        async def fake_search(query, limit=5):
            return [{"bgg_id": 555, "title": query, "year": 2019}]

        with patch("services.award_winners.search_bgg", side_effect=fake_search):
            results = await get_award_winners(db_session, years=1)

        for entry in results:
            assert entry["status"] == "new"
            assert entry["bgg_id"] == 555
            assert "boardgamegeek.com/geeksearch" in entry["bgg_search_url"]

    @pytest.mark.asyncio
    async def test_no_bgg_match_leaves_bgg_id_none(self, db_session):
        with patch("services.award_winners.search_bgg", new_callable=AsyncMock, return_value=[]):
            results = await get_award_winners(db_session, years=1)

        for entry in results:
            assert entry["bgg_id"] is None
            assert entry["status"] == "new"

    @pytest.mark.asyncio
    async def test_bgg_search_failure_does_not_raise(self, db_session):
        with patch(
            "services.award_winners.search_bgg",
            side_effect=RuntimeError("BGG unreachable"),
        ):
            results = await get_award_winners(db_session, years=1)

        for entry in results:
            assert entry["bgg_id"] is None

    @pytest.mark.asyncio
    async def test_years_filters_to_most_recent_award_years(self, db_session):
        with patch("services.award_winners.search_bgg", new_callable=AsyncMock, return_value=[]):
            results_all = await get_award_winners(db_session, years=None)
            results_one_year = await get_award_winners(db_session, years=1)

        assert len(results_one_year) == 3  # one winner per award
        assert len(results_all) == len(AWARD_WINNERS)

    @pytest.mark.asyncio
    async def test_resolution_is_cached_across_calls(self, db_session):
        mock_search = AsyncMock(return_value=[{"bgg_id": 777, "title": "Whatever", "year": 2020}])
        with patch("services.award_winners.search_bgg", mock_search):
            await get_award_winners(db_session, years=1)
            await get_award_winners(db_session, years=1)

        # Three new winners (one per award) resolved once each, not re-fetched
        # on the second call.
        assert mock_search.await_count == 3

    @pytest.mark.asyncio
    async def test_award_label_is_included(self, db_session):
        with patch("services.award_winners.search_bgg", new_callable=AsyncMock, return_value=[]):
            results = await get_award_winners(db_session, years=1)

        labels = {r["award"]: r["award_label"] for r in results}
        assert labels["spiel_des_jahres"] == "Spiel des Jahres"
        assert labels["kennerspiel_des_jahres"] == "Kennerspiel des Jahres"
        assert labels["kinderspiel_des_jahres"] == "Kinderspiel des Jahres"
