# shared/rate_limiting.py
"""
Shared rate limiting configuration and utilities.
Centralizes rate limiting setup to avoid circular imports and improve modularity.

Sprint 8: Migrated to Redis for horizontal scaling support.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import REDIS_ENABLED

logger = logging.getLogger(__name__)


def get_limiter() -> Limiter:
    """Create and configure the rate limiter instance"""
    return Limiter(key_func=get_remote_address)


def get_rate_limit_exception_handler():
    """Get the rate limit exception handler"""
    return _rate_limit_exceeded_handler


def get_rate_limit_exception():
    """Get the rate limit exception class"""
    return RateLimitExceeded


# ============================================================================
# Session Storage - Redis or In-Memory fallback
# ============================================================================

class SessionStorage:
    """
    Session storage with Redis backend or in-memory fallback.
    Sprint 8: Redis Session Storage for horizontal scaling.
    """

    def __init__(self):
        """Initialize session storage"""
        self._memory_sessions: Dict[str, Dict[str, Any]] = {}
        self._redis_client = None

        if REDIS_ENABLED:
            try:
                from redis_client import get_redis_client
                self._redis_client = get_redis_client()
                if self._redis_client.is_available:
                    logger.info("SessionStorage initialized with Redis backend")
                else:
                    logger.warning("Redis unavailable, falling back to in-memory sessions")
                    self._redis_client = None
            except Exception as e:
                logger.error(f"Failed to initialize Redis client: {e}")
                self._redis_client = None
        else:
            logger.info("SessionStorage initialized with in-memory backend (Redis disabled)")

    def _get_redis_key(self, session_token: str) -> str:
        """Get Redis key for session token"""
        return f"session:{session_token}"

    def set_session(self, session_token: str, session_data: Dict[str, Any], ttl_seconds: int) -> bool:
        """
        Store session data with expiration.

        Args:
            session_token: Session token
            session_data: Session data dictionary
            ttl_seconds: Time to live in seconds

        Returns:
            True if successful
        """
        # Convert datetime objects to ISO format for JSON serialization
        serializable_data = session_data.copy()
        if "created_at" in serializable_data and isinstance(serializable_data["created_at"], datetime):
            serializable_data["created_at"] = serializable_data["created_at"].isoformat()

        if self._redis_client and self._redis_client.is_available:
            # Store in Redis
            key = self._get_redis_key(session_token)
            success = self._redis_client.set(key, json.dumps(serializable_data), ex=ttl_seconds)
            if success:
                logger.debug(f"Session stored in Redis: {session_token[:8]}...")
                return True
            else:
                logger.warning("Redis set failed, falling back to memory")

        # Fallback to in-memory storage
        self._memory_sessions[session_token] = session_data
        logger.debug(f"Session stored in memory: {session_token[:8]}...")
        return True

    def get_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session data.

        Args:
            session_token: Session token

        Returns:
            Session data dictionary or None if not found
        """
        if self._redis_client and self._redis_client.is_available:
            # Try Redis first
            key = self._get_redis_key(session_token)
            session_json = self._redis_client.get(key)
            if session_json:
                try:
                    session_data = json.loads(session_json)
                    # Convert ISO format back to datetime
                    if "created_at" in session_data and isinstance(session_data["created_at"], str):
                        session_data["created_at"] = datetime.fromisoformat(session_data["created_at"])
                    logger.debug(f"Session retrieved from Redis: {session_token[:8]}...")
                    return session_data
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode session JSON: {e}")
                    return None

        # Fallback to in-memory storage
        session_data = self._memory_sessions.get(session_token)
        if session_data:
            logger.debug(f"Session retrieved from memory: {session_token[:8]}...")
        return session_data

    def delete_session(self, session_token: str) -> bool:
        """
        Delete session data.

        Args:
            session_token: Session token

        Returns:
            True if successful
        """
        if self._redis_client and self._redis_client.is_available:
            # Delete from Redis
            key = self._get_redis_key(session_token)
            success = self._redis_client.delete(key)
            if success:
                logger.debug(f"Session deleted from Redis: {session_token[:8]}...")
                return True

        # Fallback to in-memory storage
        if session_token in self._memory_sessions:
            del self._memory_sessions[session_token]
            logger.debug(f"Session deleted from memory: {session_token[:8]}...")
            return True

        return False


# ============================================================================
# Rate Limit Tracker - Redis or In-Memory fallback
# ============================================================================

class RateLimitTracker:
    """
    Rate limit tracking with Redis backend or in-memory fallback.
    Sprint 8: Redis Session Storage for horizontal scaling.
    """

    def __init__(self):
        """Initialize rate limit tracker"""
        self._memory_tracker: Dict[str, List[float]] = defaultdict(list)
        self._redis_client = None

        if REDIS_ENABLED:
            try:
                from redis_client import get_redis_client
                self._redis_client = get_redis_client()
                if self._redis_client.is_available:
                    logger.info("RateLimitTracker initialized with Redis backend")
                else:
                    logger.warning("Redis unavailable, falling back to in-memory rate limiting")
                    self._redis_client = None
            except Exception as e:
                logger.error(f"Failed to initialize Redis client: {e}")
                self._redis_client = None
        else:
            logger.info("RateLimitTracker initialized with in-memory backend (Redis disabled)")

    def _get_redis_key(self, client_ip: str) -> str:
        """Get Redis key for client IP"""
        return f"ratelimit:admin:{client_ip}"

    def get_attempts(self, client_ip: str) -> List[float]:
        """
        Get rate limit attempts for client IP.

        Args:
            client_ip: Client IP address

        Returns:
            List of attempt timestamps
        """
        if self._redis_client and self._redis_client.is_available:
            # Try Redis first
            key = self._get_redis_key(client_ip)
            attempts_json = self._redis_client.get(key)
            if attempts_json:
                try:
                    return json.loads(attempts_json)
                except json.JSONDecodeError:
                    return []
            return []

        # Fallback to in-memory storage
        return self._memory_tracker[client_ip]

    def set_attempts(self, client_ip: str, attempts: List[float], ttl_seconds: int) -> bool:
        """
        Set rate limit attempts for client IP.

        Args:
            client_ip: Client IP address
            attempts: List of attempt timestamps
            ttl_seconds: Time to live in seconds

        Returns:
            True if successful
        """
        if self._redis_client and self._redis_client.is_available:
            # Store in Redis
            key = self._get_redis_key(client_ip)
            success = self._redis_client.set(key, json.dumps(attempts), ex=ttl_seconds)
            if success:
                return True

        # Fallback to in-memory storage
        self._memory_tracker[client_ip] = attempts
        return True


# ============================================================================
# Global instances
# ============================================================================

# Session storage instance (replaces admin_sessions dict)
session_storage = SessionStorage()

# Rate limit tracker instance (replaces admin_attempt_tracker dict)
rate_limit_tracker = RateLimitTracker()

# Legacy in-memory storage for backward compatibility
# These will be deprecated in favor of Redis-backed storage
admin_sessions: Dict[str, Dict[str, Any]] = {}
admin_attempt_tracker: Dict[str, List[float]] = defaultdict(list)
