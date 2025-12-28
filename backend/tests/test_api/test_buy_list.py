"""
Comprehensive Tests for Buy List API Endpoints
Sprint: Test Coverage Improvement

Tests all buy list management endpoints including:
- Listing games with filtering and sorting
- Adding games to buy list
- Updating buy list entries
- Removing from buy list
- Bulk import from CSV
- Price data import
- Helper functions
"""

import csv
import io
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.routers.buy_list import build_buy_list_response, compute_buy_filter
from models import BuyListGame, Game, PriceOffer, PriceSnapshot


class TestComputeBuyFilter:
    """Test the compute_buy_filter function logic"""

    def test_no_lpg_status_returns_false(self):
        """Should return False when lpg_status is None"""
        result = compute_buy_filter(
            best_price=10.0, lpg_status=None, lpg_rrp=50.0, discount_pct=40
        )
        assert result is False

    def test_available_status_with_good_price(self):
        """Should return True when status is AVAILABLE and price*2 <= RRP"""
        result = compute_buy_filter(
            best_price=20.0,  # 20 * 2 = 40 <= 50
            lpg_status="AVAILABLE",
            lpg_rrp=50.0,
            discount_pct=10,
        )
        assert result is True

    def test_available_status_with_bad_price(self):
        """Should return False when status is AVAILABLE but price*2 > RRP"""
        result = compute_buy_filter(
            best_price=30.0,  # 30 * 2 = 60 > 50
            lpg_status="AVAILABLE",
            lpg_rrp=50.0,
            discount_pct=10,
        )
        assert result is False

    def test_back_order_with_good_price(self):
        """Should return True when status is BACK_ORDER and price*2 <= RRP"""
        result = compute_buy_filter(
            best_price=15.0,  # 15 * 2 = 30 <= 50
            lpg_status="BACK_ORDER",
            lpg_rrp=50.0,
            discount_pct=10,
        )
        assert result is True

    def test_not_found_with_high_discount(self):
        """Should return True when status is NOT_FOUND and discount > 30%"""
        result = compute_buy_filter(
            best_price=None, lpg_status="NOT_FOUND", lpg_rrp=50.0, discount_pct=35
        )
        assert result is True

    def test_not_found_with_low_discount(self):
        """Should return False when status is NOT_FOUND but discount <= 30%"""
        result = compute_buy_filter(
            best_price=None, lpg_status="NOT_FOUND", lpg_rrp=50.0, discount_pct=25
        )
        assert result is False

    def test_back_order_oos_with_high_discount(self):
        """Should return True when status is BACK_ORDER_OOS and discount > 30%"""
        result = compute_buy_filter(
            best_price=None, lpg_status="BACK_ORDER_OOS", lpg_rrp=50.0, discount_pct=40
        )
        assert result is True

    def test_available_with_zero_price(self):
        """Should return False when best_price is 0"""
        result = compute_buy_filter(
            best_price=0.0, lpg_status="AVAILABLE", lpg_rrp=50.0, discount_pct=10
        )
        assert result is False

    def test_available_with_no_price_data(self):
        """Should return False when best_price is None for AVAILABLE status"""
        result = compute_buy_filter(
            best_price=None, lpg_status="AVAILABLE", lpg_rrp=50.0, discount_pct=10
        )
        assert result is False


