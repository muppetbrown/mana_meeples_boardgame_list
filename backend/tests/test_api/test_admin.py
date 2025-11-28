"""
Tests for admin API endpoints
"""
import pytest
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
        assert len(data["items"]) == 4

    def test_create_game(self, client, admin_headers, sample_game_data):
        """Test creating a new game"""
        response = client.post(
            "/api/admin/games",
            json=sample_game_data,
            headers=admin_headers
        )
        assert response.status_code == 200
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
