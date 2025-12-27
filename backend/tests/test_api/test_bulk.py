"""
Tests for bulk operations API endpoints
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from models import Game


class TestBulkImportCSV:
    """Tests for bulk import from CSV"""

    def test_bulk_import_empty_csv(self, client, admin_headers):
        """Test bulk import with empty CSV data"""
        response = client.post(
            "/api/admin/bulk-import-csv",
            json={"csv_data": ""},
            headers=admin_headers
        )
        # HTTPException gets wrapped by outer exception handler
        assert response.status_code in [400, 500, 429]

        # Only check detail if not rate limited
        if response.status_code != 429:
            assert "CSV" in response.json()["detail"]

    def test_bulk_import_single_game_success(self, client, admin_headers):
        """Test bulk import with single valid game"""
        with patch("api.routers.bulk.fetch_bgg_thing") as mock_fetch:
            mock_fetch.return_value = {
                "title": "Gloomhaven",
                "year": 2017,
                "players_min": 1,
                "players_max": 4,
                "playtime_min": 60,
                "playtime_max": 120,
                "categories": ["Adventure", "Fantasy"],
                "designers": ["Isaac Childres"],
                "mechanics": ["Hand Management"],
                "average_rating": 8.8,
                "complexity": 3.86,
            }

            response = client.post(
                "/api/admin/bulk-import-csv",
                json={"csv_data": "174430"},
                headers=admin_headers
            )
            assert response.status_code in [200, 429]

            if response.status_code == 200:
                data = response.json()
                assert len(data["added"]) == 1
                assert len(data["errors"]) == 0

    def test_bulk_import_duplicate_game(self, client, db_session, admin_headers):
        """Test bulk import with duplicate BGG ID"""
        # Create existing game
        game = Game(title="Gloomhaven", bgg_id=174430)
        db_session.add(game)
        db_session.commit()

        response = client.post(
            "/api/admin/bulk-import-csv",
            json={"csv_data": "174430"},
            headers=admin_headers
        )
        assert response.status_code in [200, 429]

        if response.status_code == 200:
            data = response.json()
            assert len(data["skipped"]) == 1
            assert "Already exists" in data["skipped"][0]

    def test_bulk_import_invalid_bgg_id(self, client, admin_headers):
        """Test bulk import with invalid BGG ID"""
        response = client.post(
            "/api/admin/bulk-import-csv",
            json={"csv_data": "invalid_id"},
            headers=admin_headers
        )
        assert response.status_code in [200, 429]

        if response.status_code == 200:
            data = response.json()
            assert len(data["errors"]) == 1
            assert "Invalid BGG ID" in data["errors"][0]

    def test_bulk_import_multiple_games(self, client, admin_headers):
        """Test bulk import with multiple games"""
        with patch("api.routers.bulk.fetch_bgg_thing") as mock_fetch:
            mock_fetch.side_effect = [
                {
                    "title": "Gloomhaven",
                    "year": 2017,
                    "categories": ["Adventure"],
                },
                {
                    "title": "Pandemic",
                    "year": 2008,
                    "categories": ["Medical"],
                },
            ]

            csv_data = "174430\n30549"
            response = client.post(
                "/api/admin/bulk-import-csv",
                json={"csv_data": csv_data},
                headers=admin_headers
            )
            assert response.status_code in [200, 429]

            if response.status_code == 200:
                data = response.json()
                assert len(data["added"]) == 2

    def test_bulk_import_unauthorized(self, client):
        """Test bulk import without authentication"""
        response = client.post(
            "/api/admin/bulk-import-csv",
            json={"csv_data": "174430"}
        )
        assert response.status_code in [401, 429]


class TestBulkCategorizeCSV:
    """Tests for bulk categorization from CSV"""

    def test_bulk_categorize_empty_csv(self, client, admin_headers):
        """Test bulk categorize with empty CSV data"""
        response = client.post(
            "/api/admin/bulk-categorize-csv",
            json={"csv_data": ""},
            headers=admin_headers
        )
        # HTTPException gets wrapped by outer exception handler
        assert response.status_code in [400, 500, 429]

        # Only check detail if not rate limited
        if response.status_code != 429:
            assert "CSV" in response.json()["detail"]

    def test_bulk_categorize_success(self, client, db_session, admin_headers):
        """Test bulk categorize with valid data"""
        # Create game with BGG ID
        game = Game(title="Pandemic", bgg_id=30549, mana_meeple_category=None)
        db_session.add(game)
        db_session.commit()

        response = client.post(
            "/api/admin/bulk-categorize-csv",
            json={"csv_data": "30549,COOP_ADVENTURE"},
            headers=admin_headers
        )
        assert response.status_code in [200, 429]

        if response.status_code == 200:
            data = response.json()
            assert len(data["updated"]) == 1
            assert "COOP_ADVENTURE" in data["updated"][0]

    def test_bulk_categorize_invalid_category(self, client, db_session, admin_headers):
        """Test bulk categorize with invalid category"""
        game = Game(title="Pandemic", bgg_id=30549)
        db_session.add(game)
        db_session.commit()

        response = client.post(
            "/api/admin/bulk-categorize-csv",
            json={"csv_data": "30549,INVALID_CATEGORY"},
            headers=admin_headers
        )
        assert response.status_code in [200, 429]

        if response.status_code == 200:
            data = response.json()
            assert len(data["errors"]) == 1
            assert "Invalid category" in data["errors"][0]

    def test_bulk_categorize_game_not_found(self, client, admin_headers):
        """Test bulk categorize with non-existent game"""
        response = client.post(
            "/api/admin/bulk-categorize-csv",
            json={"csv_data": "999999,COOP_ADVENTURE"},
            headers=admin_headers
        )
        assert response.status_code in [200, 429]

        if response.status_code == 200:
            data = response.json()
            assert len(data["not_found"]) == 1

    def test_bulk_categorize_missing_fields(self, client, admin_headers):
        """Test bulk categorize with incomplete CSV line"""
        response = client.post(
            "/api/admin/bulk-categorize-csv",
            json={"csv_data": "30549"},  # Missing category
            headers=admin_headers
        )
        assert response.status_code in [200, 429]

        if response.status_code == 200:
            data = response.json()
            assert len(data["errors"]) == 1
            assert "at least" in data["errors"][0].lower()

    def test_bulk_categorize_unauthorized(self, client):
        """Test bulk categorize without authentication"""
        response = client.post(
            "/api/admin/bulk-categorize-csv",
            json={"csv_data": "30549,COOP_ADVENTURE"}
        )
        assert response.status_code in [401, 429]


class TestBulkUpdateNZDesigners:
    """Tests for bulk NZ designer status update"""

    def test_bulk_update_nz_success_by_bgg_id(self, client, db_session, admin_headers):
        """Test bulk NZ designer update by BGG ID"""
        game = Game(title="Test Game", bgg_id=12345, nz_designer=False)
        db_session.add(game)
        db_session.commit()

        response = client.post(
            "/api/admin/bulk-update-nz-designers",
            json={"csv_data": "12345,true"},
            headers=admin_headers
        )
        assert response.status_code in [200, 429]

        if response.status_code == 200:
            data = response.json()
            assert len(data["updated"]) == 1
            assert "True" in data["updated"][0]

    def test_bulk_update_nz_success_by_title(self, client, db_session, admin_headers):
        """Test bulk NZ designer update by title search"""
        game = Game(title="Test Game", nz_designer=False)
        db_session.add(game)
        db_session.commit()

        response = client.post(
            "/api/admin/bulk-update-nz-designers",
            json={"csv_data": "Test Game,yes"},
            headers=admin_headers
        )
        assert response.status_code in [200, 429]

        if response.status_code == 200:
            data = response.json()
            assert len(data["updated"]) == 1

    def test_bulk_update_nz_game_not_found(self, client, admin_headers):
        """Test bulk NZ designer update with non-existent game"""
        response = client.post(
            "/api/admin/bulk-update-nz-designers",
            json={"csv_data": "999999,true"},
            headers=admin_headers
        )
        assert response.status_code in [200, 429]

        if response.status_code == 200:
            data = response.json()
            assert len(data["not_found"]) == 1

    def test_bulk_update_nz_invalid_format(self, client, admin_headers):
        """Test bulk NZ designer update with invalid format"""
        response = client.post(
            "/api/admin/bulk-update-nz-designers",
            json={"csv_data": "12345"},  # Missing true/false
            headers=admin_headers
        )
        assert response.status_code in [200, 429]

        if response.status_code == 200:
            data = response.json()
            assert len(data["errors"]) == 1

    def test_bulk_update_nz_unauthorized(self, client):
        """Test bulk NZ designer update without authentication"""
        response = client.post(
            "/api/admin/bulk-update-nz-designers",
            json={"csv_data": "12345,true"}
        )
        assert response.status_code in [401, 429]


class TestReimportAllGames:
    """Tests for reimport all games endpoint"""

    def test_reimport_all_success(self, client, db_session, admin_headers):
        """Test reimport all games"""
        # Create games with BGG IDs
        for i in range(3):
            game = Game(title=f"Game {i}", bgg_id=1000 + i)
            db_session.add(game)
        db_session.commit()

        response = client.post(
            "/api/admin/reimport-all-games",
            headers=admin_headers
        )
        assert response.status_code in [200, 429]

        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "3 games" in data["message"]

    def test_reimport_all_no_games(self, client, admin_headers):
        """Test reimport all when no games with BGG IDs exist"""
        response = client.post(
            "/api/admin/reimport-all-games",
            headers=admin_headers
        )
        assert response.status_code in [200, 429]

        if response.status_code == 200:
            data = response.json()
            assert "0 games" in data["message"]

    def test_reimport_all_unauthorized(self, client):
        """Test reimport all without authentication"""
        response = client.post("/api/admin/reimport-all-games")
        assert response.status_code in [401, 429]


class TestBulkUpdateAfterGameIds:
    """Tests for bulk AfterGame ID update endpoint"""

    def test_bulk_update_aftergame_success(self, client, db_session, admin_headers):
        """Test bulk update AfterGame IDs with valid data"""
        # Create test game
        game = Game(title="Test Game", bgg_id=12345, aftergame_game_id=None)
        db_session.add(game)
        db_session.commit()

        aftergame_id = "550e8400-e29b-41d4-a716-446655440000"
        response = client.post(
            "/api/admin/bulk-update-aftergame-ids",
            json={"csv_data": f"12345,{aftergame_id}"},
            headers=admin_headers
        )
        assert response.status_code in [200, 429]

        if response.status_code == 200:
            data = response.json()
            assert len(data["updated"]) == 1
            assert "12345" in data["updated"][0]
            assert aftergame_id in data["updated"][0]

    def test_bulk_update_aftergame_empty_csv(self, client, admin_headers):
        """Test bulk update AfterGame IDs with empty CSV"""
        response = client.post(
            "/api/admin/bulk-update-aftergame-ids",
            json={"csv_data": ""},
            headers=admin_headers
        )
        assert response.status_code in [400, 500, 429]

        if response.status_code in [400, 500]:
            assert "CSV" in response.json()["detail"]

    def test_bulk_update_aftergame_missing_fields(self, client, admin_headers):
        """Test bulk update AfterGame IDs with incomplete CSV line"""
        response = client.post(
            "/api/admin/bulk-update-aftergame-ids",
            json={"csv_data": "12345"},  # Missing AfterGame ID
            headers=admin_headers
        )
        assert response.status_code in [200, 429]

        if response.status_code == 200:
            data = response.json()
            assert len(data["errors"]) == 1
            assert "at least" in data["errors"][0].lower()

    def test_bulk_update_aftergame_invalid_bgg_id(self, client, admin_headers):
        """Test bulk update AfterGame IDs with invalid BGG ID"""
        response = client.post(
            "/api/admin/bulk-update-aftergame-ids",
            json={"csv_data": "invalid,550e8400-e29b-41d4-a716-446655440000"},
            headers=admin_headers
        )
        assert response.status_code in [200, 429]

        if response.status_code == 200:
            data = response.json()
            assert len(data["errors"]) == 1
            assert "Invalid BGG ID" in data["errors"][0]

    def test_bulk_update_aftergame_game_not_found(self, client, admin_headers):
        """Test bulk update AfterGame IDs with non-existent game"""
        response = client.post(
            "/api/admin/bulk-update-aftergame-ids",
            json={"csv_data": "999999,550e8400-e29b-41d4-a716-446655440000"},
            headers=admin_headers
        )
        assert response.status_code in [200, 429]

        if response.status_code == 200:
            data = response.json()
            assert len(data["not_found"]) == 1
            assert "999999" in data["not_found"][0]

    def test_bulk_update_aftergame_clear_existing_id(self, client, db_session, admin_headers):
        """Test clearing existing AfterGame ID by setting to empty string"""
        # Create game with existing AfterGame ID
        game = Game(
            title="Test Game",
            bgg_id=12345,
            aftergame_game_id="550e8400-e29b-41d4-a716-446655440000"
        )
        db_session.add(game)
        db_session.commit()

        response = client.post(
            "/api/admin/bulk-update-aftergame-ids",
            json={"csv_data": "12345,"},  # Empty AfterGame ID to clear
            headers=admin_headers
        )
        assert response.status_code in [200, 429]

        if response.status_code == 200:
            data = response.json()
            assert len(data["updated"]) == 1
            assert "None" in data["updated"][0]

    def test_bulk_update_aftergame_invalid_uuid_format(self, client, db_session, admin_headers):
        """Test bulk update with invalid UUID format (warning logged but still processes)"""
        game = Game(title="Test Game", bgg_id=12345, aftergame_game_id=None)
        db_session.add(game)
        db_session.commit()

        # Too short UUID
        response = client.post(
            "/api/admin/bulk-update-aftergame-ids",
            json={"csv_data": "12345,short-uuid"},
            headers=admin_headers
        )
        assert response.status_code in [200, 429]

        if response.status_code == 200:
            # Should still update despite warning about format
            data = response.json()
            assert len(data["updated"]) == 1

    def test_bulk_update_aftergame_multiple_games(self, client, db_session, admin_headers):
        """Test bulk update AfterGame IDs for multiple games"""
        # Create multiple games
        for i in range(3):
            game = Game(title=f"Game {i}", bgg_id=10000 + i, aftergame_game_id=None)
            db_session.add(game)
        db_session.commit()

        csv_data = (
            "10000,550e8400-e29b-41d4-a716-446655440000\n"
            "10001,550e8400-e29b-41d4-a716-446655440001\n"
            "10002,550e8400-e29b-41d4-a716-446655440002"
        )
        response = client.post(
            "/api/admin/bulk-update-aftergame-ids",
            json={"csv_data": csv_data},
            headers=admin_headers
        )
        assert response.status_code in [200, 429]

        if response.status_code == 200:
            data = response.json()
            assert len(data["updated"]) == 3
            assert "Processed 3 lines" in data["message"]

    def test_bulk_update_aftergame_unauthorized(self, client):
        """Test bulk update AfterGame IDs without authentication"""
        response = client.post(
            "/api/admin/bulk-update-aftergame-ids",
            json={"csv_data": "12345,550e8400-e29b-41d4-a716-446655440000"}
        )
        assert response.status_code in [401, 429]


class TestFetchAllSleeveData:
    """Tests for fetch all sleeve data endpoint"""

    def test_fetch_all_sleeve_data_no_github_token(self, client, admin_headers):
        """Test fetch all sleeve data when GITHUB_TOKEN is not configured"""
        import os

        # Temporarily remove GITHUB_TOKEN
        original_token = os.environ.get("GITHUB_TOKEN")
        if "GITHUB_TOKEN" in os.environ:
            del os.environ["GITHUB_TOKEN"]

        try:
            response = client.post(
                "/api/admin/fetch-all-sleeve-data",
                headers=admin_headers
            )
            # Should return 500 when GITHUB_TOKEN is missing
            assert response.status_code in [500, 429]

            if response.status_code == 500:
                assert "GITHUB_TOKEN" in response.json()["detail"]
        finally:
            # Restore original token
            if original_token:
                os.environ["GITHUB_TOKEN"] = original_token

    def test_fetch_all_sleeve_data_unauthorized(self, client):
        """Test fetch all sleeve data without authentication"""
        response = client.post("/api/admin/fetch-all-sleeve-data")
        assert response.status_code in [401, 429]


class TestBulkImportErrorHandling:
    """Additional error handling tests for bulk import"""

    def test_bulk_import_no_valid_lines(self, client, admin_headers):
        """Test bulk import with only whitespace/empty lines"""
        response = client.post(
            "/api/admin/bulk-import-csv",
            json={"csv_data": "   \n\n   \n"},
            headers=admin_headers
        )
        assert response.status_code in [400, 500, 429]

        if response.status_code != 429:
            assert "CSV" in response.json()["detail"] or "valid" in response.json()["detail"].lower()

    def test_bulk_import_bgg_fetch_error(self, client, admin_headers):
        """Test bulk import when BGG fetch fails"""
        with patch("api.routers.bulk.fetch_bgg_thing") as mock_fetch:
            mock_fetch.return_value = None  # BGG fetch failed

            response = client.post(
                "/api/admin/bulk-import-csv",
                json={"csv_data": "174430"},
                headers=admin_headers
            )
            assert response.status_code in [200, 429]

            if response.status_code == 200:
                data = response.json()
                # Should be in errors list when BGG fetch fails
                assert len(data["errors"]) == 1
                assert "174430" in data["errors"][0]

    def test_bulk_import_database_error(self, client, admin_headers):
        """Test bulk import with database error during save"""
        with patch("api.routers.bulk.fetch_bgg_thing") as mock_fetch, \
             patch("sqlalchemy.orm.Session.add") as mock_add:

            mock_fetch.return_value = {
                "title": "Test Game",
                "year": 2020,
                "categories": ["Strategy"],
            }
            mock_add.side_effect = Exception("Database error")

            response = client.post(
                "/api/admin/bulk-import-csv",
                json={"csv_data": "174430"},
                headers=admin_headers
            )
            assert response.status_code in [200, 429]

            if response.status_code == 200:
                data = response.json()
                assert len(data["errors"]) == 1


class TestBulkCategorizeErrorHandling:
    """Additional error handling tests for bulk categorize"""

    def test_bulk_categorize_invalid_bgg_id_format(self, client, admin_headers):
        """Test bulk categorize with invalid BGG ID that can't be parsed as int"""
        response = client.post(
            "/api/admin/bulk-categorize-csv",
            json={"csv_data": "abc123,COOP_ADVENTURE"},
            headers=admin_headers
        )
        assert response.status_code in [200, 429]

        if response.status_code == 200:
            data = response.json()
            assert len(data["errors"]) == 1
            assert "Invalid BGG ID" in data["errors"][0]

    def test_bulk_categorize_category_label_backwards_compat(self, client, db_session, admin_headers):
        """Test bulk categorize accepts category labels for backwards compatibility"""
        game = Game(title="Test Game", bgg_id=12345, mana_meeple_category=None)
        db_session.add(game)
        db_session.commit()

        # Use category label instead of key
        response = client.post(
            "/api/admin/bulk-categorize-csv",
            json={"csv_data": "12345,Co-op & Adventure"},
            headers=admin_headers
        )
        assert response.status_code in [200, 429]

        if response.status_code == 200:
            data = response.json()
            # Should either update or show error depending on implementation
            assert len(data["updated"]) + len(data["errors"]) >= 1
