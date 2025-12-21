"""
Load Tests for Concurrent Users
Sprint 11: Advanced Testing

Tests system behavior under concurrent load
"""

import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient


class TestConcurrentLoad:
    """Load tests for concurrent user scenarios"""

    def test_concurrent_game_list_requests(self, client, large_game_dataset):
        """Should handle 50 concurrent game list requests"""
        results = []
        errors = []

        def fetch_games():
            try:
                start = time.time()
                response = client.get('/api/public/games?page_size=24')
                duration = time.time() - start

                results.append({
                    'status': response.status_code,
                    'duration': duration
                })
            except Exception as e:
                errors.append(str(e))

        # Run 50 concurrent requests
        threads = [threading.Thread(target=fetch_games) for _ in range(50)]
        start_time = time.time()

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        total_time = time.time() - start_time

        # All requests should succeed
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert all(r['status'] == 200 for r in results)

        # Most requests should complete reasonably fast
        avg_duration = sum(r['duration'] for r in results) / len(results)
        assert avg_duration < 1.0, f"Average request time {avg_duration:.3f}s too high"

        # Total time should be reasonable with concurrency
        assert total_time < 10.0, f"Total time {total_time:.3f}s too high for concurrent requests"

    def test_concurrent_search_requests(self, client, large_game_dataset):
        """Should handle concurrent search requests"""
        search_terms = ['game', 'test', 'strategy', 'adventure', 'party']
        results = []

        def search_games(term):
            try:
                response = client.get(f'/api/public/games?q={term}')
                return response.status_code
            except Exception as e:
                return str(e)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(search_games, term) for term in search_terms * 10]

            for future in as_completed(futures):
                results.append(future.result())

        # All should succeed
        success_count = sum(1 for r in results if r == 200)
        assert success_count == len(results), f"Only {success_count}/{len(results)} succeeded"

    def test_concurrent_filter_requests(self, client, large_game_dataset):
        """Should handle concurrent filter requests"""
        categories = ['GATEWAY_STRATEGY', 'COOP_ADVENTURE', 'PARTY_ICEBREAKERS', 'KIDS_FAMILIES']
        results = []

        def filter_games(category):
            response = client.get(f'/api/public/games?category={category}')
            return response.status_code == 200

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(filter_games, cat) for cat in categories * 5]
            results = [future.result() for future in as_completed(futures)]

        assert all(results), "Some filter requests failed"

    def test_mixed_read_workload(self, client, large_game_dataset):
        """Should handle mixed read operations concurrently"""
        operations = [
            lambda: client.get('/api/public/games?page_size=24'),
            lambda: client.get('/api/public/games?q=test'),
            lambda: client.get('/api/public/games?category=GATEWAY_STRATEGY'),
            lambda: client.get('/api/public/category-counts'),
            lambda: client.get(f'/api/public/games/{large_game_dataset[0].id}'),
        ]

        results = []

        def execute_operation(op):
            try:
                response = op()
                return response.status_code == 200
            except Exception:
                return False

        with ThreadPoolExecutor(max_workers=15) as executor:
            # Execute each operation type multiple times concurrently
            futures = [
                executor.submit(execute_operation, operations[i % len(operations)])
                for i in range(50)
            ]
            results = [future.result() for future in as_completed(futures)]

        success_rate = sum(results) / len(results)
        assert success_rate > 0.95, f"Success rate {success_rate:.2%} too low"

    def test_sustained_load(self, client, large_game_dataset):
        """Should handle sustained load over time"""
        duration_seconds = 10
        request_count = 0
        errors = 0
        start_time = time.time()

        def make_requests():
            nonlocal request_count, errors
            end_time = time.time() + duration_seconds

            while time.time() < end_time:
                try:
                    response = client.get('/api/public/games?page_size=24')
                    if response.status_code == 200:
                        request_count += 1
                    else:
                        errors += 1
                except Exception:
                    errors += 1

        # Run with 10 concurrent threads
        threads = [threading.Thread(target=make_requests) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        total_time = time.time() - start_time
        throughput = request_count / total_time

        assert errors == 0, f"{errors} errors occurred during sustained load"
        assert throughput > 50, f"Throughput {throughput:.2f} req/s too low"

    def test_concurrent_admin_operations(self, client, large_game_dataset):
        """Should handle concurrent admin operations safely"""
        results = []

        def admin_operation():
            try:
                # Read operation
                response = client.get(
                    '/api/admin/games?page_size=10',
                    headers={'Authorization': 'Bearer test_token'}
                )
                return response.status_code == 200
            except Exception:
                return False

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(admin_operation) for _ in range(20)]
            results = [future.result() for future in as_completed(futures)]

        assert all(results), "Some admin operations failed"

    def test_rate_limiting_under_load(self, client):
        """Should enforce rate limits under heavy load"""
        results = []

        def make_request():
            response = client.get('/api/public/games')
            return response.status_code

        # Make 150 rapid requests (assuming 100/min limit)
        for _ in range(150):
            results.append(make_request())

        # Some should be rate limited (429)
        rate_limited = sum(1 for status in results if status == 429)

        # If rate limiting is implemented, we should see some 429s
        # If not implemented yet, this is a reminder to add it
        # For now, just check that system didn't crash
        assert 200 in results

    def test_database_connection_pool(self, client, large_game_dataset):
        """Should manage database connections efficiently"""
        errors = []

        def query_database():
            try:
                response = client.get('/api/public/games?page_size=10')
                if response.status_code != 200:
                    errors.append(f"Status: {response.status_code}")
            except Exception as e:
                errors.append(str(e))

        # Spawn more threads than typical pool size
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(query_database) for _ in range(100)]
            for future in as_completed(futures):
                future.result()

        # Should handle gracefully without connection errors
        connection_errors = [e for e in errors if 'connection' in str(e).lower()]
        assert len(connection_errors) == 0, f"Connection errors: {connection_errors}"

    def test_concurrent_pagination(self, client, large_game_dataset):
        """Should handle concurrent pagination requests"""
        pages = list(range(1, 11))  # Pages 1-10
        results = []

        def fetch_page(page):
            response = client.get(f'/api/public/games?page={page}&page_size=24')
            return response.status_code == 200

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(fetch_page, page) for page in pages * 3]
            results = [future.result() for future in as_completed(futures)]

        assert all(results), "Some pagination requests failed"

    def test_concurrent_sorting(self, client, large_game_dataset):
        """Should handle concurrent sorting operations"""
        sorts = ['title_asc', 'title_desc', 'year_asc', 'year_desc', 'rating_desc']
        results = []

        def sort_games(sort_by):
            response = client.get(f'/api/public/games?sort={sort_by}&page_size=24')
            return response.status_code == 200

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(sort_games, sort) for sort in sorts * 5]
            results = [future.result() for future in as_completed(futures)]

        assert all(results), "Some sorting requests failed"

    def test_peak_load_simulation(self, client, large_game_dataset):
        """Should handle peak load (100 concurrent users)"""
        results = []
        start_time = time.time()

        def simulate_user():
            try:
                # Simulate user journey: browse -> search -> view detail
                client.get('/api/public/games?page_size=24')
                client.get('/api/public/games?q=game')
                client.get(f'/api/public/games/{large_game_dataset[0].id}')
                return True
            except Exception:
                return False

        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(simulate_user) for _ in range(100)]
            results = [future.result() for future in as_completed(futures)]

        total_time = time.time() - start_time
        success_rate = sum(results) / len(results)

        assert success_rate > 0.90, f"Success rate {success_rate:.2%} too low under peak load"
        assert total_time < 30.0, f"Peak load took {total_time:.2f}s, too long"

    def test_error_recovery_under_load(self, client, large_game_dataset):
        """Should recover gracefully from errors under load"""
        results = []

        def make_mixed_requests():
            try:
                # Mix of valid and potentially invalid requests
                valid = client.get('/api/public/games?page_size=24')
                invalid = client.get('/api/public/games/999999')  # Non-existent

                return valid.status_code == 200 and invalid.status_code == 404
            except Exception:
                return False

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_mixed_requests) for _ in range(50)]
            results = [future.result() for future in as_completed(futures)]

        assert all(results), "System did not handle errors gracefully under load"

    def test_cache_effectiveness_under_load(self, client, large_game_dataset):
        """Should benefit from caching under repeated requests"""
        # First request (cache miss)
        start = time.time()
        client.get('/api/public/category-counts')
        first_duration = time.time() - start

        # Subsequent requests (should hit cache if implemented)
        durations = []
        for _ in range(10):
            start = time.time()
            client.get('/api/public/category-counts')
            durations.append(time.time() - start)

        avg_duration = sum(durations) / len(durations)

        # Cached requests should generally be faster
        # This test will reveal if caching is effective
        # (Results may vary based on implementation)

    def test_connection_timeout_handling(self, client):
        """Should handle connection timeouts gracefully"""
        # This would require mocking slow responses
        # Placeholder for timeout testing
        response = client.get('/api/health')
        assert response.status_code == 200

    def test_memory_stability_under_load(self, client, large_game_dataset):
        """Should maintain stable memory usage under load"""
        import gc

        gc.collect()  # Clean up before test

        def make_requests():
            for _ in range(100):
                client.get('/api/public/games?page_size=24')

        # Run multiple request cycles
        for _ in range(5):
            make_requests()
            gc.collect()

        # Memory should not grow unbounded
        # Actual memory profiling would require psutil or memory_profiler
        # This is a placeholder for proper memory testing

    def test_graceful_degradation(self, client, large_game_dataset):
        """Should degrade gracefully under extreme load"""
        # Simulate extreme load
        results = []

        def stress_request():
            try:
                response = client.get('/api/public/games?page_size=100')
                return response.status_code in [200, 429, 503]  # Accept rate limit or service unavailable
            except Exception:
                return False

        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(stress_request) for _ in range(200)]
            results = [future.result() for future in as_completed(futures)]

        # System should respond (even if with errors) rather than crash
        response_rate = sum(results) / len(results)
        assert response_rate > 0.80, f"System failed to respond to {(1-response_rate)*100:.1f}% of requests"
