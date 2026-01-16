"""
Comprehensive Tests for Sleeves API Endpoints
Sprint: Test Coverage Improvement

Tests all sleeve management endpoints including:
- Generating sleeve shopping lists
- Retrieving sleeve requirements for games
- Filtering sleeved vs unsleeved games
- Grouping sleeves by size
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from models import Game, Sleeve


class TestGenerateSleeveShoppingList:
    """Test POST /api/admin/sleeves/shopping-list endpoint"""

    def test_empty_game_list(self, client, admin_headers):
        """Should return empty list when no games provided"""
        response = client.post(
            "/api/admin/sleeves/shopping-list",
            headers=admin_headers,
            json={"game_ids": []},
        )

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_games_with_no_sleeves(self, client, db_session, admin_headers):
        """Should return empty list when games have no sleeve data"""
        # Create game without sleeves
        game = Game(title="Test Game", bgg_id=12345)
        db_session.add(game)
        db_session.commit()

        response = client.post(
            "/api/admin/sleeves/shopping-list",
            headers=admin_headers,
            json={"game_ids": [game.id]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_single_game_with_sleeves(self, client, db_session, admin_headers):
        """Should generate shopping list for single game"""
        # Create game
        game = Game(title="Test Game", bgg_id=12345, is_sleeved=False)
        db_session.add(game)
        db_session.flush()

        # Add sleeve requirements
        sleeve1 = Sleeve(
            game_id=game.id, card_name="Standard", width_mm=63, height_mm=88, quantity=50
        )
        sleeve2 = Sleeve(
            game_id=game.id, card_name="Mini", width_mm=45, height_mm=68, quantity=30
        )
        db_session.add_all([sleeve1, sleeve2])
        db_session.commit()

        response = client.post(
            "/api/admin/sleeves/shopping-list",
            headers=admin_headers,
            json={"game_ids": [game.id]},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Verify first sleeve size
        item = next(i for i in data if i["width_mm"] == 45)
        assert item["height_mm"] == 68
        assert item["total_quantity"] == 30
        assert item["games_count"] == 1
        assert "Test Game" in item["game_names"]

    def test_multiple_games_same_sleeve_size(self, client, db_session, admin_headers):
        """Should group sleeves with same size from different games"""
        # Create two games
        game1 = Game(title="Game 1", bgg_id=111, is_sleeved=False)
        game2 = Game(title="Game 2", bgg_id=222, is_sleeved=False)
        db_session.add_all([game1, game2])
        db_session.flush()

        # Add same size sleeves to both games
        sleeve1 = Sleeve(
            game_id=game1.id, width_mm=63, height_mm=88, quantity=50
        )
        sleeve2 = Sleeve(
            game_id=game2.id, width_mm=63, height_mm=88, quantity=40
        )
        db_session.add_all([sleeve1, sleeve2])
        db_session.commit()

        response = client.post(
            "/api/admin/sleeves/shopping-list",
            headers=admin_headers,
            json={"game_ids": [game1.id, game2.id]},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        # Should combine quantities
        item = data[0]
        assert item["width_mm"] == 63
        assert item["height_mm"] == 88
        assert item["total_quantity"] == 90  # 50 + 40
        assert item["games_count"] == 2
        assert "Game 1" in item["game_names"]
        assert "Game 2" in item["game_names"]

    def test_excludes_already_sleeved_games(self, client, db_session, admin_headers):
        """Should exclude games that are already sleeved"""
        # Create sleeved game
        sleeved_game = Game(title="Sleeved Game", bgg_id=111, is_sleeved=True)
        # Create unsleeved game
        unsleeved_game = Game(title="Unsleeved Game", bgg_id=222, is_sleeved=False)
        db_session.add_all([sleeved_game, unsleeved_game])
        db_session.flush()

        # Add sleeves to both
        sleeve1 = Sleeve(
            game_id=sleeved_game.id, width_mm=63, height_mm=88, quantity=50
        )
        sleeve2 = Sleeve(
            game_id=unsleeved_game.id, width_mm=63, height_mm=88, quantity=40
        )
        db_session.add_all([sleeve1, sleeve2])
        db_session.commit()

        response = client.post(
            "/api/admin/sleeves/shopping-list",
            headers=admin_headers,
            json={"game_ids": [sleeved_game.id, unsleeved_game.id]},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        # Should only include unsleeved game
        item = data[0]
        assert item["total_quantity"] == 40
        assert item["games_count"] == 1
        assert "Unsleeved Game" in item["game_names"]
        assert "Sleeved Game" not in item["game_names"]

    def test_sorting_by_size(self, client, db_session, admin_headers):
        """Should sort results by width then height"""
        # Create game
        game = Game(title="Test Game", bgg_id=12345, is_sleeved=False)
        db_session.add(game)
        db_session.flush()

        # Add sleeves in random order
        sleeve1 = Sleeve(game_id=game.id, width_mm=70, height_mm=120, quantity=10)
        sleeve2 = Sleeve(game_id=game.id, width_mm=63, height_mm=88, quantity=20)
        sleeve3 = Sleeve(game_id=game.id, width_mm=63, height_mm=100, quantity=15)
        db_session.add_all([sleeve1, sleeve2, sleeve3])
        db_session.commit()

        response = client.post(
            "/api/admin/sleeves/shopping-list",
            headers=admin_headers,
            json={"game_ids": [game.id]},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

        # Verify sorting
        assert data[0]["width_mm"] == 63
        assert data[0]["height_mm"] == 88
        assert data[1]["width_mm"] == 63
        assert data[1]["height_mm"] == 100
        assert data[2]["width_mm"] == 70
        assert data[2]["height_mm"] == 120

    def test_includes_games_with_null_is_sleeved(self, client, db_session, admin_headers):
        """Should include games where is_sleeved is None"""
        # Create game with is_sleeved = None
        game = Game(title="Test Game", bgg_id=12345, is_sleeved=None)
        db_session.add(game)
        db_session.flush()

        # Add sleeve
        sleeve = Sleeve(game_id=game.id, width_mm=63, height_mm=88, quantity=50)
        db_session.add(sleeve)
        db_session.commit()

        response = client.post(
            "/api/admin/sleeves/shopping-list",
            headers=admin_headers,
            json={"game_ids": [game.id]},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["total_quantity"] == 50

    def test_requires_auth(self, client, csrf_headers):
        """Should require admin authentication"""
        response = client.post(
            "/api/admin/sleeves/shopping-list",
            json={"game_ids": [1]},
            headers=csrf_headers
        )

        assert response.status_code == 401


class TestGetGameSleeves:
    """Test GET /api/admin/sleeves/game/{game_id} endpoint"""

    def test_get_sleeves_for_game(self, client, db_session, admin_headers):
        """Should return all sleeves for a game"""
        # Create game
        game = Game(title="Test Game", bgg_id=12345)
        db_session.add(game)
        db_session.flush()

        # Add multiple sleeve types
        sleeve1 = Sleeve(
            game_id=game.id,
            card_name="Standard Cards",
            width_mm=63,
            height_mm=88,
            quantity=50,
        )
        sleeve2 = Sleeve(
            game_id=game.id,
            card_name="Mini Cards",
            width_mm=45,
            height_mm=68,
            quantity=30,
        )
        db_session.add_all([sleeve1, sleeve2])
        db_session.commit()

        response = client.get(
            f"/api/admin/sleeves/game/{game.id}", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Verify sleeve data
        standard = next(s for s in data if s["card_name"] == "Standard Cards")
        assert standard["width_mm"] == 63
        assert standard["height_mm"] == 88
        assert standard["quantity"] == 50

        mini = next(s for s in data if s["card_name"] == "Mini Cards")
        assert mini["width_mm"] == 45
        assert mini["height_mm"] == 68
        assert mini["quantity"] == 30

    def test_get_sleeves_for_game_with_no_sleeves(self, client, db_session, admin_headers):
        """Should return empty list when game has no sleeves"""
        # Create game without sleeves
        game = Game(title="Test Game", bgg_id=12345)
        db_session.add(game)
        db_session.commit()

        response = client.get(
            f"/api/admin/sleeves/game/{game.id}", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_get_sleeves_for_nonexistent_game(self, client, admin_headers):
        """Should return empty list for nonexistent game"""
        response = client.get("/api/admin/sleeves/game/99999", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_requires_auth(self, client):
        """Should require admin authentication"""
        response = client.get("/api/admin/sleeves/game/1")

        assert response.status_code == 401


class TestSleeveShoppingListEdgeCases:
    """Test edge cases for sleeve shopping list generation"""

    def test_multiple_sleeve_types_per_game(self, client, db_session, admin_headers):
        """Should handle games with multiple sleeve types correctly"""
        # Create game
        game = Game(title="Complex Game", bgg_id=12345, is_sleeved=False)
        db_session.add(game)
        db_session.flush()

        # Add multiple sleeve types
        sleeves = [
            Sleeve(game_id=game.id, card_name=f"Type {i}", width_mm=60 + i * 5, height_mm=85 + i * 5, quantity=10 + i * 5)
            for i in range(5)
        ]
        db_session.add_all(sleeves)
        db_session.commit()

        response = client.post(
            "/api/admin/sleeves/shopping-list",
            headers=admin_headers,
            json={"game_ids": [game.id]},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

    def test_variations_grouped_count(self, client, db_session, admin_headers):
        """Should correctly count variations grouped"""
        # Create game
        game = Game(title="Test Game", bgg_id=12345, is_sleeved=False)
        db_session.add(game)
        db_session.flush()

        # Add sleeves with exact same dimensions
        sleeve1 = Sleeve(game_id=game.id, width_mm=63, height_mm=88, quantity=50)
        sleeve2 = Sleeve(game_id=game.id, width_mm=63, height_mm=88, quantity=30)
        db_session.add_all([sleeve1, sleeve2])
        db_session.commit()

        response = client.post(
            "/api/admin/sleeves/shopping-list",
            headers=admin_headers,
            json={"game_ids": [game.id]},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        # Should show 1 variation (same size)
        item = data[0]
        assert item["variations_grouped"] == 1
        assert item["total_quantity"] == 80  # 50 + 30

    def test_mixed_sleeved_and_unsleeved_games(self, client, db_session, admin_headers):
        """Should correctly handle mix of sleeved and unsleeved games"""
        # Create multiple games with different sleeve states
        games = [
            Game(title=f"Game {i}", bgg_id=12340 + i, is_sleeved=(i % 2 == 0))
            for i in range(4)
        ]
        db_session.add_all(games)
        db_session.flush()

        # Add same size sleeves to all games
        for game in games:
            sleeve = Sleeve(game_id=game.id, width_mm=63, height_mm=88, quantity=25)
            db_session.add(sleeve)
        db_session.commit()

        response = client.post(
            "/api/admin/sleeves/shopping-list",
            headers=admin_headers,
            json={"game_ids": [g.id for g in games]},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        # Should only count unsleeved games (games 1 and 3, where i % 2 != 0)
        item = data[0]
        assert item["total_quantity"] == 50  # 2 unsleeved games * 25
        assert item["games_count"] == 2


class TestUpdateSleeveStatus:
    """Test PATCH /api/admin/sleeves/sleeve/{sleeve_id} endpoint"""

    def test_update_sleeve_to_sleeved(self, client, db_session, admin_headers):
        """Should mark a sleeve as sleeved"""
        # Create game and sleeve
        game = Game(title="Test Game", bgg_id=12345)
        db_session.add(game)
        db_session.flush()

        sleeve = Sleeve(
            game_id=game.id, card_name="Standard", width_mm=63, height_mm=88,
            quantity=50, is_sleeved=False
        )
        db_session.add(sleeve)
        db_session.commit()

        response = client.patch(
            f"/api/admin/sleeves/sleeve/{sleeve.id}",
            headers=admin_headers,
            json={"is_sleeved": True}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["sleeve_id"] == sleeve.id
        assert data["is_sleeved"] == True

        # Verify in database
        db_session.refresh(sleeve)
        assert sleeve.is_sleeved == True

    def test_update_sleeve_to_unsleeved(self, client, db_session, admin_headers):
        """Should mark a sleeved sleeve as unsleeved"""
        # Create game and already sleeved sleeve
        game = Game(title="Test Game", bgg_id=12345)
        db_session.add(game)
        db_session.flush()

        sleeve = Sleeve(
            game_id=game.id, card_name="Standard", width_mm=63, height_mm=88,
            quantity=50, is_sleeved=True
        )
        db_session.add(sleeve)
        db_session.commit()

        response = client.patch(
            f"/api/admin/sleeves/sleeve/{sleeve.id}",
            headers=admin_headers,
            json={"is_sleeved": False}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["is_sleeved"] == False

        # Verify in database
        db_session.refresh(sleeve)
        assert sleeve.is_sleeved == False

    def test_update_nonexistent_sleeve(self, client, admin_headers):
        """Should return 404 for nonexistent sleeve"""
        response = client.patch(
            "/api/admin/sleeves/sleeve/999999",
            headers=admin_headers,
            json={"is_sleeved": True}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_sleeve_requires_auth(self, client, csrf_headers):
        """Should require admin authentication"""
        response = client.patch(
            "/api/admin/sleeves/sleeve/1",
            headers=csrf_headers,
            json={"is_sleeved": True}
        )

        assert response.status_code == 401

    def test_update_sleeve_missing_is_sleeved(self, client, db_session, admin_headers):
        """Should fail when is_sleeved field is missing"""
        game = Game(title="Test Game", bgg_id=12345)
        db_session.add(game)
        db_session.flush()

        sleeve = Sleeve(
            game_id=game.id, card_name="Standard", width_mm=63, height_mm=88, quantity=50
        )
        db_session.add(sleeve)
        db_session.commit()

        response = client.patch(
            f"/api/admin/sleeves/sleeve/{sleeve.id}",
            headers=admin_headers,
            json={}
        )

        assert response.status_code == 422  # Validation error

    def test_update_sleeve_invalid_is_sleeved_type(self, client, db_session, admin_headers):
        """Should fail when is_sleeved is not a boolean-coercible value"""
        game = Game(title="Test Game", bgg_id=12345)
        db_session.add(game)
        db_session.flush()

        sleeve = Sleeve(
            game_id=game.id, card_name="Standard", width_mm=63, height_mm=88, quantity=50
        )
        db_session.add(sleeve)
        db_session.commit()

        # Note: Pydantic coerces "yes", "true", "1", etc. to True
        # We need a truly invalid value that can't be coerced
        response = client.patch(
            f"/api/admin/sleeves/sleeve/{sleeve.id}",
            headers=admin_headers,
            json={"is_sleeved": [1, 2, 3]}  # Array cannot be coerced to boolean
        )

        assert response.status_code == 422  # Validation error


class TestSleeveShoppingListWithIndividualSleeveStatus:
    """Test sleeve shopping list with individual sleeve is_sleeved status"""

    def test_excludes_individually_sleeved_sleeves(self, client, db_session, admin_headers):
        """Should exclude sleeve types marked as sleeved individually"""
        # Create unsleeved game
        game = Game(title="Test Game", bgg_id=12345, is_sleeved=False)
        db_session.add(game)
        db_session.flush()

        # Add two sleeves - one sleeved, one unsleeved
        sleeved_sleeve = Sleeve(
            game_id=game.id, card_name="Sleeved Type", width_mm=63, height_mm=88,
            quantity=50, is_sleeved=True
        )
        unsleeved_sleeve = Sleeve(
            game_id=game.id, card_name="Unsleeved Type", width_mm=45, height_mm=68,
            quantity=30, is_sleeved=False
        )
        db_session.add_all([sleeved_sleeve, unsleeved_sleeve])
        db_session.commit()

        response = client.post(
            "/api/admin/sleeves/shopping-list",
            headers=admin_headers,
            json={"game_ids": [game.id]},
        )

        assert response.status_code == 200
        data = response.json()

        # Should only include unsleeved sleeve
        assert len(data) == 1
        assert data[0]["width_mm"] == 45
        assert data[0]["height_mm"] == 68
        assert data[0]["total_quantity"] == 30

    def test_includes_sleeves_with_null_is_sleeved(self, client, db_session, admin_headers):
        """Should include sleeves where is_sleeved is None"""
        game = Game(title="Test Game", bgg_id=12345, is_sleeved=False)
        db_session.add(game)
        db_session.flush()

        sleeve = Sleeve(
            game_id=game.id, card_name="Standard", width_mm=63, height_mm=88,
            quantity=50, is_sleeved=None
        )
        db_session.add(sleeve)
        db_session.commit()

        response = client.post(
            "/api/admin/sleeves/shopping-list",
            headers=admin_headers,
            json={"game_ids": [game.id]},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["total_quantity"] == 50


class TestSleeveResponseFormat:
    """Test sleeve response format and fields"""

    def test_sleeve_response_includes_all_fields(self, client, db_session, admin_headers):
        """Should return all sleeve fields in response"""
        game = Game(title="Test Game", bgg_id=12345)
        db_session.add(game)
        db_session.flush()

        sleeve = Sleeve(
            game_id=game.id,
            card_name="Standard Cards",
            width_mm=63,
            height_mm=88,
            quantity=50,
            notes="Test notes",
            is_sleeved=True
        )
        db_session.add(sleeve)
        db_session.commit()

        response = client.get(
            f"/api/admin/sleeves/game/{game.id}", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        sleeve_data = data[0]
        assert "id" in sleeve_data
        assert "game_id" in sleeve_data
        assert sleeve_data["card_name"] == "Standard Cards"
        assert sleeve_data["width_mm"] == 63
        assert sleeve_data["height_mm"] == 88
        assert sleeve_data["quantity"] == 50
        assert sleeve_data["notes"] == "Test notes"
        assert sleeve_data["is_sleeved"] == True

    def test_sleeve_response_with_null_notes(self, client, db_session, admin_headers):
        """Should handle null notes correctly"""
        game = Game(title="Test Game", bgg_id=12345)
        db_session.add(game)
        db_session.flush()

        sleeve = Sleeve(
            game_id=game.id,
            card_name="Standard",
            width_mm=63,
            height_mm=88,
            quantity=50,
            notes=None
        )
        db_session.add(sleeve)
        db_session.commit()

        response = client.get(
            f"/api/admin/sleeves/game/{game.id}", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data[0]["notes"] is None

    def test_sleeve_response_is_sleeved_defaults_to_false(self, client, db_session, admin_headers):
        """Should default is_sleeved to False when null"""
        game = Game(title="Test Game", bgg_id=12345)
        db_session.add(game)
        db_session.flush()

        sleeve = Sleeve(
            game_id=game.id,
            width_mm=63,
            height_mm=88,
            quantity=50,
            is_sleeved=None
        )
        db_session.add(sleeve)
        db_session.commit()

        response = client.get(
            f"/api/admin/sleeves/game/{game.id}", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        # Should default to False in response
        assert data[0]["is_sleeved"] == False
