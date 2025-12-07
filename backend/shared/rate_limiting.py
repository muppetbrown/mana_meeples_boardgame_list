# shared/rate_limiting.py
"""
Shared rate limiting configuration and utilities.
Centralizes rate limiting setup to avoid circular imports and improve modularity.
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from collections import defaultdict
from typing import Dict, List, Any


def get_limiter() -> Limiter:
    """Create and configure the rate limiter instance"""
    return Limiter(key_func=get_remote_address)


def get_rate_limit_exception_handler():
    """Get the rate limit exception handler"""
    return _rate_limit_exceeded_handler


def get_rate_limit_exception():
    """Get the rate limit exception class"""
    return RateLimitExceeded


# Admin authentication attempt tracking
# TODO: Move to Redis or database for multi-instance deployments
admin_attempt_tracker: Dict[str, List[float]] = defaultdict(list)

# Admin session storage
# TODO: Move to Redis or database for multi-instance deployments
admin_sessions: Dict[str, Dict[str, Any]] = {}
