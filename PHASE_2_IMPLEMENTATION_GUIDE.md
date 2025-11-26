# Phase 2: Backend Reorganization - Implementation Guide

## Overview
This guide provides step-by-step instructions to break apart the 1,712-line `main.py` into a clean, maintainable structure.

**Estimated Time:** 12-16 hours
**Current Status:** Directory structure created ✅

---

## Directory Structure Created

```
backend/
├── api/
│   ├── __init__.py ✅
│   └── routers/
│       └── __init__.py ✅
├── services/
│   └── __init__.py ✅
├── middleware/
│   └── __init__.py ✅
└── utils/
    └── __init__.py ✅
```

---

## Step 1: Extract Middleware (2 hours)

### 1.1 Create `middleware/performance.py`

```python
# middleware/performance.py
import time
from collections import deque, OrderedDict

class PerformanceMonitor:
    """Monitor API performance with LRU eviction to prevent memory leaks"""

    def __init__(self):
        self.request_times = deque(maxlen=1000)  # Keep last 1000 requests
        self.endpoint_stats = OrderedDict()  # Use OrderedDict to prevent unbounded growth
        self.max_endpoints = 100  # Maximum unique endpoints to track
        self.slow_queries = deque(maxlen=100)  # Keep last 100 slow queries

    def record_request(self, path: str, method: str, duration: float, status_code: int):
        """Record request metrics with LRU eviction"""
        self.request_times.append(duration)
        endpoint_key = f"{method} {path}"

        # Trim old endpoints if we've hit the limit (LRU eviction)
        if endpoint_key not in self.endpoint_stats and len(self.endpoint_stats) >= self.max_endpoints:
            self.endpoint_stats.popitem(last=False)  # Remove oldest endpoint

        # Initialize stats if new endpoint
        if endpoint_key not in self.endpoint_stats:
            self.endpoint_stats[endpoint_key] = {"count": 0, "total_time": 0, "errors": 0}

        # Move to end (mark as recently used)
        stats = self.endpoint_stats.pop(endpoint_key)
        stats["count"] += 1
        stats["total_time"] += duration
        if status_code >= 400:
            stats["errors"] += 1
        self.endpoint_stats[endpoint_key] = stats

        # Record slow queries (>2 seconds)
        if duration > 2.0:
            self.slow_queries.append({
                "path": path,
                "method": method,
                "duration": duration,
                "timestamp": time.time()
            })

    def get_stats(self):
        """Get performance statistics"""
        if not self.request_times:
            return {"message": "No requests recorded yet"}

        total_requests = len(self.request_times)
        avg_response_time = sum(self.request_times) / total_requests

        return {
            "total_requests": total_requests,
            "avg_response_time_ms": round(avg_response_time * 1000, 2),
            "slowest_endpoints": sorted([
                {
                    "endpoint": endpoint,
                    "avg_time_ms": round((stats["total_time"] / stats["count"]) * 1000, 2),
                    "requests": stats["count"],
                    "errors": stats["errors"]
                }
                for endpoint, stats in self.endpoint_stats.items()
            ], key=lambda x: x["avg_time_ms"], reverse=True)[:10],
            "recent_slow_queries": list(self.slow_queries)[-10:]
        }

# Global instance
performance_monitor = PerformanceMonitor()
```

### 1.2 Create `middleware/logging.py`

```python
# middleware/logging.py
import time
import uuid
import logging
from starlette.types import ASGIApp, Receive, Scope, Send
from .performance import performance_monitor

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware:
    """Log all HTTP requests with timing and request IDs"""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]
        status_code = 200  # Default

        # Add request ID to scope for downstream handlers
        scope["request_id"] = request_id

        path = scope.get("path", "")
        method = scope.get("method", "")

        logger.info(f"Request started: {method} {path}", extra={'request_id': request_id})

        # Capture status code from response
        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            duration = time.time() - start_time
            status_code = 500
            performance_monitor.record_request(path, method, duration, status_code)
            logger.error(
                f"Request failed: {method} {path} - {str(e)} ({duration:.3f}s)",
                extra={'request_id': request_id}
            )
            raise
        else:
            duration = time.time() - start_time
            performance_monitor.record_request(path, method, duration, status_code)
            logger.info(
                f"Request completed: {method} {path} ({duration:.3f}s)",
                extra={'request_id': request_id}
            )
```

---

## Step 2: Extract Dependencies (1 hour)

### 2.1 Create `api/dependencies.py`

