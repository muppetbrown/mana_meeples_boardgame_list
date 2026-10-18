# tests/test_services/test_distro_availability.py
"""Tests for services/distro_availability.py - matching game titles to distro_codes."""
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from services import distro_availability
from services.distro_availability import availability_for_titles, normalize_title
from services.hl_stock_service import HLStockServiceError


def _row(distributor, name, cost=None, qty=None, code="X1"):
    return {
        "distributor": distributor,
        "distro_code": code,
        "name": name,
        "cost_price_ex_gst": cost,
        "qty_available": qty,
        "qty_updated_at": datetime(2026, 10, 1, tzinfo=timezone.utc),
    }


@pytest.fixture(autouse=True)
def reset_cache():
    distro_availability._cache.update(loaded_at=0.0, rows=None)
    yield
    distro_availability._cache.update(loaded_at=0.0, rows=None)


def _with_catalogue(rows):
    return patch("services.distro_availability.fetch_distro_catalogue", return_value=rows)


class TestNormalizeTitle:
    def test_strips_punctuation_accents_and_noise(self):
        assert normalize_title("Catan: The Board Game") == "catan"
        assert normalize_title("Café & Co") == "cafe and co"


class TestAvailabilityForTitles:
    def test_matches_across_distributors_in_stock_first_then_cheapest(self):
        rows = [
            _row("LPG", "Wingspan Board Game", cost=60.0, qty=0, code="L1"),
            _row("VR", "Wingspan", cost=70.0, qty=5, code="V1"),
            _row("BANTER", "Wingspan", cost=65.0, qty=3, code="B1"),
        ]
        with _with_catalogue(rows):
            result = availability_for_titles(["Wingspan"])["Wingspan"]

        assert result["status"] == "in_stock"
        assert [o["distributor"] for o in result["options"]] == ["BANTER", "VR", "LPG"]
        assert result["options"][0]["cost_price_ex_gst"] == 65.0

    def test_expansion_is_not_a_match_for_base_game(self):
        with _with_catalogue([_row("VR", "Wingspan Oceania Expansion", qty=4)]):
            result = availability_for_titles(["Wingspan"])["Wingspan"]
        assert result == {"status": "not_listed", "options": []}

    def test_status_out_of_stock_and_unknown_stock(self):
        rows = [_row("LPG", "Azul", qty=0), _row("VR", "Cascadia", qty=None)]
        with _with_catalogue(rows):
            result = availability_for_titles(["Azul", "Cascadia"])
        assert result["Azul"]["status"] == "out_of_stock"
        assert result["Cascadia"]["status"] == "listed"

    def test_one_option_per_distributor(self):
        rows = [
            _row("LPG", "Azul", qty=0, code="A1"),
            _row("LPG", "Azul Board Game", qty=7, code="A2"),
        ]
        with _with_catalogue(rows):
            options = availability_for_titles(["Azul"])["Azul"]["options"]
        assert len(options) == 1
        assert options[0]["qty_available"] == 7

    def test_returns_none_when_catalogue_unavailable(self):
        with patch(
            "services.distro_availability.fetch_distro_catalogue",
            side_effect=HLStockServiceError("not configured"),
        ):
            assert availability_for_titles(["Azul"]) is None

    def test_returns_none_when_catalogue_empty(self):
        with _with_catalogue([]):
            assert availability_for_titles(["Azul"]) is None


class TestApplyManualLinks:
    class _Link:
        def __init__(self, id, distributor, distro_code):
            self.id, self.distributor, self.distro_code = id, distributor, distro_code

    def _availability(self):
        with _with_catalogue([_row("LPG", "Azul", cost=50.0, qty=2, code="L1")]):
            return availability_for_titles(["Azul", "Obscure Game"])

    def test_manual_link_added_to_unlisted_game(self):
        from services.distro_availability import apply_manual_links

        availability = self._availability()
        assert availability["Obscure Game"]["status"] == "not_listed"
        row = _row("VR", "OBSC GME EURO", cost=30.0, qty=4, code="V9")
        with patch("services.distro_availability.fetch_distro_codes_by_key", return_value=[row]):
            merged = apply_manual_links(availability, {"Obscure Game": [self._Link(7, "VR", "V9")]})

        result = merged["Obscure Game"]
        assert result["status"] == "in_stock"
        assert result["options"][0]["link_id"] == 7
        assert result["options"][0]["match_score"] is None
        assert merged["Azul"] == availability["Azul"]  # untouched

    def test_manual_link_replaces_fuzzy_option_for_same_distributor(self):
        from services.distro_availability import apply_manual_links

        availability = self._availability()
        row = _row("LPG", "Azul (2nd print)", cost=45.0, qty=9, code="L2")
        with patch("services.distro_availability.fetch_distro_codes_by_key", return_value=[row]):
            merged = apply_manual_links(availability, {"Azul": [self._Link(3, "LPG", "L2")]})

        options = merged["Azul"]["options"]
        assert [o["distro_code"] for o in options] == ["L2"]

    def test_link_to_inactive_code_is_skipped(self):
        from services.distro_availability import apply_manual_links

        availability = self._availability()
        with patch("services.distro_availability.fetch_distro_codes_by_key", return_value=[]):
            merged = apply_manual_links(availability, {"Obscure Game": [self._Link(1, "VR", "GONE")]})
        assert merged["Obscure Game"]["status"] == "not_listed"

    def test_passthrough_when_availability_unknown_or_no_links(self):
        from services.distro_availability import apply_manual_links

        assert apply_manual_links(None, {"x": [self._Link(1, "VR", "V")]}) is None
        availability = self._availability()
        assert apply_manual_links(availability, {}) is availability

    def test_returns_none_if_hl_unreadable(self):
        from services.distro_availability import apply_manual_links

        with patch(
            "services.distro_availability.fetch_distro_codes_by_key",
            side_effect=HLStockServiceError("down"),
        ):
            assert apply_manual_links(self._availability(), {"Azul": [self._Link(1, "LPG", "L1")]}) is None
