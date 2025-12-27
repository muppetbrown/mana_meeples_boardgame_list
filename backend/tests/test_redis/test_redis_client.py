"""
Unit tests for redis_client.py

Tests Redis client wrapper with connection pooling and error handling.
Focuses on both successful operations and error scenarios with mocked Redis.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
import redis_client
from redis_client import RedisClient, get_redis_client


class TestRedisClientInitialization:
    """Test Redis client initialization and connection"""

    @patch('redis_client.redis.from_url')
    def test_init_successful_connection(self, mock_from_url):
        """Test successful Redis client initialization"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_from_url.return_value = mock_client

        client = RedisClient("redis://localhost:6379/0")

        assert client.url == "redis://localhost:6379/0"
        assert client.decode_responses is True
        assert client._client == mock_client
        mock_from_url.assert_called_once_with(
            "redis://localhost:6379/0",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30,
        )
        mock_client.ping.assert_called_once()

    @patch('redis_client.redis.from_url')
    def test_init_connection_failure(self, mock_from_url):
        """Test Redis client initialization with connection failure"""
        mock_from_url.side_effect = RedisConnectionError("Connection refused")

        client = RedisClient("redis://invalid:6379/0")

        assert client._client is None
        assert client.url == "redis://invalid:6379/0"

    @patch('redis_client.redis.from_url')
    def test_init_with_decode_responses_false(self, mock_from_url):
        """Test initialization with decode_responses=False"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_from_url.return_value = mock_client

        client = RedisClient("redis://localhost:6379/0", decode_responses=False)

        assert client.decode_responses is False
        mock_from_url.assert_called_once()
        assert mock_from_url.call_args[1]['decode_responses'] is False

    @patch('redis_client.redis.from_url')
    def test_init_ping_failure(self, mock_from_url):
        """Test initialization when ping fails"""
        mock_client = Mock()
        mock_client.ping.side_effect = RedisError("Ping failed")
        mock_from_url.return_value = mock_client

        client = RedisClient("redis://localhost:6379/0")

        assert client._client is None


class TestRedisClientIsAvailable:
    """Test Redis availability checking"""

    @patch('redis_client.redis.from_url')
    def test_is_available_when_connected(self, mock_from_url):
        """Test is_available returns True when Redis is connected"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_from_url.return_value = mock_client

        client = RedisClient("redis://localhost:6379/0")

        assert client.is_available is True

    @patch('redis_client.redis.from_url')
    def test_is_available_when_client_none(self, mock_from_url):
        """Test is_available returns False when client is None"""
        mock_from_url.side_effect = RedisConnectionError("Failed")

        client = RedisClient("redis://localhost:6379/0")

        assert client.is_available is False

    @patch('redis_client.redis.from_url')
    def test_is_available_when_ping_fails(self, mock_from_url):
        """Test is_available returns False when ping fails"""
        mock_client = Mock()
        # First ping succeeds (initialization), second fails (availability check)
        mock_client.ping.side_effect = [True, RedisError("Ping failed")]
        mock_from_url.return_value = mock_client

        client = RedisClient("redis://localhost:6379/0")

        assert client.is_available is False