```python
# api/dependencies.py
"""
Shared dependencies for API endpoints including authentication,
session management, and helper functions.
"""
import time
import secrets
from typing import Optional, Dict, Any
from datetime import datetime
from collections import defaultdict
from fastapi import Header, Cookie, HTTPException, Request
from config import (
    ADMIN_TOKEN,
    RATE_LIMIT_ATTEMPTS,
    RATE_LIMIT_WINDOW,
    SESSION_SECRET,
    SESSION_TIMEOUT_SECONDS
)
import logging

logger = logging.getLogger(__name__)

# Session storage for admin authentication
# Format: {session_token: {"created_at": datetime, "ip": str}}
admin_sessions: Dict[str, Dict[str, Any]] = {}

# Rate limiting for admin authentication attempts
admin_attempt_tracker = defaultdict(list)

def _get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies"""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def _create_session(client_ip: str) -> str:
    """Create a new admin session and return session token"""
    session_token = secrets.token_urlsafe(32)
    admin_sessions[session_token] = {
        "created_at": datetime.utcnow(),
        "ip": client_ip
    }
    logger.info(f"Created new admin session from {client_ip}")
    return session_token

def _validate_session(session_token: Optional[str], client_ip: str) -> bool:
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

def _cleanup_expired_sessions():
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

def _revoke_session(session_token: Optional[str]):
    """Revoke/logout an admin session"""
    if session_token and session_token in admin_sessions:
        del admin_sessions[session_token]
        logger.info(f"Revoked admin session")

def require_admin_auth(
    x_admin_token: Optional[str] = Header(None),
    admin_session: Optional[str] = Cookie(None),
    request: Request = None
) -> None:
    """
    Dependency for admin endpoints.
    Validates admin authentication via session cookie or token header.

    Usage:
        @router.get("/admin/endpoint")
        async def endpoint(auth: None = Depends(require_admin_auth)):
            # Endpoint logic
    """
    client_ip = _get_client_ip(request) if request else "unknown"

    # Clean up expired sessions periodically
    _cleanup_expired_sessions()

    # Try session cookie first (preferred method)
    if admin_session and _validate_session(admin_session, client_ip):
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
```

---

## Step 3: Extract Public Router (2 hours)

### 3.1 Create `api/routers/public.py`

This file will contain all `/api/public/*` endpoints.

**Key endpoints to move:**
- `GET /api/public/games`
- `GET /api/public/games/{game_id}`
- `GET /api/public/category-counts`
- `GET /api/public/games/by-designer/{designer_name}`
- `GET /api/public/image-proxy`

**Template:**

```python
# api/routers/public.py
from fastapi import APIRouter, Depends, Query, Request, Path
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Optional

from database import get_db
from models import Game
from exceptions import GameNotFoundError
# Import helper functions from main.py (will be moved to services later)

router = APIRouter(prefix="/api/public", tags=["public"])
limiter = Limiter(key_func=get_remote_address)

@router.get("/games")
@limiter.limit("100/minute")
async def get_public_games(
    request: Request,
    q: str = Query("", description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(24, ge=1, le=1000, description="Items per page"),
    sort: str = Query("title_asc", description="Sort order"),
    category: Optional[str] = Query(None, description="Category filter"),
    designer: Optional[str] = Query(None, description="Designer filter"),
    nz_designer: Optional[bool] = Query(None, description="NZ designer filter"),
    db: Session = Depends(get_db)
):
    """Get paginated list of games with filters"""
    # Move logic from main.py here
    pass

# ... Add other public endpoints
```

---

## Step 4: Extract Admin Router (2 hours)

### 4.1 Create `api/routers/admin.py`

**Key endpoints:**
- `POST /api/admin/login`
- `POST /api/admin/logout`
- `GET /api/admin/validate`
- `GET /api/admin/games`
- `GET /api/admin/games/{game_id}`
- `PUT /api/admin/games/{game_id}`
- `POST /api/admin/games/{game_id}/update`
- `DELETE /api/admin/games/{game_id}`
- `POST /api/admin/games`
- `POST /api/admin/import/bgg`

---

## Step 5: Extract Bulk Router (1 hour)

### 5.1 Create `api/routers/bulk.py`

**Key endpoints:**
- `POST /api/admin/bulk-import-csv`
- `POST /api/admin/bulk-categorize-csv`
- `POST /api/admin/bulk-update-nz-designers`
- `POST /api/admin/reimport-all-games`

---

## Step 6: Extract Health Router (1 hour)

### 6.1 Create `api/routers/health.py`

**Key endpoints:**
- `GET /api/health`
- `GET /api/health/db`
- `GET /api/debug/categories`
- `GET /api/debug/database-info`
- `GET /api/debug/performance`
- `GET /api/debug/export-games-csv`

---

## Step 7: Extract Services (3 hours)

### 7.1 Create `services/game_service.py`

Extract all game-related business logic:
- Game filtering and sorting logic
- Category calculation
- Game CRUD operations
- Helper functions like `_game_to_dict`, `_parse_categories`, `_categorize_game`

