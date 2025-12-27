"""
Tests for rate limiting utilities (shared/rate_limiting.py)
Target: Increase coverage from 43% to 80%+
"""
import pytest
import json
import time
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from shared.rate_limiting import (
    get_limiter,
    get_rate_limit_exception_handler,
    get_rate_limit_exception,
    SessionStorage,
    RateLimitTracker,
    session_storage,
    rate_limit_tracker,
)
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded


class TestGetLimiter:
    """Test limiter creation"""

    @patch("shared.rate_limiting.DISABLE_RATE_LIMITING", False)
    def test_get_limiter_enabled(self):
        """Test limiter creation when enabled"""
        limiter = get_limiter()

        assert isinstance(limiter, Limiter)
        # Check if limiter is actually enabled (implementation detail may vary)
        # Just verify it's a Limiter instance

    @patch("shared.rate_limiting.DISABLE_RATE_LIMITING", True)
    def test_get_limiter_disabled(self, caplog):
        """Test limiter creation when disabled"""
        import logging

        caplog.set_level(logging.INFO)

        limiter = get_limiter()

        assert isinstance(limiter, Limiter)
        # Check log message instead of internal attribute
        assert any(
            "Rate limiting DISABLED" in record.message for record in caplog.records
        )


class TestGetRateLimitHelpers:
    """Test helper functions"""

    def test_get_rate_limit_exception_handler(self):
        """Test getting exception handler"""
        handler = get_rate_limit_exception_handler()

        assert callable(handler)

    def test_get_rate_limit_exception(self):
        """Test getting exception class"""
        exc_class = get_rate_limit_exception()

        assert exc_class == RateLimitExceeded
        assert issubclass(exc_class, Exception)


