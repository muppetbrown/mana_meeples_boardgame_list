# utils/cache.py
"""
Simple TTL-based caching for database query results.
Sprint 12: Performance Optimization
"""
import time
import hashlib
import json
from typing import Any, Optional, Callable
from functools import wraps

# Simple in-memory cache with TTL
_cache_store = {}
_cache_timestamps = {}

# Default TTL: 5 seconds (good for load tests, prevents stale data in production)
DEFAULT_TTL_SECONDS = 5


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

            return result

        return wrapper
    return decorator


def clear_cache():
    """Clear all cached entries"""
    _cache_store.clear()
    _cache_timestamps.clear()


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
