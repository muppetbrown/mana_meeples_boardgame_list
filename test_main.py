import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app, get_db
from models import Base, Game
from database import SessionLocal


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_game_data():
    return {
        "title": "Test Game",
        "bgg_id": 12345,
        "year": 2020,
        "description": "A test game",
        "image_url": "http://example.com/image.jpg",
        "thumbnail_url": "http://example.com/thumb.jpg",
        "min_players": 2,
        "max_players": 4,
        "playtime_min": 30,
        "playtime_max": 60,
        "min_age": 10,
        "complexity": 2.5,
        "average_rating": 7.8,
        "mana_meeple_category": "GATEWAY_STRATEGY"
    }


class TestPublicEndpoints:
    """Test public API endpoints"""
    
    def test_get_public_games_default(self, client):
        """Test getting public games with default parameters"""
        response = client.get("/api/public/games")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
    
    def test_get_public_games_with_search(self, client):
        """Test searching public games"""
        response = client.get("/api/public/games?q=test")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
    
    def test_get_public_games_with_pagination(self, client):
        """Test pagination parameters"""
        response = client.get("/api/public/games?page=2&page_size=12")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 12
    
    def test_get_public_games_with_category_filter(self, client):
        """Test category filtering"""
        response = client.get("/api/public/games?category=GATEWAY_STRATEGY")
        assert response.status_code == 200
    
    def test_get_public_games_with_sort(self, client):
        """Test sorting options"""
        for sort_option in ["title_asc", "title_desc", "year_asc", "year_desc", "rating_asc", "rating_desc"]:
            response = client.get(f"/api/public/games?sort={sort_option}")
            assert response.status_code == 200
    
    def test_get_category_counts(self, client):
        """Test getting category counts"""
        response = client.get("/api/public/category-counts")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
    
    def test_get_public_game_details(self, client):
        """Test getting game details"""
        # This will return 404 for non-existent game, which is expected
        response = client.get("/api/public/games/999999")
        assert response.status_code == 404


class TestAdminEndpoints:
    """Test admin API endpoints"""
    
    @pytest.fixture
    def admin_headers(self):
        return {"X-Admin-Token": "test-token"}
    
    def test_get_admin_games_unauthorized(self, client):
        """Test admin endpoints without token"""
        response = client.get("/api/admin/games")
        assert response.status_code == 401
    
    @patch.dict(os.environ, {"ADMIN_TOKEN": "test-token"})
    def test_get_admin_games_authorized(self, client, admin_headers):
        """Test admin games endpoint with valid token"""
        response = client.get("/api/admin/games", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @patch.dict(os.environ, {"ADMIN_TOKEN": "test-token"})
    @patch('main.fetch_bgg_thing')
    def test_import_bgg_game(self, mock_fetch, client, admin_headers, sample_game_data):
        """Test importing game from BGG"""
        mock_fetch.return_value = sample_game_data
        
        response = client.post(
            "/api/admin/import/bgg?bgg_id=12345",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Game"


class TestBGGService:
    """Test BGG integration service"""
    
    @patch('httpx.AsyncClient.get')
    async def test_fetch_bgg_thing_success(self, mock_get):
        """Test successful BGG API fetch"""
        from bgg_service import fetch_bgg_thing
        
        # Mock XML response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """<?xml version="1.0" encoding="utf-8"?>
        <items termsofuse="https://boardgamegeek.com/xmlapi/termsofuse">
            <item type="boardgame" id="12345">
                <name type="primary" sortindex="1" value="Test Game" />
                <yearpublished value="2020" />
                <description>A test game</description>
                <image>http://example.com/image.jpg</image>
                <thumbnail>http://example.com/thumb.jpg</thumbnail>
                <minplayers value="2" />
                <maxplayers value="4" />
                <playingtime value="60" />
                <minplaytime value="30" />
                <maxplaytime value="60" />
                <minage value="10" />
                <statistics>
                    <ratings>
                        <average value="7.8" />
                        <averageweight value="2.5" />
                    </ratings>
                </statistics>
            </item>
        </items>"""
        mock_get.return_value = mock_response
        
        result = await fetch_bgg_thing(12345)
        assert result["title"] == "Test Game"
        assert result["bgg_id"] == 12345
        assert result["year"] == 2020


class TestUtilityFunctions:
    """Test utility functions"""
    
    def test_auto_categorize_function_exists(self):
        """Test that auto-categorization function exists"""
        from main import auto_categorize_game
        assert callable(auto_categorize_game)
    
    def test_game_to_dict_function_exists(self):
        """Test that game conversion function exists"""
        from main import _game_to_dict
        assert callable(_game_to_dict)


class TestImageProxy:
    """Test image proxy functionality"""
    
    def test_image_proxy_endpoint(self, client):
        """Test image proxy endpoint structure"""
        # Test with a basic URL - should handle gracefully even if external URL fails
        response = client.get("/proxy/image?url=http://example.com/test.jpg")
        # Should either succeed or fail gracefully (not 500)
        assert response.status_code in [200, 400, 404, 502]


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_invalid_pagination_parameters(self, client):
        """Test handling of invalid pagination"""
        response = client.get("/api/public/games?page=0")
        # Should either fix the parameter or return 422
        assert response.status_code in [200, 422]
    
    def test_invalid_sort_parameter(self, client):
        """Test handling of invalid sort parameter"""
        response = client.get("/api/public/games?sort=invalid_sort")
        assert response.status_code == 200  # Should fallback to default
    
    def test_very_large_page_size(self, client):
        """Test handling of very large page size"""
        response = client.get("/api/public/games?page_size=10000")
        assert response.status_code == 200
        data = response.json()
        # Should respect the limit (1000 based on the code)
        assert data["page_size"] <= 1000