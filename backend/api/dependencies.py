# api/dependencies.py
"""
Shared dependencies for API endpoints: admin authentication and helpers.
"""
import logging
import secrets
from typing import Optional

from fastapi import Header, HTTPException, Request

from config import (
    ADMIN_TOKEN,
    DISABLE_RATE_LIMITING,
    RATE_LIMIT_ATTEMPTS,
    RATE_LIMIT_WINDOW,
)
from shared.rate_limiting import (
    cleanup_expired_attempts,
    record_failed_attempt,
)
from utils.jwt_utils import verify_jwt_token, extract_token_from_header

logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies"""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def require_admin_auth(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_admin_token: Optional[str] = Header(None),
) -> None:
    """
    Dependency for admin endpoints.
    Validates admin authentication via JWT token (preferred) or X-Admin-Token header (fallback).

    Authentication methods (in order):
    1. JWT token from Authorization header (preferred)
    2. X-Admin-Token header (fallback for backward compatibility)

    Raises:
        HTTPException: 401 if authentication fails, 429 if rate limited
    """
    client_ip = get_client_ip(request)

    # 1. Try JWT token from Authorization header (preferred method)
    jwt_token = extract_token_from_header(authorization)
    if jwt_token:
        payload = verify_jwt_token(jwt_token)
        if payload:
            logger.debug(f"Valid JWT authentication from {client_ip}")
            return  # Valid JWT, authentication successful

    # 2. Fall back to direct admin token header (for backward compatibility)
    # Sprint 8: Use Redis-backed rate limiting (unless disabled for testing)
    if not DISABLE_RATE_LIMITING:
        # Check if rate limited (cleanup expired attempts and get current count)
        attempt_count = cleanup_expired_attempts(client_ip, RATE_LIMIT_WINDOW)
        if attempt_count >= RATE_LIMIT_ATTEMPTS:
            logger.warning(f"Rate limited admin token attempts from {client_ip}")
            raise HTTPException(
                status_code=429,
                detail=(
                    "Too many failed authentication attempts. "
                    "Please try again later."
                ),
            )

    # Validate direct admin token (using constant-time comparison to prevent timing attacks)
    if not ADMIN_TOKEN or not secrets.compare_digest(x_admin_token or "", ADMIN_TOKEN):
        if not DISABLE_RATE_LIMITING:
            record_failed_attempt(client_ip, RATE_LIMIT_WINDOW)
        logger.warning(f"Invalid admin token attempt from {client_ip}")
        raise HTTPException(status_code=401, detail="Invalid admin token")