### 7.2 Create `services/image_service.py`

Extract image/thumbnail handling:
- `_download_thumbnail`
- `_download_and_update_thumbnail` (background task)
- Thumbnail caching logic

---

## Step 8: Create New main.py (1 hour)

### 8.1 New minimal `main.py`

```python
# main.py
"""
Mana & Meeples Board Game Library API
Main application entry point - minimal configuration only
"""
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi import Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import CORS_ORIGINS
from database import engine, init_db, run_migrations
from models import Base
from exceptions import GameNotFoundError, ValidationError, BGGServiceError, DatabaseError
from middleware.logging import RequestLoggingMiddleware
from middleware.performance import performance_monitor

# Import routers
from api.routers import public, admin, bulk, health

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize database
init_db()
run_migrations()
Base.metadata.create_all(bind=engine)

# Create app
app = FastAPI(
    title="Mana & Meeples Board Game Library API",
    version="2.0.0",
    description="Public game catalogue and admin management"
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Exception handlers
@app.exception_handler(GameNotFoundError)
async def game_not_found_handler(request: Request, exc: GameNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})

@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})

@app.exception_handler(BGGServiceError)
async def bgg_service_error_handler(request: Request, exc: BGGServiceError):
    return JSONResponse(status_code=503, content={"detail": f"BGG service error: {str(exc)}"})

@app.exception_handler(DatabaseError)
async def database_error_handler(request: Request, exc: DatabaseError):
    return JSONResponse(status_code=500, content={"detail": f"Database error: {str(exc)}"})

# CORS middleware
cors_origins = CORS_ORIGINS.copy()
if "http://localhost:3000" not in cors_origins:
    cors_origins = cors_origins + ["http://localhost:3000", "http://127.0.0.1:3000"]

logger.info(f"CORS origins configured: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware
app.add_middleware(RequestLoggingMiddleware)

# Static files
THUMBS_DIR = os.getenv("THUMBS_DIR", "/tmp/thumbs")
os.makedirs(THUMBS_DIR, exist_ok=True)
app.mount("/thumbs", StaticFiles(directory=THUMBS_DIR), name="thumbs")

# Include routers
app.include_router(public.router)
app.include_router(admin.router)
app.include_router(bulk.router)
app.include_router(health.router)

# Root endpoint
@app.get("/")
async def root():
    return {
        "name": "Mana & Meeples Board Game Library API",
        "version": "2.0.0",
        "status": "operational"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## Step 9: Testing (2 hours)

### 9.1 Test Checklist

- [ ] All public endpoints work
- [ ] All admin endpoints work
- [ ] Authentication still works (both cookie and header)
- [ ] Rate limiting functions correctly
- [ ] Performance monitoring still records requests
- [ ] Logging outputs correctly
- [ ] No import errors
- [ ] Database operations succeed

### 9.2 Manual Testing

```bash
# Test public endpoints
curl http://localhost:8000/api/public/games
curl http://localhost:8000/api/public/category-counts

# Test admin login
curl -X POST http://localhost:8000/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{"token": "YOUR_ADMIN_TOKEN"}'

# Test health endpoints
curl http://localhost:8000/api/health
curl http://localhost:8000/api/health/db
```

---

## Step 10: Commit (30 min)

```bash
git add api/ services/ middleware/ utils/ main.py
git commit -m "Phase 2: Backend reorganization - modular structure

- Extracted middleware to middleware/ directory
- Created api/routers/ for endpoint organization
- Separated business logic into services/
- New minimal main.py (50 lines vs 1,712)
- Maintained all functionality with cleaner structure
"
git push
```

---

## Benefits After Completion

✅ **Maintainability:** Easy to find and modify specific functionality
✅ **Testability:** Each module can be tested in isolation
✅ **Scalability:** Clear structure for adding new features
✅ **Collaboration:** Multiple developers can work without conflicts
✅ **Code Review:** Smaller, focused files are easier to review

---

## Troubleshooting

### Import Errors
- Ensure all `__init__.py` files exist
- Use relative imports within modules: `from ..database import get_db`
- Use absolute imports from main: `from api.routers import public`

### Circular Dependencies
- Move shared utilities to `utils/` directory
- Use dependency injection instead of direct imports where possible

### Missing Dependencies
- If you get `ModuleNotFoundError`, check that all imports are updated
- The `performance_monitor` global instance needs to be accessible from middleware

---

## Next Phase

After completing Phase 2, move to:
- **Phase 3:** Frontend Reorganization
- **Phase 4:** Testing & CI/CD
- **Phase 5:** Documentation

See `REFACTORING_PLAN.md` for complete roadmap.
