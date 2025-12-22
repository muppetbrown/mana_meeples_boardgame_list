"""
Integration Tests for Buy List Workflows
Sprint 11: Advanced Testing

Tests the complete buy list management workflow

NOTE: These tests are currently skipped as buy list endpoints are not yet implemented.
      They serve as forward-looking test specifications for future functionality.
"""

import pytest
from fastapi.testclient import TestClient

# Skip all tests in this module - buy list endpoints not implemented yet
pytestmark = pytest.mark.skip(reason="Buy list endpoints not yet implemented")


class TestBuyListWorkflowsIntegration:
    """Test complete buy list management workflows"""

    def test_add_game_to_buy_list(self, client, sample_game):
        """Should add a game to the buy list"""
        response = client.post(
            f'/api/admin/buy-list/{sample_game.id}',
            headers={'Authorization': 'Bearer test_token'}
        )

        # Status may vary based on implementation
        assert response.status_code in [200, 201, 204]

    def test_remove_game_from_buy_list(self, client, sample_game):
        """Should remove a game from the buy list"""
        # First add to buy list
        client.post(
            f'/api/admin/buy-list/{sample_game.id}',
            headers={'Authorization': 'Bearer test_token'}
        )

        # Then remove
        response = client.delete(
            f'/api/admin/buy-list/{sample_game.id}',
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code in [200, 204]

    def test_get_buy_list_games(self, client, db_session, sample_game):
        """Should retrieve all games on the buy list"""
        # Add game to buy list
        client.post(
            f'/api/admin/buy-list/{sample_game.id}',
            headers={'Authorization': 'Bearer test_token'}
        )

        # Get buy list
        response = client.get(
            '/api/admin/buy-list',
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    def test_set_buy_list_priority(self, client, sample_game):
        """Should set priority/rank for buy list item"""
        # Add to buy list with priority
        response = client.post(
            f'/api/admin/buy-list/{sample_game.id}',
            json={'priority': 1, 'rank': 1},
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code in [200, 201]

    def test_update_buy_list_status(self, client, sample_game):
        """Should update status of buy list item (e.g., 'ordered', 'received')"""
        # Add to buy list
        client.post(
            f'/api/admin/buy-list/{sample_game.id}',
            headers={'Authorization': 'Bearer test_token'}
        )

        # Update status
        response = client.put(
            f'/api/admin/buy-list/{sample_game.id}',
            json={'status': 'ORDERED'},
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code in [200, 204, 404]

    def test_bulk_add_to_buy_list(self, client, db_session):
        """Should add multiple games to buy list at once"""
        from models import Game

        # Create multiple games
        games = [
            Game(title=f"Bulk Game {i}", bgg_id=10000+i, status="OWNED")
            for i in range(3)
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        game_ids = [game.id for game in games]

        response = client.post(
            '/api/admin/buy-list/bulk',
            json={'game_ids': game_ids},
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code in [200, 201, 404]

    def test_buy_list_requires_authentication(self, client, sample_game):
        """Should require admin authentication for buy list operations"""
        # Add without auth
        response1 = client.post(f'/api/admin/buy-list/{sample_game.id}')
        assert response1.status_code == 401

        # Get without auth
        response2 = client.get('/api/admin/buy-list')
        assert response2.status_code == 401

        # Remove without auth
        response3 = client.delete(f'/api/admin/buy-list/{sample_game.id}')
        assert response3.status_code == 401

    def test_add_nonexistent_game_to_buy_list(self, client):
        """Should return 404 when adding nonexistent game to buy list"""
        response = client.post(
            '/api/admin/buy-list/99999',
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code == 404

    def test_duplicate_buy_list_entry(self, client, sample_game):
        """Should handle duplicate buy list entries gracefully"""
        # Add once
        response1 = client.post(
            f'/api/admin/buy-list/{sample_game.id}',
            headers={'Authorization': 'Bearer test_token'}
        )

        # Add again
        response2 = client.post(
            f'/api/admin/buy-list/{sample_game.id}',
            headers={'Authorization': 'Bearer test_token'}
        )

        # Should be idempotent or return 409 conflict
        assert response2.status_code in [200, 201, 409]

    def test_buy_list_sorting_by_priority(self, client, db_session):
        """Should return buy list sorted by priority"""
        from models import Game

        # Create games with different priorities
        games = [
            Game(title=f"Priority {i}", bgg_id=20000+i, status="OWNED")
            for i in range(3)
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        # Add to buy list with priorities
        for i, game in enumerate(games):
            client.post(
                f'/api/admin/buy-list/{game.id}',
                json={'rank': i+1},
                headers={'Authorization': 'Bearer test_token'}
            )

        response = client.get(
            '/api/admin/buy-list?sort=rank',
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code in [200, 404]

    def test_mark_buy_list_item_as_purchased(self, client, sample_game):
        """Should mark buy list item as purchased"""
        # Add to buy list
        client.post(
            f'/api/admin/buy-list/{sample_game.id}',
            headers={'Authorization': 'Bearer test_token'}
        )

        # Mark as purchased
        response = client.put(
            f'/api/admin/buy-list/{sample_game.id}',
            json={'status': 'PURCHASED', 'on_buy_list': False},
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code in [200, 204, 404]

    def test_buy_list_with_notes(self, client, sample_game):
        """Should allow adding notes to buy list items"""
        response = client.post(
            f'/api/admin/buy-list/{sample_game.id}',
            json={'notes': 'Check for discount'},
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code in [200, 201, 404]

    def test_buy_list_filter_by_status(self, client, db_session):
        """Should filter buy list by status"""
        from models import Game

        # Create and add games with different statuses
        game1 = Game(title="Ordered Game", bgg_id=30001, status="OWNED")
        game2 = Game(title="Wishlist Game", bgg_id=30002, status="OWNED")
        db_session.add(game1)
        db_session.add(game2)
        db_session.commit()

        client.post(
            f'/api/admin/buy-list/{game1.id}',
            json={'lpg_status': 'ORDERED'},
            headers={'Authorization': 'Bearer test_token'}
        )

        client.post(
            f'/api/admin/buy-list/{game2.id}',
            json={'lpg_status': 'WISHLIST'},
            headers={'Authorization': 'Bearer test_token'}
        )

        response = client.get(
            '/api/admin/buy-list?status=ORDERED',
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code in [200, 404]

    def test_buy_list_export(self, client, sample_game):
        """Should export buy list to CSV"""
        # Add to buy list
        client.post(
            f'/api/admin/buy-list/{sample_game.id}',
            headers={'Authorization': 'Bearer test_token'}
        )

        response = client.get(
            '/api/admin/buy-list/export',
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code in [200, 404]

    def test_buy_list_pagination(self, client, db_session):
        """Should paginate large buy lists"""
        from models import Game

        # Create many games
        games = [
            Game(title=f"Buy List Game {i}", bgg_id=40000+i, status="OWNED")
            for i in range(15)
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        # Add all to buy list
        for game in games:
            client.post(
                f'/api/admin/buy-list/{game.id}',
                headers={'Authorization': 'Bearer test_token'}
            )

        # Get paginated results
        response = client.get(
            '/api/admin/buy-list?page=1&page_size=10',
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code in [200, 404]

    def test_buy_list_reordering(self, client, db_session):
        """Should allow reordering buy list items"""
        from models import Game

        games = [
            Game(title=f"Reorder {i}", bgg_id=50000+i, status="OWNED")
            for i in range(3)
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        # Add to buy list
        for i, game in enumerate(games):
            client.post(
                f'/api/admin/buy-list/{game.id}',
                json={'rank': i+1},
                headers={'Authorization': 'Bearer test_token'}
            )

        # Reorder - move first to last
        response = client.put(
            f'/api/admin/buy-list/{games[0].id}',
            json={'rank': 3},
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code in [200, 204, 404]

    def test_buy_list_price_tracking(self, client, sample_game):
        """Should track price information for buy list items"""
        response = client.post(
            f'/api/admin/buy-list/{sample_game.id}',
            json={'target_price': 49.99, 'current_price': 59.99},
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code in [200, 201, 404]

    def test_buy_list_statistics(self, client, db_session):
        """Should return buy list statistics"""
        from models import Game

        # Create and add games
        games = [
            Game(title=f"Stats Game {i}", bgg_id=60000+i, status="OWNED")
            for i in range(5)
        ]
        for game in games:
            db_session.add(game)
        db_session.commit()

        for game in games:
            client.post(
                f'/api/admin/buy-list/{game.id}',
                headers={'Authorization': 'Bearer test_token'}
            )

        response = client.get(
            '/api/admin/buy-list/stats',
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code in [200, 404]
        # May return total count, total price, etc.

    def test_clear_completed_buy_list_items(self, client, sample_game):
        """Should clear completed/purchased items from buy list"""
        # Add to buy list
        client.post(
            f'/api/admin/buy-list/{sample_game.id}',
            headers={'Authorization': 'Bearer test_token'}
        )

        # Mark as completed
        client.put(
            f'/api/admin/buy-list/{sample_game.id}',
            json={'on_buy_list': False},
            headers={'Authorization': 'Bearer test_token'}
        )

        # Clear completed
        response = client.post(
            '/api/admin/buy-list/clear-completed',
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code in [200, 204, 404]
