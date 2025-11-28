# middleware/performance.py
"""
Performance monitoring middleware with LRU eviction to prevent memory leaks.
Tracks request times, endpoint statistics, and slow queries.
"""
import time
from collections import deque, OrderedDict


class PerformanceMonitor:
    """Monitor API performance with LRU eviction to prevent memory leaks"""

    def __init__(self):
        self.request_times = deque(maxlen=1000)  # Keep last 1000 requests
        self.endpoint_stats = OrderedDict()  # Use OrderedDict to prevent unbounded growth
        self.max_endpoints = 100  # Maximum unique endpoints to track
        self.slow_queries = deque(maxlen=100)  # Keep last 100 slow queries

    def record_request(self, path: str, method: str, duration: float, status_code: int):
        """Record request metrics with LRU eviction"""
        self.request_times.append(duration)
        endpoint_key = f"{method} {path}"

        # Trim old endpoints if we've hit the limit (LRU eviction)
        if endpoint_key not in self.endpoint_stats and len(self.endpoint_stats) >= self.max_endpoints:
            self.endpoint_stats.popitem(last=False)  # Remove oldest endpoint

        # Initialize stats if new endpoint
        if endpoint_key not in self.endpoint_stats:
            self.endpoint_stats[endpoint_key] = {"count": 0, "total_time": 0, "errors": 0}

        # Move to end (mark as recently used)
        stats = self.endpoint_stats.pop(endpoint_key)
        stats["count"] += 1
        stats["total_time"] += duration
        if status_code >= 400:
            stats["errors"] += 1
        self.endpoint_stats[endpoint_key] = stats

        # Record slow queries (>2 seconds)
        if duration > 2.0:
            self.slow_queries.append({
                "path": path,
                "method": method,
                "duration": duration,
                "timestamp": time.time()
            })

    def get_stats(self):
        """Get performance statistics"""
        if not self.request_times:
            return {"message": "No requests recorded yet"}

        total_requests = len(self.request_times)
        avg_response_time = sum(self.request_times) / total_requests

        return {
            "total_requests": total_requests,
            "avg_response_time_ms": round(avg_response_time * 1000, 2),
            "slowest_endpoints": sorted([
                {
                    "endpoint": endpoint,
                    "avg_time_ms": round((stats["total_time"] / stats["count"]) * 1000, 2),
                    "requests": stats["count"],
                    "errors": stats["errors"]
                }
                for endpoint, stats in self.endpoint_stats.items()
            ], key=lambda x: x["avg_time_ms"], reverse=True)[:10],
            "recent_slow_queries": list(self.slow_queries)[-10:]
        }


# Global instance
performance_monitor = PerformanceMonitor()
