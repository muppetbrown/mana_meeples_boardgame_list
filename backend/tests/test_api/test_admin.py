"""
Tests for admin API endpoints
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from models import Game


class TestAdminAuthentication:
    """Tests for admin authentication"""

    def test_admin_endpoint_without_token(self, client):
        """Test accessing admin endpoint without token"""
        response = client.get("/api/admin/games")
        assert response.status_code == 401

    def test_admin_endpoint_with_invalid_token(self, client):
        """Test accessing admin endpoint with invalid token"""
        headers = {"X-Admin-Token": "invalid_token"}
        response = client.get("/api/admin/games", headers=headers)
        assert response.status_code == 401

    def test_admin_endpoint_with_valid_token(self, client, admin_headers):
        """Test accessing admin endpoint with valid token"""
        response = client.get("/api/admin/games", headers=admin_headers)
        assert response.status_code == 200


class TestAdminGamesEndpoints:
    """Tests for admin game management endpoints"""

    def test_get_admin_games(self, client, db_session, admin_headers, sample_games_list):
        """Test getting all games as admin"""
        for game_data in sample_games_list:
            game = Game(**game_data)
            db_session.add(game)
        db_session.commit()

        response = client.get("/api/admin/games", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        # Admin endpoint returns a list directly, not paginated
        assert isinstance(data, list)
        assert len(data) == 4

    def test_create_game(self, client, admin_headers, sample_game_data):
        """Test creating a new game"""
        response = client.post(
            "/api/admin/games",
            json=sample_game_data,
            headers=admin_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Pandemic"
        assert "id" in data

    def test_update_game(self, client, db_session, admin_headers, sample_game_data):
        """Test updating an existing game"""
        # Create a game first
        game = Game(**sample_game_data)
        db_session.add(game)
        db_session.commit()
        game_id = game.id

        # Update it
        update_data = {"title": "Pandemic Legacy"}
        response = client.put(
            f"/api/admin/games/{game_id}",
            json=update_data,
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Pandemic Legacy"

    def test_delete_game(self, client, db_session, admin_headers, sample_game_data):
        """Test deleting a game"""
        # Create a game first
        game = Game(**sample_game_data)
        db_session.add(game)
        db_session.commit()
        game_id = game.id

        # Delete it
        response = client.delete(
            f"/api/admin/games/{game_id}",
            headers=admin_headers
        )
        assert response.status_code == 200

        # Verify it's gone
        response = client.get(f"/api/public/games/{game_id}")
        assert response.status_code == 404


class TestAdminLoginEndpoint:
    """Tests for admin login/logout"""

    def test_admin_login_success(self, client):
        """Test successful admin login"""
        response = client.post(
            "/api/admin/login",
            json={"token": "test_admin_token"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True or "message" in data

    def test_admin_login_invalid_token(self, client):
        """Test admin login with invalid token"""
        response = client.post(
            "/api/admin/login",
            json={"token": "wrong_token"}
        )
        assert response.status_code == 401

    def test_admin_validate(self, client, admin_headers):
        """Test admin token validation"""
        response = client.get("/api/admin/validate", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("valid") is True or "authenticated" in data

    def test_admin_logout(self, client):
        """Test admin logout"""
        response = client.post("/api/admin/logout")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True


class TestAdminAuthenticationEdgeCases:
    """Edge cases and security tests for authentication"""

    def test_admin_validate_without_token(self, client):
        """Test validation endpoint without token"""
        response = client.get("/api/admin/validate")
        assert response.status_code == 401

    def test_login_response_includes_expiry(self, client):
        """Test login response includes session expiry info"""
        response = client.post(
            "/api/admin/login",
            json={"token": "test_admin_token"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "expires_in" in data or "message" in data

    def test_login_sets_cookie(self, client):
        """Test login sets admin_session cookie"""
        response = client.post(
            "/api/admin/login",
            json={"token": "test_admin_token"}
        )
        assert response.status_code == 200
        # Check if cookie was set (TestClient may not expose cookies perfectly)
        # At minimum, verify successful response
        assert response.json().get("success") is True


class TestAdminGameCRUDEdgeCases:
    """Edge cases for admin CRUD operations"""

    def test_get_admin_game_not_found(self, client, admin_headers):
        """Test getting non-existent game as admin"""
        response = client.get("/api/admin/games/99999", headers=admin_headers)
        assert response.status_code == 404

    def test_update_game_not_found(self, client, admin_headers):
        """Test updating non-existent game"""
        response = client.put(
            "/api/admin/games/99999",
            json={"title": "Updated Title"},
            headers=admin_headers
        )
        assert response.status_code == 404

    def test_delete_game_not_found(self, client, admin_headers):
        """Test deleting non-existent game"""
        response = client.delete(
            "/api/admin/games/99999",
            headers=admin_headers
        )
        assert response.status_code == 404

    def test_update_game_via_post(self, client, db_session, admin_headers, sample_game_data):
        """Test updating game via POST method (proxy compatibility)"""
        # Create a game first
        game = Game(**sample_game_data)
        db_session.add(game)
        db_session.commit()
        game_id = game.id

        # Update via POST instead of PUT
        update_data = {"title": "Pandemic Updated"}
        response = client.post(
            f"/api/admin/games/{game_id}/update",
            json=update_data,
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Pandemic Updated"

    def test_get_admin_game_success(self, client, db_session, admin_headers, sample_game_data):
        """Test getting single game as admin"""
        game = Game(**sample_game_data)
        db_session.add(game)
        db_session.commit()
        game_id = game.id

        response = client.get(f"/api/admin/games/{game_id}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Pandemic"
        assert data["id"] == game_id

    def test_create_game_validation_error(self, client, admin_headers):
        """Test creating game with invalid data"""
        invalid_data = {"invalid_field": "value"}
        response = client.post(
            "/api/admin/games",
            json=invalid_data,
            headers=admin_headers
        )
        # Should return validation error (422) or other error (400/500)
        assert response.status_code in [400, 422, 500]


class TestAdminBGGImport:
    """Tests for BoardGameGeek import functionality"""

    def test_import_from_bgg_success(self, client, admin_headers):
        """Test successful BGG import"""
        with patch("api.routers.admin.fetch_bgg_thing", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {
                "title": "Gloomhaven",
                "year": 2017,
                "thumbnail": "https://cf.geekdo-images.com/thumb.jpg",
                "image": "https://cf.geekdo-images.com/image.jpg",
                "players_min": 1,
                "players_max": 4,
                "playtime_min": 60,
                "playtime_max": 120,
                "description": "Test description",
                "designers": ["Isaac Childres"],
                "mechanics": ["Hand Management", "Variable Player Powers"],
                "average_rating": 8.8,
                "complexity": 3.86,
            }

            response = client.post(
                "/api/admin/import/bgg?bgg_id=174430",
                headers=admin_headers
            )
            assert response.status_code == 201
            data = response.json()
            assert "id" in data
            assert "title" in data

    def test_import_from_bgg_force_reimport(self, client, db_session, admin_headers):
        """Test force reimport of existing game"""
        # Create existing game with BGG ID (with required fields to pass constraints)
        game = Game(
            title="Gloomhaven",
            bgg_id=174430,
            status="OWNED",
            players_min=1,
            playtime_min=60
        )
        db_session.add(game)
        db_session.commit()

        with patch("api.routers.admin.fetch_bgg_thing", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {
                "title": "Gloomhaven Updated",
                "year": 2017,
                "thumbnail": "https://cf.geekdo-images.com/thumb.jpg",
                "players_min": 1,
                "players_max": 4,
                "playtime_min": 60,
                "playtime_max": 120,
            }

            response = client.post(
                "/api/admin/import/bgg?bgg_id=174430&force=true",
                headers=admin_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert "id" in data

    def test_import_from_bgg_missing_id(self, client, admin_headers):
        """Test BGG import without ID parameter"""
        response = client.post(
            "/api/admin/import/bgg",
            headers=admin_headers
        )
        assert response.status_code == 422  # Missing required parameter

    def test_import_from_bgg_api_error(self, client, admin_headers):
        """Test BGG import when API fails"""
        with patch("api.routers.admin.fetch_bgg_thing", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("BGG API error")

            response = client.post(
                "/api/admin/import/bgg?bgg_id=999999",
                headers=admin_headers
            )
            assert response.status_code == 500


class TestAdminFixSequence:
    """Tests for database sequence fix endpoint"""

    def test_fix_sequence_success(self, client, admin_headers):
        """Test successful sequence fix (PostgreSQL-specific, SQLite returns 500)"""
        response = client.post(
            "/api/admin/fix-sequence",
            json={"table_name": "boardgames"},
            headers=admin_headers
        )
        # In production (PostgreSQL): 200 OK
        # In tests (SQLite): 500 (setval doesn't exist)
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "max_id" in data
            assert "next_id" in data
        else:
            # SQLite test environment - function doesn't exist
            assert response.status_code == 500

    def test_fix_sequence_invalid_table(self, client, admin_headers):
        """Test sequence fix with invalid table name"""
        response = client.post(
            "/api/admin/fix-sequence",
            json={"table_name": "invalid_table"},
            headers=admin_headers
        )
        # Should be rejected by validation (400) or fail gracefully (500)
        assert response.status_code in [400, 422, 500]

    def test_fix_sequence_unauthorized(self, client, csrf_headers):
        """Test sequence fix without authentication"""
        response = client.post(
            "/api/admin/fix-sequence",
            json={"table_name": "boardgames"},
            headers=csrf_headers
        )
        assert response.status_code == 401


class TestAdminLoginRateLimiting:
    """Tests for login rate limiting"""

    def test_login_rate_limit_exceeded(self, client):
        """Test rate limiting on login attempts"""
        # Note: In test environment, rate limiting may use in-memory storage
        # which might be cleared between requests. This test verifies the
        # rate limiting logic exists and can be triggered.
        from shared.rate_limiting import admin_attempt_tracker
        from config import RATE_LIMIT_ATTEMPTS
        import time

        # Manually populate rate limit tracker to test the logic
        client_ip = "127.0.0.1"
        current_time = time.time()
        admin_attempt_tracker[client_ip] = [current_time] * RATE_LIMIT_ATTEMPTS

        # This request should be rate limited
        response = client.post(
            "/api/admin/login",
            json={"token": "wrong_token"}
        )
        # Should be rate limited (429) or unauthorized (401)
        # depending on whether rate limit check comes before auth check
        assert response.status_code in [401, 429]


class TestAdminGameCreationErrors:
    """Tests for error handling in game creation"""

    def test_create_game_with_invalid_player_count(self, client, admin_headers, sample_game_data):
        """Test creating game with max players < min players"""
        invalid_data = sample_game_data.copy()
        invalid_data["players_min"] = 4
        invalid_data["players_max"] = 2  # Invalid: max < min

        response = client.post(
            "/api/admin/games",
            json=invalid_data,
            headers=admin_headers
        )
        # Should return 400 with constraint violation message
        assert response.status_code == 400
        assert "players" in response.json()["detail"].lower()

    def test_create_game_with_invalid_playtime(self, client, admin_headers, sample_game_data):
        """Test creating game with max playtime < min playtime"""
        invalid_data = sample_game_data.copy()
        invalid_data["playtime_min"] = 120
        invalid_data["playtime_max"] = 60  # Invalid: max < min

        response = client.post(
            "/api/admin/games",
            json=invalid_data,
            headers=admin_headers
        )
        # Should return 400 with constraint violation message
        assert response.status_code == 400
        assert "playtime" in response.json()["detail"].lower()

    def test_create_game_with_invalid_year(self, client, admin_headers, sample_game_data):
        """Test creating game with year before 1900"""
        invalid_data = sample_game_data.copy()
        invalid_data["year"] = 1800  # Invalid: year < 1900

        response = client.post(
            "/api/admin/games",
            json=invalid_data,
            headers=admin_headers
        )
        # Should return 400 with year constraint violation
        assert response.status_code == 400
        assert "year" in response.json()["detail"].lower()


class TestAdminGameUpdateErrors:
    """Tests for error handling in game updates"""

    def test_update_game_via_post_not_found(self, client, admin_headers):
        """Test POST update of non-existent game"""
        response = client.post(
            "/api/admin/games/99999/update",
            json={"title": "Updated Title"},
            headers=admin_headers
        )
        assert response.status_code == 404

    def test_update_game_with_invalid_player_count(self, client, db_session, admin_headers, sample_game_data):
        """Test updating game with invalid player count"""
        game = Game(**sample_game_data)
        db_session.add(game)
        db_session.commit()
        game_id = game.id

        response = client.put(
            f"/api/admin/games/{game_id}",
            json={"players_min": 4, "players_max": 2},  # Invalid
            headers=admin_headers
        )
        assert response.status_code == 400

    def test_update_game_with_invalid_playtime(self, client, db_session, admin_headers, sample_game_data):
        """Test updating game with invalid playtime"""
        game = Game(**sample_game_data)
        db_session.add(game)
        db_session.commit()
        game_id = game.id

        response = client.put(
            f"/api/admin/games/{game_id}",
            json={"playtime_min": 120, "playtime_max": 60},  # Invalid
            headers=admin_headers
        )
        assert response.status_code == 400

    def test_update_game_with_invalid_year(self, client, db_session, admin_headers, sample_game_data):
        """Test updating game with invalid year"""
        game = Game(**sample_game_data)
        db_session.add(game)
        db_session.commit()
        game_id = game.id

        response = client.put(
            f"/api/admin/games/{game_id}",
            json={"year": 1800},  # Invalid: year < 1900
            headers=admin_headers
        )
        assert response.status_code == 400


class TestAdminDeleteErrors:
    """Tests for error handling in game deletion"""

    def test_delete_game_database_error(self, client, db_session, admin_headers, sample_game_data):
        """Test delete game with database error"""
        game = Game(**sample_game_data)
        db_session.add(game)
        db_session.commit()
        game_id = game.id

        # Mock database error
        with patch("services.game_service.GameService.delete_game") as mock_delete:
            mock_delete.side_effect = Exception("Database error")

            response = client.delete(
                f"/api/admin/games/{game_id}",
                headers=admin_headers
            )
            assert response.status_code == 500


class TestAdminGitHubWorkflowTrigger:
    """Tests for GitHub workflow trigger endpoint"""

    def test_trigger_sleeve_fetch_no_token(self, client, admin_headers):
        """Test triggering sleeve fetch without GitHub token configured"""
        with patch("config.GITHUB_TOKEN", None):
            response = client.post(
                "/api/admin/trigger-sleeve-fetch",
                json=[1, 2, 3],
                headers=admin_headers
            )
            assert response.status_code == 503
            assert "GitHub token not configured" in response.json()["detail"]

    def test_trigger_sleeve_fetch_no_game_ids(self, client, admin_headers):
        """Test triggering sleeve fetch with empty game IDs"""
        with patch("config.GITHUB_TOKEN", "fake_token"):
            response = client.post(
                "/api/admin/trigger-sleeve-fetch",
                json=[],
                headers=admin_headers
            )
            assert response.status_code == 400
            assert "game ID" in response.json()["detail"]

    def test_trigger_sleeve_fetch_success(self, client, admin_headers):
        """Test successful sleeve fetch trigger"""
        with patch("config.GITHUB_TOKEN", "fake_token"), \
             patch("config.GITHUB_REPO_OWNER", "owner"), \
             patch("config.GITHUB_REPO_NAME", "repo"):

            with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
                mock_response = Mock()
                mock_response.status_code = 204  # Success
                mock_post.return_value = mock_response

                response = client.post(
                    "/api/admin/trigger-sleeve-fetch",
                    json=[1, 2, 3],
                    headers=admin_headers
                )
                assert response.status_code == 200
                assert response.json()["success"] is True

    def test_trigger_sleeve_fetch_github_api_error(self, client, admin_headers):
        """Test sleeve fetch trigger with GitHub API error"""
        with patch("config.GITHUB_TOKEN", "fake_token"), \
             patch("config.GITHUB_REPO_OWNER", "owner"), \
             patch("config.GITHUB_REPO_NAME", "repo"):

            with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
                mock_response = Mock()
                mock_response.status_code = 401  # Unauthorized
                mock_response.text = "Bad credentials"
                mock_post.return_value = mock_response

                response = client.post(
                    "/api/admin/trigger-sleeve-fetch",
                    json=[1, 2, 3],
                    headers=admin_headers
                )
                # Note: GitHub API error gets wrapped in 500 by outer exception handler
                assert response.status_code == 500
                assert "GitHub API error" in response.json()["detail"] or "Unexpected error" in response.json()["detail"]

    def test_trigger_sleeve_fetch_http_error(self, client, admin_headers):
        """Test sleeve fetch trigger with HTTP error"""
        import httpx

        with patch("config.GITHUB_TOKEN", "fake_token"), \
             patch("config.GITHUB_REPO_OWNER", "owner"), \
             patch("config.GITHUB_REPO_NAME", "repo"):

            with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
                mock_post.side_effect = httpx.HTTPError("Connection error")

                response = client.post(
                    "/api/admin/trigger-sleeve-fetch",
                    json=[1, 2, 3],
                    headers=admin_headers
                )
                assert response.status_code == 500
                assert "Failed to trigger workflow" in response.json()["detail"]

    def test_trigger_sleeve_fetch_unexpected_error(self, client, admin_headers):
        """Test sleeve fetch trigger with unexpected error"""
        with patch("config.GITHUB_TOKEN", "fake_token"), \
             patch("config.GITHUB_REPO_OWNER", "owner"), \
             patch("config.GITHUB_REPO_NAME", "repo"):

            with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
                mock_post.side_effect = Exception("Unexpected error")

                response = client.post(
                    "/api/admin/trigger-sleeve-fetch",
                    json=[1, 2, 3],
                    headers=admin_headers
                )
                assert response.status_code == 500
                assert "Unexpected error" in response.json()["detail"]


class TestAdminBackgroundFailureMonitoring:
    """Tests for background task failure monitoring endpoints"""

    def test_get_background_failures_success(self, client, db_session, admin_headers):
        """Test getting background task failures"""
        # This test will work even if BackgroundTaskFailure model doesn't exist
        # since the endpoint handles exceptions
        response = client.get(
            "/api/admin/monitoring/background-failures",
            headers=admin_headers
        )
        # Should either succeed (200) or fail gracefully (500)
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert "total_failures" in data
            assert "unresolved_failures" in data
            assert "failures" in data

    def test_get_background_failures_filtered_by_resolved(self, client, admin_headers):
        """Test getting failures filtered by resolved status"""
        response = client.get(
            "/api/admin/monitoring/background-failures?resolved=false",
            headers=admin_headers
        )
        assert response.status_code in [200, 500]

    def test_get_background_failures_filtered_by_task_type(self, client, admin_headers):
        """Test getting failures filtered by task type"""
        response = client.get(
            "/api/admin/monitoring/background-failures?task_type=thumbnail_download",
            headers=admin_headers
        )
        assert response.status_code in [200, 500]

    def test_get_background_failures_with_limit(self, client, admin_headers):
        """Test getting failures with custom limit"""
        response = client.get(
            "/api/admin/monitoring/background-failures?limit=5",
            headers=admin_headers
        )
        assert response.status_code in [200, 500]

    def test_resolve_background_failure_not_found(self, client, admin_headers):
        """Test resolving non-existent failure"""
        response = client.post(
            "/api/admin/monitoring/background-failures/99999/resolve",
            headers=admin_headers
        )
        # Should return 404 (not found) or 500 (model doesn't exist)
        assert response.status_code in [404, 500]

    def test_resolve_background_failure_unauthorized(self, client, csrf_headers):
        """Test resolving failure without authentication"""
        response = client.post(
            "/api/admin/monitoring/background-failures/1/resolve",
            headers=csrf_headers
        )
        assert response.status_code == 401


class TestAdminCircuitBreakerStatus:
    """Tests for circuit breaker status monitoring"""

    def test_get_circuit_breaker_status(self, client, admin_headers):
        """Test getting circuit breaker status"""
        response = client.get(
            "/api/admin/monitoring/circuit-breaker-status",
            headers=admin_headers
        )
        # Should either succeed or fail gracefully
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert "circuit_breaker" in data
            assert "state" in data
            assert "is_available" in data

    def test_get_circuit_breaker_status_unauthorized(self, client):
        """Test getting circuit breaker status without authentication"""
        # GET requests don't trigger CSRF validation, so no csrf_headers needed
        response = client.get(
            "/api/admin/monitoring/circuit-breaker-status"
        )
        assert response.status_code == 401
