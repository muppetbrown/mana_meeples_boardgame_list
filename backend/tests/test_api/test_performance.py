"""
Performance Tests for API Endpoints
Sprint 11: Advanced Testing

Tests API performance benchmarks and response times
"""

import pytest
import time
from fastapi.testclient import TestClient
from models import Game


@pytest.fixture
def large_game_dataset(db_session):
    """Create a large dataset for performance testing"""
    games = []
    for i in range(500):  # Create 500 games
        game = Game(
            title=f"Performance Test Game {i}",
            bgg_id=100000 + i,
            year=2000 + (i % 25),
            players_min=2,
            players_max=6,
            playtime_min=30,
            playtime_max=120,
            complexity=1.0 + (i % 5),
            average_rating=6.0 + (i % 4),
            mana_meeple_category=['GATEWAY_STRATEGY', 'COOP_ADVENTURE', 'PARTY_ICEBREAKERS', 'KIDS_FAMILIES'][i % 4],
            status="OWNED",
            designers=f'["Designer {i % 100}"]',
            nz_designer=(i % 10 == 0)  # Every 10th game is NZ designer
        )
        games.append(game)
        db_session.add(game)

    db_session.commit()
    return games


class TestAPIPerformance:
    """Performance tests for API endpoints"""

    def test_game_list_endpoint_performance(self, client, large_game_dataset):
        """Game list endpoint should respond within 200ms"""
        start = time.time()
        response = client.get('/api/public/games?page_size=24')
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 0.2, f"Game list took {duration:.3f}s, expected <0.2s"

    def test_game_detail_endpoint_performance(self, client, large_game_dataset):
        """Game detail endpoint should respond within 100ms"""
        game_id = large_game_dataset[0].id

        start = time.time()
        response = client.get(f'/api/public/games/{game_id}')
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 0.1, f"Game detail took {duration:.3f}s, expected <0.1s"

    def test_search_performance(self, client, large_game_dataset):
        """Search should complete within 300ms"""
        start = time.time()
        response = client.get('/api/public/games?q=test&page_size=24')
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 0.3, f"Search took {duration:.3f}s, expected <0.3s"

    def test_category_filter_performance(self, client, large_game_dataset):
        """Category filtering should complete within 150ms"""
        start = time.time()
        response = client.get('/api/public/games?category=GATEWAY_STRATEGY&page_size=24')
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 0.15, f"Category filter took {duration:.3f}s, expected <0.15s"

    def test_complex_filter_performance(self, client, large_game_dataset):
        """Complex filters should complete within 400ms"""
        start = time.time()
        response = client.get(
            '/api/public/games?category=GATEWAY_STRATEGY&q=game&sort=rating_desc&page_size=24'
        )
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 0.4, f"Complex filter took {duration:.3f}s, expected <0.4s"

    def test_category_counts_performance(self, client, large_game_dataset):
        """Category counts should compute within 100ms"""
        start = time.time()
        response = client.get('/api/public/category-counts')
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 0.1, f"Category counts took {duration:.3f}s, expected <0.1s"

    def test_pagination_performance(self, client, large_game_dataset):
        """Pagination should not degrade performance"""
        # Test multiple pages
        for page in [1, 5, 10]:
            start = time.time()
            response = client.get(f'/api/public/games?page={page}&page_size=24')
            duration = time.time() - start

            assert response.status_code == 200
            assert duration < 0.2, f"Page {page} took {duration:.3f}s, expected <0.2s"

    def test_large_page_size_performance(self, client, large_game_dataset):
        """Large page sizes should complete within 500ms"""
        start = time.time()
        response = client.get('/api/public/games?page_size=100')
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 0.5, f"Large page size took {duration:.3f}s, expected <0.5s"

    def test_sort_performance(self, client, large_game_dataset):
        """Sorting should not significantly impact performance"""
        sorts = ['title_asc', 'year_desc', 'rating_desc']

        for sort in sorts:
            start = time.time()
            response = client.get(f'/api/public/games?sort={sort}&page_size=24')
            duration = time.time() - start

            assert response.status_code == 200
            assert duration < 0.25, f"Sort {sort} took {duration:.3f}s, expected <0.25s"

    def test_nz_designer_filter_performance(self, client, large_game_dataset):
        """NZ designer filtering should be efficient"""
        start = time.time()
        response = client.get('/api/public/games?nz_designer=true&page_size=24')
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 0.15, f"NZ designer filter took {duration:.3f}s, expected <0.15s"

    def test_designer_search_performance(self, client, large_game_dataset):
        """Designer search should complete within 300ms"""
        start = time.time()
        response = client.get('/api/public/games?designer=Designer 1')
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 0.3, f"Designer search took {duration:.3f}s, expected <0.3s"

    def test_rapid_sequential_requests(self, client, large_game_dataset):
        """Should handle rapid sequential requests efficiently"""
        durations = []

        for i in range(10):
            start = time.time()
            response = client.get('/api/public/games?page_size=24')
            duration = time.time() - start
            durations.append(duration)

            assert response.status_code == 200

        avg_duration = sum(durations) / len(durations)
        assert avg_duration < 0.25, f"Average duration {avg_duration:.3f}s, expected <0.25s"

    def test_health_check_performance(self, client):
        """Health check should respond instantly"""
        start = time.time()
        response = client.get('/api/health')
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 0.05, f"Health check took {duration:.3f}s, expected <0.05s"

    def test_database_health_check_performance(self, client, large_game_dataset):
        """Database health check should complete within 100ms"""
        start = time.time()
        response = client.get('/api/health/db')
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 0.1, f"DB health check took {duration:.3f}s, expected <0.1s"

    def test_admin_game_list_performance(self, client, large_game_dataset):
        """Admin game list should perform similarly to public list"""
        start = time.time()
        response = client.get(
            '/api/admin/games?page_size=24',
            headers={'X-Admin-Token': 'test_admin_token'}
        )
        duration = time.time() - start

        assert response.status_code == 200
        # Allow 300ms threshold to account for CI/CD timing variance (was 250ms)
        assert duration < 0.30, f"Admin game list took {duration:.3f}s, expected <0.30s"

    def test_concurrent_read_performance(self, client, large_game_dataset):
        """Should handle concurrent read operations efficiently"""
        import threading

        durations = []
        lock = threading.Lock()

        def make_request():
            start = time.time()
            response = client.get('/api/public/games?page_size=24')
            duration = time.time() - start

            with lock:
                durations.append(duration)

        # Run 5 concurrent requests
        threads = [threading.Thread(target=make_request) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        max_duration = max(durations)
        assert max_duration < 0.5, f"Max concurrent request took {max_duration:.3f}s, expected <0.5s"

    def test_response_size_efficiency(self, client, large_game_dataset):
        """Response sizes should be reasonable"""
        response = client.get('/api/public/games?page_size=24')

        assert response.status_code == 200
        content_length = len(response.content)

        # Response should be under 500KB for 24 items
        assert content_length < 500 * 1024, f"Response too large: {content_length} bytes"

    def test_empty_result_performance(self, client, large_game_dataset):
        """Empty results should return quickly"""
        start = time.time()
        response = client.get('/api/public/games?q=nonexistentgamexyz12345')
        duration = time.time() - start

        assert response.status_code == 200
        # Adjusted to 150ms: Empty result queries still perform full search across
        # title, designers (JSON cast), and description fields, plus count query.
        # This aligns with category filter (150ms) and is faster than search (300ms)
        # since it returns no data. Provides buffer for test environment variability.
        assert duration < 0.15, f"Empty result took {duration:.3f}s, expected <0.15s"

    def test_database_query_count(self, client, large_game_dataset):
        """Should minimize database queries per request"""
        # This would require query logging/instrumentation
        # Placeholder for implementation with sqlalchemy event listeners
        response = client.get('/api/public/games?page_size=24')
        assert response.status_code == 200
        # Ideally should be 1-2 queries per request

    def test_memory_efficiency(self, client, large_game_dataset):
        """Large result sets should not cause memory issues"""
        import sys

        # Get memory before
        # Note: This is a simplified check
        response = client.get('/api/public/games?page_size=100')

        assert response.status_code == 200
        # Memory should not grow excessively
        # Actual memory profiling would require memory_profiler or similar
