# utils/cache.py
"""
Simple TTL-based caching for database query results.
Sprint 12: Performance Optimization
Phase 1 Performance: Added automatic cache cleanup to prevent memory leaks
"""
import time
import hashlib
import json
import logging
from typing import Any, Optional, Callable
from functools import wraps

logger = logging.getLogger(__name__)

# Simple in-memory cache with TTL
_cache_store = {}
_cache_timestamps = {}

# Default TTL: 5 seconds (good for load tests, prevents stale data in production)
DEFAULT_TTL_SECONDS = 5

# Cache cleanup configuration
# Maximum number of entries before forcing cleanup
MAX_CACHE_ENTRIES = 10000
# Cleanup check interval (only cleanup every N cache operations to reduce overhead)
_cleanup_counter = 0
CLEANUP_CHECK_INTERVAL = 100


def make_cache_key(*args, **kwargs) -> str:
    """
    Generate a cache key from function arguments.

    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Hash string to use as cache key
    """
    # Create a deterministic string representation
    key_parts = [str(arg) for arg in args]
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    key_string = "|".join(key_parts)

    # Hash it to get a fixed-length key
    return hashlib.md5(key_string.encode()).hexdigest()


def cached_query(ttl_seconds: int = DEFAULT_TTL_SECONDS):
    """
    Decorator to cache query results with TTL.

    Args:
        ttl_seconds: Time to live for cache entries in seconds

    Usage:
        @cached_query(ttl_seconds=10)
        def expensive_query(param1, param2):
            return db.query()...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Generate cache key
            cache_key = f"{func.__module__}.{func.__name__}:{make_cache_key(*args, **kwargs)}"

            # Check if we have a valid cached result
            current_time = time.time()
            if cache_key in _cache_store and cache_key in _cache_timestamps:
                if current_time - _cache_timestamps[cache_key] < ttl_seconds:
                    # Cache hit - return cached result
                    return _cache_store[cache_key]

            # Cache miss or expired - execute function
            result = func(*args, **kwargs)

            # Store in cache
            _cache_store[cache_key] = result
            _cache_timestamps[cache_key] = current_time

            # Periodic cleanup to prevent unbounded growth (Phase 1 Performance)
            cleanup_expired_entries(force=False)

            return result

        return wrapper
    return decorator


def cleanup_expired_entries(force: bool = False):
    """
    Remove expired cache entries to prevent unbounded growth.
    Phase 1 Performance: Prevents memory leak from unbounded cache dictionary.

    Args:
        force: If True, cleanup regardless of counter. If False, only cleanup periodically.
    """
    global _cleanup_counter

    # Only run cleanup periodically to reduce overhead
    if not force:
        _cleanup_counter += 1
        if _cleanup_counter < CLEANUP_CHECK_INTERVAL:
            return
        _cleanup_counter = 0

    current_time = time.time()
    expired_keys = []

    # Find all expired keys
    for key, timestamp in _cache_timestamps.items():
        # Use a conservative TTL of 60 seconds for cleanup (2x the max expected TTL)
        # This ensures we don't delete entries that might still be valid
        if current_time - timestamp > 60:
            expired_keys.append(key)

    # Remove expired entries
    if expired_keys:
        for key in expired_keys:
            _cache_store.pop(key, None)
            _cache_timestamps.pop(key, None)
        logger.debug(f"Cache cleanup: removed {len(expired_keys)} expired entries")

    # If cache is still too large, remove oldest entries (LRU eviction)
    if len(_cache_store) > MAX_CACHE_ENTRIES:
        # Sort by timestamp and remove oldest entries
        sorted_keys = sorted(_cache_timestamps.items(), key=lambda x: x[1])
        num_to_remove = len(_cache_store) - (MAX_CACHE_ENTRIES // 2)  # Remove half

        for key, _ in sorted_keys[:num_to_remove]:
            _cache_store.pop(key, None)
            _cache_timestamps.pop(key, None)

        logger.warning(
            f"Cache size exceeded {MAX_CACHE_ENTRIES} entries, "
            f"evicted {num_to_remove} oldest entries"
        )


def clear_cache():
    """Clear all cached entries"""
    _cache_store.clear()
    _cache_timestamps.clear()
    logger.info("Cache cleared manually")


def get_cache_stats() -> dict:
    """Get cache statistics"""
    return {
        "entries": len(_cache_store),
        "oldest_entry_age": (
            time.time() - min(_cache_timestamps.values())
            if _cache_timestamps
            else 0
        ),
    }
