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

# Read replica configuration (optional, for performance optimization)
# If not set, all operations use the primary database
READ_REPLICA_URL = os.getenv("READ_REPLICA_URL", "")

# Validate database configuration
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

if DATABASE_URL.startswith("postgresql://"):
    print(
        f"Using PostgreSQL database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'unknown'}",
        file=sys.stderr,
    )
    if READ_REPLICA_URL:
        print(
            f"Read replica enabled: {READ_REPLICA_URL.split('@')[1] if '@' in READ_REPLICA_URL else 'unknown'}",
            file=sys.stderr,
        )
    else:
        print(
            "Read replica not configured - using primary database for all operations",
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

# BoardGameGeek API configuration
BGG_API_KEY = os.getenv("BGG_API_KEY", "")
if not BGG_API_KEY:
    print(
        "WARNING: BGG_API_KEY not set - BGG API requests may be rate limited or fail",
        file=sys.stderr,
    )

# Rate limiting configuration
RATE_LIMIT_ATTEMPTS = int(os.getenv("RATE_LIMIT_ATTEMPTS", "5"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "300"))  # 5 minutes
DISABLE_RATE_LIMITING = os.getenv("DISABLE_RATE_LIMITING", "false").lower() in ("true", "1", "yes")

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

# JWT configuration
# JWT tokens are valid for 7 days by default
JWT_EXPIRATION_DAYS = int(os.getenv("JWT_EXPIRATION_DAYS", "7"))

# GitHub configuration for triggering workflows
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO_OWNER = os.getenv("GITHUB_REPO_OWNER", "muppetbrown")
GITHUB_REPO_NAME = os.getenv("GITHUB_REPO_NAME", "mana_meeples_boardgame_list")
if not GITHUB_TOKEN:
    print(
        "WARNING: GITHUB_TOKEN not set - workflow triggering will be unavailable",
        file=sys.stderr,
    )

# Cloudinary configuration for image CDN and optimization
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "")
CLOUDINARY_ENABLED = bool(CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET)

if CLOUDINARY_ENABLED:
    print(
        f"Cloudinary CDN enabled: {CLOUDINARY_CLOUD_NAME}",
        file=sys.stderr,
    )
else:
    print(
        "WARNING: Cloudinary not configured - using direct BGG image URLs",
        file=sys.stderr,
    )

# Redis configuration (Sprint 8: Redis Session Storage)
# For horizontal scaling and multi-instance deployments
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() in ("true", "1", "yes")

if REDIS_ENABLED:
    # Extract host for logging (hide password if present)
    try:
        from urllib.parse import urlparse
        parsed = urlparse(REDIS_URL)
        redis_host = parsed.hostname or "localhost"
        redis_port = parsed.port or 6379
        print(
            f"Redis enabled: {redis_host}:{redis_port}",
            file=sys.stderr,
        )
    except Exception:
        print("Redis enabled: configuration loaded", file=sys.stderr)
else:
    print(
        "WARNING: Redis disabled - using in-memory storage (not suitable for multi-instance deployment)",
        file=sys.stderr,
    )
