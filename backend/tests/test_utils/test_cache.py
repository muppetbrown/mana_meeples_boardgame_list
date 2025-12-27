"""
Tests for caching utilities (utils/cache.py)
Target: Increase coverage from 55% to 95%+
"""
import pytest
import time
from unittest.mock import Mock, patch
from utils.cache import (
    make_cache_key,
    cached_query,
    clear_cache,
    get_cache_stats,
    _cache_store,
    _cache_timestamps,
    DEFAULT_TTL_SECONDS,
)


class TestMakeCacheKey:
    """Test cache key generation"""

    def test_make_cache_key_args_only(self):
        """Test cache key with positional args only"""
        key1 = make_cache_key("arg1", "arg2", 123)
        key2 = make_cache_key("arg1", "arg2", 123)

        # Same args should produce same key
        assert key1 == key2
        # Key should be a hash string
        assert isinstance(key1, str)
        assert len(key1) == 32  # MD5 hash length

    def test_make_cache_key_kwargs_only(self):
        """Test cache key with keyword args only"""
        key1 = make_cache_key(param1="value1", param2="value2")
        key2 = make_cache_key(param1="value1", param2="value2")

        assert key1 == key2

    def test_make_cache_key_mixed(self):
        """Test cache key with mixed args and kwargs"""
        key1 = make_cache_key("arg1", 123, param1="value1", param2="value2")
        key2 = make_cache_key("arg1", 123, param1="value1", param2="value2")

        assert key1 == key2

    def test_make_cache_key_order_matters_args(self):
        """Test that argument order matters for cache key"""
        key1 = make_cache_key("arg1", "arg2")
        key2 = make_cache_key("arg2", "arg1")

        # Different order should produce different keys
        assert key1 != key2

    def test_make_cache_key_order_independent_kwargs(self):
        """Test that kwargs order doesn't matter (sorted)"""
        key1 = make_cache_key(a="1", b="2", c="3")
        key2 = make_cache_key(c="3", a="1", b="2")

        # Kwargs are sorted, so order shouldn't matter
        assert key1 == key2

    def test_make_cache_key_different_values(self):
        """Test different values produce different keys"""
        key1 = make_cache_key(param="value1")
        key2 = make_cache_key(param="value2")

        assert key1 != key2

    def test_make_cache_key_empty(self):
        """Test cache key with no arguments"""
        key1 = make_cache_key()
        key2 = make_cache_key()

        # Empty args should still produce consistent hash
        assert key1 == key2

    def test_make_cache_key_types(self):
        """Test cache key with different types"""
        key1 = make_cache_key(1, "string", True, None, [1, 2, 3])

        # Should handle various types
        assert isinstance(key1, str)
        assert len(key1) == 32

    def test_make_cache_key_deterministic(self):
        """Test cache key generation is deterministic"""
        keys = [make_cache_key("test", value=123) for _ in range(10)]

        # All keys should be identical
        assert all(k == keys[0] for k in keys)


