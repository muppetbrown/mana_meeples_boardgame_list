# utils/jwt_utils.py
"""
JWT token utilities for admin authentication.
Provides stateless authentication that persists across server restarts.
"""
import jwt
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import hashlib
import hmac

import config

logger = logging.getLogger(__name__)

# JWT configuration
JWT_ALGORITHM = "HS256"


def _admin_token_fingerprint() -> str:
    """Short fingerprint of the current ADMIN_TOKEN, carried in every JWT.

    A JWT is only accepted while its fingerprint matches, so changing ADMIN_TOKEN signs
    out every session issued under the old one. Without it, rotating a leaked admin
    token left already-issued JWTs valid for up to JWT_EXPIRATION_DAYS.
    """
    return hashlib.sha256(config.ADMIN_TOKEN.encode()).hexdigest()[:16]


def generate_jwt_token(client_ip: str) -> str:
    """
    Generate a JWT token for admin authentication.

    Args:
        client_ip: Client IP address for auditing

    Returns:
        JWT token string
    """
    # Token payload
    payload = {
        "sub": "admin",  # Subject (admin user)
        "ip": client_ip,  # Client IP for auditing
        "tv": _admin_token_fingerprint(),  # Revoked when ADMIN_TOKEN changes
        "iat": datetime.now(timezone.utc),  # Issued at
        "exp": datetime.now(timezone.utc) + timedelta(days=config.JWT_EXPIRATION_DAYS),  # Expiration
    }

    # Generate token
    token = jwt.encode(payload, config.SESSION_SECRET, algorithm=JWT_ALGORITHM)
    logger.info(f"Generated JWT token for {client_ip}, expires in {config.JWT_EXPIRATION_DAYS} days")

    return token


def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload if valid, None if invalid or expired
    """
    try:
        # Decode and verify token
        payload = jwt.decode(token, config.SESSION_SECRET, algorithms=[JWT_ALGORITHM])
        if not hmac.compare_digest(str(payload.get("tv", "")), _admin_token_fingerprint()):
            logger.warning("JWT token was issued under a different admin token")
            return None
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        return None


def extract_token_from_header(authorization: Optional[str]) -> Optional[str]:
    """
    Extract JWT token from Authorization header.

    Args:
        authorization: Authorization header value (e.g., "Bearer <token>")

    Returns:
        Token string if valid format, None otherwise
    """
    if not authorization:
        return None

    # Expected format: "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.warning(f"Invalid Authorization header format: {authorization[:20]}...")
        return None

    return parts[1]