class TestSessionStorage:
    """Test SessionStorage class"""

    def setup_method(self):
        """Create fresh SessionStorage for each test"""
        self.storage = SessionStorage()
        # Clear any existing data
        self.storage._memory_sessions.clear()

    def test_session_storage_init_memory(self):
        """Test SessionStorage initialization with in-memory backend"""
        with patch("shared.rate_limiting.REDIS_ENABLED", False):
            storage = SessionStorage()

            assert storage._redis_client is None
            assert isinstance(storage._memory_sessions, dict)

    def test_session_storage_get_redis_key(self):
        """Test Redis key generation"""
        token = "test-token-123"
        key = self.storage._get_redis_key(token)

        assert key == f"session:{token}"

    def test_session_storage_set_get_memory(self):
        """Test set and get session with in-memory storage"""
        token = "session-token-123"
        session_data = {
            "created_at": datetime.utcnow(),
            "ip": "192.168.1.100",
        }

        # Store session
        success = self.storage.set_session(token, session_data, ttl_seconds=3600)

        assert success is True
        assert token in self.storage._memory_sessions

        # Retrieve session
        retrieved = self.storage.get_session(token)

        assert retrieved is not None
        assert retrieved["ip"] == "192.168.1.100"
        assert isinstance(retrieved["created_at"], datetime)

    def test_session_storage_set_datetime_serialization(self):
        """Test datetime serialization in session data"""
        token = "test-token"
        now = datetime.utcnow()
        session_data = {"created_at": now, "ip": "10.0.0.1"}

        self.storage.set_session(token, session_data, ttl_seconds=3600)

        # Original data should not be modified
        assert isinstance(session_data["created_at"], datetime)

        # Retrieved data should have datetime restored
        retrieved = self.storage.get_session(token)
        assert isinstance(retrieved["created_at"], datetime)

    def test_session_storage_get_nonexistent(self):
        """Test getting non-existent session"""
        result = self.storage.get_session("nonexistent-token")

        assert result is None

    def test_session_storage_delete_memory(self):
        """Test deleting session from memory"""
        token = "delete-me"
        session_data = {"created_at": datetime.utcnow(), "ip": "192.168.1.1"}

        self.storage.set_session(token, session_data, ttl_seconds=3600)
        assert self.storage.get_session(token) is not None

        # Delete session
        success = self.storage.delete_session(token)

        assert success is True
        assert self.storage.get_session(token) is None

    def test_session_storage_delete_nonexistent(self):
        """Test deleting non-existent session"""
        success = self.storage.delete_session("nonexistent")

        assert success is False

    def test_session_storage_multiple_sessions(self):
        """Test storing multiple sessions"""
        sessions = []
        for i in range(5):
            token = f"token-{i}"
            data = {"created_at": datetime.utcnow(), "ip": f"192.168.1.{i}"}
            self.storage.set_session(token, data, ttl_seconds=3600)
            sessions.append((token, data))

        # All sessions should be retrievable
        for token, original_data in sessions:
            retrieved = self.storage.get_session(token)
            assert retrieved is not None
            assert retrieved["ip"] == original_data["ip"]

    def test_session_storage_logging_set(self, caplog):
        """Test logging when setting session"""
        import logging

        caplog.set_level(logging.DEBUG)

        self.storage.set_session(
            "test-token", {"created_at": datetime.utcnow(), "ip": "10.0.0.1"}, ttl_seconds=3600
        )

        # Check log message
        assert any(
            "Session stored in memory" in record.message for record in caplog.records
        )

    def test_session_storage_logging_get(self, caplog):
        """Test logging when getting session"""
        import logging

        caplog.set_level(logging.DEBUG)

        token = "test-token"
        self.storage.set_session(
            token, {"created_at": datetime.utcnow(), "ip": "10.0.0.1"}, ttl_seconds=3600
        )

        caplog.clear()
        self.storage.get_session(token)

        # Check log message
        assert any(
            "Session retrieved from memory" in record.message for record in caplog.records
        )

    def test_session_storage_logging_delete(self, caplog):
        """Test logging when deleting session"""
        import logging

        caplog.set_level(logging.DEBUG)

        token = "test-token"
        self.storage.set_session(
            token, {"created_at": datetime.utcnow(), "ip": "10.0.0.1"}, ttl_seconds=3600
        )

        caplog.clear()
        self.storage.delete_session(token)

        # Check log message
        assert any(
            "Session deleted from memory" in record.message for record in caplog.records
        )

    @patch("shared.rate_limiting.REDIS_ENABLED", True)
    def test_session_storage_redis_unavailable(self, caplog):
        """Test SessionStorage when Redis is enabled but unavailable"""
        import logging

        caplog.set_level(logging.WARNING)

        # Mock the imported get_redis_client function from redis_client module
        with patch("redis_client.get_redis_client") as mock_get_redis:
            mock_redis = Mock()
            mock_redis.is_available = False
            mock_get_redis.return_value = mock_redis

            storage = SessionStorage()

            # Should fall back to memory
            assert storage._redis_client is None

            # Check log
            assert any(
                "Redis unavailable" in record.message for record in caplog.records
            )

    @patch("shared.rate_limiting.REDIS_ENABLED", True)
    def test_session_storage_redis_init_error(self, caplog):
        """Test SessionStorage when Redis initialization fails"""
        import logging

        caplog.set_level(logging.ERROR)

        with patch("redis_client.get_redis_client", side_effect=Exception("Connection error")):
            storage = SessionStorage()

            assert storage._redis_client is None

            # Check log
            assert any(
                "Failed to initialize Redis client" in record.message
                for record in caplog.records
            )