class TestCachedQueryDecorator:
    """Test cached_query decorator"""

    def setup_method(self):
        """Clear cache before each test"""
        clear_cache()

    def test_cached_query_basic(self):
        """Test basic caching functionality"""
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
        assert call_count == 1  # Not incremented

    def test_cached_query_different_args(self):
        """Test caching with different arguments"""
        call_count = 0

        @cached_query(ttl_seconds=10)
        def test_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = test_func(5)
        result2 = test_func(10)

        assert result1 == 10
        assert result2 == 20
        assert call_count == 2  # Different args = cache miss

    def test_cached_query_ttl_expiration(self):
        """Test cache expiration after TTL"""
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

        # Wait for TTL to expire
        time.sleep(0.15)

        # Should execute again after expiration
        result2 = test_func(5)
        assert result2 == 10
        assert call_count == 2

    def test_cached_query_default_ttl(self):
        """Test decorator with default TTL"""
        call_count = 0

        @cached_query()  # Use default TTL
        def test_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = test_func(5)
        result2 = test_func(5)

        assert result1 == result2
        assert call_count == 1

    def test_cached_query_kwargs(self):
        """Test caching with keyword arguments"""
        call_count = 0

        @cached_query(ttl_seconds=10)
        def test_func(x, y=10):
            nonlocal call_count
            call_count += 1
            return x + y

        result1 = test_func(5, y=20)
        result2 = test_func(5, y=20)

        assert result1 == 25
        assert result2 == 25
        assert call_count == 1

        # Different kwargs should miss cache
        result3 = test_func(5, y=30)
        assert result3 == 35
        assert call_count == 2

    def test_cached_query_mixed_args_kwargs(self):
        """Test caching with both args and kwargs"""
        call_count = 0

        @cached_query(ttl_seconds=10)
        def test_func(a, b, c=10, d=20):
            nonlocal call_count
            call_count += 1
            return a + b + c + d

        result1 = test_func(1, 2, c=3, d=4)
        result2 = test_func(1, 2, c=3, d=4)

        assert result1 == 10
        assert result2 == 10
        assert call_count == 1

    def test_cached_query_return_types(self):
        """Test caching preserves return types"""

        @cached_query(ttl_seconds=10)
        def return_dict():
            return {"key": "value"}

        @cached_query(ttl_seconds=10)
        def return_list():
            return [1, 2, 3]

        @cached_query(ttl_seconds=10)
        def return_none():
            return None

        dict_result = return_dict()
        assert isinstance(dict_result, dict)
        assert return_dict() is dict_result  # Same object from cache

        list_result = return_list()
        assert isinstance(list_result, list)

        none_result = return_none()
        assert none_result is None

    def test_cached_query_preserves_function_name(self):
        """Test decorator preserves function metadata"""

        @cached_query(ttl_seconds=10)
        def my_function():
            """This is my docstring"""
            return 42

        # functools.wraps should preserve these
        assert my_function.__name__ == "my_function"
        assert "docstring" in my_function.__doc__

    def test_cached_query_multiple_functions(self):
        """Test multiple decorated functions don't share cache"""
        call_count_a = 0
        call_count_b = 0

        @cached_query(ttl_seconds=10)
        def func_a(x):
            nonlocal call_count_a
            call_count_a += 1
            return x * 2

        @cached_query(ttl_seconds=10)
        def func_b(x):
            nonlocal call_count_b
            call_count_b += 1
            return x * 3

        # Call both functions with same arg
        func_a(5)
        func_b(5)

        # Should use cache for second calls
        func_a(5)
        func_b(5)

        # Each function should only be called once
        assert call_count_a == 1
        assert call_count_b == 1

    def test_cached_query_exception_not_cached(self):
        """Test that exceptions are not cached"""
        call_count = 0

        @cached_query(ttl_seconds=10)
        def test_func(x):
            nonlocal call_count
            call_count += 1
            if x < 0:
                raise ValueError("Negative value")
            return x * 2

        # First call with valid value
        result = test_func(5)
        assert result == 10
        assert call_count == 1

        # Call that raises exception
        with pytest.raises(ValueError):
            test_func(-1)
        assert call_count == 2

        # Call again with same negative value - should execute again
        with pytest.raises(ValueError):
            test_func(-1)
        assert call_count == 3  # Exception not cached


class TestClearCache:
    """Test cache clearing"""

    def test_clear_cache_empties_store(self):
        """Test clear_cache removes all entries"""

        @cached_query(ttl_seconds=10)
        def test_func(x):
            return x * 2

        # Add some cached values
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

    def test_clear_cache_affects_subsequent_calls(self):
        """Test clearing cache causes re-execution"""
        call_count = 0

        @cached_query(ttl_seconds=10)
        def test_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call
        test_func(5)
        assert call_count == 1

        # Clear cache
        clear_cache()

        # Should execute again
        test_func(5)
        assert call_count == 2

    def test_clear_cache_idempotent(self):
        """Test clearing empty cache is safe"""
        clear_cache()
        clear_cache()  # Should not raise error

        assert len(_cache_store) == 0
        assert len(_cache_timestamps) == 0


