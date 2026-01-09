# redis_client.py
"""
Redis client for session storage, rate limiting, and caching.
Sprint 8: Redis Session Storage for horizontal scaling.
"""
import os
import logging
from typing import Optional
import redis
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Redis client wrapper with connection pooling and error handling.

    Provides a simple interface for Redis operations with automatic
    connection management and graceful degradation.
    """

    def __init__(self, url: str, decode_responses: bool = True):
        """
        Initialize Redis client with connection pooling.

        Args:
            url: Redis connection URL (e.g., "redis://localhost:6379/0")
            decode_responses: Whether to decode responses to strings
        """
        self.url = url
        self.decode_responses = decode_responses
        self._client = None
        self._availability_cache = None  # Cache availability status
        self._availability_cache_time = 0  # Timestamp of last availability check
        self._availability_cache_ttl = 5  # Cache TTL in seconds (5s)
        self._connect()

    def _connect(self):
        """Establish connection to Redis server"""
        try:
            self._client = redis.from_url(
                self.url,
                decode_responses=self.decode_responses,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )
            # Test connection
            self._client.ping()
            logger.info(f"Successfully connected to Redis at {self.url}")
        except (RedisError, RedisConnectionError) as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._client = None

    @property
    def is_available(self) -> bool:
        """
        Check if Redis connection is available (with 5s cache).

        This property is called before every Redis operation, so we cache
        the availability status for 5 seconds to reduce network overhead.
        The cache prevents doubling latency on every Redis operation.
        """
        if not self._client:
            return False

        # Check cache first
        import time
        current_time = time.time()
        if (self._availability_cache is not None and
                current_time - self._availability_cache_time < self._availability_cache_ttl):
            return self._availability_cache

        # Cache miss - check actual availability
        try:
            self._client.ping()
            self._availability_cache = True
            self._availability_cache_time = current_time
            return True
        except (RedisError, RedisConnectionError):
            self._availability_cache = False
            self._availability_cache_time = current_time
            return False

    def get(self, key: str) -> Optional[str]:
        """
        Get value from Redis.

        Args:
            key: Redis key

        Returns:
            Value as string or None if not found or Redis unavailable
        """
        if not self.is_available:
            logger.warning("Redis unavailable, get operation failed")
            return None

        try:
            return self._client.get(key)
        except RedisError as e:
            logger.error(f"Redis get failed for key {key}: {e}")
            return None

    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """
        Set value in Redis with optional expiration.

        Args:
            key: Redis key
            value: Value to store
            ex: Expiration time in seconds (optional)

        Returns:
            True if successful, False otherwise
        """
        if not self.is_available:
            logger.warning("Redis unavailable, set operation failed")
            return False

        try:
            self._client.set(key, value, ex=ex)
            return True
        except RedisError as e:
            logger.error(f"Redis set failed for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete key from Redis.

        Args:
            key: Redis key to delete

        Returns:
            True if successful, False otherwise
        """
        if not self.is_available:
            logger.warning("Redis unavailable, delete operation failed")
            return False

        try:
            self._client.delete(key)
            return True
        except RedisError as e:
            logger.error(f"Redis delete failed for key {key}: {e}")
            return False

    def incr(self, key: str) -> Optional[int]:
        """
        Increment value in Redis.

        Args:
            key: Redis key

        Returns:
            New value after increment, or None if failed
        """
        if not self.is_available:
            logger.warning("Redis unavailable, incr operation failed")
            return None

        try:
            return self._client.incr(key)
        except RedisError as e:
            logger.error(f"Redis incr failed for key {key}: {e}")
            return None

    def expire(self, key: str, seconds: int) -> bool:
        """
        Set expiration time for a key.

        Args:
            key: Redis key
            seconds: Expiration time in seconds

        Returns:
            True if successful, False otherwise
        """
        if not self.is_available:
            logger.warning("Redis unavailable, expire operation failed")
            return False

        try:
            self._client.expire(key, seconds)
            return True
        except RedisError as e:
            logger.error(f"Redis expire failed for key {key}: {e}")
            return False

    def ttl(self, key: str) -> Optional[int]:
        """
        Get time-to-live for a key.

        Args:
            key: Redis key

        Returns:
            TTL in seconds, -1 if no expiry, -2 if key doesn't exist, None if error
        """
        if not self.is_available:
            logger.warning("Redis unavailable, ttl operation failed")
            return None

        try:
            return self._client.ttl(key)
        except RedisError as e:
            logger.error(f"Redis ttl failed for key {key}: {e}")
            return None

    def ping(self) -> bool:
        """
        Ping Redis server to check connectivity.

        Returns:
            True if Redis responds, False otherwise
        """
        return self.is_available

    def flushdb(self) -> bool:
        """
        Flush all keys in current database.
        WARNING: Use with caution, only for testing!

        Returns:
            True if successful, False otherwise
        """
        if not self.is_available:
            logger.warning("Redis unavailable, flushdb operation failed")
            return False

        try:
            self._client.flushdb()
            logger.warning("Redis database flushed")
            return True
        except RedisError as e:
            logger.error(f"Redis flushdb failed: {e}")
            return False


# Global Redis client instance
# Initialize with URL from environment or default to localhost
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = RedisClient(REDIS_URL)


def get_redis_client() -> RedisClient:
    """
    Get the global Redis client instance.

    Returns:
        RedisClient instance
    """
    return redis_client
