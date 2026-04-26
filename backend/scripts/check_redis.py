#!/usr/bin/env python3
"""
Test script for Redis integration (Sprint 8).
Run this script to verify Redis connectivity and session/rate limiting functionality.

Usage:
    # Start Redis first
    docker compose up -d redis

    # Run tests
    python test_redis_integration.py
"""
import sys
import os
import logging
from datetime import datetime, timezone

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def test_redis_connection():
    """Test basic Redis connectivity"""
    logger.info("Testing Redis connection...")
    try:
        from redis_client import get_redis_client

        client = get_redis_client()
        if client.ping():
            logger.info("✓ Redis connection successful")
            return True
        else:
            logger.error("✗ Redis ping failed")
            return False
    except Exception as e:
        logger.error(f"✗ Redis connection failed: {e}")
        return False


def test_redis_operations():
    """Test basic Redis operations"""
    logger.info("\nTesting Redis operations...")
    try:
        from redis_client import get_redis_client

        client = get_redis_client()

        # Test set/get
        test_key = "test:sprint8"
        test_value = "Hello Redis!"
        client.set(test_key, test_value, ex=60)
        retrieved = client.get(test_key)

        if retrieved == test_value:
            logger.info(f"✓ Set/Get test passed: {retrieved}")
        else:
            logger.error(f"✗ Set/Get test failed: expected {test_value}, got {retrieved}")
            return False

        # Test TTL
        ttl = client.ttl(test_key)
        if ttl and ttl > 0:
            logger.info(f"✓ TTL test passed: {ttl} seconds remaining")
        else:
            logger.warning(f"⚠ TTL test unexpected result: {ttl}")

        # Test delete
        client.delete(test_key)
        if not client.get(test_key):
            logger.info("✓ Delete test passed")
        else:
            logger.error("✗ Delete test failed: key still exists")
            return False

        # Test increment
        counter_key = "test:counter"
        client.set(counter_key, "0")
        count = client.incr(counter_key)
        if count == 1:
            logger.info("✓ Increment test passed")
        else:
            logger.error(f"✗ Increment test failed: expected 1, got {count}")
            return False

        client.delete(counter_key)

        logger.info("✓ All Redis operations tests passed")
        return True

    except Exception as e:
        logger.error(f"✗ Redis operations test failed: {e}")
        return False


def test_session_storage():
    """Test session storage with Redis"""
    logger.info("\nTesting session storage...")
    try:
        from shared.rate_limiting import session_storage
        import secrets

        # Create test session
        session_token = secrets.token_urlsafe(32)
        session_data = {
            "created_at": datetime.now(timezone.utc),
            "ip": "127.0.0.1",
            "test_data": "Sprint 8 test",
        }

        # Store session
        success = session_storage.set_session(session_token, session_data, 300)
        if success:
            logger.info("✓ Session creation successful")
        else:
            logger.error("✗ Session creation failed")
            return False

        # Retrieve session
        retrieved = session_storage.get_session(session_token)
        if retrieved and retrieved.get("ip") == "127.0.0.1":
            logger.info(f"✓ Session retrieval successful: {retrieved.get('ip')}")
        else:
            logger.error(f"✗ Session retrieval failed: {retrieved}")
            return False

        # Delete session
        session_storage.delete_session(session_token)
        if not session_storage.get_session(session_token):
            logger.info("✓ Session deletion successful")
        else:
            logger.error("✗ Session deletion failed")
            return False

        logger.info("✓ All session storage tests passed")
        return True

    except Exception as e:
        logger.error(f"✗ Session storage test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rate_limiting():
    """Test rate limiting with Redis"""
    logger.info("\nTesting rate limiting...")
    try:
        from shared.rate_limiting import rate_limit_tracker
        import time

        test_ip = "192.168.1.100"

        # Get initial attempts (should be empty)
        attempts = rate_limit_tracker.get_attempts(test_ip)
        if isinstance(attempts, list):
            logger.info(f"✓ Get attempts successful: {len(attempts)} attempts")
        else:
            logger.error(f"✗ Get attempts failed: {attempts}")
            return False

        # Add some attempts
        current_time = time.time()
        test_attempts = [current_time - 60, current_time - 30, current_time]
        success = rate_limit_tracker.set_attempts(test_ip, test_attempts, 300)
        if success:
            logger.info("✓ Set attempts successful")
        else:
            logger.error("✗ Set attempts failed")
            return False

        # Retrieve attempts
        retrieved = rate_limit_tracker.get_attempts(test_ip)
        if len(retrieved) == 3:
            logger.info(f"✓ Retrieve attempts successful: {len(retrieved)} attempts")
        else:
            logger.error(f"✗ Retrieve attempts failed: expected 3, got {len(retrieved)}")
            return False

        logger.info("✓ All rate limiting tests passed")
        return True

    except Exception as e:
        logger.error(f"✗ Rate limiting test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("Sprint 8: Redis Integration Test Suite")
    logger.info("=" * 60)

    results = {
        "Redis Connection": test_redis_connection(),
        "Redis Operations": test_redis_operations(),
        "Session Storage": test_session_storage(),
        "Rate Limiting": test_rate_limiting(),
    }

    logger.info("\n" + "=" * 60)
    logger.info("Test Results Summary")
    logger.info("=" * 60)

    all_passed = True
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        logger.info(f"{test_name:.<30} {status}")
        if not result:
            all_passed = False

    logger.info("=" * 60)

    if all_passed:
        logger.info("\n🎉 All tests passed! Redis integration is working correctly.")
        return 0
    else:
        logger.error("\n❌ Some tests failed. Please check the logs above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
