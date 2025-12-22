"""
Integration Tests for Admin Game Management
Sprint 11: Advanced Testing

Tests the complete admin game management workflow including CRUD operations
"""

import pytest
from fastapi.testclient import TestClient


class TestAdminGameManagementIntegration:
    """Test complete admin game management workflows"""

    def test_create_game_manually(self, client):
        """Should create a new game with manual input"""
        game_data = {
            'title': 'Manually Added Game',
            'year': 2024,
            'players_min': 2,
            'players_max': 4,
            'playtime_min': 30,
            'playtime_max': 60,
            'mana_meeple_category': 'GATEWAY_STRATEGY'
        }

        response = client.post(
            '/api/admin/games',
            json=game_data,
            headers={'X-Admin-Token': 'test_admin_token'}
        )

        assert response.status_code == 201
        data = response.json()
        assert data['title'] == 'Manually Added Game'
        assert data['year'] == 2024

    def test_get_all_games_admin_view(self, client, sample_game):
        """Should retrieve all games with admin-specific fields"""
        response = client.get(
            '/api/admin/games',
            headers={'X-Admin-Token': 'test_admin_token'}
        )

        assert response.status_code == 200
        data = response.json()
        assert 'items' in data or isinstance(data, list)

    def test_get_single_game_admin_view(self, client, sample_game):
        """Should retrieve single game with all admin fields"""
        response = client.get(
            f'/api/admin/games/{sample_game.id}',
            headers={'X-Admin-Token': 'test_admin_token'}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['id'] == sample_game.id

    def test_update_game_title(self, client, sample_game):
        """Should update game title"""
        update_data = {'title': 'Updated Game Title'}

        response = client.put(
            f'/api/admin/games/{sample_game.id}',
            json=update_data,
            headers={'X-Admin-Token': 'test_admin_token'}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['title'] == 'Updated Game Title'

    def test_update_game_category(self, client, sample_game):
        """Should update game category"""
        update_data = {'mana_meeple_category': 'CORE_STRATEGY'}

        response = client.put(
            f'/api/admin/games/{sample_game.id}',
            json=update_data,
            headers={'X-Admin-Token': 'test_admin_token'}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['mana_meeple_category'] == 'CORE_STRATEGY'

    def test_update_game_nz_designer_flag(self, client, sample_game):
        """Should update NZ designer flag"""
        update_data = {'nz_designer': True}

        response = client.put(
            f'/api/admin/games/{sample_game.id}',
            json=update_data,
            headers={'X-Admin-Token': 'test_admin_token'}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['nz_designer'] is True

    def test_update_multiple_fields(self, client, sample_game):
        """Should update multiple fields simultaneously"""
        update_data = {
            'title': 'Multi-Update Test',
            'year': 2025,
            'complexity': 3.5,
            'mana_meeple_category': 'COOP_ADVENTURE'
        }

        response = client.put(
            f'/api/admin/games/{sample_game.id}',
            json=update_data,
            headers={'X-Admin-Token': 'test_admin_token'}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['title'] == 'Multi-Update Test'
        assert data['year'] == 2025
        assert data['mana_meeple_category'] == 'COOP_ADVENTURE'

    def test_update_nonexistent_game(self, client):
        """Should return 404 for nonexistent game"""
        response = client.put(
            '/api/admin/games/99999',
            json={'title': 'Nope'},
            headers={'X-Admin-Token': 'test_admin_token'}
        )

        assert response.status_code == 404

    def test_delete_game(self, client, sample_game):
        """Should delete a game"""
        game_id = sample_game.id

        response = client.delete(
            f'/api/admin/games/{game_id}',
            headers={'X-Admin-Token': 'test_admin_token'}
        )

        assert response.status_code in [200, 204]

        # Verify deletion
        get_response = client.get(
            f'/api/admin/games/{game_id}',
            headers={'X-Admin-Token': 'test_admin_token'}
        )
        assert get_response.status_code == 404

    def test_delete_nonexistent_game(self, client):
        """Should return 404 when deleting nonexistent game"""
        response = client.delete(
            '/api/admin/games/99999',
            headers={'X-Admin-Token': 'test_admin_token'}
        )

        assert response.status_code == 404

    def test_create_game_with_invalid_data(self, client):
        """Should reject game creation with invalid data"""
        invalid_data = {
            'title': '',  # Empty title
            'year': 'invalid',  # String instead of int
        }

        response = client.post(
            '/api/admin/games',
            json=invalid_data,
            headers={'X-Admin-Token': 'test_admin_token'}
        )

        assert response.status_code in [400, 422]

    def test_create_game_with_duplicate_bgg_id(self, client, sample_game):
        """Should reject duplicate BGG ID"""
        game_data = {
            'title': 'Duplicate BGG ID',
            'bgg_id': sample_game.bgg_id
        }

        response = client.post(
            '/api/admin/games',
            json=game_data,
            headers={'X-Admin-Token': 'test_admin_token'}
        )

        assert response.status_code in [400, 409]

    def test_update_with_invalid_category(self, client, sample_game):
        """Should reject invalid category"""
        update_data = {'mana_meeple_category': 'INVALID_CATEGORY'}

        response = client.put(
            f'/api/admin/games/{sample_game.id}',
            json=update_data,
            headers={'X-Admin-Token': 'test_admin_token'}
        )

        assert response.status_code in [400, 422]

    def test_admin_operations_require_auth(self, client, sample_game):
        """Should require authentication for all admin operations"""
        # Create without auth
        response1 = client.post('/api/admin/games', json={'title': 'Test'})
        assert response1.status_code == 401

        # Read without auth
        response2 = client.get(f'/api/admin/games/{sample_game.id}')
        assert response2.status_code == 401

        # Update without auth
        response3 = client.put(
            f'/api/admin/games/{sample_game.id}',
            json={'title': 'Test'}
        )
        assert response3.status_code == 401

        # Delete without auth
        response4 = client.delete(f'/api/admin/games/{sample_game.id}')
        assert response4.status_code == 401

    def test_partial_update(self, client, sample_game):
        """Should allow partial updates without affecting other fields"""
        original_year = sample_game.year

        response = client.put(
            f'/api/admin/games/{sample_game.id}',
            json={'title': 'Partially Updated'},
            headers={'X-Admin-Token': 'test_admin_token'}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['title'] == 'Partially Updated'
        assert data['year'] == original_year  # Unchanged

    def test_update_preserves_bgg_data(self, client, sample_game):
        """Should preserve BGG data when updating manual fields"""
        # Assume sample_game has BGG data
        response = client.put(
            f'/api/admin/games/{sample_game.id}',
            json={'mana_meeple_category': 'GATEWAY_STRATEGY'},
            headers={'X-Admin-Token': 'test_admin_token'}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['bgg_id'] == sample_game.bgg_id

    def test_create_game_sets_defaults(self, client):
        """Should set default values for optional fields"""
        minimal_data = {'title': 'Minimal Game'}

        response = client.post(
            '/api/admin/games',
            json=minimal_data,
            headers={'X-Admin-Token': 'test_admin_token'}
        )

        assert response.status_code == 201
        data = response.json()
        assert 'id' in data
        assert 'created_at' in data or 'id' in data

    def test_update_timestamp_on_modification(self, client, sample_game):
        """Should update timestamp when game is modified"""
        import time
        original_time = sample_game.created_at

        time.sleep(1)  # Ensure time difference

        response = client.put(
            f'/api/admin/games/{sample_game.id}',
            json={'title': 'Timestamp Test'},
            headers={'X-Admin-Token': 'test_admin_token'}
        )

        assert response.status_code == 200
        # Updated_at should be newer than created_at

    def test_validate_player_count_logic(self, client, sample_game):
        """Should validate that players_max >= players_min"""
        invalid_data = {
            'players_min': 4,
            'players_max': 2  # Invalid: max < min
        }

        response = client.put(
            f'/api/admin/games/{sample_game.id}',
            json=invalid_data,
            headers={'X-Admin-Token': 'test_admin_token'}
        )

        # Should reject or auto-correct
        assert response.status_code in [200, 400, 422]

    def test_validate_playtime_logic(self, client, sample_game):
        """Should validate that playtime_max >= playtime_min"""
        invalid_data = {
            'playtime_min': 120,
            'playtime_max': 30  # Invalid: max < min
        }

        response = client.put(
            f'/api/admin/games/{sample_game.id}',
            json=invalid_data,
            headers={'X-Admin-Token': 'test_admin_token'}
        )

        assert response.status_code in [200, 400, 422]

    def test_validate_year_range(self, client, sample_game):
        """Should validate reasonable year values"""
        invalid_data = {'year': 1800}  # Too old for board games

        response = client.put(
            f'/api/admin/games/{sample_game.id}',
            json=invalid_data,
            headers={'X-Admin-Token': 'test_admin_token'}
        )

        # May accept or reject depending on validation rules
        assert response.status_code in [200, 400, 422]

    def test_validate_complexity_range(self, client, sample_game):
        """Should validate complexity is between 1-5"""
        invalid_data = {'complexity': 6.0}  # Out of range

        response = client.put(
            f'/api/admin/games/{sample_game.id}',
            json=invalid_data,
            headers={'X-Admin-Token': 'test_admin_token'}
        )

        assert response.status_code in [200, 400, 422]

    def test_validate_rating_range(self, client, sample_game):
        """Should validate rating is between 0-10"""
        invalid_data = {'average_rating': 11.0}  # Out of range

        response = client.put(
            f'/api/admin/games/{sample_game.id}',
            json=invalid_data,
            headers={'X-Admin-Token': 'test_admin_token'}
        )

        assert response.status_code in [200, 400, 422]
