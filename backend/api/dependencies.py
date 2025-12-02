# api/dependencies.py
"""
Shared dependencies for API endpoints including authentication,
session management, and helper functions.
"""
import time
import secrets
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import Header, Cookie, HTTPException, Request
from config import (
    ADMIN_TOKEN,
    RATE_LIMIT_ATTEMPTS,
    RATE_LIMIT_WINDOW,
    SESSION_TIMEOUT_SECONDS
)
import logging

logger = logging.getLogger(__name__)

# Import shared session storage and rate limiting
from shared.rate_limiting import admin_sessions, admin_attempt_tracker


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies"""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def create_session(client_ip: str) -> str:
    """Create a new admin session and return session token"""
    session_token = secrets.token_urlsafe(32)
    admin_sessions[session_token] = {
        "created_at": datetime.utcnow(),
        "ip": client_ip
    }
    logger.info(f"Created new admin session from {client_ip}")
    return session_token


def validate_session(session_token: Optional[str], client_ip: str) -> bool:
    """Validate admin session token"""
    if not session_token or session_token not in admin_sessions:
        return False

    session = admin_sessions[session_token]

    # Check if session has expired
    session_age = (datetime.utcnow() - session["created_at"]).total_seconds()
    if session_age > SESSION_TIMEOUT_SECONDS:
        logger.info(f"Session expired for {client_ip} (age: {session_age}s)")
        del admin_sessions[session_token]
        return False

    return True


def cleanup_expired_sessions():
    """Remove expired sessions from storage"""
    current_time = datetime.utcnow()
    expired_tokens = [
        token for token, session in admin_sessions.items()
        if (current_time - session["created_at"]).total_seconds() > SESSION_TIMEOUT_SECONDS
    ]
    for token in expired_tokens:
        del admin_sessions[token]
    if expired_tokens:
        logger.info(f"Cleaned up {len(expired_tokens)} expired sessions")


def revoke_session(session_token: Optional[str]):
    """Revoke/logout an admin session"""
    if session_token and session_token in admin_sessions:
        del admin_sessions[session_token]
        logger.info(f"Revoked admin session")


def require_admin_auth(
    request: Request,
    x_admin_token: Optional[str] = Header(None),
    admin_session: Optional[str] = Cookie(None)
) -> None:
    """
    Dependency for admin endpoints.
    Validates admin authentication via session cookie or token header.

    Raises:
        HTTPException: 401 if authentication fails, 429 if rate limited
    """
    client_ip = get_client_ip(request)

    # Clean up expired sessions periodically
    cleanup_expired_sessions()

    # Try session cookie first (preferred method)
    if admin_session and validate_session(admin_session, client_ip):
        return  # Valid session, authentication successful

    # Fall back to legacy header-based token authentication
    current_time = time.time()

    # Clean old attempts from tracker
    cutoff_time = current_time - RATE_LIMIT_WINDOW
    admin_attempt_tracker[client_ip] = [
        attempt_time for attempt_time in admin_attempt_tracker[client_ip]
        if attempt_time > cutoff_time
    ]

    # Check if rate limited
    if len(admin_attempt_tracker[client_ip]) >= RATE_LIMIT_ATTEMPTS:
        logger.warning(f"Rate limited admin token attempts from {client_ip}")
        raise HTTPException(
            status_code=429,
            detail="Too many failed authentication attempts. Please try again later."
        )

    # Validate token
    if not ADMIN_TOKEN or x_admin_token != ADMIN_TOKEN:
        admin_attempt_tracker[client_ip].append(current_time)
        logger.warning(f"Invalid admin token attempt from {client_ip}")
        raise HTTPException(status_code=401, detail="Invalid admin token")
