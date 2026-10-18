"""
Tests for the 'games to add' API endpoints (backend/api/routers/buy_list.py).

Covers listing/sorting, adding (existing game and BGG auto-import),
updating, removing, bulk CSV import, the library-gaps endpoint,
gap-match annotation on list/add/update responses, and the HL Timaru
stock-signal sync/link/dismiss endpoints.
"""

import io
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch

from sqlalchemy import select

from api.routers.buy_list import build_buy_list_response
from models import BuyListGame, Game, HLStockLink
from services.hl_stock_service import HLStockServiceError


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
            "complexity_gaps": [],
            "playtime_gaps": [],
        }

        result = build_buy_list_response(buy_list, gaps)

        assert result["gap_match"]["category_is_gap"] is True
        assert result["gap_match"]["matching_player_count_gaps"] == ["9+"]
        assert result["gap_match"]["complexity_is_gap"] is False
        assert result["gap_match"]["playtime_is_gap"] is False


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

    def test_list_includes_distro_availability(self, client, db_session, admin_headers):
        game = Game(id=1, title="Azul", bgg_id=1)
        db_session.add(game)
        db_session.flush()
        db_session.add(BuyListGame(game_id=game.id, on_buy_list=True))
        db_session.commit()

        availability = {"Azul": {"status": "in_stock", "options": [{"distributor": "VR"}]}}
        with patch("api.routers.buy_list.availability_for_titles", return_value=availability):
            items = client.get("/api/admin/buy-list/games", headers=admin_headers).json()["items"]
        assert items[0]["distro_availability"]["status"] == "in_stock"

        with patch("api.routers.buy_list.availability_for_titles", return_value=None):
            items = client.get("/api/admin/buy-list/games", headers=admin_headers).json()["items"]
        assert items[0]["distro_availability"] is None

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


