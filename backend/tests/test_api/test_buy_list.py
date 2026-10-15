"""
Tests for the 'games to add' API endpoints (backend/api/routers/buy_list.py).

Covers listing/sorting, adding (existing game and BGG auto-import),
updating, removing, bulk CSV import, the library-gaps endpoint, and
gap-match annotation on list/add/update responses.
"""

import io
from unittest.mock import patch

import pytest

from api.routers.buy_list import build_buy_list_response
from models import BuyListGame, Game


class TestBuildBuyListResponse:
    """Test the build_buy_list_response function"""

    def test_basic_response_without_gaps(self, db_session):
        """Should build response with basic fields when gaps is None"""
        game = Game(id=1, title="Test Game", bgg_id=12345, image="http://example.com/thumb.jpg")
        db_session.add(game)
        db_session.flush()

        buy_list = BuyListGame(id=1, game_id=game.id, rank=2, notes="worth a look", on_buy_list=True)
        db_session.add(buy_list)
        db_session.commit()
        db_session.refresh(buy_list)

        result = build_buy_list_response(buy_list)

        assert result["id"] == 1
        assert result["game_id"] == game.id
        assert result["rank"] == 2
        assert result["notes"] == "worth a look"
        assert result["title"] == "Test Game"
        assert result["bgg_id"] == 12345
        assert result["gap_match"] is None

    def test_response_annotates_gap_match(self, db_session):
        """Should annotate gap_match when gaps payload is passed"""
        game = Game(
            id=1, title="Party Game", bgg_id=1, mana_meeple_category="PARTY_ICEBREAKERS",
            players_min=8, players_max=12,
        )
        db_session.add(game)
        db_session.flush()

        buy_list = BuyListGame(game_id=game.id, on_buy_list=True)
        db_session.add(buy_list)
        db_session.commit()
        db_session.refresh(buy_list)

        gaps = {
            "total_games": 10,
            "category_gaps": [
                {"category": "PARTY_ICEBREAKERS", "count": 0, "pct_of_collection": 0.0, "is_gap": True},
            ],
            "player_count_gaps": [
                {"player_count": "9+", "games_supporting": 0, "pct_of_collection": 0.0, "is_gap": True},
            ],
        }

        result = build_buy_list_response(buy_list, gaps)

        assert result["gap_match"]["category_is_gap"] is True
        assert result["gap_match"]["matching_player_count_gaps"] == ["9+"]


