# api/dependencies.py
"""
Shared dependencies for API endpoints including authentication,
session management, and helper functions.
"""
import logging
import secrets
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import Cookie, Header, HTTPException, Request

from config import (
    ADMIN_TOKEN,
    DISABLE_RATE_LIMITING,
    RATE_LIMIT_ATTEMPTS,
    RATE_LIMIT_WINDOW,
    SESSION_TIMEOUT_SECONDS,
)
from shared.rate_limiting import (
    admin_attempt_tracker,  # Legacy - for backward compatibility
    admin_sessions,  # Legacy - for backward compatibility
    session_storage,  # New Redis-backed storage
    rate_limit_tracker,  # New Redis-backed tracker
)
from utils.jwt_utils import verify_jwt_token, extract_token_from_header

logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies"""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def create_session(client_ip: str) -> str:
    """
    Create a new admin session and return session token.
    Sprint 8: Uses Redis for storage when available.
    """
    session_token = secrets.token_urlsafe(32)
    session_data = {
        "created_at": datetime.now(timezone.utc),
        "ip": client_ip,
    }

    # Store in Redis-backed storage (with automatic fallback to memory)
    session_storage.set_session(session_token, session_data, SESSION_TIMEOUT_SECONDS)
    logger.info(f"Created new admin session from {client_ip}")
    return session_token


def validate_session(session_token: Optional[str], client_ip: str) -> bool:
    """
    Validate admin session token.
    Sprint 8: Uses Redis for storage when available.
    """
    if not session_token:
        return False

    # Retrieve from Redis-backed storage (with automatic fallback to memory)
    session = session_storage.get_session(session_token)
    if not session:
        return False

    # Check if session has expired (should be handled by Redis TTL, but double-check)
    session_age = (datetime.now(timezone.utc) - session["created_at"]).total_seconds()
    if session_age > SESSION_TIMEOUT_SECONDS:
        logger.info(f"Session expired for {client_ip} (age: {session_age}s)")
        session_storage.delete_session(session_token)
        return False

    return True


def cleanup_expired_sessions():
    """
    Remove expired sessions from storage.
    Sprint 8: Redis handles expiration automatically via TTL, but we keep
    this function for backward compatibility with in-memory fallback.
    """
    # Redis handles this automatically via TTL
    # Only needed for in-memory fallback (legacy admin_sessions dict)
    if admin_sessions:
        current_time = datetime.now(timezone.utc)
        expired_tokens = [
            token
            for token, session in admin_sessions.items()
            if (current_time - session["created_at"]).total_seconds()
            > SESSION_TIMEOUT_SECONDS
        ]
        for token in expired_tokens:
            del admin_sessions[token]
        if expired_tokens:
            logger.info(f"Cleaned up {len(expired_tokens)} expired sessions from memory")


def revoke_session(session_token: Optional[str]):
    """
    Revoke/logout an admin session.
    Sprint 8: Uses Redis for storage when available.
    """
    if session_token:
        session_storage.delete_session(session_token)
        logger.info("Revoked admin session")


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
        current_time = time.time()

        # Get current attempts from Redis-backed tracker
        attempts = rate_limit_tracker.get_attempts(client_ip)

        # Clean old attempts from tracker
        cutoff_time = current_time - RATE_LIMIT_WINDOW
        attempts = [attempt_time for attempt_time in attempts if attempt_time > cutoff_time]

        # Check if rate limited
        if len(attempts) >= RATE_LIMIT_ATTEMPTS:
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
            current_time = time.time()
            attempts = rate_limit_tracker.get_attempts(client_ip)
            cutoff_time = current_time - RATE_LIMIT_WINDOW
            attempts = [attempt_time for attempt_time in attempts if attempt_time > cutoff_time]
            attempts.append(current_time)
            rate_limit_tracker.set_attempts(client_ip, attempts, RATE_LIMIT_WINDOW)
        logger.warning(f"Invalid admin token attempt from {client_ip}")
        raise HTTPException(status_code=401, detail="Invalid admin token")