class TestListBuyListGamesGapsFilledSort:
    """Test GET /api/admin/buy-list/games?sort_by=gaps_filled"""

    def test_sort_by_gaps_filled_puts_most_gap_filling_first(self, client, db_session, admin_headers):
        # 10 owned games, all CORE_STRATEGY, all supporting 2-4 players ->
        # every other category is a gap, and most player-count buckets are too.
        for i in range(10):
            db_session.add(
                Game(
                    title=f"Owned {i}", bgg_id=2000 + i, status="OWNED",
                    mana_meeple_category="CORE_STRATEGY", players_min=2, players_max=4,
                )
            )
        db_session.flush()

        no_gap_game = Game(
            title="No Gap Game", bgg_id=1,
            mana_meeple_category="CORE_STRATEGY", players_min=2, players_max=4,
        )
        category_gap_game = Game(
            title="Category Gap Game", bgg_id=2,
            mana_meeple_category="PARTY_ICEBREAKERS", players_min=2, players_max=4,
        )
        double_gap_game = Game(
            title="Double Gap Game", bgg_id=3,
            mana_meeple_category="KIDS_FAMILIES", players_min=6, players_max=10,
        )
        db_session.add_all([no_gap_game, category_gap_game, double_gap_game])
        db_session.flush()
        db_session.add_all([
            BuyListGame(game_id=no_gap_game.id, on_buy_list=True),
            BuyListGame(game_id=category_gap_game.id, on_buy_list=True),
            BuyListGame(game_id=double_gap_game.id, on_buy_list=True),
        ])
        db_session.commit()

        response = client.get(
            "/api/admin/buy-list/games",
            params={"sort_by": "gaps_filled", "sort_desc": "true"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        titles = [item["title"] for item in response.json()["items"]]
        assert titles[0] == "Double Gap Game"
        assert titles[-1] == "No Gap Game"

        # Ascending flips it
        response_asc = client.get(
            "/api/admin/buy-list/games",
            params={"sort_by": "gaps_filled", "sort_desc": "false"},
            headers=admin_headers,
        )
        titles_asc = [item["title"] for item in response_asc.json()["items"]]
        assert titles_asc[0] == "No Gap Game"
        assert titles_asc[-1] == "Double Gap Game"

    def test_complexity_and_playtime_gaps_count_too(self, client, db_session, admin_headers):
        # 10 owned games, all heavy and epic-length -> light complexity and
        # quick playtime are both flagged as gaps.
        for i in range(10):
            db_session.add(
                Game(
                    title=f"Owned {i}", bgg_id=3000 + i, status="OWNED",
                    complexity=4.0, playtime_min=180, playtime_max=180,
                )
            )
        db_session.flush()

        matches_both = Game(title="Light Quick Game", bgg_id=1, complexity=1.0, playtime_min=15, playtime_max=15)
        matches_neither = Game(title="Heavy Epic Game", bgg_id=2, complexity=4.5, playtime_min=200, playtime_max=200)
        db_session.add_all([matches_both, matches_neither])
        db_session.flush()
        db_session.add_all([
            BuyListGame(game_id=matches_both.id, on_buy_list=True),
            BuyListGame(game_id=matches_neither.id, on_buy_list=True),
        ])
        db_session.commit()

        response = client.get(
            "/api/admin/buy-list/games",
            params={"sort_by": "gaps_filled", "sort_desc": "true"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        items = {item["title"]: item for item in response.json()["items"]}
        assert items["Light Quick Game"]["gap_match"]["complexity_is_gap"] is True
        assert items["Light Quick Game"]["gap_match"]["playtime_is_gap"] is True
        assert items["Heavy Epic Game"]["gap_match"]["complexity_is_gap"] is False
        assert items["Heavy Epic Game"]["gap_match"]["playtime_is_gap"] is False

        titles = [item["title"] for item in response.json()["items"]]
        assert titles[0] == "Light Quick Game"


class TestReorderBuyList:
    """Test PUT /api/admin/buy-list/reorder"""

    def test_reorder_sets_sequential_ranks(self, client, db_session, admin_headers):
        g1, g2, g3 = Game(title="First", bgg_id=1), Game(title="Second", bgg_id=2), Game(title="Third", bgg_id=3)
        db_session.add_all([g1, g2, g3])
        db_session.flush()
        b1 = BuyListGame(game_id=g1.id, rank=10, on_buy_list=True)
        b2 = BuyListGame(game_id=g2.id, rank=20, on_buy_list=True)
        b3 = BuyListGame(game_id=g3.id, rank=30, on_buy_list=True)
        db_session.add_all([b1, b2, b3])
        db_session.commit()
        for entry in (b1, b2, b3):
            db_session.refresh(entry)

        response = client.put(
            "/api/admin/buy-list/reorder",
            headers=admin_headers,
            json={"ordered_ids": [b3.id, b1.id, b2.id]},
        )
        assert response.status_code == 200
        ranks_by_title = {item["title"]: item["rank"] for item in response.json()["items"]}
        assert ranks_by_title["Third"] == 1
        assert ranks_by_title["First"] == 2
        assert ranks_by_title["Second"] == 3

    def test_reorder_unknown_id_returns_404(self, client, db_session, admin_headers):
        game = Game(title="Solo", bgg_id=1)
        db_session.add(game)
        db_session.flush()
        entry = BuyListGame(game_id=game.id, rank=1, on_buy_list=True)
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        response = client.put(
            "/api/admin/buy-list/reorder",
            headers=admin_headers,
            json={"ordered_ids": [entry.id, 999999]},
        )
        assert response.status_code == 404

    def test_reorder_empty_list_rejected(self, client, admin_headers):
        response = client.put(
            "/api/admin/buy-list/reorder", headers=admin_headers, json={"ordered_ids": []}
        )
        assert response.status_code == 422

    def test_reorder_requires_auth(self, client):
        response = client.put("/api/admin/buy-list/reorder", json={"ordered_ids": [1]})
        assert response.status_code in (401, 403)

    def test_reorder_error_returns_500(self, client, db_session, admin_headers):
        game = Game(title="Solo", bgg_id=1)
        db_session.add(game)
        db_session.flush()
        entry = BuyListGame(game_id=game.id, rank=1, on_buy_list=True)
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        with patch("api.routers.buy_list.compute_library_gaps", side_effect=Exception("boom")):
            response = client.put(
                "/api/admin/buy-list/reorder",
                headers=admin_headers,
                json={"ordered_ids": [entry.id]},
            )
        assert response.status_code == 500


class TestSuggestGames:
    """Test POST /api/admin/buy-list/suggest"""

    def test_suggest_returns_suggestions(self, client, admin_headers):
        fake_suggestions = [
            {
                "title": "Wingspan", "year": 2019, "category_key": "GATEWAY_STRATEGY",
                "reason": "Fits the gap.", "suggested_bgg_id": 266192,
                "suggested_bgg_title": "Wingspan", "suggested_bgg_year": 2019,
                "bgg_search_url": "https://boardgamegeek.com/geeksearch.php?action=search&objecttype=boardgame&q=Wingspan",
            }
        ]
        with patch(
            "api.routers.buy_list.generate_suggestions", new_callable=AsyncMock, return_value=fake_suggestions
        ):
            response = client.post("/api/admin/buy-list/suggest", headers=admin_headers, json={"count": 1})
        assert response.status_code == 200
        assert response.json()["suggestions"] == fake_suggestions

    def test_suggest_default_count(self, client, admin_headers):
        with patch(
            "api.routers.buy_list.generate_suggestions", new_callable=AsyncMock, return_value=[]
        ) as mock_gen:
            response = client.post("/api/admin/buy-list/suggest", headers=admin_headers, json={})
        assert response.status_code == 200
        mock_gen.assert_awaited_once()
        assert mock_gen.call_args.kwargs["count"] == 6

    def test_suggest_unavailable_returns_503(self, client, admin_headers):
        from services.game_suggestion_service import SuggestionServiceError

        with patch(
            "api.routers.buy_list.generate_suggestions",
            new_callable=AsyncMock,
            side_effect=SuggestionServiceError("ANTHROPIC_API_KEY is not configured"),
        ):
            response = client.post("/api/admin/buy-list/suggest", headers=admin_headers, json={"count": 3})
        assert response.status_code == 503

    def test_suggest_unexpected_error_returns_500(self, client, admin_headers):
        with patch(
            "api.routers.buy_list.generate_suggestions",
            new_callable=AsyncMock,
            side_effect=RuntimeError("boom"),
        ):
            response = client.post("/api/admin/buy-list/suggest", headers=admin_headers, json={"count": 3})
        assert response.status_code == 500

    def test_suggest_requires_auth(self, client):
        response = client.post("/api/admin/buy-list/suggest", json={"count": 3})
        assert response.status_code in (401, 403)

    def test_suggest_count_out_of_range_rejected(self, client, admin_headers):
        response = client.post("/api/admin/buy-list/suggest", headers=admin_headers, json={"count": 50})
        assert response.status_code == 422


def _fake_hl_item(internal_id, name, **overrides):
    item = {
        "internal_id": internal_id,
        "name": name,
        "sku": f"SKU-{internal_id}",
        "current_stock": 3,
        "price": 49.99,
        "units_sold": 5,
        "sale_days": 3,
        "last_sale_date": date(2026, 10, 1),
        "approx_revenue": 249.95,
    }
    item.update(overrides)
    return item


class TestListHLStockSignals:
    """Test GET /api/admin/buy-list/hl-signals"""

    def test_requires_auth(self, client):
        response = client.get("/api/admin/buy-list/hl-signals")
        assert response.status_code in (401, 403)

    def test_defaults_to_top_10_by_units_sold(self, client, admin_headers):
        fake_items = [
            _fake_hl_item(600 + i, f"Game {i}", units_sold=100 - i)
            for i in range(15)
        ]
        with patch("api.routers.buy_list.fetch_hl_board_game_signals", return_value=fake_items):
            response = client.get("/api/admin/buy-list/hl-signals", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 10
        assert [item["units_sold"] for item in data["items"]] == list(range(100, 90, -1))

    def test_limit_query_param_is_respected(self, client, admin_headers):
        fake_items = [_fake_hl_item(700 + i, f"Game {i}", units_sold=i) for i in range(5)]
        with patch("api.routers.buy_list.fetch_hl_board_game_signals", return_value=fake_items):
            response = client.get(
                "/api/admin/buy-list/hl-signals", headers=admin_headers, params={"limit": 3}
            )
        assert response.status_code == 200
        assert response.json()["total"] == 3

    def test_unavailable_returns_503(self, client, admin_headers):
        with patch(
            "api.routers.buy_list.fetch_hl_board_game_signals",
            side_effect=HLStockServiceError("HL_STOCK_DATABASE_URL not configured"),
        ):
            response = client.get("/api/admin/buy-list/hl-signals", headers=admin_headers)
        assert response.status_code == 503

    def test_new_unmatched_product_is_returned_and_persisted(self, client, db_session, admin_headers):
        fake_items = [_fake_hl_item(501, "Completely New Game")]
        with patch("api.routers.buy_list.fetch_hl_board_game_signals", return_value=fake_items):
            response = client.get("/api/admin/buy-list/hl-signals", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["hl_internal_id"] == 501
        assert item["match_status"] == "unmatched"
        assert item["linked_game"] is None
        assert item["units_sold"] == 5
        assert item["current_stock"] == 3

        link = db_session.execute(
            select(HLStockLink).where(HLStockLink.hl_internal_id == 501)
        ).scalar_one()
        assert link.game_id is None
        assert link.hl_product_name == "Completely New Game"

    def test_fuzzy_matches_existing_unowned_game(self, client, db_session, admin_headers):
        game = Game(title="Wingspan: European Expansion", status="WISHLIST")
        db_session.add(game)
        db_session.commit()

        fake_items = [_fake_hl_item(502, "Wingspan European Expansion")]
        with patch("api.routers.buy_list.fetch_hl_board_game_signals", return_value=fake_items):
            response = client.get("/api/admin/buy-list/hl-signals", headers=admin_headers)
        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["match_status"] == "linked"
        assert item["linked_game"]["title"] == "Wingspan: European Expansion"
        assert item["match_confidence"] is not None

    def test_excludes_already_owned_game(self, client, db_session, admin_headers):
        game = Game(title="Catan", status="OWNED")
        db_session.add(game)
        db_session.flush()
        db_session.add(HLStockLink(
            hl_internal_id=503, game_id=game.id, hl_product_name="Catan",
            last_synced_at=datetime.now(timezone.utc),
        ))
        db_session.commit()

        fake_items = [_fake_hl_item(503, "Catan")]
        with patch("api.routers.buy_list.fetch_hl_board_game_signals", return_value=fake_items):
            response = client.get("/api/admin/buy-list/hl-signals", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_excludes_game_already_on_buy_list(self, client, db_session, admin_headers):
        game = Game(title="Root", status="BUY_LIST")
        db_session.add(game)
        db_session.flush()
        db_session.add(BuyListGame(game_id=game.id, on_buy_list=True))
        db_session.add(HLStockLink(
            hl_internal_id=504, game_id=game.id, hl_product_name="Root",
            last_synced_at=datetime.now(timezone.utc),
        ))
        db_session.commit()

        fake_items = [_fake_hl_item(504, "Root")]
        with patch("api.routers.buy_list.fetch_hl_board_game_signals", return_value=fake_items):
            response = client.get("/api/admin/buy-list/hl-signals", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_excludes_dismissed_product(self, client, db_session, admin_headers):
        db_session.add(HLStockLink(
            hl_internal_id=505, dismissed=True, hl_product_name="Junk Item",
            last_synced_at=datetime.now(timezone.utc),
        ))
        db_session.commit()

        fake_items = [_fake_hl_item(505, "Junk Item")]
        with patch("api.routers.buy_list.fetch_hl_board_game_signals", return_value=fake_items):
            response = client.get("/api/admin/buy-list/hl-signals", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_linked_product_is_not_rematched(self, client, db_session, admin_headers):
        """A product already linked to a game keeps that link even if the
        cached product name drifts from the matched title - it's never
        silently re-resolved once confirmed."""
        game = Game(title="Terraforming Mars", status="WISHLIST")
        other_game = Game(title="Completely Different Game", status="WISHLIST")
        db_session.add_all([game, other_game])
        db_session.flush()
        db_session.add(HLStockLink(
            hl_internal_id=506, game_id=game.id, hl_product_name="Terraforming Mars",
            match_confidence=None, last_synced_at=datetime.now(timezone.utc),
        ))
        db_session.commit()

        fake_items = [_fake_hl_item(506, "Completely Different Game")]
        with patch("api.routers.buy_list.fetch_hl_board_game_signals", return_value=fake_items):
            response = client.get("/api/admin/buy-list/hl-signals", headers=admin_headers)
        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["linked_game"]["title"] == "Terraforming Mars"

    def test_sync_error_rolls_back_and_returns_500(self, client, admin_headers):
        fake_items = [_fake_hl_item(507, "Some Game")]
        with patch("api.routers.buy_list.fetch_hl_board_game_signals", return_value=fake_items), \
             patch("api.routers.buy_list.find_best_title_match", side_effect=RuntimeError("boom")):
            response = client.get("/api/admin/buy-list/hl-signals", headers=admin_headers)
        assert response.status_code == 500


class TestLinkHLStockSignal:
    """Test POST /api/admin/buy-list/hl-signals/{id}/link"""

    def test_requires_auth(self, client):
        response = client.post("/api/admin/buy-list/hl-signals/1/link", json={"game_id": 1})
        assert response.status_code in (401, 403)

    def test_signal_not_found_returns_404(self, client, admin_headers):
        response = client.post(
            "/api/admin/buy-list/hl-signals/999/link", headers=admin_headers, json={"game_id": 1}
        )
        assert response.status_code == 404

    def test_game_not_found_returns_404(self, client, db_session, admin_headers):
        db_session.add(HLStockLink(
            hl_internal_id=601, hl_product_name="Mystery Game",
            last_synced_at=datetime.now(timezone.utc),
        ))
        db_session.commit()

        response = client.post(
            "/api/admin/buy-list/hl-signals/601/link", headers=admin_headers, json={"game_id": 999999}
        )
        assert response.status_code == 404

    def test_link_success_clears_confidence_and_dismissed(self, client, db_session, admin_headers):
        game = Game(title="Azul", status="WISHLIST")
        db_session.add(game)
        db_session.flush()
        db_session.add(HLStockLink(
            hl_internal_id=602, hl_product_name="Azul", match_confidence=70.0,
            dismissed=True, last_synced_at=datetime.now(timezone.utc),
        ))
        db_session.commit()

        response = client.post(
            "/api/admin/buy-list/hl-signals/602/link", headers=admin_headers, json={"game_id": game.id}
        )
        assert response.status_code == 200
        assert response.json()["linked_game_id"] == game.id

        link = db_session.execute(
            select(HLStockLink).where(HLStockLink.hl_internal_id == 602)
        ).scalar_one()
        assert link.game_id == game.id
        assert link.match_confidence is None
        assert link.dismissed is False


class TestDismissHLStockSignal:
    """Test POST /api/admin/buy-list/hl-signals/{id}/dismiss"""

    def test_requires_auth(self, client):
        response = client.post("/api/admin/buy-list/hl-signals/1/dismiss")
        assert response.status_code in (401, 403)

    def test_signal_not_found_returns_404(self, client, admin_headers):
        response = client.post("/api/admin/buy-list/hl-signals/999/dismiss", headers=admin_headers)
        assert response.status_code == 404

    def test_dismiss_success(self, client, db_session, admin_headers):
        db_session.add(HLStockLink(
            hl_internal_id=701, hl_product_name="Dice Tower",
            last_synced_at=datetime.now(timezone.utc),
        ))
        db_session.commit()

        response = client.post("/api/admin/buy-list/hl-signals/701/dismiss", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["dismissed"] is True

        link = db_session.execute(
            select(HLStockLink).where(HLStockLink.hl_internal_id == 701)
        ).scalar_one()
        assert link.dismissed is True


class TestGetTrendingGames:
    """Test GET /api/admin/buy-list/trending"""

    def test_returns_trending_with_status_annotations(self, client, db_session, admin_headers):
        owned_game = Game(title="Owned Trending Game", bgg_id=174430, status="OWNED")
        queued_game = Game(title="Queued Trending Game", bgg_id=266192, status="BUY_LIST")
        db_session.add_all([owned_game, queued_game])
        db_session.flush()
        db_session.add(BuyListGame(game_id=queued_game.id, on_buy_list=True))
        db_session.commit()

        hot_list = [
            {"bgg_id": 174430, "rank": 1, "title": "Owned Trending Game", "year": 2017, "thumbnail_url": None},
            {"bgg_id": 266192, "rank": 2, "title": "Queued Trending Game", "year": 2019, "thumbnail_url": None},
            {"bgg_id": 999999, "rank": 3, "title": "New Trending Game", "year": 2024, "thumbnail_url": None},
        ]

        with patch(
            "api.routers.buy_list.get_hot_games", new_callable=AsyncMock, return_value=hot_list
        ):
            response = client.get("/api/admin/buy-list/trending", headers=admin_headers)

        assert response.status_code == 200
        by_bgg_id = {item["bgg_id"]: item for item in response.json()["trending"]}
        assert by_bgg_id[174430]["status"] == "owned"
        assert by_bgg_id[266192]["status"] == "on_buy_list"
        assert by_bgg_id[999999]["status"] == "new"

    def test_empty_hot_list(self, client, admin_headers):
        with patch(
            "api.routers.buy_list.get_hot_games", new_callable=AsyncMock, return_value=[]
        ):
            response = client.get("/api/admin/buy-list/trending", headers=admin_headers)

        assert response.status_code == 200
        assert response.json() == {"trending": []}

    def test_fetch_failure_returns_502(self, client, admin_headers):
        with patch(
            "api.routers.buy_list.get_hot_games",
            new_callable=AsyncMock,
            side_effect=RuntimeError("BGG unreachable"),
        ):
            response = client.get("/api/admin/buy-list/trending", headers=admin_headers)

        assert response.status_code == 502

    def test_respects_limit_query_param(self, client, admin_headers):
        with patch(
            "api.routers.buy_list.get_hot_games", new_callable=AsyncMock, return_value=[]
        ) as mock_hot:
            client.get("/api/admin/buy-list/trending", params={"limit": 10}, headers=admin_headers)

        mock_hot.assert_awaited_once_with(limit=10)

    def test_requires_auth(self, client):
        response = client.get("/api/admin/buy-list/trending")
        assert response.status_code in (401, 403)


class TestGetAwardWinners:
    """Test GET /api/admin/buy-list/award-winners"""

    def test_returns_award_winners(self, client, admin_headers):
        winners = [
            {
                "year": 2024,
                "award": "spiel_des_jahres",
                "award_label": "Spiel des Jahres",
                "title": "Sky Team",
                "bgg_id": 373106,
                "thumbnail_url": None,
                "status": "new",
                "bgg_search_url": "https://boardgamegeek.com/geeksearch.php?action=search&objecttype=boardgame&q=Sky+Team",
            },
        ]
        with patch(
            "api.routers.buy_list.get_award_winners", new_callable=AsyncMock, return_value=winners
        ):
            response = client.get("/api/admin/buy-list/award-winners", headers=admin_headers)

        assert response.status_code == 200
        assert response.json() == {"award_winners": winners}

    def test_fetch_failure_returns_500(self, client, admin_headers):
        with patch(
            "api.routers.buy_list.get_award_winners",
            new_callable=AsyncMock,
            side_effect=RuntimeError("BGG unreachable"),
        ):
            response = client.get("/api/admin/buy-list/award-winners", headers=admin_headers)

        assert response.status_code == 500

    def test_respects_years_query_param(self, client, admin_headers):
        with patch(
            "api.routers.buy_list.get_award_winners", new_callable=AsyncMock, return_value=[]
        ) as mock_winners:
            client.get("/api/admin/buy-list/award-winners", params={"years": 3}, headers=admin_headers)

        mock_winners.assert_awaited_once()
        assert mock_winners.call_args.kwargs.get("years") == 3

    def test_requires_auth(self, client):
        response = client.get("/api/admin/buy-list/award-winners")
        assert response.status_code in (401, 403)


class TestManualDistroLinks:
    ROW = {
        "distributor": "VR",
        "distro_code": "V9",
        "name": "OBSC GME EURO",
        "cost_price_ex_gst": 30.0,
        "qty_available": 4,
        "qty_updated_at": None,
    }

    def _game(self, db_session, title="Obscure Game"):
        game = Game(title=title, bgg_id=999)
        db_session.add(game)
        db_session.commit()
        return game

    def test_search_returns_catalogue_rows(self, client, admin_headers):
        with patch("api.routers.buy_list.search_distro_codes", return_value=[self.ROW]) as mock:
            response = client.get(
                "/api/admin/buy-list/distro-codes/search?q=obsc", headers=admin_headers
            )
        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["distro_code"] == "V9" and item["distro_product_name"] == "OBSC GME EURO"
        mock.assert_called_once_with("obsc", limit=20)

    def test_search_requires_auth_and_min_length(self, client, admin_headers):
        unauthenticated = client.get("/api/admin/buy-list/distro-codes/search?q=ob")
        too_short = client.get("/api/admin/buy-list/distro-codes/search?q=o", headers=admin_headers)
        assert unauthenticated.status_code in (401, 403)
        assert too_short.status_code == 422

    def test_search_503_when_hl_unavailable(self, client, admin_headers):
        with patch("api.routers.buy_list.search_distro_codes", side_effect=HLStockServiceError("nope")):
            response = client.get(
                "/api/admin/buy-list/distro-codes/search?q=obsc", headers=admin_headers
            )
        assert response.status_code == 503

    def test_link_creates_and_list_shows_manual_option(self, client, db_session, admin_headers):
        game = self._game(db_session)
        db_session.add(BuyListGame(game_id=game.id, on_buy_list=True))
        db_session.commit()

        with patch("api.routers.buy_list.fetch_distro_codes_by_key", return_value=[self.ROW]), patch(
            "api.routers.buy_list.availability_for_titles",
            return_value={"Obscure Game": {"status": "not_listed", "options": []}},
        ), patch("services.distro_availability.fetch_distro_codes_by_key", return_value=[self.ROW]):
            created = client.post(
                f"/api/admin/buy-list/games/{game.id}/distro-links",
                json={"distributor": "VR", "distro_code": "V9"},
                headers=admin_headers,
            )
            assert created.status_code == 200
            body = created.json()
            assert body["distro_availability"]["status"] == "in_stock"
            assert body["distro_availability"]["options"][0]["link_id"] == body["link_id"]

            items = client.get("/api/admin/buy-list/games", headers=admin_headers).json()["items"]
            assert items[0]["distro_availability"]["options"][0]["distro_code"] == "V9"

    def test_link_rejects_unknown_code_duplicate_and_missing_game(self, client, db_session, admin_headers):
        game = self._game(db_session)
        url = f"/api/admin/buy-list/games/{game.id}/distro-links"
        payload = {"distributor": "VR", "distro_code": "V9"}

        with patch("api.routers.buy_list.fetch_distro_codes_by_key", return_value=[]):
            unknown_code = client.post(url, json=payload, headers=admin_headers)
        assert unknown_code.status_code == 404

        with patch("api.routers.buy_list.fetch_distro_codes_by_key", return_value=[self.ROW]), patch(
            "api.routers.buy_list.availability_for_titles", return_value=None
        ):
            first = client.post(url, json=payload, headers=admin_headers)
            duplicate = client.post(url, json=payload, headers=admin_headers)
            missing_game = client.post(
                "/api/admin/buy-list/games/99999/distro-links", json=payload, headers=admin_headers
            )
        assert first.status_code == 200
        assert duplicate.status_code == 409
        assert missing_game.status_code == 404

    def test_unlink_removes_link(self, client, db_session, admin_headers):
        from models import GameDistroLink

        game = self._game(db_session)
        link = GameDistroLink(game_id=game.id, distributor="VR", distro_code="V9")
        db_session.add(link)
        db_session.commit()
        link_id = link.id

        with patch("api.routers.buy_list.availability_for_titles", return_value=None):
            response = client.delete(
                f"/api/admin/buy-list/distro-links/{link_id}", headers=admin_headers
            )
            repeat = client.delete(
                f"/api/admin/buy-list/distro-links/{link_id}", headers=admin_headers
            )
        assert response.status_code == 200
        assert repeat.status_code == 404
        db_session.expire_all()
        remaining = db_session.get(GameDistroLink, link_id)
        assert remaining is None
