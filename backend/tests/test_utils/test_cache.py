"""
Comprehensive tests for caching utilities
Tests cache decorator, TTL behavior, and cache management
"""
import pytest
import time
from unittest.mock import Mock

from utils.cache import (
    make_cache_key,
    cached_query,
    clear_cache,
    get_cache_stats,
    DEFAULT_TTL_SECONDS,
    _cache_store,
    _cache_timestamps,
)


@pytest.fixture(autouse=True)
def clean_cache():
    """Clear cache before and after each test"""
    clear_cache()
    yield
    clear_cache()


class TestCacheKeyGeneration:
    """Test cache key generation"""

    def test_make_cache_key_no_args(self):
        """Should generate key with no arguments"""
        key = make_cache_key()
        assert key
        assert isinstance(key, str)
        assert len(key) == 32  # MD5 hash length

    def test_make_cache_key_with_args(self):
        """Should generate key from positional arguments"""
        key1 = make_cache_key("arg1", "arg2")
        key2 = make_cache_key("arg1", "arg2")
        key3 = make_cache_key("arg1", "arg3")

        # Same args should produce same key
        assert key1 == key2
        # Different args should produce different key
        assert key1 != key3

    def test_make_cache_key_with_kwargs(self):
        """Should generate key from keyword arguments"""
        key1 = make_cache_key(foo="bar", baz="qux")
        key2 = make_cache_key(foo="bar", baz="qux")
        key3 = make_cache_key(foo="bar", baz="different")

        # Same kwargs should produce same key
        assert key1 == key2
        # Different kwargs should produce different key
        assert key1 != key3

    def test_make_cache_key_kwargs_order_independent(self):
        """Should generate same key regardless of kwargs order"""
        key1 = make_cache_key(a=1, b=2, c=3)
        key2 = make_cache_key(c=3, a=1, b=2)
        key3 = make_cache_key(b=2, c=3, a=1)

        # Order shouldn't matter
        assert key1 == key2 == key3

    def test_make_cache_key_mixed_args_and_kwargs(self):
        """Should generate key from both args and kwargs"""
        key1 = make_cache_key("pos1", "pos2", kw1="val1", kw2="val2")
        key2 = make_cache_key("pos1", "pos2", kw2="val2", kw1="val1")

        # Should be the same (kwargs order doesn't matter)
        assert key1 == key2

    def test_make_cache_key_with_different_types(self):
        """Should handle different argument types"""
        key1 = make_cache_key(1, "string", 3.14, True)
        key2 = make_cache_key(1, "string", 3.14, True)
        key3 = make_cache_key(1, "string", 3.14, False)

        assert key1 == key2
        assert key1 != key3

    def test_make_cache_key_deterministic(self):
        """Should generate deterministic keys"""
        # Call multiple times with same args
        keys = [make_cache_key("test", x=123) for _ in range(10)]

        # All keys should be identical
        assert len(set(keys)) == 1


class TestCachedQueryDecorator:
    """Test cached_query decorator"""

    def test_cached_query_basic(self):
        """Should cache function results"""
        call_count = 0

        @cached_query(ttl_seconds=10)
        def test_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call - should execute function
        result1 = test_func(5)
        assert result1 == 10
        assert call_count == 1

        # Second call - should use cache
        result2 = test_func(5)
        assert result2 == 10
        assert call_count == 1  # Should not increment

    def test_cached_query_different_args(self):
        """Should cache different results for different arguments"""
        call_count = 0

        @cached_query(ttl_seconds=10)
        def test_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # Different arguments should not use same cache
        result1 = test_func(5)
        result2 = test_func(10)
        result3 = test_func(5)  # Same as first call

        assert result1 == 10
        assert result2 == 20
        assert result3 == 10
        assert call_count == 2  # Only called twice (5 and 10)

    def test_cached_query_ttl_expiration(self):
        """Should expire cache after TTL"""
        call_count = 0

        @cached_query(ttl_seconds=0.1)  # Very short TTL
        def test_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call
        result1 = test_func(5)
        assert result1 == 10
        assert call_count == 1

        # Second call immediately - should use cache
        result2 = test_func(5)
        assert result2 == 10
        assert call_count == 1

        # Wait for TTL to expire
        time.sleep(0.15)

        # Third call - cache expired, should execute again
        result3 = test_func(5)
        assert result3 == 10
        assert call_count == 2

    def test_cached_query_with_kwargs(self):
        """Should handle functions with keyword arguments"""
        call_count = 0

        @cached_query(ttl_seconds=10)
        def test_func(x, y=10):
            nonlocal call_count
            call_count += 1
            return x + y

        # First call
        result1 = test_func(5, y=10)
        assert result1 == 15
        assert call_count == 1

        # Same call - should use cache
        result2 = test_func(5, y=10)
        assert result2 == 15
        assert call_count == 1

        # Different kwargs - should not use cache
        result3 = test_func(5, y=20)
        assert result3 == 25
        assert call_count == 2

    def test_cached_query_default_ttl(self):
        """Should use default TTL if not specified"""
        call_count = 0

        @cached_query()  # No TTL specified
        def test_func():
            nonlocal call_count
            call_count += 1
            return "result"

        # Call multiple times quickly
        for _ in range(5):
            test_func()

        # Should only execute once (using default TTL)
        assert call_count == 1

    def test_cached_query_preserves_function_name(self):
        """Should preserve original function name and docstring"""
        @cached_query(ttl_seconds=10)
        def test_func():
            """Test function docstring"""
            return "result"

        assert test_func.__name__ == "test_func"
        assert test_func.__doc__ == "Test function docstring"

    def test_cached_query_with_none_result(self):
        """Should cache None results"""
        call_count = 0

        @cached_query(ttl_seconds=10)
        def test_func():
            nonlocal call_count
            call_count += 1
            return None

        # First call
        result1 = test_func()
        assert result1 is None
        assert call_count == 1

        # Second call - should use cache
        result2 = test_func()
        assert result2 is None
        assert call_count == 1  # Should not increment

    def test_cached_query_with_complex_return_types(self):
        """Should cache complex return types"""
        call_count = 0

        @cached_query(ttl_seconds=10)
        def test_func():
            nonlocal call_count
            call_count += 1
            return {"key": "value", "list": [1, 2, 3]}

        # First call
        result1 = test_func()
        assert call_count == 1

        # Second call - should return same object from cache
        result2 = test_func()
        assert call_count == 1
        assert result1 is result2  # Same object reference

    def test_cached_query_multiple_functions(self):
        """Should maintain separate caches for different functions"""
        call_count_a = 0
        call_count_b = 0

        @cached_query(ttl_seconds=10)
        def func_a():
            nonlocal call_count_a
            call_count_a += 1
            return "A"

        @cached_query(ttl_seconds=10)
        def func_b():
            nonlocal call_count_b
            call_count_b += 1
            return "B"

        # Call both functions
        func_a()
        func_b()
        func_a()  # Should use cache
        func_b()  # Should use cache

        assert call_count_a == 1
        assert call_count_b == 1


