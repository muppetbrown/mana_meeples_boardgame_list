"""
Tests for rate limiting utilities (shared/rate_limiting.py)
Target: Increase coverage from 43% to 80%+
"""
import json
from collections import defaultdict
from unittest.mock import Mock, patch
from shared.rate_limiting import (
    get_limiter,
    get_rate_limit_exception_handler,
    get_rate_limit_exception,
    RateLimitTracker,
    rate_limit_tracker,
)


class TestRateLimiterConfiguration:
    """Test rate limiter configuration functions"""

    def test_get_limiter(self):
        """Should return a configured Limiter instance"""
        limiter = get_limiter()

        assert limiter is not None
        # Check it's a Limiter instance
        from slowapi import Limiter
        assert isinstance(limiter, Limiter)

    def test_get_limiter_with_rate_limiting_disabled(self):
        """Should return disabled limiter when DISABLE_RATE_LIMITING is True"""
        with patch('shared.rate_limiting.DISABLE_RATE_LIMITING', True):
            limiter = get_limiter()
            assert limiter is not None
            assert limiter.enabled is False

    def test_get_limiter_with_rate_limiting_enabled(self):
        """Should return enabled limiter when DISABLE_RATE_LIMITING is False"""
        with patch('shared.rate_limiting.DISABLE_RATE_LIMITING', False):
            limiter = get_limiter()
            assert limiter is not None
            assert limiter.enabled is True

    def test_get_rate_limit_exception_handler(self):
        """Should return rate limit exception handler"""
        handler = get_rate_limit_exception_handler()
        assert handler is not None
        assert callable(handler)

    def test_get_rate_limit_exception(self):
        """Should return RateLimitExceeded exception class"""
        from slowapi.errors import RateLimitExceeded
        exc_class = get_rate_limit_exception()
        assert exc_class is RateLimitExceeded


class TestRateLimitTrackerMemoryBackend:
    """Test RateLimitTracker with in-memory backend"""

    def test_init_with_redis_disabled(self):
        """Should initialize with in-memory backend when Redis is disabled"""
        with patch('shared.rate_limiting.REDIS_ENABLED', False):
            from shared.rate_limiting import RateLimitTracker as RLT
            tracker = RLT()
            assert tracker._redis_client is None
            assert isinstance(tracker._memory_tracker, defaultdict)

    def test_get_attempts_memory_empty(self):
        """Should return empty list for new IP"""
        tracker = RateLimitTracker()
        tracker._redis_client = None  # Force memory backend

        attempts = tracker.get_attempts("192.168.1.1")
        assert attempts == []

    def test_set_attempts_memory(self):
        """Should store attempts in memory"""
        tracker = RateLimitTracker()
        tracker._redis_client = None  # Force memory backend

        client_ip = "192.168.1.1"
        attempts = [1704067200.0, 1704067260.0, 1704067320.0]

        result = tracker.set_attempts(client_ip, attempts, 300)
        assert result is True
        assert tracker._memory_tracker[client_ip] == attempts

    def test_get_attempts_memory(self):
        """Should retrieve attempts from memory"""
        tracker = RateLimitTracker()
        tracker._redis_client = None  # Force memory backend

        client_ip = "192.168.1.2"
        attempts = [1704067200.0, 1704067260.0]

        tracker.set_attempts(client_ip, attempts, 300)
        retrieved = tracker.get_attempts(client_ip)

        assert retrieved == attempts

    def test_multiple_ips_memory(self):
        """Should track attempts for multiple IPs separately"""
        tracker = RateLimitTracker()
        tracker._redis_client = None  # Force memory backend

        ip1 = "192.168.1.1"
        ip2 = "192.168.1.2"
        attempts1 = [1704067200.0]
        attempts2 = [1704067260.0, 1704067320.0]

        tracker.set_attempts(ip1, attempts1, 300)
        tracker.set_attempts(ip2, attempts2, 300)

        assert tracker.get_attempts(ip1) == attempts1
        assert tracker.get_attempts(ip2) == attempts2


