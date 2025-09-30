import os

# CORS origins, comma-separated
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]

# Admin token for protected endpoints (we’ll use it in Phase 3)
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

# SQLite by default; on Render we’ll set sqlite:////data/app.db
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

# HTTP client configuration
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "30"))
HTTP_RETRIES = int(os.getenv("HTTP_RETRIES", "3"))

# Rate limiting configuration
RATE_LIMIT_ATTEMPTS = int(os.getenv("RATE_LIMIT_ATTEMPTS", "5"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "300"))  # 5 minutes

# Debug configuration for BGG data extraction
SAVE_DEBUG_INFO = os.getenv("SAVE_DEBUG_INFO", "false").lower() in ("true", "1", "yes")
