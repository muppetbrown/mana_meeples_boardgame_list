"""
Tests for public API endpoints
"""
import pytest
from models import Game


class TestPublicGamesEndpoint:
    """Tests for GET /api/public/games"""

    def test_get_games_empty_database(self, client):
        """Test getting games from empty database"""
        response = client.get("/api/public/games")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 0
        assert len(data["items"]) == 0

    def test_get_games_with_data(self, client, db_session, sample_games_list):
        """Test getting games with data in database"""
        # Add sample games to database
        for game_data in sample_games_list:
            game = Game(**game_data)
            db_session.add(game)
        db_session.commit()

        response = client.get("/api/public/games")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 4
        assert len(data["items"]) == 4

    def test_get_games_pagination(self, client, db_session, sample_games_list):
        """Test pagination parameters"""
        # Add sample games
        for game_data in sample_games_list:
            game = Game(**game_data)
            db_session.add(game)
        db_session.commit()

        # Test page size
        response = client.get("/api/public/games?page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 4

        # Test page 2
        response = client.get("/api/public/games?page=2&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2

    def test_get_games_search(self, client, db_session, sample_games_list):
        """Test search functionality"""
        for game_data in sample_games_list:
            game = Game(**game_data)
            db_session.add(game)
        db_session.commit()

        # Search for "Pandemic"
        response = client.get("/api/public/games?q=Pandemic")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Pandemic"

        # Search for "code" (should match Codenames)
        response = client.get("/api/public/games?q=code")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert "Codenames" in data["items"][0]["title"]

    def test_get_games_category_filter(self, client, db_session, sample_games_list):
        """Test filtering by category"""
        for game_data in sample_games_list:
            game = Game(**game_data)
            db_session.add(game)
        db_session.commit()

        # Filter by COOP_ADVENTURE
        response = client.get("/api/public/games?category=COOP_ADVENTURE")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Pandemic"

        # Filter by GATEWAY_STRATEGY
        response = client.get("/api/public/games?category=GATEWAY_STRATEGY")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Catan"

    def test_get_games_sorting(self, client, db_session, sample_games_list):
        """Test sorting options"""
        for game_data in sample_games_list:
            game = Game(**game_data)
            db_session.add(game)
        db_session.commit()

        # Sort by title ascending (default)
        response = client.get("/api/public/games?sort=title_asc")
        assert response.status_code == 200
        data = response.json()
        titles = [game["title"] for game in data["items"]]
        assert titles == sorted(titles)

        # Sort by year descending
        response = client.get("/api/public/games?sort=year_desc")
        assert response.status_code == 200
        data = response.json()
        years = [game["year"] for game in data["items"] if game["year"]]
        assert years == sorted(years, reverse=True)


class TestPublicGameDetailEndpoint:
    """Tests for GET /api/public/games/{game_id}"""

    def test_get_game_not_found(self, client):
        """Test getting non-existent game"""
        response = client.get("/api/public/games/99999")
        assert response.status_code == 404

    def test_get_game_success(self, client, db_session, sample_game_data):
        """Test getting existing game"""
        game = Game(**sample_game_data)
        db_session.add(game)
        db_session.commit()
        game_id = game.id

        response = client.get(f"/api/public/games/{game_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Pandemic"
        assert data["id"] == game_id


class TestCategoryCountsEndpoint:
    """Tests for GET /api/public/category-counts"""

    def test_category_counts_empty(self, client):
        """Test category counts with empty database"""
        response = client.get("/api/public/category-counts")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_category_counts_with_data(self, client, db_session, sample_games_list):
        """Test category counts with games"""
        for game_data in sample_games_list:
            game = Game(**game_data)
            db_session.add(game)
        db_session.commit()

        response = client.get("/api/public/category-counts")
        assert response.status_code == 200
        data = response.json()

        # Verify counts match our sample data
        assert data.get("COOP_ADVENTURE") == 1
        assert data.get("GATEWAY_STRATEGY") == 1
        assert data.get("CORE_STRATEGY") == 1
        assert data.get("PARTY_ICEBREAKERS") == 1


class TestHealthEndpoints:
    """Tests for health check endpoints"""

    def test_health_check(self, client):
        """Test basic health check"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_health_db_check(self, client):
        """Test database health check"""
        response = client.get("/api/health/db")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "game_count" in data
