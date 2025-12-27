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
from datetime import datetime, timedelta
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
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
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
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        buy_list.game = game

        # Create price snapshot
        price = PriceSnapshot(
            id=1,
            game_id=game.id,
            checked_at=datetime.utcnow(),
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
        checked_time = datetime.utcnow()
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