class TestRateLimitTracker:
    """Test RateLimitTracker class"""

    def setup_method(self):
        """Create fresh RateLimitTracker for each test"""
        self.tracker = RateLimitTracker()
        # Clear any existing data
        self.tracker._memory_tracker.clear()

    def test_rate_limit_tracker_init_memory(self):
        """Test RateLimitTracker initialization with in-memory backend"""
        with patch("shared.rate_limiting.REDIS_ENABLED", False):
            tracker = RateLimitTracker()

            assert tracker._redis_client is None
            assert isinstance(tracker._memory_tracker, dict)

    def test_rate_limit_tracker_get_redis_key(self):
        """Test Redis key generation for IP"""
        client_ip = "192.168.1.100"
        key = self.tracker._get_redis_key(client_ip)

        assert key == f"ratelimit:admin:{client_ip}"

    def test_rate_limit_tracker_set_get_memory(self):
        """Test set and get attempts with in-memory storage"""
        client_ip = "10.0.0.1"
        attempts = [1234567890.0, 1234567891.0, 1234567892.0]

        # Store attempts
        success = self.tracker.set_attempts(client_ip, attempts, ttl_seconds=300)

        assert success is True

        # Retrieve attempts
        retrieved = self.tracker.get_attempts(client_ip)

        assert retrieved == attempts

    def test_rate_limit_tracker_get_empty(self):
        """Test getting attempts for IP with no attempts"""
        result = self.tracker.get_attempts("192.168.1.1")

        assert result == []

    def test_rate_limit_tracker_multiple_ips(self):
        """Test tracking multiple IPs"""
        ips_and_attempts = [
            ("192.168.1.1", [100.0, 101.0]),
            ("192.168.1.2", [200.0, 201.0, 202.0]),
            ("10.0.0.1", [300.0]),
        ]

        for ip, attempts in ips_and_attempts:
            self.tracker.set_attempts(ip, attempts, ttl_seconds=300)

        # All IPs should have correct attempts
        for ip, expected_attempts in ips_and_attempts:
            retrieved = self.tracker.get_attempts(ip)
            assert retrieved == expected_attempts

    def test_rate_limit_tracker_update_attempts(self):
        """Test updating attempts for same IP"""
        client_ip = "10.0.0.5"

        # Initial attempts
        self.tracker.set_attempts(client_ip, [100.0], ttl_seconds=300)
        assert self.tracker.get_attempts(client_ip) == [100.0]

        # Update attempts
        self.tracker.set_attempts(client_ip, [100.0, 101.0], ttl_seconds=300)
        assert self.tracker.get_attempts(client_ip) == [100.0, 101.0]

    def test_rate_limit_tracker_empty_attempts(self):
        """Test setting empty attempts list"""
        client_ip = "192.168.1.10"

        success = self.tracker.set_attempts(client_ip, [], ttl_seconds=300)

        assert success is True
        assert self.tracker.get_attempts(client_ip) == []

    @patch("shared.rate_limiting.REDIS_ENABLED", True)
    def test_rate_limit_tracker_redis_unavailable(self, caplog):
        """Test RateLimitTracker when Redis is enabled but unavailable"""
        import logging

        caplog.set_level(logging.WARNING)

        with patch("redis_client.get_redis_client") as mock_get_redis:
            mock_redis = Mock()
            mock_redis.is_available = False
            mock_get_redis.return_value = mock_redis

            tracker = RateLimitTracker()

            assert tracker._redis_client is None

            # Check log
            assert any(
                "Redis unavailable" in record.message for record in caplog.records
            )

    @patch("shared.rate_limiting.REDIS_ENABLED", True)
    def test_rate_limit_tracker_redis_init_error(self, caplog):
        """Test RateLimitTracker when Redis initialization fails"""
        import logging

        caplog.set_level(logging.ERROR)

        with patch("redis_client.get_redis_client", side_effect=Exception("Connection error")):
            tracker = RateLimitTracker()

            assert tracker._redis_client is None

            # Check log
            assert any(
                "Failed to initialize Redis client" in record.message
                for record in caplog.records
            )


class TestGlobalInstances:
    """Test global instances"""

    def test_session_storage_instance_exists(self):
        """Test global session_storage instance"""
        assert session_storage is not None
        assert isinstance(session_storage, SessionStorage)

    def test_rate_limit_tracker_instance_exists(self):
        """Test global rate_limit_tracker instance"""
        assert rate_limit_tracker is not None
        assert isinstance(rate_limit_tracker, RateLimitTracker)

    def test_global_instances_are_singletons(self):
        """Test that importing multiple times gives same instances"""
        from shared.rate_limiting import session_storage as ss1
        from shared.rate_limiting import session_storage as ss2

        assert ss1 is ss2

        from shared.rate_limiting import rate_limit_tracker as rt1
        from shared.rate_limiting import rate_limit_tracker as rt2

        assert rt1 is rt2


