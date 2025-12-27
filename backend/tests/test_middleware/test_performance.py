"""
Unit tests for middleware/performance.py

Tests performance monitoring including LRU eviction and slow query tracking.
"""
import pytest
from middleware.performance import PerformanceMonitor


class TestPerformanceMonitor:
    """Test performance monitoring"""

    def test_record_request_basic(self):
        """Test basic request recording"""
        monitor = PerformanceMonitor()

        monitor.record_request("/api/test", "GET", 0.1, 200)

        stats = monitor.get_stats()
        assert stats["total_requests"] == 1
        assert stats["avg_response_time_ms"] == 100.0

    def test_get_stats_no_requests(self):
        """Test get_stats with no requests"""
        monitor = PerformanceMonitor()

        stats = monitor.get_stats()

        assert stats == {"message": "No requests recorded yet"}

    def test_lru_eviction_when_max_endpoints_reached(self):
        """Test LRU eviction when max endpoints is reached"""
        monitor = PerformanceMonitor()
        monitor.max_endpoints = 3  # Set low limit for testing

        # Add 3 endpoints
        monitor.record_request("/api/endpoint1", "GET", 0.1, 200)
        monitor.record_request("/api/endpoint2", "GET", 0.1, 200)
        monitor.record_request("/api/endpoint3", "GET", 0.1, 200)

        # Add 4th endpoint - should evict oldest
        monitor.record_request("/api/endpoint4", "GET", 0.1, 200)

        # Endpoint1 should be evicted
        assert len(monitor.endpoint_stats) == 3
        assert "GET /api/endpoint1" not in monitor.endpoint_stats
        assert "GET /api/endpoint4" in monitor.endpoint_stats

    def test_error_tracking(self):
        """Test error status codes are tracked"""
        monitor = PerformanceMonitor()

        monitor.record_request("/api/test", "GET", 0.1, 200)
        monitor.record_request("/api/test", "GET", 0.1, 404)
        monitor.record_request("/api/test", "GET", 0.1, 500)

        stats = monitor.get_stats()
        endpoint_stats = stats["slowest_endpoints"][0]
        assert endpoint_stats["errors"] == 2  # 404 and 500

    def test_slow_query_recording(self):
        """Test slow queries are recorded"""
        monitor = PerformanceMonitor()

        # Record a slow query (>2s)
        monitor.record_request("/api/slow", "GET", 3.0, 200)

        stats = monitor.get_stats()
        assert len(stats["recent_slow_queries"]) == 1
        assert stats["recent_slow_queries"][0]["path"] == "/api/slow"
        assert stats["recent_slow_queries"][0]["duration"] == 3.0

    def test_slow_query_limit(self):
        """Test slow queries are limited to 100"""
        monitor = PerformanceMonitor()

        # Add 150 slow queries
        for i in range(150):
            monitor.record_request(f"/api/slow{i}", "GET", 3.0, 200)

        # Should only keep last 100
        assert len(monitor.slow_queries) == 100

    def test_request_times_limit(self):
        """Test request times are limited to 1000"""
        monitor = PerformanceMonitor()

        # Add 1500 requests
        for i in range(1500):
            monitor.record_request("/api/test", "GET", 0.1, 200)

        # Should only keep last 1000
        assert len(monitor.request_times) == 1000

    def test_endpoint_stats_sorting(self):
        """Test endpoint stats are sorted by average time"""
        monitor = PerformanceMonitor()

        monitor.record_request("/api/fast", "GET", 0.05, 200)
        monitor.record_request("/api/slow", "GET", 0.5, 200)
        monitor.record_request("/api/medium", "GET", 0.2, 200)

        stats = monitor.get_stats()
        slowest = stats["slowest_endpoints"]

        # Should be sorted by avg_time_ms descending
        assert slowest[0]["endpoint"] == "GET /api/slow"
        assert slowest[1]["endpoint"] == "GET /api/medium"
        assert slowest[2]["endpoint"] == "GET /api/fast"

    def test_endpoint_stats_limit_to_10(self):
        """Test slowest endpoints limited to 10"""
        monitor = PerformanceMonitor()

        # Add 20 endpoints
        for i in range(20):
            monitor.record_request(f"/api/endpoint{i}", "GET", 0.1 + (i * 0.01), 200)

        stats = monitor.get_stats()

        # Should only return top 10
        assert len(stats["slowest_endpoints"]) == 10

    def test_recent_slow_queries_limit_to_10(self):
        """Test recent slow queries limited to 10"""
        monitor = PerformanceMonitor()

        # Add 15 slow queries
        for i in range(15):
            monitor.record_request(f"/api/slow{i}", "GET", 3.0, 200)

        stats = monitor.get_stats()

        # Should only return last 10
        assert len(stats["recent_slow_queries"]) == 10

    def test_endpoint_moves_to_end_on_access(self):
        """Test endpoint is marked as recently used"""
        monitor = PerformanceMonitor()

        # Add endpoints in order
        monitor.record_request("/api/first", "GET", 0.1, 200)
        monitor.record_request("/api/second", "GET", 0.1, 200)
        monitor.record_request("/api/third", "GET", 0.1, 200)

        # Access first endpoint again
        monitor.record_request("/api/first", "GET", 0.1, 200)

        # First should now be at the end (most recently used)
        keys = list(monitor.endpoint_stats.keys())
        assert keys[-1] == "GET /api/first"


class TestPerformanceMonitorIntegration:
    """Integration tests for performance monitor"""

    def test_complete_monitoring_workflow(self):
        """Test complete monitoring workflow"""
        monitor = PerformanceMonitor()

        # Simulate various requests
        monitor.record_request("/api/users", "GET", 0.15, 200)
        monitor.record_request("/api/users", "POST", 0.25, 201)
        monitor.record_request("/api/data", "GET", 0.1, 200)
        monitor.record_request("/api/error", "GET", 0.5, 500)
        monitor.record_request("/api/slow", "GET", 2.5, 200)  # Slow query

        stats = monitor.get_stats()

        # Verify complete stats
        assert stats["total_requests"] == 5
        assert "avg_response_time_ms" in stats
        assert len(stats["slowest_endpoints"]) >= 1
        assert len(stats["recent_slow_queries"]) == 1

        # Verify slow query details
        slow_query = stats["recent_slow_queries"][0]
        assert slow_query["path"] == "/api/slow"
        assert slow_query["duration"] == 2.5

    def test_global_instance_exists(self):
        """Test global performance_monitor instance exists"""
        from middleware.performance import performance_monitor

        assert performance_monitor is not None
        assert isinstance(performance_monitor, PerformanceMonitor)
