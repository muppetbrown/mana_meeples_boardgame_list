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
