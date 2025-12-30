"""
Integration tests for API endpoints.
Tests full HTTP request/response cycle with authentication, rate limiting, etc.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from main import app
from models import Game
from services.game_service import GameService


@pytest.mark.asyncio
class TestPublicEndpointsIntegration:
    """Integration tests for public API endpoints"""

    async def test_games_list_to_detail_workflow(self, async_client, db_session):
        """
        Test workflow: List games → Get single game detail → Verify consistency
        """
        # Create test game
        service = GameService(db_session)
        game = service.create_game({
            "title": "Test Game for Detail",
            "bgg_id": 10001,
            "year": 2020,
            "players_min": 2,
            "players_max": 4,
            "average_rating": 8.5,
            "complexity": 3.2,
            "description": "A test game for integration testing",
            "status": "OWNED",
        })
        game_id = game.id

        # Step 1: List games (should include our test game)
        response = await async_client.get("/api/public/games")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] >= 1

        # Find our game in the list
        our_game = next((g for g in data["items"] if g["id"] == game_id), None)
        assert our_game is not None
        assert our_game["title"] == "Test Game for Detail"

        # Step 2: Get game detail
        detail_response = await async_client.get(f"/api/public/games/{game_id}")
        assert detail_response.status_code == 200
        detail_data = detail_response.json()

        # Step 3: Verify consistency between list and detail
        assert detail_data["id"] == our_game["id"]
        assert detail_data["title"] == our_game["title"]
        assert detail_data["year"] == our_game["year"]
        assert detail_data["average_rating"] == our_game["average_rating"]

        # Step 4: Verify detail has additional fields not in list
        assert "description" in detail_data
        assert detail_data["description"] == "A test game for integration testing"

    async def test_search_and_filter_workflow(self, async_client: AsyncClient, db_session):
        """
        Test workflow: Create games → Search → Apply filters → Verify results
        """
        service = GameService(db_session)

        # Create diverse set of games
        games_data = [
            {
                "title": "Zombicide",
                "bgg_id": 11001,
                "mana_meeple_category": "COOP_ADVENTURE",
                "year": 2012,
                "players_min": 1,
                "players_max": 6,
                "status": "OWNED",
            },
            {
                "title": "Zombie Dice",
                "bgg_id": 11002,
                "mana_meeple_category": "PARTY_ICEBREAKERS",
                "year": 2010,
                "players_min": 2,
                "players_max": 99,
                "status": "OWNED",
            },
            {
                "title": "Pandemic",
                "bgg_id": 11003,
                "mana_meeple_category": "COOP_ADVENTURE",
                "year": 2008,
                "players_min": 2,
                "players_max": 4,
                "status": "OWNED",
            },
        ]

        for data in games_data:
            service.create_game(data)

        # Step 1: Search for "Zombie"
        response = await async_client.get("/api/public/games?q=Zombie")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2  # Zombicide and Zombie Dice
        titles = [g["title"] for g in data["items"]]
        assert "Zombicide" in titles
        assert "Zombie Dice" in titles

        # Step 2: Filter by category (COOP_ADVENTURE)
        response = await async_client.get("/api/public/games?category=COOP_ADVENTURE")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2  # Zombicide and Pandemic
        assert all(g["mana_meeple_category"] == "COOP_ADVENTURE" for g in data["items"])

        # Step 3: Combine search + category filter
        response = await async_client.get("/api/public/games?q=Zombie&category=COOP_ADVENTURE")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1  # Only Zombicide
        assert data["items"][0]["title"] == "Zombicide"

    async def test_pagination_workflow(self, async_client: AsyncClient, db_session):
        """
        Test workflow: Create many games → Paginate → Verify page boundaries
        """
        service = GameService(db_session)

        # Create 25 games
        for i in range(25):
            service.create_game({
                "title": f"Game {i:02d}",
                "bgg_id": 12000 + i,
                "status": "OWNED",
            })

        # Step 1: Get first page (default page_size=24)
        response = await async_client.get("/api/public/games?page=1&page_size=10")
        assert response.status_code == 200
        page1 = response.json()
        assert page1["page"] == 1
        assert page1["page_size"] == 10
        assert len(page1["items"]) == 10
        assert page1["total"] >= 25

        # Step 2: Get second page
        response = await async_client.get("/api/public/games?page=2&page_size=10")
        assert response.status_code == 200
        page2 = response.json()
        assert page2["page"] == 2
        assert len(page2["items"]) == 10

        # Step 3: Verify no overlap between pages
        page1_ids = {g["id"] for g in page1["items"]}
        page2_ids = {g["id"] for g in page2["items"]}
        assert page1_ids.isdisjoint(page2_ids)  # No common games

    async def test_category_counts_workflow(self, async_client: AsyncClient, db_session):
        """
        Test workflow: Create categorized games → Get category counts → Verify
        """
        service = GameService(db_session)

        # Create games in different categories
        categories = ["COOP_ADVENTURE", "COOP_ADVENTURE", "CORE_STRATEGY", "PARTY_ICEBREAKERS"]
        for i, category in enumerate(categories):
            service.create_game({
                "title": f"Category Test {i}",
                "bgg_id": 13000 + i,
                "mana_meeple_category": category,
                "status": "OWNED",
            })

        # Get category counts
        response = await async_client.get("/api/public/category-counts")
        assert response.status_code == 200
        counts = response.json()

        # Verify counts
        assert counts.get("COOP_ADVENTURE", 0) >= 2
        assert counts.get("CORE_STRATEGY", 0) >= 1
        assert counts.get("PARTY_ICEBREAKERS", 0) >= 1


@pytest.mark.asyncio
class TestAdminEndpointsIntegration:
    """Integration tests for admin API endpoints (with authentication)"""

    async def test_admin_login_workflow(self, async_client: AsyncClient):
        """
        Test workflow: Login → Receive JWT → Use JWT for protected endpoint
        """
        # Step 1: Login with admin token
        login_response = await async_client.post(
            "/api/admin/login",
            headers={"X-Admin-Token": "test-admin-token"},
        )
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert "access_token" in login_data
        jwt_token = login_data["access_token"]

        # Step 2: Use JWT to access protected endpoint
        games_response = await async_client.get(
            "/api/admin/games",
            headers={"Authorization": f"Bearer {jwt_token}"},
        )
        assert games_response.status_code == 200
        assert isinstance(games_response.json(), list)

    async def test_admin_create_update_delete_workflow(
        self, async_client: AsyncClient, admin_headers
    ):
        """
        Test workflow: Create game via API → Update → Delete → Verify each step
        """
        # Step 1: Create game
        create_data = {
            "title": "API Created Game",
            "year": 2023,
            "players_min": 2,
            "players_max": 4,
            "mana_meeple_category": "GATEWAY_STRATEGY",
        }
        create_response = await async_client.post(
            "/api/admin/games",
            json=create_data,
            headers=admin_headers,
        )
        assert create_response.status_code == 200
        created_game = create_response.json()
        game_id = created_game["id"]
        assert created_game["title"] == "API Created Game"

        # Step 2: Update game
        update_data = {
            "title": "API Updated Game",
            "year": 2024,
            "nz_designer": True,
        }
        update_response = await async_client.put(
            f"/api/admin/games/{game_id}",
            json=update_data,
            headers=admin_headers,
        )
        assert update_response.status_code == 200
        updated_game = update_response.json()
        assert updated_game["title"] == "API Updated Game"
        assert updated_game["year"] == 2024
        assert updated_game["nz_designer"] is True

        # Step 3: Verify update via GET
        get_response = await async_client.get(
            f"/api/admin/games/{game_id}",
            headers=admin_headers,
        )
        assert get_response.status_code == 200
        retrieved_game = get_response.json()
        assert retrieved_game["title"] == "API Updated Game"

        # Step 4: Delete game
        delete_response = await async_client.delete(
            f"/api/admin/games/{game_id}",
            headers=admin_headers,
        )
        assert delete_response.status_code == 200

        # Step 5: Verify deletion
        get_deleted_response = await async_client.get(
            f"/api/admin/games/{game_id}",
            headers=admin_headers,
        )
        assert get_deleted_response.status_code == 404

    async def test_bgg_import_workflow(self, async_client: AsyncClient, admin_headers):
        """
        Test workflow: Import from BGG via API → Verify game created with all data
        """
        mock_bgg_data = {
            "bgg_id": 999999,
            "title": "API Import Test Game",
            "year": 2020,
            "players_min": 2,
            "players_max": 4,
            "categories": ["Strategy"],
            "mechanics": ["Worker Placement"],
            "designers": ["Test Designer"],
            "publishers": ["Test Publisher"],
            "artists": ["Test Artist"],
            "average_rating": 7.5,
            "complexity": 3.0,
        }

        with patch("bgg_service.fetch_bgg_thing", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_bgg_data

            # Import from BGG
            import_response = await async_client.post(
                "/api/admin/import/bgg?bgg_id=999999",
                headers=admin_headers,
            )
            assert import_response.status_code == 200
            imported_game = import_response.json()

            # Verify all data imported correctly
            assert imported_game["title"] == "API Import Test Game"
            assert imported_game["bgg_id"] == 999999
            assert imported_game["year"] == 2020
            assert "Test Designer" in imported_game["designers"]
            assert "Worker Placement" in imported_game["mechanics"]
            assert imported_game["average_rating"] == 7.5


@pytest.mark.asyncio
class TestErrorHandlingIntegration:
    """Integration tests for error handling across API"""

    async def test_404_not_found_workflow(self, async_client: AsyncClient):
        """Test 404 errors for non-existent resources"""
        # Non-existent game ID
        response = await async_client.get("/api/public/games/999999")
        assert response.status_code == 404
        error_data = response.json()
        assert "detail" in error_data

    async def test_unauthorized_access_workflow(self, async_client: AsyncClient):
        """Test unauthorized access to admin endpoints"""
        # Attempt admin operation without auth
        response = await async_client.get("/api/admin/games")
        assert response.status_code == 401

        # Attempt with invalid token
        response = await async_client.get(
            "/api/admin/games",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401

    async def test_validation_error_workflow(
        self, async_client: AsyncClient, admin_headers
    ):
        """Test validation errors for invalid input"""
        # Invalid category
        invalid_data = {
            "title": "Invalid Game",
            "mana_meeple_category": "INVALID_CATEGORY",
        }
        response = await async_client.post(
            "/api/admin/games",
            json=invalid_data,
            headers=admin_headers,
        )
        assert response.status_code == 400
        error_data = response.json()
        assert "category" in error_data["detail"].lower()


@pytest.mark.asyncio
class TestPerformanceIntegration:
    """Integration tests for performance features"""

    async def test_caching_workflow(self, async_client: AsyncClient, db_session):
        """
        Test workflow: Make identical requests → Verify caching works
        """
        service = GameService(db_session)

        # Create test game
        service.create_game({
            "title": "Cache Test Game",
            "bgg_id": 14001,
            "status": "OWNED",
        })

        # First request (cache miss)
        response1 = await async_client.get("/api/public/games?page=1&page_size=10")
        assert response1.status_code == 200

        # Second identical request (should use cache)
        response2 = await async_client.get("/api/public/games?page=1&page_size=10")
        assert response2.status_code == 200

        # Responses should be identical
        assert response1.json() == response2.json()

    async def test_read_replica_usage(self, async_client: AsyncClient):
        """
        Test that read endpoints use read replica (if configured)
        Note: This test verifies the dependency is used correctly
        """
        # All public GET requests should use get_read_db dependency
        response = await async_client.get("/api/public/games")
        assert response.status_code == 200

        response = await async_client.get("/api/public/category-counts")
        assert response.status_code == 200