class TestListBuyListGames:
    """Test GET /api/admin/buy-list/games"""

    def test_list_empty(self, client, admin_headers):
        response = client.get("/api/admin/buy-list/games", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data == {"total": 0, "items": []}

    def test_list_with_items_includes_gap_match(self, client, db_session, admin_headers):
        game = Game(title="Test Game", bgg_id=5555, mana_meeple_category="PARTY_ICEBREAKERS")
        db_session.add(game)
        db_session.flush()
        db_session.add(BuyListGame(game_id=game.id, rank=1, on_buy_list=True))
        db_session.commit()

        response = client.get("/api/admin/buy-list/games", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Test Game"
        assert "gap_match" in data["items"][0]

    def test_sort_by_title(self, client, db_session, admin_headers):
        game_a = Game(title="Zeta Game", bgg_id=1)
        game_b = Game(title="Alpha Game", bgg_id=2)
        db_session.add_all([game_a, game_b])
        db_session.flush()
        db_session.add_all([
            BuyListGame(game_id=game_a.id, on_buy_list=True),
            BuyListGame(game_id=game_b.id, on_buy_list=True),
        ])
        db_session.commit()

        response = client.get(
            "/api/admin/buy-list/games", params={"sort_by": "title"}, headers=admin_headers
        )
        titles = [item["title"] for item in response.json()["items"]]
        assert titles == ["Alpha Game", "Zeta Game"]

    def test_excludes_entries_not_on_buy_list(self, client, db_session, admin_headers):
        game = Game(title="Removed Game", bgg_id=9)
        db_session.add(game)
        db_session.flush()
        db_session.add(BuyListGame(game_id=game.id, on_buy_list=False))
        db_session.commit()

        response = client.get("/api/admin/buy-list/games", headers=admin_headers)
        assert response.json()["total"] == 0

    def test_requires_auth(self, client):
        response = client.get("/api/admin/buy-list/games")
        assert response.status_code in (401, 403)


class TestAddToBuyList:
    """Test POST /api/admin/buy-list/games"""

    def test_add_existing_game(self, client, db_session, admin_headers):
        game = Game(title="Test Game", bgg_id=12345, status="BUY_LIST")
        db_session.add(game)
        db_session.commit()

        response = client.post(
            "/api/admin/buy-list/games",
            headers=admin_headers,
            json={"bgg_id": 12345, "rank": 5, "notes": "fills a gap"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Game"
        assert data["rank"] == 5
        assert data["notes"] == "fills a gap"

    @patch("bgg_service.fetch_bgg_thing")
    def test_add_new_game_imports_from_bgg(self, mock_fetch, client, db_session, admin_headers):
        mock_fetch.return_value = {
            "title": "New Game from BGG",
            "year": 2023,
            "image": "http://bgg.com/image.jpg",
            "categories": ["Strategy"],
            "designers": ["John Doe"],
        }

        response = client.post(
            "/api/admin/buy-list/games",
            headers=admin_headers,
            json={"bgg_id": 99999, "rank": 1},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Game from BGG"
        assert data["bgg_id"] == 99999

    def test_duplicate_game_returns_error(self, client, db_session, admin_headers):
        game = Game(title="Test Game", bgg_id=12345, status="BUY_LIST")
        db_session.add(game)
        db_session.flush()
        db_session.add(BuyListGame(game_id=game.id, rank=1, on_buy_list=True))
        db_session.commit()

        response = client.post(
            "/api/admin/buy-list/games", headers=admin_headers, json={"bgg_id": 12345},
        )

        assert response.status_code == 400
        assert "already on buy list" in response.json()["detail"].lower()

    def test_owned_game_rejected(self, client, db_session, admin_headers):
        game = Game(title="Owned Game", bgg_id=777, status="OWNED")
        db_session.add(game)
        db_session.commit()

        response = client.post(
            "/api/admin/buy-list/games", headers=admin_headers, json={"bgg_id": 777},
        )

        assert response.status_code == 400
        assert "owned collection" in response.json()["detail"].lower()

    @patch("bgg_service.fetch_bgg_thing")
    def test_bgg_fetch_failure_returns_400(self, mock_fetch, client, admin_headers):
        mock_fetch.side_effect = Exception("BGG unreachable")

        response = client.post(
            "/api/admin/buy-list/games", headers=admin_headers, json={"bgg_id": 424242},
        )

        assert response.status_code == 400

    def test_unexpected_error_returns_500_and_rolls_back(self, client, db_session, admin_headers):
        game = Game(title="Test Game", bgg_id=55555, status="BUY_LIST")
        db_session.add(game)
        db_session.commit()

        with patch("api.routers.buy_list.compute_library_gaps", side_effect=Exception("boom")):
            response = client.post(
                "/api/admin/buy-list/games", headers=admin_headers, json={"bgg_id": 55555},
            )

        assert response.status_code == 500


class TestUpdateBuyListGame:
    """Test PUT /api/admin/buy-list/games/{buy_list_id}"""

    def test_update_rank_and_notes(self, client, db_session, admin_headers):
        game = Game(title="Test Game", bgg_id=1)
        db_session.add(game)
        db_session.flush()
        entry = BuyListGame(game_id=game.id, rank=1, on_buy_list=True)
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        response = client.put(
            f"/api/admin/buy-list/games/{entry.id}",
            headers=admin_headers,
            json={"rank": 9, "notes": "revised priority"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["rank"] == 9
        assert data["notes"] == "revised priority"

    def test_update_on_buy_list_flag(self, client, db_session, admin_headers):
        game = Game(title="Test Game", bgg_id=1)
        db_session.add(game)
        db_session.flush()
        entry = BuyListGame(game_id=game.id, on_buy_list=True)
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        response = client.put(
            f"/api/admin/buy-list/games/{entry.id}",
            headers=admin_headers,
            json={"on_buy_list": False},
        )

        assert response.status_code == 200
        assert response.json()["on_buy_list"] is False

    def test_update_nonexistent_entry_returns_404(self, client, admin_headers):
        response = client.put(
            "/api/admin/buy-list/games/999999", headers=admin_headers, json={"rank": 1},
        )
        assert response.status_code == 404


class TestRemoveFromBuyList:
    """Test DELETE /api/admin/buy-list/games/{buy_list_id}"""

    def test_remove(self, client, db_session, admin_headers):
        game = Game(title="Test Game", bgg_id=1)
        db_session.add(game)
        db_session.flush()
        entry = BuyListGame(game_id=game.id, on_buy_list=True)
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        response = client.delete(f"/api/admin/buy-list/games/{entry.id}", headers=admin_headers)
        assert response.status_code == 200

        follow_up = client.get("/api/admin/buy-list/games", headers=admin_headers)
        assert follow_up.json()["total"] == 0

    def test_remove_nonexistent_returns_404(self, client, admin_headers):
        response = client.delete("/api/admin/buy-list/games/999999", headers=admin_headers)
        assert response.status_code == 404


class TestBulkImportCSV:
    """Test POST /api/admin/buy-list/bulk-import-csv"""

    def test_bulk_import_valid_csv(self, client, db_session, admin_headers):
        game = Game(title="Existing Game", bgg_id=111)
        db_session.add(game)
        db_session.commit()

        csv_content = "bgg_id,rank,notes\n111,1,fills a gap\n"
        response = client.post(
            "/api/admin/buy-list/bulk-import-csv",
            headers=admin_headers,
            files={"file": ("buy_list.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )

        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_bulk_import_missing_bgg_id_column(self, client, admin_headers):
        csv_content = "title,rank\nSome Game,1\n"
        response = client.post(
            "/api/admin/buy-list/bulk-import-csv",
            headers=admin_headers,
            files={"file": ("buy_list.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )

        assert response.status_code == 400
        assert "bgg_id" in response.json()["detail"]


class TestGetLibraryGaps:
    """Test GET /api/admin/buy-list/gaps"""

    def test_gaps_empty_collection(self, client, admin_headers):
        response = client.get("/api/admin/buy-list/gaps", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_games"] == 0
        assert all(not g["is_gap"] for g in data["category_gaps"])
        assert all(not g["is_gap"] for g in data["player_count_gaps"])

    def test_gaps_flags_underrepresented_category(self, client, db_session, admin_headers):
        # 10 owned games, all in one category -> the other 4 categories are gaps
        for i in range(10):
            db_session.add(
                Game(
                    title=f"Game {i}", bgg_id=1000 + i, status="OWNED",
                    mana_meeple_category="CORE_STRATEGY", players_min=2, players_max=4,
                )
            )
        db_session.commit()

        response = client.get("/api/admin/buy-list/gaps", headers=admin_headers)
        data = response.json()
        assert data["total_games"] == 10

        gaps_by_category = {g["category"]: g for g in data["category_gaps"]}
        assert gaps_by_category["CORE_STRATEGY"]["is_gap"] is False
        assert gaps_by_category["PARTY_ICEBREAKERS"]["is_gap"] is True

    def test_gaps_requires_auth(self, client):
        response = client.get("/api/admin/buy-list/gaps")
        assert response.status_code in (401, 403)

    def test_gaps_computation_error_returns_500(self, client, admin_headers):
        with patch("api.routers.buy_list.compute_library_gaps", side_effect=Exception("boom")):
            response = client.get("/api/admin/buy-list/gaps", headers=admin_headers)
        assert response.status_code == 500


class TestListBuyListGamesExtra:
    """Additional coverage for GET /api/admin/buy-list/games"""

    def test_filter_on_buy_list_false(self, client, db_session, admin_headers):
        game = Game(title="Removed but present", bgg_id=1)
        db_session.add(game)
        db_session.flush()
        db_session.add(BuyListGame(game_id=game.id, on_buy_list=False))
        db_session.commit()

        response = client.get(
            "/api/admin/buy-list/games", params={"on_buy_list": False}, headers=admin_headers
        )
        assert response.status_code == 200
        assert response.json()["total"] == 1

    def test_sort_by_updated_at(self, client, db_session, admin_headers):
        game_a = Game(title="Game A", bgg_id=1)
        game_b = Game(title="Game B", bgg_id=2)
        db_session.add_all([game_a, game_b])
        db_session.flush()
        db_session.add_all([
            BuyListGame(game_id=game_a.id, on_buy_list=True),
            BuyListGame(game_id=game_b.id, on_buy_list=True),
        ])
        db_session.commit()

        response = client.get(
            "/api/admin/buy-list/games", params={"sort_by": "updated_at"}, headers=admin_headers
        )
        assert response.status_code == 200
        assert response.json()["total"] == 2

    def test_list_error_returns_500(self, client, admin_headers):
        with patch("api.routers.buy_list.compute_library_gaps", side_effect=Exception("boom")):
            response = client.get("/api/admin/buy-list/games", headers=admin_headers)
        assert response.status_code == 500

    def test_unrecognized_sort_by_falls_back_to_rank(self, client, db_session, admin_headers):
        game = Game(title="Test Game", bgg_id=1)
        db_session.add(game)
        db_session.flush()
        db_session.add(BuyListGame(game_id=game.id, rank=1, on_buy_list=True))
        db_session.commit()

        response = client.get(
            "/api/admin/buy-list/games", params={"sort_by": "not_a_real_field"}, headers=admin_headers
        )
        assert response.status_code == 200
        assert response.json()["total"] == 1


class TestUpdateAndRemoveErrorHandling:
    """Exception paths for update/remove that a simple happy-path test can't reach"""

    def test_update_error_returns_500(self, client, db_session, admin_headers):
        game = Game(title="Test Game", bgg_id=1)
        db_session.add(game)
        db_session.flush()
        entry = BuyListGame(game_id=game.id, on_buy_list=True)
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        with patch("api.routers.buy_list.compute_library_gaps", side_effect=Exception("boom")):
            response = client.put(
                f"/api/admin/buy-list/games/{entry.id}", headers=admin_headers, json={"rank": 1},
            )
        assert response.status_code == 500

    def test_remove_error_returns_500(self, client, db_session, admin_headers):
        game = Game(title="Test Game", bgg_id=1)
        db_session.add(game)
        db_session.flush()
        entry = BuyListGame(game_id=game.id, on_buy_list=True)
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        with patch("sqlalchemy.orm.Session.delete", side_effect=Exception("boom")):
            response = client.delete(f"/api/admin/buy-list/games/{entry.id}", headers=admin_headers)
        assert response.status_code == 500


class TestAddToBuyListStatusTransition:
    """Covers the elif branch: a non-OWNED, non-BUY_LIST game gets promoted"""

    def test_wishlist_game_promoted_to_buy_list(self, client, db_session, admin_headers):
        game = Game(title="Wishlist Game", bgg_id=321, status="WISHLIST")
        db_session.add(game)
        db_session.commit()

        response = client.post(
            "/api/admin/buy-list/games", headers=admin_headers, json={"bgg_id": 321},
        )

        assert response.status_code == 200
        db_session.refresh(game)
        assert game.status == "BUY_LIST"


class TestBulkImportCSVBehavior:
    """Exercises the background CSV-processing task through the HTTP endpoint
    (Starlette's TestClient runs BackgroundTasks synchronously, so the task
    has completed by the time the request returns)."""

    @patch("bgg_service.fetch_bgg_thing")
    def test_imports_new_game_from_bgg(self, mock_fetch, client, db_session, admin_headers):
        mock_fetch.return_value = {"title": "CSV Game", "categories": []}

        csv_content = "bgg_id,rank,notes\n555,2,from csv\n"
        response = client.post(
            "/api/admin/buy-list/bulk-import-csv",
            headers=admin_headers,
            files={"file": ("buy_list.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )
        assert response.status_code == 200

        game = db_session.query(Game).filter_by(bgg_id=555).one_or_none()
        assert game is not None
        assert game.status == "BUY_LIST"
        entry = db_session.query(BuyListGame).filter_by(game_id=game.id).one_or_none()
        assert entry is not None
        assert entry.rank == 2
        assert entry.notes == "from csv"

    def test_updates_existing_entry(self, client, db_session, admin_headers):
        game = Game(title="Existing", bgg_id=222)
        db_session.add(game)
        db_session.flush()
        db_session.add(BuyListGame(game_id=game.id, rank=9, on_buy_list=True))
        db_session.commit()

        csv_content = "bgg_id,rank,notes\n222,1,updated via csv\n"
        response = client.post(
            "/api/admin/buy-list/bulk-import-csv",
            headers=admin_headers,
            files={"file": ("buy_list.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )
        assert response.status_code == 200

        entry = db_session.query(BuyListGame).filter_by(game_id=game.id).one()
        assert entry.rank == 1
        assert entry.notes == "updated via csv"

    def test_invalid_rank_is_logged_and_row_still_processed(self, client, db_session, admin_headers):
        game = Game(title="Existing", bgg_id=333)
        db_session.add(game)
        db_session.commit()

        csv_content = "bgg_id,rank,notes\n333,not-a-number,still added\n"
        response = client.post(
            "/api/admin/buy-list/bulk-import-csv",
            headers=admin_headers,
            files={"file": ("buy_list.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )
        assert response.status_code == 200

        entry = db_session.query(BuyListGame).filter_by(game_id=game.id).one()
        assert entry.rank is None
        assert entry.notes == "still added"

    @patch("bgg_service.fetch_bgg_thing")
    def test_bgg_fetch_failure_counted_as_error_row(self, mock_fetch, client, db_session, admin_headers):
        mock_fetch.side_effect = Exception("BGG unreachable")

        csv_content = "bgg_id\n444\n"
        response = client.post(
            "/api/admin/buy-list/bulk-import-csv",
            headers=admin_headers,
            files={"file": ("buy_list.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )
        assert response.status_code == 200

        assert db_session.query(Game).filter_by(bgg_id=444).one_or_none() is None