class TestRedisClientGet:
    """Test Redis GET operations"""

    @patch('redis_client.redis.from_url')
    def test_get_success(self, mock_from_url):
        """Test successful GET operation"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.get.return_value = "test_value"
        mock_from_url.return_value = mock_client

        client = RedisClient("redis://localhost:6379/0")
        result = client.get("test_key")

        assert result == "test_value"
        mock_client.get.assert_called_once_with("test_key")

    @patch('redis_client.redis.from_url')
    def test_get_when_unavailable(self, mock_from_url):
        """Test GET when Redis is unavailable"""
        mock_from_url.side_effect = RedisConnectionError("Failed")

        client = RedisClient("redis://localhost:6379/0")
        result = client.get("test_key")

        assert result is None

    @patch('redis_client.redis.from_url')
    def test_get_redis_error(self, mock_from_url):
        """Test GET with Redis error"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.get.side_effect = RedisError("Get failed")
        mock_from_url.return_value = mock_client

        client = RedisClient("redis://localhost:6379/0")
        result = client.get("test_key")

        assert result is None

    @patch('redis_client.redis.from_url')
    def test_get_returns_none_for_missing_key(self, mock_from_url):
        """Test GET returns None for non-existent key"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.get.return_value = None
        mock_from_url.return_value = mock_client

        client = RedisClient("redis://localhost:6379/0")
        result = client.get("nonexistent_key")

        assert result is None


class TestRedisClientSet:
    """Test Redis SET operations"""

    @patch('redis_client.redis.from_url')
    def test_set_success(self, mock_from_url):
        """Test successful SET operation"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.set.return_value = True
        mock_from_url.return_value = mock_client

        client = RedisClient("redis://localhost:6379/0")
        result = client.set("test_key", "test_value")

        assert result is True
        mock_client.set.assert_called_once_with("test_key", "test_value", ex=None)

    @patch('redis_client.redis.from_url')
    def test_set_with_expiration(self, mock_from_url):
        """Test SET with expiration time"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.set.return_value = True
        mock_from_url.return_value = mock_client

        client = RedisClient("redis://localhost:6379/0")
        result = client.set("test_key", "test_value", ex=300)

        assert result is True
        mock_client.set.assert_called_once_with("test_key", "test_value", ex=300)

    @patch('redis_client.redis.from_url')
    def test_set_when_unavailable(self, mock_from_url):
        """Test SET when Redis is unavailable"""
        mock_from_url.side_effect = RedisConnectionError("Failed")

        client = RedisClient("redis://localhost:6379/0")
        result = client.set("test_key", "test_value")

        assert result is False

    @patch('redis_client.redis.from_url')
    def test_set_redis_error(self, mock_from_url):
        """Test SET with Redis error"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.set.side_effect = RedisError("Set failed")
        mock_from_url.return_value = mock_client

        client = RedisClient("redis://localhost:6379/0")
        result = client.set("test_key", "test_value")

        assert result is False


class TestRedisClientDelete:
    """Test Redis DELETE operations"""

    @patch('redis_client.redis.from_url')
    def test_delete_success(self, mock_from_url):
        """Test successful DELETE operation"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.delete.return_value = 1
        mock_from_url.return_value = mock_client

        client = RedisClient("redis://localhost:6379/0")
        result = client.delete("test_key")

        assert result is True
        mock_client.delete.assert_called_once_with("test_key")

    @patch('redis_client.redis.from_url')
    def test_delete_when_unavailable(self, mock_from_url):
        """Test DELETE when Redis is unavailable"""
        mock_from_url.side_effect = RedisConnectionError("Failed")

        client = RedisClient("redis://localhost:6379/0")
        result = client.delete("test_key")

        assert result is False

    @patch('redis_client.redis.from_url')
    def test_delete_redis_error(self, mock_from_url):
        """Test DELETE with Redis error"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.delete.side_effect = RedisError("Delete failed")
        mock_from_url.return_value = mock_client

        client = RedisClient("redis://localhost:6379/0")
        result = client.delete("test_key")

        assert result is False


class TestRedisClientIncr:
    """Test Redis INCR operations"""

    @patch('redis_client.redis.from_url')
    def test_incr_success(self, mock_from_url):
        """Test successful INCR operation"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.incr.return_value = 5
        mock_from_url.return_value = mock_client

        client = RedisClient("redis://localhost:6379/0")
        result = client.incr("counter_key")

        assert result == 5
        mock_client.incr.assert_called_once_with("counter_key")

    @patch('redis_client.redis.from_url')
    def test_incr_when_unavailable(self, mock_from_url):
        """Test INCR when Redis is unavailable"""
        mock_from_url.side_effect = RedisConnectionError("Failed")

        client = RedisClient("redis://localhost:6379/0")
        result = client.incr("counter_key")

        assert result is None

    @patch('redis_client.redis.from_url')
    def test_incr_redis_error(self, mock_from_url):
        """Test INCR with Redis error"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.incr.side_effect = RedisError("Incr failed")
        mock_from_url.return_value = mock_client

        client = RedisClient("redis://localhost:6379/0")
        result = client.incr("counter_key")

        assert result is None


