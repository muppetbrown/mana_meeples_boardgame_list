import os
import sys

# CORS origins, comma-separated
CORS_ORIGINS = [
    o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()
]

# Admin token for protected endpoints
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
if not ADMIN_TOKEN:
    print(
        "WARNING: ADMIN_TOKEN not set - admin endpoints will be unavailable",
        file=sys.stderr,
    )

# Database configuration
# Production: PostgreSQL on Render
# Local dev: SQLite fallback for testing
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# Validate database configuration
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

if DATABASE_URL.startswith("postgresql://"):
    print(
        f"Using PostgreSQL database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'unknown'}",
        file=sys.stderr,
    )
elif DATABASE_URL.startswith("sqlite"):
    print(f"Using SQLite database: {DATABASE_URL}", file=sys.stderr)
else:
    print(
        f"WARNING: Unrecognized database URL format: {DATABASE_URL[:20]}...",
        file=sys.stderr,
    )

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

# API base URL for image proxying and absolute URLs
API_BASE = (
    PUBLIC_BASE_URL or "https://mana-meeples-boardgame-list.onrender.com"
)

# HTTP client configuration
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "30"))
HTTP_RETRIES = int(os.getenv("HTTP_RETRIES", "3"))

# Rate limiting configuration
RATE_LIMIT_ATTEMPTS = int(os.getenv("RATE_LIMIT_ATTEMPTS", "5"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "300"))  # 5 minutes

# Debug configuration for BGG data extraction
SAVE_DEBUG_INFO = os.getenv("SAVE_DEBUG_INFO", "false").lower() in (
    "true",
    "1",
    "yes",
)

# Session configuration
# In production, set SESSION_SECRET to a secure random value
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
SESSION_SECRET = os.getenv("SESSION_SECRET", "")
if not SESSION_SECRET:
    import secrets

    SESSION_SECRET = secrets.token_hex(32)
    print(
        "WARNING: SESSION_SECRET not set - generated temporary secret (not suitable for multi-instance deployment)",
        file=sys.stderr,
    )

# Session timeout (1 hour by default)
SESSION_TIMEOUT_SECONDS = int(os.getenv("SESSION_TIMEOUT_SECONDS", "3600"))