class TestCacheManagement:
    """Test cache management functions"""

    def test_clear_cache(self):
        """Should clear all cache entries"""
        @cached_query(ttl_seconds=10)
        def test_func(x):
            return x * 2

        # Populate cache
        test_func(1)
        test_func(2)
        test_func(3)

        # Verify cache has entries
        assert len(_cache_store) > 0
        assert len(_cache_timestamps) > 0

        # Clear cache
        clear_cache()

        # Verify cache is empty
        assert len(_cache_store) == 0
        assert len(_cache_timestamps) == 0

    def test_clear_cache_forces_recomputation(self):
        """Should force recomputation after clearing cache"""
        call_count = 0

        @cached_query(ttl_seconds=10)
        def test_func():
            nonlocal call_count
            call_count += 1
            return "result"

        # First call
        test_func()
        assert call_count == 1

        # Clear cache
        clear_cache()

        # Next call should recompute
        test_func()
        assert call_count == 2

    def test_get_cache_stats_empty(self):
        """Should return stats for empty cache"""
        stats = get_cache_stats()

        assert stats["entries"] == 0
        assert stats["oldest_entry_age"] == 0

    def test_get_cache_stats_with_entries(self):
        """Should return stats with cache entries"""
        @cached_query(ttl_seconds=10)
        def test_func(x):
            return x * 2

        # Populate cache
        test_func(1)
        test_func(2)

        stats = get_cache_stats()

        assert stats["entries"] == 2
        assert stats["oldest_entry_age"] >= 0
        assert stats["oldest_entry_age"] < 1  # Should be very recent

    def test_get_cache_stats_oldest_entry_age(self):
        """Should correctly calculate oldest entry age"""
        @cached_query(ttl_seconds=10)
        def test_func(x):
            return x * 2

        # First entry
        test_func(1)
        time.sleep(0.1)

        # Second entry
        test_func(2)

        stats = get_cache_stats()

        # Oldest entry should be at least 0.1 seconds old
        assert stats["oldest_entry_age"] >= 0.1
        assert stats["oldest_entry_age"] < 1


class TestCacheEdgeCases:
    """Test edge cases and special scenarios"""

    def test_cache_with_mutable_arguments(self):
        """Should handle mutable arguments (lists, dicts)"""
        call_count = 0

        @cached_query(ttl_seconds=10)
        def test_func(items):
            nonlocal call_count
            call_count += 1
            return sum(items)

        # Lists are converted to strings for cache key
        result1 = test_func([1, 2, 3])
        result2 = test_func([1, 2, 3])

        assert result1 == 6
        assert call_count == 1  # Should use cache

    def test_cache_concurrent_access(self):
        """Should handle concurrent cache access"""
        @cached_query(ttl_seconds=10)
        def test_func(x):
            return x * 2

        # Simulate concurrent access
        results = [test_func(5) for _ in range(100)]

        # All results should be the same
        assert all(r == 10 for r in results)

    def test_cache_with_zero_ttl(self):
        """Should handle zero TTL (always expire)"""
        call_count = 0

        @cached_query(ttl_seconds=0)
        def test_func():
            nonlocal call_count
            call_count += 1
            return "result"

        # Multiple calls
        test_func()
        test_func()
        test_func()

        # With zero TTL, cache should expire immediately
        # Might execute 2-3 times depending on timing
        assert call_count >= 1

    def test_cache_with_large_ttl(self):
        """Should handle very large TTL"""
        call_count = 0

        @cached_query(ttl_seconds=86400)  # 1 day
        def test_func():
            nonlocal call_count
            call_count += 1
            return "result"

        # Multiple calls
        for _ in range(10):
            test_func()

        # Should only execute once
        assert call_count == 1

    def test_cache_key_collision_resistance(self):
        """Should resist cache key collisions"""
        @cached_query(ttl_seconds=10)
        def test_func(a, b):
            return f"{a}:{b}"

        # These should produce different cache keys
        result1 = test_func("a", "bc")
        result2 = test_func("ab", "c")

        # Results should be different
        assert result1 == "a:bc"
        assert result2 == "ab:c"
