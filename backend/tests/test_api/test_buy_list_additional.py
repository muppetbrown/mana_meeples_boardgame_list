"""
Additional Tests for Buy List API to Improve Coverage
Focus: Uncovered lines and edge cases in buy_list.py
Target: Increase coverage from 73.8% to 90%+
"""

import csv
import io
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from models import BuyListGame, Game, PriceOffer, PriceSnapshot


class TestBulkImportCSVEdgeCases:
    """Test edge cases in bulk CSV import to cover uncovered lines"""

    @patch("bgg_service.fetch_bgg_thing")
    def test_bulk_import_with_invalid_rank_value(
        self, mock_fetch, client, db_session, admin_headers
    ):
        """Test bulk import with invalid rank value (line 532-533)"""
        # Mock BGG response for new game
        mock_fetch.return_value = {
            "title": "Test Game",
            "year": 2023,
            "categories": ["Strategy"],
        }

        # CSV with invalid rank
        csv_content = "bgg_id,rank,lpg_rrp\n12345,invalid_rank,49.99\n"

        response = client.post(
            "/api/admin/buy-list/bulk-import-csv",
            files={"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Should have added the game despite invalid rank
        assert data["added"] >= 1
        # Error details should mention invalid rank
        assert data["error_details"] is not None
        assert any("rank" in error.lower() for error in data["error_details"])

    @patch("bgg_service.fetch_bgg_thing")
    def test_bulk_import_with_invalid_lpg_rrp(
        self, mock_fetch, client, db_session, admin_headers
    ):
        """Test bulk import with invalid lpg_rrp value (line 539-540)"""
        mock_fetch.return_value = {
            "title": "Test Game",
            "year": 2023,
            "categories": ["Strategy"],
        }

        # CSV with invalid lpg_rrp
        csv_content = "bgg_id,lpg_rrp\n12346,not_a_number\n"

        response = client.post(
            "/api/admin/buy-list/bulk-import-csv",
            files={"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Should still add the game
        assert data["added"] >= 1
        # Error details should mention invalid lpg_rrp
        assert data["error_details"] is not None

    @patch("bgg_service.fetch_bgg_thing")
    def test_bulk_import_empty_bgg_id_rows(
        self, mock_fetch, client, db_session, admin_headers
    ):
        """Test bulk import skips rows with empty bgg_id (line 517-518)"""
        mock_fetch.return_value = {
            "title": "Valid Game",
            "year": 2023,
            "categories": ["Strategy"],
        }

        # CSV with empty bgg_id rows
        csv_content = "bgg_id,rank\n,1\n  ,2\n12347,3\n"

        response = client.post(
            "/api/admin/buy-list/bulk-import-csv",
            files={"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Should have skipped 2 rows with empty bgg_id
        assert data["skipped"] == 2
        # Should have added 1 valid game
        assert data["added"] == 1

    @patch("bgg_service.fetch_bgg_thing")
    def test_bulk_import_invalid_bgg_id_format(
        self, mock_fetch, client, db_session, admin_headers
    ):
        """Test bulk import with non-numeric bgg_id (line 522-525)"""
        csv_content = "bgg_id,rank\nabc123,1\n"

        response = client.post(
            "/api/admin/buy-list/bulk-import-csv",
            files={"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Should have 1 error for invalid BGG ID
        assert data["errors"] == 1
        assert any("Invalid BGG ID" in error for error in data["error_details"])

    @patch("bgg_service.fetch_bgg_thing")
    def test_bulk_import_update_existing_buy_list_entry(
        self, mock_fetch, client, db_session, admin_headers
    ):
        """Test bulk import updates existing buy list entries (line 598-607)"""
        # Create existing game and buy list entry
        game = Game(title="Existing Game", bgg_id=12348)
        db_session.add(game)
        db_session.flush()

        existing_entry = BuyListGame(
            game_id=game.id,
            rank=10,
            bgo_link="http://old-link.com",
            lpg_rrp=Decimal("30.00"),
            lpg_status="NOT_FOUND",
            on_buy_list=True,
        )
        db_session.add(existing_entry)
        db_session.commit()

        # CSV to update the existing entry
        csv_content = "bgg_id,rank,bgo_link,lpg_rrp,lpg_status\n12348,1,http://new-link.com,49.99,AVAILABLE\n"

        response = client.post(
            "/api/admin/buy-list/bulk-import-csv",
            files={"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Should have updated 1 entry
        assert data["updated"] == 1
        assert data["added"] == 0

        # Verify the update
        db_session.refresh(existing_entry)
        assert existing_entry.rank == 1
        assert existing_entry.bgo_link == "http://new-link.com"
        assert float(existing_entry.lpg_rrp) == 49.99
        assert existing_entry.lpg_status == "AVAILABLE"

    @patch("bgg_service.fetch_bgg_thing")
    def test_bulk_import_updates_game_status_to_buy_list(
        self, mock_fetch, client, db_session, admin_headers
    ):
        """Test bulk import updates game status to BUY_LIST (line 588-589)"""
        # Create existing game with a valid status (not BUY_LIST)
        # Valid statuses based on models.py: OWNED, BUY_LIST, WISHLIST, or NULL
        game = Game(title="Catalogued Game", bgg_id=12349, status="OWNED")
        db_session.add(game)
        db_session.commit()

        # CSV to add this game to buy list
        csv_content = "bgg_id,rank\n12349,5\n"

        response = client.post(
            "/api/admin/buy-list/bulk-import-csv",
            files={"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["added"] == 1

        # Verify status was updated
        db_session.refresh(game)
        assert game.status == "BUY_LIST"

    def test_bulk_import_row_exception_handling(
        self, client, db_session, admin_headers
    ):
        """Test bulk import handles row-level exceptions (line 621-624)"""
        # Create a game that exists
        game = Game(title="Existing", bgg_id=12350)
        db_session.add(game)
        db_session.commit()

        # Patch BuyListGame to raise exception on specific row
        original_init = BuyListGame.__init__

        def mock_init(self, **kwargs):
            if kwargs.get("rank") == 999:
                raise ValueError("Simulated row error")
            original_init(self, **kwargs)

        with patch.object(BuyListGame, "__init__", mock_init):
            csv_content = "bgg_id,rank\n12350,999\n"

            response = client.post(
                "/api/admin/buy-list/bulk-import-csv",
                files={
                    "file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")
                },
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()
            # Should have error count
            assert data["errors"] >= 1

    def test_bulk_import_general_exception_handling(
        self, client, admin_headers
    ):
        """Test bulk import general exception handling (line 645-648)"""
        # Patch csv.DictReader to raise exception
        with patch("csv.DictReader", side_effect=Exception("General CSV error")):
            csv_content = "bgg_id,rank\n12351,1\n"

            response = client.post(
                "/api/admin/buy-list/bulk-import-csv",
                files={
                    "file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")
                },
                headers=admin_headers,
            )

            assert response.status_code == 500
            assert "Failed to import CSV" in response.json()["detail"]


class TestUpdateBuyListGameEdgeCases:
    """Test edge cases for update endpoint"""

    def test_update_with_bgo_link(self, client, db_session, admin_headers):
        """Test updating bgo_link field (line 405)"""
        game = Game(title="Test Game", bgg_id=12352)
        db_session.add(game)
        db_session.flush()

        entry = BuyListGame(game_id=game.id, rank=1)
        db_session.add(entry)
        db_session.commit()

        response = client.put(
            f"/api/admin/buy-list/games/{entry.id}",
            json={"bgo_link": "http://example.com/new-link"},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["bgo_link"] == "http://example.com/new-link"

    def test_update_on_buy_list_field(self, client, db_session, admin_headers):
        """Test updating on_buy_list field (line 411)"""
        game = Game(title="Test Game", bgg_id=12353)
        db_session.add(game)
        db_session.flush()

        entry = BuyListGame(game_id=game.id, rank=1, on_buy_list=True)
        db_session.add(entry)
        db_session.commit()

        response = client.put(
            f"/api/admin/buy-list/games/{entry.id}",
            json={"on_buy_list": False},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["on_buy_list"] is False


class TestAddToBuyListEdgeCases:
    """Test edge cases for add to buy list endpoint"""

    @patch("bgg_service.fetch_bgg_thing")
    def test_add_game_http_exception_reraise(
        self, mock_fetch, client, db_session, admin_headers
    ):
        """Test that HTTPException is re-raised (line 383-384)"""
        # Create game that already exists on buy list
        game = Game(title="Duplicate", bgg_id=12354)
        db_session.add(game)
        db_session.flush()

        entry = BuyListGame(game_id=game.id, rank=1, on_buy_list=True)
        db_session.add(entry)
        db_session.commit()

        response = client.post(
            "/api/admin/buy-list/games",
            json={"bgg_id": 12354, "rank": 2},
            headers=admin_headers,
        )

        # Should re-raise HTTPException with 400 status
        assert response.status_code == 400
        assert "already on buy list" in response.json()["detail"].lower()

    def test_add_game_general_exception_handling(
        self, client, db_session, admin_headers
    ):
        """Test general exception handling in add endpoint (line 385-386)"""
        # Create a game
        game = Game(title="Test Game", bgg_id=12355)
        db_session.add(game)
        db_session.commit()

        # Mock select to raise unexpected exception
        with patch("api.routers.buy_list.select", side_effect=Exception("Database connection lost")):
            response = client.post(
                "/api/admin/buy-list/games",
                json={"bgg_id": 12355, "rank": 1},
                headers=admin_headers,
            )

            assert response.status_code == 500
            assert "Failed to add game to buy list" in response.json()["detail"]


class TestListBuyListGamesEdgeCases:
    """Test edge cases for list endpoint"""

    def test_list_with_invalid_sort_field(self, client, db_session, admin_headers):
        """Test list with invalid sort field defaults to rank (line 202)"""
        game = Game(title="Test Game", bgg_id=12356)
        db_session.add(game)
        db_session.flush()

        entry = BuyListGame(game_id=game.id, rank=1, on_buy_list=True)
        db_session.add(entry)
        db_session.commit()

        # Use invalid sort field
        response = client.get(
            "/api/admin/buy-list/games?sort_by=invalid_field",
            headers=admin_headers,
        )

        # Should still succeed and use default rank sorting
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    def test_list_exception_handling(self, client, admin_headers):
        """Test list endpoint exception handling (line 280-282)"""
        # Mock select to raise exception
        with patch("api.routers.buy_list.select", side_effect=Exception("Database error")):
            response = client.get("/api/admin/buy-list/games", headers=admin_headers)

            assert response.status_code == 500
            assert "Failed to retrieve buy list" in response.json()["detail"]


class TestImportPricesFromJSON:
    """Test price import endpoint to cover uncovered lines"""

    def test_import_prices_with_valid_json_creates_price_data(
        self, client, db_session, admin_headers
    ):
        """Test importing prices from valid JSON file (lines 686-693)"""
        # Create a game
        game = Game(title="Priced Game", bgg_id=12357)
        db_session.add(game)
        db_session.commit()

        # Create actual price_data directory structure
        import os
        backend_dir = Path(__file__).parent.parent.parent
        price_data_dir = backend_dir / "price_data"
        price_data_dir.mkdir(exist_ok=True)

        json_file = price_data_dir / "test_import_prices.json"

        try:
            # Create valid JSON price data
            price_data = {
                "checked_at": datetime.utcnow().isoformat(),
                "games": [
                    {
                        "bgg_id": 12357,
                        "name": "Priced Game",
                        "low_price": 25.00,
                        "mean_price": 30.00,
                        "best_price": 27.00,
                        "best_store": "Test Store",
                        "discount_pct": 10.0,
                        "disc_mean_pct": 5.0,
                        "delta": 2.0,
                        "offers": [
                            {
                                "store": "Store A",
                                "price_nzd": 27.00,
                                "availability": "In Stock",
                                "store_link": "http://store-a.com/game",
                                "in_stock": True,
                            }
                        ],
                    }
                ],
            }

            with open(json_file, "w") as f:
                json.dump(price_data, f)

            response = client.post(
                "/api/admin/buy-list/import-prices?source_file=test_import_prices.json",
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["imported"] == 1
            assert data["skipped"] == 0

        finally:
            # Cleanup
            if json_file.exists():
                json_file.unlink()

    def test_import_prices_invalid_json_structure(
        self, client, db_session, admin_headers
    ):
        """Test import with invalid JSON structure (line 680-684)"""
        backend_dir = Path(__file__).parent.parent.parent
        price_data_dir = backend_dir / "price_data"
        price_data_dir.mkdir(exist_ok=True)

        json_file = price_data_dir / "test_invalid_structure.json"

        try:
            # Create invalid JSON (missing required fields)
            invalid_data = {"invalid": "structure"}

            with open(json_file, "w") as f:
                json.dump(invalid_data, f)

            response = client.post(
                "/api/admin/buy-list/import-prices?source_file=test_invalid_structure.json",
                headers=admin_headers,
            )

            assert response.status_code == 400
            assert "Invalid JSON structure" in response.json()["detail"]

        finally:
            # Cleanup
            if json_file.exists():
                json_file.unlink()

    def test_import_prices_game_not_found_skips(
        self, client, db_session, admin_headers
    ):
        """Test import skips games not found by BGG ID or name (line 709-713)"""
        backend_dir = Path(__file__).parent.parent.parent
        price_data_dir = backend_dir / "price_data"
        price_data_dir.mkdir(exist_ok=True)

        json_file = price_data_dir / "test_unknown_game.json"

        try:
            # Create JSON with unknown game
            price_data = {
                "checked_at": datetime.utcnow().isoformat(),
                "games": [
                    {
                        "bgg_id": 999999,  # Non-existent game
                        "name": "Unknown Game",
                        "best_price": 25.00,
                    }
                ],
            }

            with open(json_file, "w") as f:
                json.dump(price_data, f)

            response = client.post(
                "/api/admin/buy-list/import-prices?source_file=test_unknown_game.json",
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()
            # Should skip the unknown game
            assert data["skipped"] == 1
            assert data["imported"] == 0

        finally:
            # Cleanup
            if json_file.exists():
                json_file.unlink()


class TestSortByDiscount:
    """Test discount sorting edge cases"""

    def test_sort_by_discount_with_none_values(
        self, client, db_session, admin_headers
    ):
        """Test discount sorting handles None discount values (line 268-276)"""
        # Create games with and without discount data
        game1 = Game(title="No Discount Data", bgg_id=12358)
        game2 = Game(title="Has Discount", bgg_id=12359)
        db_session.add_all([game1, game2])
        db_session.flush()

        entry1 = BuyListGame(game_id=game1.id, rank=1, on_buy_list=True)
        entry2 = BuyListGame(game_id=game2.id, rank=2, on_buy_list=True)
        db_session.add_all([entry1, entry2])
        db_session.flush()

        # Add price with discount only for game2
        snapshot = PriceSnapshot(
            game_id=game2.id,
            checked_at=datetime.utcnow(),
            best_price=Decimal("25.00"),
            discount_pct=Decimal("20.00"),
        )
        db_session.add(snapshot)
        db_session.commit()

        # Sort by discount
        response = client.get(
            "/api/admin/buy-list/games?sort_by=discount&sort_desc=true",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Should handle None values gracefully
        assert data["total"] >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
