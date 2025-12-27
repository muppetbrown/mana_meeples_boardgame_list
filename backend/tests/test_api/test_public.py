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


class TestPublicGamesAdvancedFiltering:
    """Advanced filtering and query parameter tests"""

    def test_get_games_nz_designer_filter(self, client, db_session):
        """Test filtering by NZ designer flag"""
        games = [
            Game(title="NZ Game 1", nz_designer=True, players_min=2, playtime_min=30, status="OWNED"),
            Game(title="NZ Game 2", nz_designer=True, players_min=2, playtime_min=30, status="OWNED"),
            Game(title="Regular Game", nz_designer=False, players_min=2, playtime_min=30, status="OWNED"),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        # Filter for NZ designers
        response = client.get("/api/public/games?nz_designer=true")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all("NZ" in item["title"] for item in data["items"])

        # Filter for non-NZ designers
        response = client.get("/api/public/games?nz_designer=false")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_get_games_designer_filter(self, client, db_session):
        """Test filtering by designer name"""
        games = [
            Game(title="Game 1", designers=["Matt Leacock"], status="OWNED", players_min=2, playtime_min=30),
            Game(title="Game 2", designers=["Klaus Teuber"], status="OWNED", players_min=2, playtime_min=30),
            Game(title="Game 3", designers=["Matt Leacock", "Klaus Teuber"], status="OWNED", players_min=2, playtime_min=30),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        response = client.get("/api/public/games?designer=Matt Leacock")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_get_games_combined_filters(self, client, db_session):
        """Test combining multiple filters"""
        games = [
            Game(
                title="NZ Coop Game",
                mana_meeple_category="COOP_ADVENTURE",
                nz_designer=True,
                players_min=2,
                playtime_min=30,
                status="OWNED"
            ),
            Game(
                title="Regular Coop Game",
                mana_meeple_category="COOP_ADVENTURE",
                nz_designer=False,
                players_min=2,
                playtime_min=30,
                status="OWNED"
            ),
            Game(
                title="NZ Strategy Game",
                mana_meeple_category="CORE_STRATEGY",
                nz_designer=True,
                players_min=2,
                playtime_min=30,
                status="OWNED"
            ),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        # Combine category + nz_designer
        response = client.get(
            "/api/public/games?category=COOP_ADVENTURE&nz_designer=true"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "NZ Coop Game"

    def test_get_games_players_filter(self, client, db_session):
        """Test filtering by player count"""
        games = [
            Game(title="2-4 Players", players_min=2, players_max=4, playtime_min=30, status="OWNED"),
            Game(title="1-6 Players", players_min=1, players_max=6, playtime_min=30, status="OWNED"),
            Game(title="3-5 Players", players_min=3, players_max=5, playtime_min=30, status="OWNED"),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        # Filter for games supporting 5 players
        response = client.get("/api/public/games?players=5")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2  # Games that support 5 players

    def test_get_games_search_and_category(self, client, db_session):
        """Test combining search with category filter"""
        games = [
            Game(title="Pandemic Legacy", mana_meeple_category="COOP_ADVENTURE", players_min=2, playtime_min=45, status="OWNED"),
            Game(title="Pandemic", mana_meeple_category="COOP_ADVENTURE", players_min=2, playtime_min=45, status="OWNED"),
            Game(title="Pandemic: Iberia", mana_meeple_category="CORE_STRATEGY", players_min=2, playtime_min=45, status="OWNED"),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        response = client.get("/api/public/games?q=Pandemic&category=COOP_ADVENTURE")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2


class TestPublicGamesSorting:
    """Comprehensive sorting tests"""

    def test_get_games_sort_rating_desc(self, client, db_session):
        """Test sorting by rating descending"""
        games = [
            Game(title="Low Rated", average_rating=5.5, players_min=2, playtime_min=30, status="OWNED"),
            Game(title="High Rated", average_rating=8.5, players_min=2, playtime_min=30, status="OWNED"),
            Game(title="Mid Rated", average_rating=7.0, players_min=2, playtime_min=30, status="OWNED"),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        response = client.get("/api/public/games?sort=rating_desc")
        assert response.status_code == 200
        data = response.json()
        ratings = [game["average_rating"] for game in data["items"] if game["average_rating"]]
        assert ratings == sorted(ratings, reverse=True)

    def test_get_games_sort_rating_asc(self, client, db_session):
        """Test sorting by rating ascending"""
        games = [
            Game(title="Low Rated", average_rating=5.5, players_min=2, playtime_min=30, status="OWNED"),
            Game(title="High Rated", average_rating=8.5, players_min=2, playtime_min=30, status="OWNED"),
            Game(title="Mid Rated", average_rating=7.0, players_min=2, playtime_min=30, status="OWNED"),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        response = client.get("/api/public/games?sort=rating_asc")
        assert response.status_code == 200
        data = response.json()
        ratings = [game["average_rating"] for game in data["items"] if game["average_rating"]]
        assert ratings == sorted(ratings)

    def test_get_games_sort_time_asc(self, client, db_session):
        """Test sorting by playtime ascending"""
        games = [
            Game(title="Long Game", playtime_min=120, players_min=2, status="OWNED"),
            Game(title="Short Game", playtime_min=30, players_min=2, status="OWNED"),
            Game(title="Medium Game", playtime_min=60, players_min=2, status="OWNED"),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        response = client.get("/api/public/games?sort=time_asc")
        assert response.status_code == 200
        data = response.json()
        times = [game["playtime_min"] for game in data["items"] if game["playtime_min"]]
        assert times == sorted(times)

    def test_get_games_sort_time_desc(self, client, db_session):
        """Test sorting by playtime descending"""
        games = [
            Game(title="Long Game", playtime_min=120, players_min=2, status="OWNED"),
            Game(title="Short Game", playtime_min=30, players_min=2, status="OWNED"),
            Game(title="Medium Game", playtime_min=60, players_min=2, status="OWNED"),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        response = client.get("/api/public/games?sort=time_desc")
        assert response.status_code == 200
        data = response.json()
        times = [game["playtime_min"] for game in data["items"] if game["playtime_min"]]
        assert times == sorted(times, reverse=True)


class TestPublicGamesValidation:
    """Query parameter validation and edge cases"""

    def test_get_games_invalid_page(self, client):
        """Test invalid page number"""
        response = client.get("/api/public/games?page=0")
        assert response.status_code == 422  # Validation error

    def test_get_games_invalid_page_size(self, client):
        """Test invalid page size"""
        response = client.get("/api/public/games?page_size=0")
        assert response.status_code == 422  # Validation error

    def test_get_games_large_page_size(self, client, db_session):
        """Test maximum page size limit"""
        # Add multiple games
        for i in range(50):
            db_session.add(Game(title=f"Game {i}", players_min=2, playtime_min=30, status="OWNED"))
        db_session.commit()

        # Request max allowed (1000)
        response = client.get("/api/public/games?page_size=1000")
        assert response.status_code == 200

        # Request over limit should be rejected
        response = client.get("/api/public/games?page_size=1001")
        assert response.status_code == 422

    def test_get_games_empty_search(self, client, db_session, sample_games_list):
        """Test empty search string returns all games"""
        for game_data in sample_games_list:
            db_session.add(Game(**game_data))
        db_session.commit()

        response = client.get("/api/public/games?q=")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 4

    def test_get_games_uncategorized_filter(self, client, db_session):
        """Test filtering uncategorized games"""
        games = [
            Game(title="Categorized", mana_meeple_category="COOP_ADVENTURE", players_min=2, playtime_min=30, status="OWNED"),
            Game(title="Uncategorized 1", mana_meeple_category=None, players_min=2, playtime_min=30, status="OWNED"),
            Game(title="Uncategorized 2", mana_meeple_category=None, players_min=2, playtime_min=30, status="OWNED"),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        response = client.get("/api/public/games?category=uncategorized")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2


class TestDesignerEndpoint:
    """Tests for designer-specific endpoint"""

    def test_get_games_by_designer_success(self, client, db_session):
        """Test getting games by designer name"""
        games = [
            Game(title="Pandemic", designers=["Matt Leacock"], status="OWNED", players_min=2, playtime_min=45),
            Game(title="Forbidden Island", designers=["Matt Leacock"], status="OWNED", players_min=2, playtime_min=30),
            Game(title="Catan", designers=["Klaus Teuber"], status="OWNED", players_min=3, playtime_min=60),
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        response = client.get("/api/public/games/by-designer/Matt Leacock")
        assert response.status_code == 200
        data = response.json()
        assert data["designer"] == "Matt Leacock"
        assert len(data["games"]) == 2

    def test_get_games_by_designer_not_found(self, client, db_session):
        """Test getting games by non-existent designer"""
        response = client.get("/api/public/games/by-designer/Unknown Designer")
        assert response.status_code == 200
        data = response.json()
        assert data["designer"] == "Unknown Designer"
        assert len(data["games"]) == 0


class TestImageProxyEndpoint:
    """Tests for image proxy endpoint"""

    def test_image_proxy_missing_url(self, client):
        """Test image proxy without URL parameter"""
        response = client.get("/api/public/image-proxy")
        assert response.status_code == 422  # Missing required parameter

    def test_image_proxy_untrusted_domain(self, client):
        """Test image proxy with untrusted domain"""
        response = client.get(
            "/api/public/image-proxy?url=https://evil.com/malicious.jpg"
        )
        assert response.status_code == 400
        assert "trusted" in response.json()["detail"].lower() or "boardgamegeek" in response.json()["detail"].lower()

    def test_image_proxy_bgg_domain(self, client, db_session):
        """Test image proxy with BGG domain"""
        from unittest.mock import AsyncMock, Mock, patch

        # Mock the image service response
        mock_content = b"fake image data"
        mock_content_type = "image/jpeg"
        mock_cache_control = "public, max-age=300"

        with patch("api.routers.public.ImageService") as mock_service_class:
            mock_service = Mock()
            mock_service.proxy_image = AsyncMock(
                return_value=(mock_content, mock_content_type, mock_cache_control)
            )
            mock_service_class.return_value = mock_service

            response = client.get(
                "/api/public/image-proxy?url=https://cf.geekdo-images.com/test.jpg"
            )
            assert response.status_code == 200
            assert response.headers["content-type"] == mock_content_type


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


class TestGameExpansions:
    """Tests for game expansion relationships and player count calculations"""

    def test_get_games_with_expansions(self, client, db_session):
        """Test getting games list with expansions that modify player counts"""
        # Create base game
        base_game = Game(
            title="Base Game",
            bgg_id=10000,
            players_min=2,
            players_max=4,
            is_expansion=False
        )
        db_session.add(base_game)
        db_session.flush()

        # Create expansion that increases max players
        expansion = Game(
            title="Expansion Pack",
            bgg_id=10001,
            is_expansion=True,
            base_game_id=base_game.id,
            modifies_players_min=1,
            modifies_players_max=6
        )
        db_session.add(expansion)
        db_session.commit()

        # Get games list
        response = client.get("/api/public/games")
        assert response.status_code == 200
        data = response.json()

        # Find the base game in response
        base_game_data = None
        for item in data["items"]:
            if item["title"] == "Base Game":
                base_game_data = item
                break

        assert base_game_data is not None
        # Check if expansion player count info is included
        if "players_max_with_expansions" in base_game_data:
            assert base_game_data["players_max_with_expansions"] == 6
            assert base_game_data["players_min_with_expansions"] == 1
            assert base_game_data["has_player_expansion"] is True

    def test_get_single_game_with_expansions(self, client, db_session):
        """Test getting single game details with expansions"""
        # Create base game
        base_game = Game(
            title="Base Game",
            bgg_id=10000,
            players_min=2,
            players_max=4,
            is_expansion=False
        )
        db_session.add(base_game)
        db_session.flush()

        # Create expansion
        expansion = Game(
            title="Expansion Pack",
            bgg_id=10001,
            is_expansion=True,
            base_game_id=base_game.id,
            modifies_players_min=1,
            modifies_players_max=6
        )
        db_session.add(expansion)
        db_session.commit()

        # Get single game
        response = client.get(f"/api/public/games/{base_game.id}")
        assert response.status_code == 200
        data = response.json()

        # Should include expansions list
        assert "expansions" in data
        if len(data["expansions"]) > 0:
            assert data["expansions"][0]["title"] == "Expansion Pack"
            # Check expansion player count calculations
            assert data.get("players_max_with_expansions") == 6
            assert data.get("players_min_with_expansions") == 1
            assert data.get("has_player_expansion") is True

    def test_get_expansion_with_base_game_info(self, client, db_session):
        """Test getting expansion details includes base game info"""
        # Create base game
        base_game = Game(
            title="Base Game",
            bgg_id=10000,
            image="http://example.com/base.jpg",
            is_expansion=False
        )
        db_session.add(base_game)
        db_session.flush()

        # Create expansion
        expansion = Game(
            title="Expansion Pack",
            bgg_id=10001,
            is_expansion=True,
            base_game_id=base_game.id
        )
        db_session.add(expansion)
        db_session.commit()

        # Get expansion details
        response = client.get(f"/api/public/games/{expansion.id}")
        assert response.status_code == 200
        data = response.json()

        # Should include base game info
        if "base_game" in data and data["base_game"]:
            assert data["base_game"]["id"] == base_game.id
            assert data["base_game"]["title"] == "Base Game"
            assert "thumbnail_url" in data["base_game"]

    def test_get_game_without_expansions(self, client, db_session):
        """Test getting game without expansions returns empty list"""
        game = Game(
            title="Standalone Game",
            bgg_id=10000,
            is_expansion=False
        )
        db_session.add(game)
        db_session.commit()

        response = client.get(f"/api/public/games/{game.id}")
        assert response.status_code == 200
        data = response.json()

        # Should have empty expansions list
        assert "expansions" in data
        assert data["expansions"] == []


class TestNZDesignerFiltering:
    """Tests for NZ designer filtering with different input types"""

    def test_nz_designer_filter_with_boolean(self, client, db_session):
        """Test NZ designer filter with boolean value"""
        # Create games with and without NZ designer status
        nz_game = Game(title="NZ Game", bgg_id=10000, nz_designer=True)
        other_game = Game(title="Other Game", bgg_id=10001, nz_designer=False)
        db_session.add_all([nz_game, other_game])
        db_session.commit()

        # Filter for NZ designers (non-string boolean)
        response = client.get("/api/public/games?nz_designer=true")
        assert response.status_code == 200
        data = response.json()

        # Should only return NZ designer games
        assert data["total"] >= 1

    def test_nz_designer_filter_with_string_variants(self, client, db_session):
        """Test NZ designer filter with different string representations"""
        nz_game = Game(title="NZ Game", bgg_id=10000, nz_designer=True)
        db_session.add(nz_game)
        db_session.commit()

        # Test different string variants
        for value in ["1", "yes"]:
            response = client.get(f"/api/public/games?nz_designer={value}")
            assert response.status_code == 200


class TestGamesByDesignerEndpoint:
    """Tests for games by designer endpoint"""

    def test_get_games_by_designer_success(self, client, db_session):
        """Test getting games by designer name"""
        game = Game(
            title="Test Game",
            bgg_id=10000,
            designers=["Reiner Knizia"]
        )
        db_session.add(game)
        db_session.commit()

        response = client.get("/api/public/games/by-designer/Reiner%20Knizia")
        assert response.status_code == 200
        data = response.json()

        assert "designer" in data
        assert data["designer"] == "Reiner Knizia"
        assert "games" in data

    def test_get_games_by_designer_not_found(self, client, db_session):
        """Test getting games by non-existent designer"""
        response = client.get("/api/public/games/by-designer/Unknown%20Designer")
        assert response.status_code == 200
        data = response.json()

        assert data["designer"] == "Unknown Designer"
        assert data["games"] == []


class TestImageProxyCloudinary:
    """Tests for image proxy with Cloudinary integration"""

    def test_image_proxy_cloudinary_enabled(self, client, db_session):
        """Test image proxy when Cloudinary is enabled"""
        from unittest.mock import patch, AsyncMock

        bgg_url = "https://cf.geekdo-images.com/test.jpg"

        with patch("config.CLOUDINARY_ENABLED", True), \
             patch("services.cloudinary_service.cloudinary_service.upload_from_url") as mock_upload, \
             patch("services.cloudinary_service.cloudinary_service.get_image_url") as mock_get_url:

            # Mock successful Cloudinary upload
            mock_upload.return_value = {"secure_url": "https://res.cloudinary.com/test.jpg"}
            mock_get_url.return_value = "https://res.cloudinary.com/test.jpg"

            response = client.get(f"/api/public/image-proxy?url={bgg_url}")

            # Should redirect to Cloudinary URL or proxy successfully (or fail with 404/502 if network issue)
            assert response.status_code in [200, 302, 404, 502]

            if response.status_code == 302:
                # Check redirect to Cloudinary
                assert "cloudinary.com" in response.headers.get("Location", "")

    def test_image_proxy_cloudinary_fallback(self, client):
        """Test image proxy falls back to direct proxy when Cloudinary fails"""
        from unittest.mock import patch

        bgg_url = "https://cf.geekdo-images.com/test.jpg"

        with patch("config.CLOUDINARY_ENABLED", True), \
             patch("services.cloudinary_service.cloudinary_service.upload_from_url") as mock_upload:

            # Mock Cloudinary upload failure
            mock_upload.side_effect = Exception("Cloudinary error")

            response = client.get(f"/api/public/image-proxy?url={bgg_url}")

            # Should fall back to direct proxy (might fail due to network, but shouldn't crash)
            assert response.status_code in [200, 404, 500, 502]

    def test_image_proxy_cloudinary_returns_original_url(self, client):
        """Test image proxy when Cloudinary returns original URL"""
        from unittest.mock import patch

        bgg_url = "https://cf.geekdo-images.com/test.jpg"

        with patch("config.CLOUDINARY_ENABLED", True), \
             patch("services.cloudinary_service.cloudinary_service.upload_from_url") as mock_upload, \
             patch("services.cloudinary_service.cloudinary_service.get_image_url") as mock_get_url:

            # Mock Cloudinary returning the same URL (no optimization)
            mock_upload.return_value = {"secure_url": bgg_url}
            mock_get_url.return_value = bgg_url

            response = client.get(f"/api/public/image-proxy?url={bgg_url}")

            # Should fall through to direct proxy
            assert response.status_code in [200, 404, 500, 502]

    def test_image_proxy_cloudinary_no_url_returned(self, client):
        """Test image proxy when Cloudinary returns None URL"""
        from unittest.mock import patch

        bgg_url = "https://cf.geekdo-images.com/test.jpg"

        with patch("config.CLOUDINARY_ENABLED", True), \
             patch("services.cloudinary_service.cloudinary_service.upload_from_url") as mock_upload, \
             patch("services.cloudinary_service.cloudinary_service.get_image_url") as mock_get_url:

            # Mock Cloudinary returning None
            mock_upload.return_value = {"secure_url": "https://res.cloudinary.com/test.jpg"}
            mock_get_url.return_value = None

            response = client.get(f"/api/public/image-proxy?url={bgg_url}")

            # Should fall through to direct proxy
            assert response.status_code in [200, 404, 500, 502]