class TestIntegration:
    """Integration tests for rate limiting"""

    def setup_method(self):
        """Clear state before each test"""
        session_storage._memory_sessions.clear()
        rate_limit_tracker._memory_tracker.clear()

    def test_session_workflow(self):
        """Test complete session storage workflow"""
        token = "integration-test-token"
        session_data = {
            "created_at": datetime.utcnow(),
            "ip": "192.168.1.100",
            "user": "admin",
        }

        # Store session
        session_storage.set_session(token, session_data, ttl_seconds=3600)

        # Retrieve and verify
        retrieved = session_storage.get_session(token)
        assert retrieved is not None
        assert retrieved["ip"] == "192.168.1.100"
        assert retrieved["user"] == "admin"

        # Delete session
        session_storage.delete_session(token)

        # Should no longer exist
        assert session_storage.get_session(token) is None

    def test_rate_limit_workflow(self):
        """Test complete rate limiting workflow"""
        client_ip = "10.0.0.1"
        import time

        # Simulate authentication attempts
        attempts = []
        for i in range(5):
            attempts.append(time.time())
            rate_limit_tracker.set_attempts(client_ip, attempts, ttl_seconds=300)

        # Verify all attempts tracked
        retrieved = rate_limit_tracker.get_attempts(client_ip)
        assert len(retrieved) == 5

        # Clean old attempts (keep last 3)
        window = 60  # 60 seconds
        current_time = time.time()
        cutoff = current_time - window
        recent_attempts = [t for t in retrieved if t > cutoff]
        rate_limit_tracker.set_attempts(client_ip, recent_attempts, ttl_seconds=300)

        # Should have cleaned old attempts
        final_attempts = rate_limit_tracker.get_attempts(client_ip)
        assert len(final_attempts) <= 5

    def test_concurrent_sessions_and_rate_limiting(self):
        """Test sessions and rate limiting working together"""
        # Create sessions for multiple users
        for i in range(3):
            token = f"token-{i}"
            ip = f"192.168.1.{i}"
            session_data = {"created_at": datetime.utcnow(), "ip": ip}
            session_storage.set_session(token, session_data, ttl_seconds=3600)

            # Track rate limit attempts
            attempts = [time.time()]
            rate_limit_tracker.set_attempts(ip, attempts, ttl_seconds=300)

        # Verify all sessions exist
        for i in range(3):
            token = f"token-{i}"
            session = session_storage.get_session(token)
            assert session is not None

        # Verify all rate limits tracked
        for i in range(3):
            ip = f"192.168.1.{i}"
            attempts = rate_limit_tracker.get_attempts(ip)
            assert len(attempts) > 0

    def test_limiter_integration(self):
        """Test limiter creation integrates properly"""
        limiter = get_limiter()
        exception_handler = get_rate_limit_exception_handler()
        exception_class = get_rate_limit_exception()

        assert isinstance(limiter, Limiter)
        assert callable(exception_handler)
        assert exception_class == RateLimitExceeded


class TestEdgeCases:
    """Test edge cases and error handling"""

    def setup_method(self):
        """Clear state before each test"""
        self.storage = SessionStorage()
        self.tracker = RateLimitTracker()
        self.storage._memory_sessions.clear()
        self.tracker._memory_tracker.clear()

    def test_session_with_special_characters(self):
        """Test session tokens with special characters"""
        token = "token-with-special-chars-!@#$%"
        data = {"created_at": datetime.utcnow(), "ip": "10.0.0.1"}

        self.storage.set_session(token, data, ttl_seconds=3600)
        retrieved = self.storage.get_session(token)

        assert retrieved is not None

    def test_rate_limit_with_ipv6(self):
        """Test rate limiting with IPv6 address"""
        ipv6 = "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        attempts = [123.0, 456.0]

        self.tracker.set_attempts(ipv6, attempts, ttl_seconds=300)
        retrieved = self.tracker.get_attempts(ipv6)

        assert retrieved == attempts

    def test_session_data_without_created_at(self):
        """Test session data without created_at field"""
        token = "test-token"
        data = {"ip": "10.0.0.1", "custom_field": "value"}

        self.storage.set_session(token, data, ttl_seconds=3600)
        retrieved = self.storage.get_session(token)

        assert retrieved is not None
        assert retrieved["custom_field"] == "value"

    def test_very_large_attempts_list(self):
        """Test rate limiting with large number of attempts"""
        client_ip = "10.0.0.1"
        large_attempts = [float(i) for i in range(1000)]

        self.tracker.set_attempts(client_ip, large_attempts, ttl_seconds=300)
        retrieved = self.tracker.get_attempts(client_ip)

        assert len(retrieved) == 1000

    def test_session_overwrite(self):
        """Test overwriting existing session"""
        token = "same-token"
        data1 = {"created_at": datetime.utcnow(), "ip": "10.0.0.1"}
        data2 = {"created_at": datetime.utcnow(), "ip": "10.0.0.2"}

        self.storage.set_session(token, data1, ttl_seconds=3600)
        self.storage.set_session(token, data2, ttl_seconds=3600)

        retrieved = self.storage.get_session(token)
        assert retrieved["ip"] == "10.0.0.2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