class TestRedisClientExpire:
    """Test Redis EXPIRE operations"""

    @patch('redis_client.redis.from_url')
    def test_expire_success(self, mock_from_url):
        """Test successful EXPIRE operation"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.expire.return_value = True
        mock_from_url.return_value = mock_client

        client = RedisClient("redis://localhost:6379/0")
        result = client.expire("test_key", 300)

        assert result is True
        mock_client.expire.assert_called_once_with("test_key", 300)

    @patch('redis_client.redis.from_url')
    def test_expire_when_unavailable(self, mock_from_url):
        """Test EXPIRE when Redis is unavailable"""
        mock_from_url.side_effect = RedisConnectionError("Failed")

        client = RedisClient("redis://localhost:6379/0")
        result = client.expire("test_key", 300)

        assert result is False

    @patch('redis_client.redis.from_url')
    def test_expire_redis_error(self, mock_from_url):
        """Test EXPIRE with Redis error"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.expire.side_effect = RedisError("Expire failed")
        mock_from_url.return_value = mock_client

        client = RedisClient("redis://localhost:6379/0")
        result = client.expire("test_key", 300)

        assert result is False


class TestRedisClientTTL:
    """Test Redis TTL operations"""

    @patch('redis_client.redis.from_url')
    def test_ttl_success(self, mock_from_url):
        """Test successful TTL operation"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.ttl.return_value = 250
        mock_from_url.return_value = mock_client

        client = RedisClient("redis://localhost:6379/0")
        result = client.ttl("test_key")

        assert result == 250
        mock_client.ttl.assert_called_once_with("test_key")

    @patch('redis_client.redis.from_url')
    def test_ttl_no_expiry(self, mock_from_url):
        """Test TTL when key has no expiry"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.ttl.return_value = -1
        mock_from_url.return_value = mock_client

        client = RedisClient("redis://localhost:6379/0")
        result = client.ttl("test_key")

        assert result == -1

    @patch('redis_client.redis.from_url')
    def test_ttl_key_not_found(self, mock_from_url):
        """Test TTL when key doesn't exist"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.ttl.return_value = -2
        mock_from_url.return_value = mock_client

        client = RedisClient("redis://localhost:6379/0")
        result = client.ttl("nonexistent_key")

        assert result == -2

    @patch('redis_client.redis.from_url')
    def test_ttl_when_unavailable(self, mock_from_url):
        """Test TTL when Redis is unavailable"""
        mock_from_url.side_effect = RedisConnectionError("Failed")

        client = RedisClient("redis://localhost:6379/0")
        result = client.ttl("test_key")

        assert result is None

    @patch('redis_client.redis.from_url')
    def test_ttl_redis_error(self, mock_from_url):
        """Test TTL with Redis error"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.ttl.side_effect = RedisError("TTL failed")
        mock_from_url.return_value = mock_client

        client = RedisClient("redis://localhost:6379/0")
        result = client.ttl("test_key")

        assert result is None


