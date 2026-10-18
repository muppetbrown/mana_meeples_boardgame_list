# tests/test_services/test_hl_signal_fit.py
"""Tests for services/hl_signal_fit.py - BGG enrichment and gap-fit scoring of HL products."""
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from exceptions import BGGServiceError
from models import HLStockLink, utc_now
from services import hl_signal_fit
from services.hl_signal_fit import enrich_links_task, gaps_filled, needs_bgg_lookup


def _link(db_session, hl_id=1, name="Wingspan Euro Exp", **kwargs):
    link = HLStockLink(
        hl_internal_id=hl_id, hl_product_name=name, last_synced_at=utc_now(), **kwargs
    )
    db_session.add(link)
    db_session.commit()
    return link


@pytest.fixture(autouse=True)
def session_local(db_session):
    # enrich_links_task opens its own session; point it at the test session
    # (and keep the task's db.close() from detaching the test's objects).
    with patch("database.SessionLocal", return_value=db_session), patch.object(db_session, "close"):
        yield


BGG_DATA = {
    "title": "Wingspan: European Expansion",
    "year": 2019,
    "players_min": 1,
    "players_max": 5,
    "playtime_min": 40,
    "playtime_max": 70,
    "complexity": 2.4,
    "categories": ["Animals", "Card Game"],
}


class TestGapsFilled:
    def test_counts_each_gap_type(self):
        assert gaps_filled({
            "category_is_gap": True,
            "matching_player_count_gaps": ["8", "9+"],
            "complexity_is_gap": True,
            "playtime_is_gap": False,
        }) == 4

    def test_none_is_zero(self):
        assert gaps_filled(None) == 0


class TestNeedsBggLookup:
    def test_new_unmatched_link_needs_lookup(self, db_session):
        assert needs_bgg_lookup(_link(db_session))

    def test_linked_or_dismissed_does_not(self, db_session):
        assert not needs_bgg_lookup(_link(db_session, 1, game_id=None, dismissed=True))

    def test_enriched_does_not_but_stale_miss_retries(self, db_session):
        hit = _link(db_session, 1, bgg_id=5, bgg_enriched_at=utc_now())
        recent_miss = _link(db_session, 2, bgg_enriched_at=utc_now())
        old_miss = _link(db_session, 3, bgg_enriched_at=utc_now() - timedelta(days=8))
        assert not needs_bgg_lookup(hit)
        assert not needs_bgg_lookup(recent_miss)
        assert needs_bgg_lookup(old_miss)


class TestEnrichLinksTask:
    @pytest.mark.asyncio
    async def test_caches_best_bgg_match(self, db_session):
        _link(db_session)
        candidates = [
            {"bgg_id": 1, "title": "Something Unrelated", "year": 2000},
            {"bgg_id": 266192, "title": "Wingspan: European Expansion", "year": 2019},
        ]
        with patch("services.hl_signal_fit.search_bgg", new_callable=AsyncMock, return_value=candidates), patch(
            "services.hl_signal_fit.fetch_bgg_thing", new_callable=AsyncMock, return_value=BGG_DATA
        ) as fetch:
            await enrich_links_task([1])

        fetch.assert_awaited_once_with(266192)
        db_session.expire_all()
        link = db_session.execute(select(HLStockLink)).scalar_one()
        assert link.bgg_id == 266192
        assert link.bgg_players_max == 5 and link.bgg_complexity == 2.4
        assert link.bgg_match_score >= hl_signal_fit.BGG_MATCH_THRESHOLD
        assert link.bgg_enriched_at is not None

    @pytest.mark.asyncio
    async def test_no_confident_match_is_recorded_without_fetching(self, db_session):
        _link(db_session, name="Zzzq Xylo")
        candidates = [{"bgg_id": 1, "title": "Completely Different Title", "year": 2000}]
        with patch("services.hl_signal_fit.search_bgg", new_callable=AsyncMock, return_value=candidates), patch(
            "services.hl_signal_fit.fetch_bgg_thing", new_callable=AsyncMock
        ) as fetch:
            await enrich_links_task([1])

        fetch.assert_not_awaited()
        db_session.expire_all()
        link = db_session.execute(select(HLStockLink)).scalar_one()
        assert link.bgg_id is None and link.bgg_enriched_at is not None

    @pytest.mark.asyncio
    async def test_bgg_outage_stops_and_leaves_link_retryable(self, db_session):
        _link(db_session, 1)
        _link(db_session, 2, name="Other Game")
        with patch(
            "services.hl_signal_fit.search_bgg", new_callable=AsyncMock, side_effect=BGGServiceError("down")
        ) as search:
            await enrich_links_task([1, 2])

        assert search.await_count == 1  # stopped after the first failure
        db_session.expire_all()
        assert all(l.bgg_enriched_at is None for l in db_session.execute(select(HLStockLink)).scalars())

    @pytest.mark.asyncio
    async def test_skips_products_already_in_flight(self, db_session):
        _link(db_session)
        hl_signal_fit._in_flight.add(1)
        try:
            with patch("services.hl_signal_fit.search_bgg", new_callable=AsyncMock) as search:
                await enrich_links_task([1])
            search.assert_not_awaited()
        finally:
            hl_signal_fit._in_flight.discard(1)
