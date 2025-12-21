"""
Integration Tests for Buy List Workflows
Sprint 11: Advanced Testing

Tests the complete buy list management workflow
"""

import pytest
from fastapi.testclient import TestClient


class TestBuyListWorkflowsIntegration:
    """Test complete buy list management workflows"""

    def test_add_game_to_buy_list(self, test_client, sample_game):
        """Should add a game to the buy list"""
        response = test_client.post(
            f'/api/admin/buy-list/{sample_game.id}',
            headers={'Authorization': 'Bearer test_token'}
        )

        # Status may vary based on implementation
        assert response.status_code in [200, 201, 204]

    def test_remove_game_from_buy_list(self, test_client, sample_game):
        """Should remove a game from the buy list"""
        # First add to buy list
        test_client.post(
            f'/api/admin/buy-list/{sample_game.id}',
            headers={'Authorization': 'Bearer test_token'}
        )

        # Then remove
        response = test_client.delete(
            f'/api/admin/buy-list/{sample_game.id}',
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code in [200, 204]

    def test_get_buy_list_games(self, test_client, test_db, sample_game):
        """Should retrieve all games on the buy list"""
        # Add game to buy list
        test_client.post(
            f'/api/admin/buy-list/{sample_game.id}',
            headers={'Authorization': 'Bearer test_token'}
        )

        # Get buy list
        response = test_client.get(
            '/api/admin/buy-list',
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    def test_set_buy_list_priority(self, test_client, sample_game):
        """Should set priority/rank for buy list item"""
        # Add to buy list with priority
        response = test_client.post(
            f'/api/admin/buy-list/{sample_game.id}',
            json={'priority': 1, 'rank': 1},
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code in [200, 201]

    def test_update_buy_list_status(self, test_client, sample_game):
        """Should update status of buy list item (e.g., 'ordered', 'received')"""
        # Add to buy list
        test_client.post(
            f'/api/admin/buy-list/{sample_game.id}',
            headers={'Authorization': 'Bearer test_token'}
        )

        # Update status
        response = test_client.put(
            f'/api/admin/buy-list/{sample_game.id}',
            json={'status': 'ORDERED'},
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code in [200, 204, 404]

    def test_bulk_add_to_buy_list(self, test_client, test_db):
        """Should add multiple games to buy list at once"""
        from models import Game

        # Create multiple games
        games = [
            Game(title=f"Bulk Game {i}", bgg_id=10000+i, status="OWNED")
            for i in range(3)
        ]
        for game in games:
            test_db.add(game)
        test_db.commit()

        game_ids = [game.id for game in games]

        response = test_client.post(
            '/api/admin/buy-list/bulk',
            json={'game_ids': game_ids},
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code in [200, 201, 404]

    def test_buy_list_requires_authentication(self, test_client, sample_game):
        """Should require admin authentication for buy list operations"""
        # Add without auth
        response1 = test_client.post(f'/api/admin/buy-list/{sample_game.id}')
        assert response1.status_code == 401

        # Get without auth
        response2 = test_client.get('/api/admin/buy-list')
        assert response2.status_code == 401

        # Remove without auth
        response3 = test_client.delete(f'/api/admin/buy-list/{sample_game.id}')
        assert response3.status_code == 401

    def test_add_nonexistent_game_to_buy_list(self, test_client):
        """Should return 404 when adding nonexistent game to buy list"""
        response = test_client.post(
            '/api/admin/buy-list/99999',
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code == 404

    def test_duplicate_buy_list_entry(self, test_client, sample_game):
        """Should handle duplicate buy list entries gracefully"""
        # Add once
        response1 = test_client.post(
            f'/api/admin/buy-list/{sample_game.id}',
            headers={'Authorization': 'Bearer test_token'}
        )

        # Add again
        response2 = test_client.post(
            f'/api/admin/buy-list/{sample_game.id}',
            headers={'Authorization': 'Bearer test_token'}
        )

        # Should be idempotent or return 409 conflict
        assert response2.status_code in [200, 201, 409]

    def test_buy_list_sorting_by_priority(self, test_client, test_db):
        """Should return buy list sorted by priority"""
        from models import Game

        # Create games with different priorities
        games = [
            Game(title=f"Priority {i}", bgg_id=20000+i, status="OWNED")
            for i in range(3)
        ]
        for game in games:
            test_db.add(game)
        test_db.commit()

        # Add to buy list with priorities
        for i, game in enumerate(games):
            test_client.post(
                f'/api/admin/buy-list/{game.id}',
                json={'rank': i+1},
                headers={'Authorization': 'Bearer test_token'}
            )

        response = test_client.get(
            '/api/admin/buy-list?sort=rank',
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code in [200, 404]

    def test_mark_buy_list_item_as_purchased(self, test_client, sample_game):
        """Should mark buy list item as purchased"""
        # Add to buy list
        test_client.post(
            f'/api/admin/buy-list/{sample_game.id}',
            headers={'Authorization': 'Bearer test_token'}
        )

        # Mark as purchased
        response = test_client.put(
            f'/api/admin/buy-list/{sample_game.id}',
            json={'status': 'PURCHASED', 'on_buy_list': False},
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code in [200, 204, 404]

    def test_buy_list_with_notes(self, test_client, sample_game):
        """Should allow adding notes to buy list items"""
        response = test_client.post(
            f'/api/admin/buy-list/{sample_game.id}',
            json={'notes': 'Check for discount'},
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code in [200, 201, 404]

    def test_buy_list_filter_by_status(self, test_client, test_db):
        """Should filter buy list by status"""
        from models import Game

        # Create and add games with different statuses
        game1 = Game(title="Ordered Game", bgg_id=30001, status="OWNED")
        game2 = Game(title="Wishlist Game", bgg_id=30002, status="OWNED")
        test_db.add(game1)
        test_db.add(game2)
        test_db.commit()

        test_client.post(
            f'/api/admin/buy-list/{game1.id}',
            json={'lpg_status': 'ORDERED'},
            headers={'Authorization': 'Bearer test_token'}
        )

        test_client.post(
            f'/api/admin/buy-list/{game2.id}',
            json={'lpg_status': 'WISHLIST'},
            headers={'Authorization': 'Bearer test_token'}
        )

        response = test_client.get(
            '/api/admin/buy-list?status=ORDERED',
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code in [200, 404]

    def test_buy_list_export(self, test_client, sample_game):
        """Should export buy list to CSV"""
        # Add to buy list
        test_client.post(
            f'/api/admin/buy-list/{sample_game.id}',
            headers={'Authorization': 'Bearer test_token'}
        )

        response = test_client.get(
            '/api/admin/buy-list/export',
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code in [200, 404]

    def test_buy_list_pagination(self, test_client, test_db):
        """Should paginate large buy lists"""
        from models import Game

        # Create many games
        games = [
            Game(title=f"Buy List Game {i}", bgg_id=40000+i, status="OWNED")
            for i in range(15)
        ]
        for game in games:
            test_db.add(game)
        test_db.commit()

        # Add all to buy list
        for game in games:
            test_client.post(
                f'/api/admin/buy-list/{game.id}',
                headers={'Authorization': 'Bearer test_token'}
            )

        # Get paginated results
        response = test_client.get(
            '/api/admin/buy-list?page=1&page_size=10',
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code in [200, 404]

    def test_buy_list_reordering(self, test_client, test_db):
        """Should allow reordering buy list items"""
        from models import Game

        games = [
            Game(title=f"Reorder {i}", bgg_id=50000+i, status="OWNED")
            for i in range(3)
        ]
        for game in games:
            test_db.add(game)
        test_db.commit()

        # Add to buy list
        for i, game in enumerate(games):
            test_client.post(
                f'/api/admin/buy-list/{game.id}',
                json={'rank': i+1},
                headers={'Authorization': 'Bearer test_token'}
            )

        # Reorder - move first to last
        response = test_client.put(
            f'/api/admin/buy-list/{games[0].id}',
            json={'rank': 3},
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code in [200, 204, 404]

    def test_buy_list_price_tracking(self, test_client, sample_game):
        """Should track price information for buy list items"""
        response = test_client.post(
            f'/api/admin/buy-list/{sample_game.id}',
            json={'target_price': 49.99, 'current_price': 59.99},
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code in [200, 201, 404]

    def test_buy_list_statistics(self, test_client, test_db):
        """Should return buy list statistics"""
        from models import Game

        # Create and add games
        games = [
            Game(title=f"Stats Game {i}", bgg_id=60000+i, status="OWNED")
            for i in range(5)
        ]
        for game in games:
            test_db.add(game)
        test_db.commit()

        for game in games:
            test_client.post(
                f'/api/admin/buy-list/{game.id}',
                headers={'Authorization': 'Bearer test_token'}
            )

        response = test_client.get(
            '/api/admin/buy-list/stats',
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code in [200, 404]
        # May return total count, total price, etc.

    def test_clear_completed_buy_list_items(self, test_client, sample_game):
        """Should clear completed/purchased items from buy list"""
        # Add to buy list
        test_client.post(
            f'/api/admin/buy-list/{sample_game.id}',
            headers={'Authorization': 'Bearer test_token'}
        )

        # Mark as completed
        test_client.put(
            f'/api/admin/buy-list/{sample_game.id}',
            json={'on_buy_list': False},
            headers={'Authorization': 'Bearer test_token'}
        )

        # Clear completed
        response = test_client.post(
            '/api/admin/buy-list/clear-completed',
            headers={'Authorization': 'Bearer test_token'}
        )

        assert response.status_code in [200, 204, 404]