class TestRedisClientPing:
    """Test Redis PING operations"""

    @patch('redis_client.redis.from_url')
    def test_ping_success(self, mock_from_url):
        """Test successful PING operation"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_from_url.return_value = mock_client

        client = RedisClient("redis://localhost:6379/0")
        result = client.ping()

        assert result is True

    @patch('redis_client.redis.from_url')
    def test_ping_when_unavailable(self, mock_from_url):
        """Test PING when Redis is unavailable"""
        mock_from_url.side_effect = RedisConnectionError("Failed")

        client = RedisClient("redis://localhost:6379/0")
        result = client.ping()

        assert result is False


class TestRedisClientFlushdb:
    """Test Redis FLUSHDB operations"""

    @patch('redis_client.redis.from_url')
    def test_flushdb_success(self, mock_from_url):
        """Test successful FLUSHDB operation"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.flushdb.return_value = True
        mock_from_url.return_value = mock_client

        client = RedisClient("redis://localhost:6379/0")
        result = client.flushdb()

        assert result is True
        mock_client.flushdb.assert_called_once()

    @patch('redis_client.redis.from_url')
    def test_flushdb_when_unavailable(self, mock_from_url):
        """Test FLUSHDB when Redis is unavailable"""
        mock_from_url.side_effect = RedisConnectionError("Failed")

        client = RedisClient("redis://localhost:6379/0")
        result = client.flushdb()

        assert result is False

    @patch('redis_client.redis.from_url')
    def test_flushdb_redis_error(self, mock_from_url):
        """Test FLUSHDB with Redis error"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.flushdb.side_effect = RedisError("Flushdb failed")
        mock_from_url.return_value = mock_client

        client = RedisClient("redis://localhost:6379/0")
        result = client.flushdb()

        assert result is False


class TestGlobalRedisClient:
    """Test global Redis client instance"""

    @patch('redis_client.RedisClient')
    @patch.dict('os.environ', {'REDIS_URL': 'redis://testhost:6379/1'})
    def test_get_redis_client_returns_instance(self, mock_redis_client_class):
        """Test get_redis_client returns the global instance"""
        # Need to reload module to pick up env var
        import importlib
        importlib.reload(redis_client)

        client = redis_client.get_redis_client()

        assert client is not None
        assert client == redis_client.redis_client

    @patch('redis_client.redis.from_url')
    def test_global_client_initialization(self, mock_from_url):
        """Test global Redis client is initialized with correct defaults"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_from_url.return_value = mock_client

        # Reload module to trigger initialization
        import importlib
        importlib.reload(redis_client)

        # Check that the global client was created
        assert redis_client.redis_client is not None
        # After reload, RedisClient class reference may change, so check type name
        assert type(redis_client.redis_client).__name__ == 'RedisClient'


class TestRedisClientIntegration:
    """Integration tests for Redis client workflows"""

    @patch('redis_client.redis.from_url')
    def test_set_get_delete_workflow(self, mock_from_url):
        """Test complete SET -> GET -> DELETE workflow"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.set.return_value = True
        mock_client.get.return_value = "value123"
        mock_client.delete.return_value = 1
        mock_from_url.return_value = mock_client

        client = RedisClient("redis://localhost:6379/0")

        # Set value
        assert client.set("key", "value123", ex=300) is True

        # Get value
        assert client.get("key") == "value123"

        # Delete value
        assert client.delete("key") is True

    @patch('redis_client.redis.from_url')
    def test_counter_workflow(self, mock_from_url):
        """Test counter increment workflow"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.set.return_value = True
        mock_client.incr.side_effect = [1, 2, 3]
        mock_from_url.return_value = mock_client

        client = RedisClient("redis://localhost:6379/0")

        # Initialize counter
        assert client.set("counter", "0") is True

        # Increment multiple times
        assert client.incr("counter") == 1
        assert client.incr("counter") == 2
        assert client.incr("counter") == 3

    @patch('redis_client.redis.from_url')
    def test_ttl_workflow(self, mock_from_url):
        """Test TTL and expiration workflow"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.set.return_value = True
        mock_client.expire.return_value = True
        mock_client.ttl.return_value = 250
        mock_from_url.return_value = mock_client

        client = RedisClient("redis://localhost:6379/0")

        # Set key without expiration
        assert client.set("key", "value") is True

        # Set expiration
        assert client.expire("key", 300) is True

        # Check TTL
        ttl = client.ttl("key")
        assert ttl == 250
        assert ttl > 0

    @patch('redis_client.redis.from_url')
    def test_graceful_degradation_workflow(self, mock_from_url):
        """Test that all operations fail gracefully when Redis is unavailable"""
        mock_from_url.side_effect = RedisConnectionError("Connection refused")

        client = RedisClient("redis://localhost:6379/0")

        # All operations should return None or False without raising exceptions
        assert client.is_available is False
        assert client.get("key") is None
        assert client.set("key", "value") is False
        assert client.delete("key") is False
        assert client.incr("counter") is None
        assert client.expire("key", 300) is False
        assert client.ttl("key") is None
        assert client.ping() is False
        assert client.flushdb() is False