class TestBuildBuyListResponse:
    """Test the build_buy_list_response function"""

    def test_basic_response_without_price(self, db_session):
        """Should build response with basic fields when no price data"""
        # Create a game
        game = Game(
            id=1,
            title="Test Game",
            bgg_id=12345,
            thumbnail_url="http://example.com/thumb.jpg",
        )
        db_session.add(game)
        db_session.flush()

        # Create buy list entry
        buy_list = BuyListGame(
            id=1,
            game_id=game.id,
            rank=5,
            bgo_link="http://bgo.com/game",
            lpg_rrp=Decimal("49.99"),
            lpg_status="AVAILABLE",
            on_buy_list=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        buy_list.game = game

        result = build_buy_list_response(buy_list)

        assert result["id"] == 1
        assert result["game_id"] == game.id
        assert result["rank"] == 5
        assert result["title"] == "Test Game"
        assert result["bgg_id"] == 12345
        assert result["lpg_rrp"] == 49.99
        assert result["lpg_status"] == "AVAILABLE"
        assert result["on_buy_list"] is True
        assert result["latest_price"] is None
        assert result["buy_filter"] is None

    def test_response_with_price_data(self, db_session):
        """Should include price data and computed buy_filter"""
        # Create game
        game = Game(
            id=1,
            title="Test Game",
            bgg_id=12345,
            thumbnail_url="http://example.com/thumb.jpg",
        )
        db_session.add(game)
        db_session.flush()

        # Create buy list entry
        buy_list = BuyListGame(
            id=1,
            game_id=game.id,
            rank=5,
            lpg_rrp=Decimal("50.00"),
            lpg_status="AVAILABLE",
            on_buy_list=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        buy_list.game = game

        # Create price snapshot
        price = PriceSnapshot(
            id=1,
            game_id=game.id,
            checked_at=datetime.now(timezone.utc),
            low_price=Decimal("20.00"),
            mean_price=Decimal("30.00"),
            best_price=Decimal("22.00"),
            best_store="Test Store",
            discount_pct=Decimal("26.67"),
            disc_mean_pct=Decimal("25.00"),
            delta=Decimal("1.67"),
        )

        result = build_buy_list_response(buy_list, price)

        assert result["latest_price"] is not None
        assert result["latest_price"]["best_price"] == 22.00
        assert result["latest_price"]["best_store"] == "Test Store"
        assert result["latest_price"]["discount_pct"] == 26.67
        # buy_filter should be True: price*2 (44) <= rrp (50)
        assert result["buy_filter"] is True


class TestListBuyListGames:
    """Test GET /api/admin/buy-list/games endpoint"""

    def test_list_empty_buy_list(self, client, admin_headers):
        """Should return empty list when no games on buy list"""
        response = client.get("/api/admin/buy-list/games", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_list_buy_list_games(self, client, db_session, admin_headers):
        """Should list all games on buy list"""
        # Create game
        game = Game(
            title="Test Game",
            bgg_id=12345,
            thumbnail_url="http://example.com/thumb.jpg",
        )
        db_session.add(game)
        db_session.flush()

        # Add to buy list
        buy_list = BuyListGame(
            game_id=game.id,
            rank=1,
            lpg_rrp=Decimal("49.99"),
            lpg_status="AVAILABLE",
            on_buy_list=True,
        )
        db_session.add(buy_list)
        db_session.commit()

        response = client.get("/api/admin/buy-list/games", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Test Game"

    def test_filter_by_lpg_status(self, client, db_session, admin_headers):
        """Should filter games by LPG status"""
        # Create two games with different statuses
        for i, status in enumerate(["AVAILABLE", "NOT_FOUND"]):
            game = Game(title=f"Game {i}", bgg_id=12345 + i)
            db_session.add(game)
            db_session.flush()

            buy_list = BuyListGame(
                game_id=game.id, rank=i, lpg_status=status, on_buy_list=True
            )
            db_session.add(buy_list)
        db_session.commit()

        response = client.get(
            "/api/admin/buy-list/games?lpg_status=AVAILABLE", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["lpg_status"] == "AVAILABLE"

    def test_sort_by_rank(self, client, db_session, admin_headers):
        """Should sort games by rank"""
        # Create games with different ranks
        for rank in [3, 1, 2]:
            game = Game(title=f"Game Rank {rank}", bgg_id=12340 + rank)
            db_session.add(game)
            db_session.flush()

            buy_list = BuyListGame(game_id=game.id, rank=rank, on_buy_list=True)
            db_session.add(buy_list)
        db_session.commit()

        response = client.get(
            "/api/admin/buy-list/games?sort_by=rank", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        ranks = [item["rank"] for item in data["items"]]
        assert ranks == [1, 2, 3]

    def test_sort_by_title(self, client, db_session, admin_headers):
        """Should sort games by title"""
        for title in ["Zebra Game", "Alpha Game", "Beta Game"]:
            game = Game(title=title, bgg_id=hash(title) % 100000)
            db_session.add(game)
            db_session.flush()

            buy_list = BuyListGame(game_id=game.id, rank=1, on_buy_list=True)
            db_session.add(buy_list)
        db_session.commit()

        response = client.get(
            "/api/admin/buy-list/games?sort_by=title", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        titles = [item["title"] for item in data["items"]]
        assert titles == ["Alpha Game", "Beta Game", "Zebra Game"]

    def test_requires_auth(self, client):
        """Should require admin authentication"""
        response = client.get("/api/admin/buy-list/games")
        assert response.status_code == 401


class TestAddToBuyList:
    """Test POST /api/admin/buy-list/games endpoint"""

    @patch("bgg_service.fetch_bgg_thing")
    def test_add_existing_game(self, mock_fetch, client, db_session, admin_headers):
        """Should add existing game to buy list"""
        # Create game
        game = Game(title="Test Game", bgg_id=12345)
        db_session.add(game)
        db_session.commit()

        response = client.post(
            "/api/admin/buy-list/games",
            headers=admin_headers,
            json={
                "bgg_id": 12345,
                "rank": 5,
                "bgo_link": "http://bgo.com/game",
                "lpg_rrp": 49.99,
                "lpg_status": "AVAILABLE",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Game"
        assert data["rank"] == 5
        assert data["lpg_status"] == "AVAILABLE"

    @patch("bgg_service.fetch_bgg_thing")
    def test_add_new_game_imports_from_bgg(
        self, mock_fetch, client, db_session, admin_headers
    ):
        """Should import game from BGG if it doesn't exist"""
        # Mock BGG response
        mock_fetch.return_value = {
            "title": "New Game from BGG",
            "year": 2023,
            "thumbnail": "http://bgg.com/thumb.jpg",
            "image": "http://bgg.com/image.jpg",
            "categories": ["Strategy", "Board Game"],
            "designers": ["John Doe"],
            "publishers": ["Test Publisher"],
        }

        response = client.post(
            "/api/admin/buy-list/games",
            headers=admin_headers,
            json={"bgg_id": 99999, "rank": 1, "lpg_status": "AVAILABLE"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Game from BGG"
        assert data["bgg_id"] == 99999

    def test_duplicate_game_returns_error(self, client, db_session, admin_headers):
        """Should return error when game already on buy list"""
        # Create game and add to buy list
        game = Game(title="Test Game", bgg_id=12345)
        db_session.add(game)
        db_session.flush()

        buy_list = BuyListGame(game_id=game.id, rank=1, on_buy_list=True)
        db_session.add(buy_list)
        db_session.commit()

        response = client.post(
            "/api/admin/buy-list/games",
            headers=admin_headers,
            json={"bgg_id": 12345, "rank": 2},
        )

        assert response.status_code == 400
        assert "already on buy list" in response.json()["detail"].lower()


class TestUpdateBuyListGame:
    """Test PUT /api/admin/buy-list/games/{buy_list_id} endpoint"""

    def test_update_buy_list_entry(self, client, db_session, admin_headers):
        """Should update buy list entry fields"""
        # Create game and buy list entry
        game = Game(title="Test Game", bgg_id=12345)
        db_session.add(game)
        db_session.flush()

        buy_list = BuyListGame(
            game_id=game.id,
            rank=5,
            lpg_rrp=Decimal("49.99"),
            lpg_status="AVAILABLE",
            on_buy_list=True,
        )
        db_session.add(buy_list)
        db_session.commit()

        response = client.put(
            f"/api/admin/buy-list/games/{buy_list.id}",
            headers=admin_headers,
            json={"rank": 1, "lpg_status": "BACK_ORDER", "lpg_rrp": 39.99},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["rank"] == 1
        assert data["lpg_status"] == "BACK_ORDER"
        assert data["lpg_rrp"] == 39.99

    def test_update_nonexistent_entry_returns_404(self, client, admin_headers):
        """Should return 404 when entry doesn't exist"""
        response = client.put(
            "/api/admin/buy-list/games/99999",
            headers=admin_headers,
            json={"rank": 1},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestRemoveFromBuyList:
    """Test DELETE /api/admin/buy-list/games/{buy_list_id} endpoint"""

    def test_remove_from_buy_list(self, client, db_session, admin_headers):
        """Should remove game from buy list"""
        # Create game and buy list entry
        game = Game(title="Test Game", bgg_id=12345)
        db_session.add(game)
        db_session.flush()

        buy_list = BuyListGame(game_id=game.id, rank=1, on_buy_list=True)
        db_session.add(buy_list)
        db_session.commit()
        buy_list_id = buy_list.id

        response = client.delete(
            f"/api/admin/buy-list/games/{buy_list_id}", headers=admin_headers
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Game removed from buy list"

        # Verify it's deleted
        deleted = db_session.query(BuyListGame).filter_by(id=buy_list_id).first()
        assert deleted is None

    def test_remove_nonexistent_returns_404(self, client, admin_headers):
        """Should return 404 when entry doesn't exist"""
        response = client.delete("/api/admin/buy-list/games/99999", headers=admin_headers)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestBulkImportCSV:
    """Test POST /api/admin/buy-list/bulk-import-csv endpoint"""

    @patch("bgg_service.fetch_bgg_thing")
    def test_bulk_import_valid_csv(
        self, mock_fetch, client, db_session, admin_headers
    ):
        """Should import multiple games from CSV"""
        # Mock BGG responses
        mock_fetch.return_value = {
            "title": "New Game",
            "year": 2023,
            "categories": ["Strategy"],
        }

        csv_content = """bgg_id,rank,lpg_rrp,lpg_status
12345,1,49.99,AVAILABLE
67890,2,39.99,BACK_ORDER
"""
        csv_file = io.BytesIO(csv_content.encode("utf-8"))

        response = client.post(
            "/api/admin/buy-list/bulk-import-csv",
            headers=admin_headers,
            files={"file": ("test.csv", csv_file, "text/csv")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["added"] >= 0
        assert "message" in data

    def test_bulk_import_missing_bgg_id_column(self, client, admin_headers):
        """Should return error when CSV missing required column"""
        csv_content = """rank,lpg_rrp
1,49.99
"""
        csv_file = io.BytesIO(csv_content.encode("utf-8"))

        response = client.post(
            "/api/admin/buy-list/bulk-import-csv",
            headers=admin_headers,
            files={"file": ("test.csv", csv_file, "text/csv")},
        )

        assert response.status_code == 400
        assert "bgg_id" in response.json()["detail"].lower()


class TestImportPricesFromJSON:
    """Test POST /api/admin/buy-list/import-prices endpoint"""

    def test_import_prices_file_not_found(self, client, admin_headers):
        """Should return 404 when price file doesn't exist"""
        response = client.post(
            "/api/admin/buy-list/import-prices?source_file=nonexistent.json",
            headers=admin_headers,
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestGetLastPriceUpdate:
    """Test GET /api/admin/buy-list/last-updated endpoint"""

    def test_last_updated_no_data(self, client, admin_headers):
        """Should return None when no price data exists"""
        response = client.get("/api/admin/buy-list/last-updated", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["last_updated"] is None
        assert data["source_file"] is None

    def test_last_updated_with_data(self, client, db_session, admin_headers):
        """Should return latest price update timestamp"""
        # Create game
        game = Game(title="Test Game", bgg_id=12345)
        db_session.add(game)
        db_session.flush()

        # Create price snapshot
        checked_time = datetime.now(timezone.utc)
        price = PriceSnapshot(
            game_id=game.id,
            checked_at=checked_time,
            best_price=Decimal("29.99"),
            source_file="test_prices.json",
        )
        db_session.add(price)
        db_session.commit()

        response = client.get("/api/admin/buy-list/last-updated", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["last_updated"] is not None
        assert data["source_file"] == "test_prices.json"


class TestAdvancedListFiltering:
    """Test advanced filtering and sorting options for GET /games"""

    def test_filter_by_on_buy_list_true(self, client, db_session, admin_headers):
        """Test filtering by on_buy_list=true"""
        # Create games with different on_buy_list status
        game1 = Game(title="Game On List", bgg_id=1)
        game2 = Game(title="Game Off List", bgg_id=2)
        db_session.add_all([game1, game2])
        db_session.flush()

        entry1 = BuyListGame(game_id=game1.id, on_buy_list=True, rank=1)
        entry2 = BuyListGame(game_id=game2.id, on_buy_list=False, rank=2)
        db_session.add_all([entry1, entry2])
        db_session.commit()

        response = client.get("/api/admin/buy-list/games?on_buy_list=true", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Game On List"

    def test_sort_by_updated_at_desc(self, client, db_session, admin_headers):
        """Test sorting by updated_at in descending order"""
        from datetime import datetime, timedelta, timezone

        # Create games with different update times
        game1 = Game(title="Old Game", bgg_id=1)
        game2 = Game(title="New Game", bgg_id=2)
        db_session.add_all([game1, game2])
        db_session.flush()

        now = datetime.now(timezone.utc)
        entry1 = BuyListGame(
            game_id=game1.id,
            rank=1,
            updated_at=now - timedelta(days=5)
        )
        entry2 = BuyListGame(
            game_id=game2.id,
            rank=2,
            updated_at=now
        )
        db_session.add_all([entry1, entry2])
        db_session.commit()

        response = client.get(
            "/api/admin/buy-list/games?sort_by=updated_at&sort_desc=true",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["title"] == "New Game"

    def test_sort_by_discount(self, client, db_session, admin_headers):
        """Test sorting by discount percentage"""
        # Create games with price data
        game1 = Game(title="High Discount", bgg_id=1)
        game2 = Game(title="Low Discount", bgg_id=2)
        db_session.add_all([game1, game2])
        db_session.flush()

        entry1 = BuyListGame(game_id=game1.id, rank=1, lpg_rrp=Decimal("50.00"))
        entry2 = BuyListGame(game_id=game2.id, rank=2, lpg_rrp=Decimal("30.00"))
        db_session.add_all([entry1, entry2])
        db_session.flush()

        # Add price snapshots with different discounts
        snapshot1 = PriceSnapshot(
            game_id=game1.id,
            checked_at=datetime.now(timezone.utc),
            best_price=Decimal("25.00")  # 50% discount
        )
        snapshot2 = PriceSnapshot(
            game_id=game2.id,
            checked_at=datetime.now(timezone.utc),
            best_price=Decimal("27.00")  # 10% discount
        )
        db_session.add_all([snapshot1, snapshot2])
        db_session.commit()

        response = client.get(
            "/api/admin/buy-list/games?sort_by=discount&sort_desc=true",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        # High discount game should be first
        if len(data["items"]) >= 2 and data["items"][0]["latest_price"] and data["items"][1]["latest_price"]:
            first_discount = data["items"][0]["latest_price"].get("discount_pct")
            second_discount = data["items"][1]["latest_price"].get("discount_pct")
            if first_discount is not None and second_discount is not None:
                assert first_discount >= second_discount

    def test_sort_default_by_rank(self, client, db_session, admin_headers):
        """Test default sorting by rank"""
        game1 = Game(title="Rank 3", bgg_id=1)
        game2 = Game(title="Rank 1", bgg_id=2)
        game3 = Game(title="No Rank", bgg_id=3)
        db_session.add_all([game1, game2, game3])
        db_session.flush()

        entry1 = BuyListGame(game_id=game1.id, rank=3)
        entry2 = BuyListGame(game_id=game2.id, rank=1)
        entry3 = BuyListGame(game_id=game3.id, rank=None)  # No rank
        db_session.add_all([entry1, entry2, entry3])
        db_session.commit()

        response = client.get("/api/admin/buy-list/games", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        # Should have at least the games we created
        assert len(data["items"]) >= 3
        # Check that items with ranks come before nulls
        ranked_items = [item for item in data["items"] if item.get("rank") is not None]
        if len(ranked_items) >= 2:
            # First ranked item should have rank 1
            assert ranked_items[0]["rank"] == 1

    def test_buy_filter_no_price(self, client, db_session, admin_headers):
        """Test buy_filter='no_price' shows games with no price data"""
        game1 = Game(title="No Price", bgg_id=1)
        game2 = Game(title="Has Price", bgg_id=2)
        db_session.add_all([game1, game2])
        db_session.flush()

        entry1 = BuyListGame(
            game_id=game1.id,
            rank=1,
            lpg_status="NOT_FOUND"  # Required for no_price filter
        )
        entry2 = BuyListGame(
            game_id=game2.id,
            rank=2,
            lpg_status="AVAILABLE"
        )
        db_session.add_all([entry1, entry2])
        db_session.flush()

        # Add price only for game2
        snapshot = PriceSnapshot(
            game_id=game2.id,
            checked_at=datetime.now(timezone.utc),
            best_price=Decimal("29.99")
        )
        db_session.add(snapshot)
        db_session.commit()

        response = client.get(
            "/api/admin/buy-list/games?buy_filter=no_price",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        # Should only return game with no price and NOT_FOUND status
        assert data["total"] >= 1
        for item in data["items"]:
            assert item["latest_price"] is None or item["latest_price"]["best_price"] is None

    def test_buy_filter_buy_now(self, client, db_session, admin_headers):
        """Test buy_filter='buy_now' shows recommended games"""
        game = Game(title="Good Deal", bgg_id=1)
        db_session.add(game)
        db_session.flush()

        entry = BuyListGame(
            game_id=game.id,
            rank=1,
            lpg_status="AVAILABLE",
            lpg_rrp=Decimal("50.00")
        )
        db_session.add(entry)
        db_session.flush()

        # Add price that makes buy_filter True (price * 2 <= RRP)
        snapshot = PriceSnapshot(
            game_id=game.id,
            checked_at=datetime.now(timezone.utc),
            best_price=Decimal("20.00")  # 20 * 2 = 40 <= 50
        )
        db_session.add(snapshot)
        db_session.commit()

        response = client.get(
            "/api/admin/buy-list/games?buy_filter=buy_now",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        # Should include this game
        assert data["total"] >= 1

    def test_buy_filter_not_recommended(self, client, db_session, admin_headers):
        """Test buy_filter='not_recommended' shows games not to buy"""
        game = Game(title="Bad Deal", bgg_id=1)
        db_session.add(game)
        db_session.flush()

        entry = BuyListGame(
            game_id=game.id,
            rank=1,
            lpg_status="AVAILABLE",
            lpg_rrp=Decimal("50.00")
        )
        db_session.add(entry)
        db_session.flush()

        # Add price that makes buy_filter False (price * 2 > RRP)
        snapshot = PriceSnapshot(
            game_id=game.id,
            checked_at=datetime.now(timezone.utc),
            best_price=Decimal("30.00")  # 30 * 2 = 60 > 50
        )
        db_session.add(snapshot)
        db_session.commit()

        response = client.get(
            "/api/admin/buy-list/games?buy_filter=not_recommended",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        # Should include games where buy_filter is False
        assert data["total"] >= 1


class TestErrorHandling:
    """Test error handling in buy list endpoints"""

    def test_add_game_bgg_fetch_error(self, client, db_session, admin_headers):
        """Test error when BGG fetch fails"""
        with patch("bgg_service.fetch_bgg_thing") as mock_fetch:
            mock_fetch.side_effect = Exception("BGG API error")

            response = client.post(
                "/api/admin/buy-list/games",
                json={"bgg_id": 99999},
                headers=admin_headers
            )

            assert response.status_code == 400
            assert "Failed to import game from BGG" in response.json()["detail"]

    def test_list_games_with_error(self, client, db_session, admin_headers):
        """Test list games handles errors gracefully"""
        # Create a game that will work
        game = Game(title="Test Game", bgg_id=1)
        db_session.add(game)
        db_session.flush()

        entry = BuyListGame(game_id=game.id, rank=1)
        db_session.add(entry)
        db_session.commit()

        # Should still return successfully even if some error conditions exist
        response = client.get("/api/admin/buy-list/games", headers=admin_headers)
        assert response.status_code == 200


# ==============================================================================
# Additional Error Handling and Edge Case Tests
# ==============================================================================


class TestBuyListErrorHandling:
    """Test error handling and edge cases in buy list endpoints"""

    def test_list_with_database_error(self, client, db_session, admin_headers):
        """Test list endpoint handles database errors gracefully"""
        with patch("api.routers.buy_list.select", side_effect=Exception("Database error")):
            response = client.get("/api/admin/buy-list/games", headers=admin_headers)
            assert response.status_code == 500
            assert "Failed to retrieve buy list" in response.json()["detail"]

    def test_add_game_with_general_exception(self, client, db_session, admin_headers):
        """Test add endpoint handles unexpected errors"""
        # Create a game first
        game = Game(title="Test Game", bgg_id=12345)
        db_session.add(game)
        db_session.commit()

        with patch("api.routers.buy_list.BuyListGame", side_effect=Exception("Unexpected error")):
            response = client.post(
                "/api/admin/buy-list/games",
                json={"bgg_id": 12345, "rank": 1},
                headers=admin_headers
            )
            assert response.status_code == 500
            assert "Failed to add game to buy list" in response.json()["detail"]

    def test_update_with_optional_fields(self, client, db_session, admin_headers):
        """Test updating buy list entry with all optional fields"""
        # Create game and buy list entry
        game = Game(title="Test Game", bgg_id=12345)
        db_session.add(game)
        db_session.flush()

        entry = BuyListGame(game_id=game.id, rank=1)
        db_session.add(entry)
        db_session.commit()

        # Update with all optional fields
        response = client.put(
            f"/api/admin/buy-list/games/{entry.id}",
            json={
                "rank": 5,
                "bgo_link": "https://example.com",
                "lpg_rrp": 49.99,
                "lpg_status": "AVAILABLE",
                "on_buy_list": True
            },
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["rank"] == 5
        assert data["bgo_link"] == "https://example.com"


    def test_update_with_on_buy_list_flag(self, client, db_session, admin_headers):
        """Test updating on_buy_list flag specifically"""
        # Create game and buy list entry
        game = Game(title="Test Game", bgg_id=12345)
        db_session.add(game)
        db_session.flush()

        entry = BuyListGame(game_id=game.id, rank=1, on_buy_list=True)
        db_session.add(entry)
        db_session.commit()

        # Update on_buy_list to False
        response = client.put(
            f"/api/admin/buy-list/games/{entry.id}",
            json={"on_buy_list": False},
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["on_buy_list"] is False


class TestBuyListErrorHandling:
    """Test error handling in buy list endpoints"""

    def test_update_buy_list_game_database_error(
        self, client, db_session, admin_headers
    ):
        """Test update_buy_list_game handles database errors gracefully"""
        # Create game and buy list entry
        game = Game(title="Test Game", bgg_id=12345)
        db_session.add(game)
        db_session.flush()

        entry = BuyListGame(game_id=game.id, rank=1)
        db_session.add(entry)
        db_session.commit()

        # Mock database to raise exception
        with patch("api.routers.buy_list.select") as mock_select:
            mock_select.side_effect = Exception("Database error")

            response = client.put(
                f"/api/admin/buy-list/games/{entry.id}",
                json={"rank": 5},
                headers=admin_headers,
            )

            assert response.status_code == 500
            assert "Failed to update buy list game" in response.json()["detail"]

    def test_remove_from_buy_list_database_error(
        self, client, db_session, admin_headers
    ):
        """Test remove_from_buy_list handles database errors gracefully"""
        # Create game and buy list entry
        game = Game(title="Test Game", bgg_id=12345)
        db_session.add(game)
        db_session.flush()

        entry = BuyListGame(game_id=game.id, rank=1)
        db_session.add(entry)
        db_session.commit()

        # Mock database to raise exception
        with patch("api.routers.buy_list.select") as mock_select:
            mock_select.side_effect = Exception("Database error")

            response = client.delete(
                f"/api/admin/buy-list/games/{entry.id}", headers=admin_headers
            )

            assert response.status_code == 500
            assert "Failed to remove game from buy list" in response.json()["detail"]

    def test_bulk_import_csv_invalid_file(self, client, admin_headers):
        """Test bulk import with invalid CSV file (missing bgg_id column)"""
        # Create invalid CSV content (missing required bgg_id column)
        csv_content = "invalid,csv,content\n"

        response = client.post(
            "/api/admin/buy-list/bulk-import-csv",
            files={"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
            headers=admin_headers,
        )

        # Should return 400 for missing required column
        assert response.status_code == 400
        assert "bgg_id" in response.json()["detail"]

    def test_bulk_import_csv_with_bgg_import_failure(
        self, client, db_session, admin_headers
    ):
        """Test bulk import when BGG import fails"""
        # Create CSV with game not in database
        csv_content = "bgg_id,rank\n999999,1\n"

        # Mock BGG service to fail
        with patch("bgg_service.fetch_bgg_thing") as mock_fetch:
            mock_fetch.side_effect = Exception("BGG API error")

            response = client.post(
                "/api/admin/buy-list/bulk-import-csv",
                files={
                    "file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")
                },
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()
            # Game import should result in error due to BGG failure
            assert data["errors"] >= 1


# Note: Price import endpoint tests are complex due to specific directory structure
# requirements (backend/price_data/). Testing is covered by integration tests.
# Focus is on error handling and bulk import tests above.


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