class TestRateLimitTrackerRedisBackend:
    """Test RateLimitTracker with Redis backend"""

    def test_get_attempts_redis_empty(self):
        """Should return empty list when Redis returns None"""
        mock_redis = Mock()
        mock_redis.is_available = True
        mock_redis.get.return_value = None

        tracker = RateLimitTracker()
        tracker._redis_client = mock_redis

        attempts = tracker.get_attempts("192.168.1.1")
        assert attempts == []

    def test_get_attempts_redis(self):
        """Should retrieve attempts from Redis"""
        attempts_list = [1704067200.0, 1704067260.0]
        mock_redis = Mock()
        mock_redis.is_available = True
        mock_redis.get.return_value = json.dumps(attempts_list)

        tracker = RateLimitTracker()
        tracker._redis_client = mock_redis

        client_ip = "192.168.1.1"
        retrieved = tracker.get_attempts(client_ip)

        assert retrieved == attempts_list
        mock_redis.get.assert_called_once_with(f"ratelimit:admin:{client_ip}")

    def test_get_attempts_redis_invalid_json(self):
        """Should return empty list for invalid JSON"""
        mock_redis = Mock()
        mock_redis.is_available = True
        mock_redis.get.return_value = "invalid json [["

        tracker = RateLimitTracker()
        tracker._redis_client = mock_redis

        retrieved = tracker.get_attempts("192.168.1.1")
        assert retrieved == []

    def test_set_attempts_redis(self):
        """Should store attempts in Redis"""
        mock_redis = Mock()
        mock_redis.is_available = True
        mock_redis.set.return_value = True

        tracker = RateLimitTracker()
        tracker._redis_client = mock_redis

        client_ip = "192.168.1.1"
        attempts = [1704067200.0, 1704067260.0]

        result = tracker.set_attempts(client_ip, attempts, 300)

        assert result is True
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == f"ratelimit:admin:{client_ip}"
        assert call_args[1]["ex"] == 300

    def test_redis_fallback_on_set_failure(self):
        """Should fall back to memory if Redis set fails"""
        mock_redis = Mock()
        mock_redis.is_available = True
        mock_redis.set.return_value = False  # Redis set failed

        tracker = RateLimitTracker()
        tracker._redis_client = mock_redis

        client_ip = "192.168.1.1"
        attempts = [1704067200.0]

        result = tracker.set_attempts(client_ip, attempts, 300)

        assert result is True
        # Should fall back to memory
        assert tracker._memory_tracker[client_ip] == attempts


class TestGlobalInstances:
    """Test global singleton instances"""

    def test_rate_limit_tracker_exists(self):
        """Should have global rate_limit_tracker instance"""
        assert rate_limit_tracker is not None
        assert isinstance(rate_limit_tracker, RateLimitTracker)

    def test_rate_limit_tracker_is_functional(self):
        """Should be able to use global rate_limit_tracker"""
        # Force memory backend
        rate_limit_tracker._redis_client = None

        ip = "192.168.1.100"
        attempts = [1704067200.0]

        rate_limit_tracker.set_attempts(ip, attempts, 300)
        retrieved = rate_limit_tracker.get_attempts(ip)

        assert retrieved == attempts


class TestRedisKeyGeneration:
    """Test Redis key generation"""

    def test_ratelimit_redis_key_format(self):
        """Should generate correct Redis key for rate limiting"""
        tracker = RateLimitTracker()
        ip = "192.168.1.1"
        key = tracker._get_redis_key(ip)
        assert key == "ratelimit:admin:192.168.1.1"

    def test_different_ips_different_keys(self):
        """Should generate different keys for different IPs"""
        tracker = RateLimitTracker()
        key1 = tracker._get_redis_key("192.168.1.1")
        key2 = tracker._get_redis_key("192.168.1.2")
        assert key1 != key2