class TestGetCacheStats:
    """Test cache statistics"""

    def setup_method(self):
        """Clear cache before each test"""
        clear_cache()

    def test_get_cache_stats_empty(self):
        """Test stats for empty cache"""
        stats = get_cache_stats()

        assert stats["entries"] == 0
        assert stats["oldest_entry_age"] == 0

    def test_get_cache_stats_with_entries(self):
        """Test stats with cached entries"""

        @cached_query(ttl_seconds=10)
        def test_func(x):
            return x * 2

        # Add cached entries
        test_func(1)
        test_func(2)
        test_func(3)

        stats = get_cache_stats()

        assert stats["entries"] == 3
        # Oldest entry should be very recent (< 1 second)
        assert 0 <= stats["oldest_entry_age"] < 1

    def test_get_cache_stats_oldest_entry_age(self):
        """Test oldest_entry_age calculation"""

        @cached_query(ttl_seconds=10)
        def test_func(x):
            return x * 2

        # Add first entry
        test_func(1)

        # Wait a bit
        time.sleep(0.1)

        # Add second entry
        test_func(2)

        stats = get_cache_stats()

        # Oldest entry should be at least 0.1 seconds old
        assert stats["oldest_entry_age"] >= 0.1
        assert stats["entries"] == 2

    def test_get_cache_stats_after_clear(self):
        """Test stats after clearing cache"""

        @cached_query(ttl_seconds=10)
        def test_func(x):
            return x * 2

        test_func(1)
        test_func(2)

        clear_cache()

        stats = get_cache_stats()

        assert stats["entries"] == 0
        assert stats["oldest_entry_age"] == 0


class TestIntegration:
    """Integration tests for cache system"""

    def setup_method(self):
        """Clear cache before each test"""
        clear_cache()

    def test_cache_workflow_complete(self):
        """Test complete cache workflow"""
        execution_times = []

        @cached_query(ttl_seconds=5)
        def expensive_query(n):
            execution_times.append(time.time())
            time.sleep(0.01)  # Simulate expensive operation
            return sum(range(n))

        # First call - should execute
        result1 = expensive_query(100)
        assert len(execution_times) == 1

        # Second call - should use cache
        result2 = expensive_query(100)
        assert len(execution_times) == 1
        assert result1 == result2

        # Check cache stats
        stats = get_cache_stats()
        assert stats["entries"] == 1

        # Different arg - should execute again
        result3 = expensive_query(200)
        assert len(execution_times) == 2
        assert result3 != result1

        stats = get_cache_stats()
        assert stats["entries"] == 2

        # Clear cache
        clear_cache()

        # Should execute again after clear
        result4 = expensive_query(100)
        assert len(execution_times) == 3
        assert result4 == result1

    def test_cache_concurrent_access(self):
        """Test cache with rapid concurrent-like access"""
        call_count = 0

        @cached_query(ttl_seconds=1)
        def test_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # Rapid calls with same argument
        results = [test_func(10) for _ in range(100)]

        # All results should be the same
        assert all(r == 20 for r in results)
        # Function should only execute once
        assert call_count == 1

    def test_cache_with_real_world_pattern(self):
        """Test cache with realistic usage pattern"""
        db_queries = []

        @cached_query(ttl_seconds=2)
        def get_user_data(user_id):
            # Simulate database query
            db_queries.append(user_id)
            return {"id": user_id, "name": f"User {user_id}"}

        # Typical request pattern
        user1 = get_user_data(1)  # DB query
        user1_again = get_user_data(1)  # Cached
        user2 = get_user_data(2)  # DB query
        user1_third = get_user_data(1)  # Cached

        assert len(db_queries) == 2  # Only 2 actual queries
        assert db_queries == [1, 2]
        assert user1 == user1_again == user1_third
