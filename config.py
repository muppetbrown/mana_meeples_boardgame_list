import os

# CORS origins, comma-separated
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]

# Admin token for protected endpoints (we’ll use it in Phase 3)
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

# SQLite by default; on Render we’ll set sqlite:////data/app.db
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
