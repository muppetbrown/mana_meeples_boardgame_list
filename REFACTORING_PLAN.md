# Comprehensive Refactoring & Improvement Plan
## Mana & Meeples Board Game Library

**Generated:** 2025-11-26
**Current State:** Functional but organizationally fragmented
**Goal:** Well-structured, maintainable, production-ready codebase

---

## Executive Summary

The codebase analysis revealed a functional but "hodgepodge" structure with several critical issues:

- **Backend:** 1,712-line monolithic `main.py` with mixed concerns
- **Frontend:** Duplicate API clients, inconsistent patterns, missing optimizations
- **Security:** Admin token vulnerabilities, XSS risks, no rate limiting on public endpoints
- **Performance:** Inefficient JSON queries, unbounded memory growth, large bundle size
- **Testing:** <10% coverage, no CI/CD pipeline

**Estimated Total Effort:** 80-120 hours (2-3 weeks full-time)

---

## Phase 1: Critical Fixes (IMMEDIATE - Days 1-2)

### 1.1 Security Vulnerabilities

#### Fix 1: Admin Token Storage (4 hours)
**Priority:** CRITICAL
**Files:** `frontend/src/api/client.js`, `backend/main.py`

**Current Issue:**
- Token stored in localStorage (vulnerable to XSS)
- No expiration
- Race condition between validation and use

**Solution:**
```python
# backend: Add session cookie endpoint
@app.post("/api/admin/login")
async def admin_login(credentials: AdminCredentials, response: Response):
    if credentials.token != ADMIN_TOKEN:
        raise HTTPException(status_code=401)

    # Set httpOnly cookie
    response.set_cookie(
        key="admin_session",
        value=create_session_token(),
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=3600  # 1 hour
    )
    return {"success": True}

# frontend: Remove localStorage, use cookies
const login = async (token) => {
    await axios.post('/api/admin/login', { token });
    // Cookie set automatically
};
```

#### Fix 2: XSS Prevention in Game Descriptions (2 hours)
**Priority:** HIGH
**Files:** `frontend/src/pages/GameDetails.jsx`

**Current Issue:**
- BGG descriptions rendered as raw HTML
- No sanitization

**Solution:**
```bash
npm install dompurify
```

```javascript
import DOMPurify from 'dompurify';

// In GameDetails.jsx
<p className="text-slate-700 leading-relaxed">
  {game.description
    ? <div dangerouslySetInnerHTML={{
        __html: DOMPurify.sanitize(game.description)
      }} />
    : "No description available"}
</p>
```

#### Fix 3: Rate Limiting on Public Endpoints (2 hours)
**Priority:** HIGH
**Files:** `backend/main.py`

**Solution:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/api/public/games")
@limiter.limit("100/minute")  # Reasonable for browsing
async def get_public_games(...):
    ...
```

---

### 1.2 Critical Bugs

#### Fix 4: Memory Leak in PerformanceMonitor (1 hour)
**Priority:** CRITICAL
**Files:** `backend/main.py` lines 182-228

**Current Issue:**
```python
self.endpoint_stats = defaultdict(lambda: {...})  # Grows unbounded
```

**Solution:**
```python
from collections import OrderedDict

class PerformanceMonitor:
    def __init__(self):
        self.request_times = deque(maxlen=1000)
        self.endpoint_stats = OrderedDict()  # Changed
        self.slow_queries = deque(maxlen=100)
        self.max_endpoints = 50  # NEW: Cap unique endpoints

    def record_request(self, endpoint: str, duration: float):
        # Trim if too large
        if len(self.endpoint_stats) >= self.max_endpoints:
            # Remove oldest entry
            self.endpoint_stats.popitem(last=False)

        if endpoint not in self.endpoint_stats:
            self.endpoint_stats[endpoint] = {
                "count": 0,
                "total_time": 0.0,
                "min_time": float("inf"),
                "max_time": 0.0
            }
        # ... rest of logic
```

#### Fix 5: Background Task Error Handling (3 hours)
**Priority:** HIGH
**Files:** `backend/main.py` lines 592-686

**Current Issue:**
- Thumbnail downloads fail silently
- User gets success before task runs
- No retry mechanism

**Solution:**
```python
from enum import Enum

class ThumbnailStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    READY = "ready"
    FAILED = "failed"

# Add column to Game model
thumbnail_status = Column(String(20), default="pending")

@app.post("/api/admin/games")
async def create_game(...):
    # ... create game logic

    if thumbnail_url:
        game.thumbnail_status = ThumbnailStatus.PENDING
        db.commit()

        # Background task now updates status
        background_tasks.add_task(
            _download_and_update_thumbnail_with_retry,
            game.id,
            thumbnail_url,
            max_retries=3
        )

    return _game_to_dict(request, game)

async def _download_and_update_thumbnail_with_retry(
    game_id: int,
    thumbnail_url: str,
    max_retries: int = 3
):
    db = SessionLocal()
    game = db.query(Game).filter_by(id=game_id).first()

    for attempt in range(max_retries):
        try:
            game.thumbnail_status = ThumbnailStatus.DOWNLOADING
            db.commit()

            # Download logic
            local_path = await download_thumbnail(thumbnail_url, game_id)

            game.thumbnail_file = local_path
            game.thumbnail_status = ThumbnailStatus.READY
            db.commit()
            logger.info(f"✓ Thumbnail downloaded for game {game_id}")
            return

        except Exception as e:
            logger.error(f"Attempt {attempt+1}/{max_retries} failed: {e}")
            if attempt == max_retries - 1:
                game.thumbnail_status = ThumbnailStatus.FAILED
                db.commit()

    db.close()
```

#### Fix 6: JSON Column Query Performance (2 hours)
**Priority:** HIGH
**Files:** `backend/main.py` lines 830-844

**Current Issue:**
```python
search_conditions.append(Game.designers.ilike(search_term))  # Table scan!
```

**Solution:**
```python
# In database.py - add after table creation
def create_indexes(engine):
    """Create performance indexes"""
    with engine.connect() as conn:
        # GIN index for JSON containment searches
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_designers_gin
            ON boardgames USING GIN (designers jsonb_path_ops)
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_mechanics_gin
            ON boardgames USING GIN (mechanics jsonb_path_ops)
        """))

        conn.commit()

# In main.py - change ILIKE to JSON containment
# Instead of:
search_conditions.append(Game.designers.ilike(search_term))

# Use:
from sqlalchemy.dialects.postgresql import JSONB
search_conditions.append(
    Game.designers.cast(JSONB).contains([designer_name])
)
```

**Note:** This requires exact match. For fuzzy search, need to denormalize to separate table.

---

## Phase 2: Backend Reorganization (Days 3-5)

### 2.1 Break Apart Monolithic main.py

**Goal:** Transform 1,712-line `main.py` into organized modules

#### New Structure:
```
backend/
├── main.py (50 lines - app initialization only)
├── config.py (environment variables, settings)
├── database.py (existing - keep as-is)
├── models.py (existing - keep as-is)
├── api/
│   ├── __init__.py
│   ├── dependencies.py (auth, rate limiting)
│   └── routers/
│       ├── __init__.py
│       ├── public.py (public game endpoints)
│       ├── admin.py (admin game CRUD)
│       ├── bulk.py (bulk import/categorize endpoints)
│       └── health.py (health/debug endpoints)
├── services/
│   ├── __init__.py
│   ├── game_service.py (business logic)
│   ├── bgg_service.py (existing - keep as-is)
│   └── image_service.py (thumbnail handling)
├── middleware/
│   ├── __init__.py
│   ├── logging.py (request logging)
│   └── performance.py (performance monitoring)
├── schemas/
│   ├── __init__.py
│   ├── game.py (Pydantic models)
│   └── admin.py (admin request/response models)
└── utils/
    ├── __init__.py
    ├── categories.py (category mapping logic)
    └── response.py (standardized responses)
```

#### Step-by-step Migration (12 hours total):

**Step 1: Extract Configuration (1 hour)**
```python
# backend/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    admin_token: str
    cors_origins: str = ""
    database_url: str
    public_base_url: str

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"

settings = Settings()
```

**Step 2: Extract Middleware (2 hours)**
```python
# backend/middleware/logging.py
import logging
from starlette.middleware.base import BaseHTTPMiddleware

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request.state.request_id = str(uuid.uuid4())[:8]
        logger.info(f"→ {request.method} {request.url.path}")

        response = await call_next(request)

        logger.info(f"← {response.status_code}")
        return response

# backend/middleware/performance.py
class PerformanceMonitor:
    # ... move from main.py
```

**Step 3: Extract Services (4 hours)**
```python
# backend/services/game_service.py
from typing import Optional, List
from sqlalchemy.orm import Session
from ..models import Game
from ..schemas.game import GameCreate, GameUpdate, GameFilters

class GameService:
    def __init__(self, db: Session):
        self.db = db

    def get_filtered_games(
        self,
        filters: GameFilters,
        page: int = 1,
        page_size: int = 24
    ) -> tuple[List[Game], int]:
        """Get games with filters, return (games, total_count)"""
        query = self.db.query(Game)

        # Apply filters
        if filters.search:
            query = query.filter(Game.title.ilike(f"%{filters.search}%"))

        if filters.category:
            if filters.category == "uncategorized":
                query = query.filter(Game.mana_meeple_category.is_(None))
            else:
                query = query.filter(Game.mana_meeple_category == filters.category)

        if filters.nz_designer:
            query = query.filter(Game.nz_designer == True)

        # Get total before pagination
        total = query.count()

        # Apply sorting
        query = self._apply_sorting(query, filters.sort)

        # Paginate
        offset = (page - 1) * page_size
        games = query.offset(offset).limit(page_size).all()

        return games, total

    def create_game(self, game_data: GameCreate) -> Game:
        """Create new game"""
        game = Game(**game_data.dict())
        self.db.add(game)
        self.db.commit()
        self.db.refresh(game)
        return game

    def update_game(self, game_id: int, game_data: GameUpdate) -> Optional[Game]:
        """Update existing game"""
        game = self.db.query(Game).filter_by(id=game_id).first()
        if not game:
            return None

        for key, value in game_data.dict(exclude_unset=True).items():
            setattr(game, key, value)

        self.db.commit()
        self.db.refresh(game)
        return game

    # ... more methods

# backend/services/image_service.py
class ImageService:
    def __init__(self, db: Session):
        self.db = db

    async def download_thumbnail(
        self,
        game_id: int,
        thumbnail_url: str,
        max_retries: int = 3
    ) -> Optional[str]:
        """Download and save thumbnail, return local path"""
        # Move _download_and_update_thumbnail logic here
        pass
```

**Step 4: Extract Routers (3 hours)**
```python
# backend/api/routers/public.py
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from ...database import get_db
from ...services.game_service import GameService
from ...schemas.game import GameFilters, GameListResponse

router = APIRouter(prefix="/api/public", tags=["public"])

@router.get("/games", response_model=GameListResponse)
async def get_public_games(
    request: Request,
    q: str = Query("", description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    sort: str = Query("title_asc"),
    category: str = Query(None),
    nz_designer: bool = Query(None),
    db: Session = Depends(get_db)
):
    service = GameService(db)
    filters = GameFilters(
        search=q,
        category=category,
        nz_designer=nz_designer,
        sort=sort
    )

    games, total = service.get_filtered_games(filters, page, page_size)

    return {
        "items": [game.to_dict(request) for game in games],
        "total": total,
        "page": page,
        "page_size": page_size
    }

# backend/api/routers/admin.py
router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(verify_admin_token)]
)

@router.post("/games")
async def create_game(...):
    # Move from main.py
    pass

# backend/api/routers/health.py
router = APIRouter(prefix="/api", tags=["health"])

@router.get("/health")
async def health_check():
    return {"status": "healthy"}
```

**Step 5: New main.py (2 hours)**
```python
# backend/main.py (NEW - only 50 lines!)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import engine, create_indexes
from .middleware.logging import RequestLoggingMiddleware
from .middleware.performance import PerformanceMiddleware
from .api.routers import public, admin, bulk, health

# Create tables
from .models import Base
Base.metadata.create_all(bind=engine)
create_indexes(engine)

# Initialize app
app = FastAPI(
    title="Mana & Meeples Board Game Library API",
    version="2.0.0"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(PerformanceMiddleware)

# Routers
app.include_router(public.router)
app.include_router(admin.router)
app.include_router(bulk.router)
app.include_router(health.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 2.2 Eliminate Code Duplication (2 hours)

**Issue:** BGG import logic duplicated in 2 places (150 lines each)

**Solution:**
```python
# backend/services/bgg_service.py (add to existing file)

def update_game_from_bgg_data(game: Game, bgg_data: dict) -> None:
    """
    Update a Game model instance with BGG data.
    Used by both single import and bulk import.
    """
    # Consolidated field assignment
    if hasattr(game, 'description'):
        game.description = bgg_data.get("description")
    if hasattr(game, 'designers'):
        game.designers = bgg_data.get("designers", [])
    if hasattr(game, 'publishers'):
        game.publishers = bgg_data.get("publishers", [])
    # ... all 20+ fields

# Then use in both places:
# api/routers/admin.py
bgg_data = fetch_bgg_game_data(bgg_id)
update_game_from_bgg_data(game, bgg_data)

# api/routers/bulk.py
bgg_data = fetch_bgg_game_data(bgg_id)
update_game_from_bgg_data(game, bgg_data)
```

### 2.3 Standardize Error Handling (3 hours)

**Create error utilities:**
```python
# backend/utils/errors.py
from fastapi import HTTPException, status
from typing import Optional, Dict, Any

class AppException(Exception):
    """Base exception for application errors"""
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

class BGGFetchError(AppException):
    """BGG API fetch failed"""
    def __init__(self, bgg_id: int, reason: str):
        super().__init__(
            code="BGG_FETCH_FAILED",
            message=f"Failed to fetch game {bgg_id} from BoardGameGeek",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details={"bgg_id": bgg_id, "reason": reason}
        )

class GameNotFoundError(AppException):
    """Game not found in database"""
    def __init__(self, game_id: int):
        super().__init__(
            code="GAME_NOT_FOUND",
            message=f"Game {game_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"game_id": game_id}
        )

# Error handler
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )

# Usage:
raise BGGFetchError(bgg_id=12345, reason="Network timeout")
```

---

## Phase 3: Frontend Reorganization (Days 6-8)

### 3.1 Consolidate API Configuration (2 hours)

**Problem:** 3 different API base resolution strategies

**Solution:**
```javascript
// frontend/src/config/api.js (NEW - single source of truth)
const resolveApiBase = () => {
  // Priority order:
  // 1. Runtime window variable (for dynamic config)
  if (window.__API_BASE__) {
    return window.__API_BASE__;
  }

  // 2. Meta tag (for static site with injected config)
  const metaTag = document.querySelector('meta[name="api-base"]');
  if (metaTag?.content) {
    return metaTag.content;
  }

  // 3. Build-time environment variable
  if (process.env.REACT_APP_API_BASE) {
    return process.env.REACT_APP_API_BASE;
  }

  // 4. Development fallback
  return "http://127.0.0.1:8000";
};

export const API_BASE = resolveApiBase();

// Validation
if (!API_BASE) {
  throw new Error("API_BASE not configured!");
}

console.log(`[API Config] Using base: ${API_BASE}`);
```

**Then update all files to import from single source:**
```javascript
// frontend/src/api/client.js
import { API_BASE } from '../config/api';
const api = axios.create({ baseURL: API_BASE });

// frontend/src/utils/api.js
import { API_BASE } from '../config/api';
export function imageProxyUrl(url) {
  return `${API_BASE}/api/public/image-proxy?url=${encodeURIComponent(url)}`;
}
```

**Delete:**
- `frontend/src/config.js` (redundant)

### 3.2 Standardize HTTP Client (3 hours)

**Problem:** Mixing axios and fetch

**Solution:** Use axios everywhere with interceptors

```javascript
// frontend/src/api/client.js (REFACTORED)
import axios from 'axios';
import { API_BASE } from '../config/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Request interceptor - add admin token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('ADMIN_TOKEN');
    if (token) {
      config.headers['X-Admin-Token'] = token;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - standardized error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const customError = {
      message: error.response?.data?.error?.message || error.message,
      code: error.response?.data?.error?.code,
      status: error.response?.status,
      details: error.response?.data?.error?.details
    };

    // Global error handling
    if (customError.status === 401) {
      // Unauthorized - clear token and redirect
      localStorage.removeItem('ADMIN_TOKEN');
      window.location.href = '/staff';
    }

    return Promise.reject(customError);
  }
);

export default api;

// Convenience methods
export const gameApi = {
  getGames: (params) => api.get('/api/public/games', { params }),
  getGame: (id) => api.get(`/api/public/games/${id}`),
  getCategoryCounts: () => api.get('/api/public/category-counts'),

  // Admin
  createGame: (data) => api.post('/api/admin/games', data),
  updateGame: (id, data) => api.put(`/api/admin/games/${id}`, data),
  deleteGame: (id) => api.delete(`/api/admin/games/${id}`),

  // Bulk
  bulkImport: (csvText) => api.post('/api/admin/bulk-import-csv', { csv_text: csvText }),
};
```

**Update all components to use gameApi:**
```javascript
// frontend/src/pages/PublicCatalogue.jsx
import { gameApi } from '../api/client';

// Replace:
const response = await axios.get('/api/public/games', { params: {...} });

// With:
const response = await gameApi.getGames({
  q, page, page_size, sort, category, nz_designer
});
```

**Delete:**
- `frontend/src/utils/api.js` fetchJson function (keep imageProxyUrl)

### 3.3 Extract State Management (6 hours)

**Problem:** StaffView has 13 state variables, deep prop drilling

**Solution:** Use React Context (lightweight, no extra deps)

```javascript
// frontend/src/context/StaffContext.jsx (NEW)
import React, { createContext, useContext, useState, useCallback } from 'react';
import { gameApi } from '../api/client';

const StaffContext = createContext();

export function StaffProvider({ children }) {
  const [library, setLibrary] = useState([]);
  const [selectedGame, setSelectedGame] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadLibrary = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await gameApi.getGames({ page_size: 1000 });
      setLibrary(response.data.items);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const createGame = useCallback(async (gameData) => {
    const response = await gameApi.createGame(gameData);
    await loadLibrary(); // Refresh
    return response.data;
  }, [loadLibrary]);

  const updateGame = useCallback(async (id, gameData) => {
    const response = await gameApi.updateGame(id, gameData);
    await loadLibrary();
    return response.data;
  }, [loadLibrary]);

  const deleteGame = useCallback(async (id) => {
    await gameApi.deleteGame(id);
    await loadLibrary();
  }, [loadLibrary]);

  const value = {
    library,
    selectedGame,
    setSelectedGame,
    isLoading,
    error,
    loadLibrary,
    createGame,
    updateGame,
    deleteGame
  };

  return (
    <StaffContext.Provider value={value}>
      {children}
    </StaffContext.Provider>
  );
}

export function useStaff() {
  const context = useContext(StaffContext);
  if (!context) {
    throw new Error('useStaff must be used within StaffProvider');
  }
  return context;
}
```

**Update App.js:**
```javascript
// frontend/src/App.js
import { StaffProvider, useStaff } from './context/StaffContext';

function StaffView() {
  const {
    library,
    selectedGame,
    setSelectedGame,
    isLoading,
    error,
    loadLibrary,
    createGame,
    updateGame,
    deleteGame
  } = useStaff();

  // Component now much simpler!
  // No local state management needed
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/staff" element={
          <StaffProvider>
            <StaffView />
          </StaffProvider>
        } />
        {/* ... other routes */}
      </Routes>
    </Router>
  );
}
```

### 3.4 Performance Optimizations (4 hours)

#### 3.4.1 Memoize Expensive Components
```javascript
// frontend/src/components/public/GameCardPublic.jsx
import React from 'react';

function GameCardPublic({ game, onShare }) {
  // Component logic
}

export default React.memo(GameCardPublic);
```

#### 3.4.2 Code Splitting by Route
```javascript
// frontend/src/App.js
import React, { lazy, Suspense } from 'react';

const PublicCatalogue = lazy(() => import('./pages/PublicCatalogue'));
const GameDetails = lazy(() => import('./pages/GameDetails'));
const StaffView = lazy(() => import('./pages/StaffView'));

function App() {
  return (
    <Router>
      <Suspense fallback={<LoadingSpinner />}>
        <Routes>
          <Route path="/" element={<PublicCatalogue />} />
          <Route path="/games/:id" element={<GameDetails />} />
          <Route path="/staff" element={<StaffView />} />
        </Routes>
      </Suspense>
    </Router>
  );
}
```

#### 3.4.3 Use API Category Counts (Remove Client-Side Computation)
```javascript
// frontend/src/pages/PublicCatalogue.jsx

// REMOVE this expensive computation:
const categoryCounts = useMemo(() => computeCounts(library), [library]);

// USE API data instead:
const [categoryCounts, setCategoryCounts] = useState({});

useEffect(() => {
  async function loadCounts() {
    const response = await gameApi.getCategoryCounts();
    setCategoryCounts(response.data);
  }
  loadCounts();
}, []);
```

#### 3.4.4 Fix URL State Sync
```javascript
// frontend/src/pages/PublicCatalogue.jsx

// ADD effect to sync state from URL changes
useEffect(() => {
  setQ(searchParams.get('q') || '');
  setCategory(searchParams.get('category') || 'all');
  setDesigner(searchParams.get('designer') || '');
  setNzDesigner(searchParams.get('nz_designer') === 'true');
  setSort(searchParams.get('sort') || 'title_asc');
  setPage(parseInt(searchParams.get('page') || '1', 10));
}, [searchParams]); // Re-run when URL changes
```

### 3.5 Shared UI Components (3 hours)

**Create consistent loading states:**
```javascript
// frontend/src/components/common/LoadingSpinner.jsx (NEW)
export function LoadingSpinner({ size = 'md', text }) {
  const sizes = {
    sm: 'w-6 h-6',
    md: 'w-12 h-12',
    lg: 'w-16 h-16'
  };

  return (
    <div className="flex flex-col items-center justify-center gap-4 p-8">
      <div className={`${sizes[size]} border-4 border-amber-200 border-t-amber-600 rounded-full animate-spin`} />
      {text && <p className="text-slate-600">{text}</p>}
    </div>
  );
}

// frontend/src/components/common/SkeletonLoader.jsx (NEW)
export function GameCardSkeleton() {
  return (
    <div className="bg-white rounded-lg shadow-sm p-4 animate-pulse">
      <div className="w-full h-48 bg-slate-200 rounded mb-3" />
      <div className="h-4 bg-slate-200 rounded w-3/4 mb-2" />
      <div className="h-3 bg-slate-200 rounded w-1/2" />
    </div>
  );
}
```

**Use consistently:**
```javascript
// PublicCatalogue.jsx
if (loading) return <LoadingSpinner size="lg" text="Loading games..." />;

// GameDetails.jsx
if (loading) return <LoadingSpinner text="Loading game details..." />;

// StaffView.jsx
if (isLoading) return <LoadingSpinner text="Loading library..." />;
```

---

## Phase 4: Testing & CI/CD (Days 9-11)

### 4.1 Backend Testing (8 hours)

#### Test Structure:
```
backend/
└── tests/
    ├── __init__.py
    ├── conftest.py (fixtures)
    ├── test_services/
    │   ├── test_game_service.py
    │   ├── test_image_service.py
    │   └── test_bgg_service.py
    ├── test_api/
    │   ├── test_public.py
    │   ├── test_admin.py
    │   └── test_bulk.py
    └── test_integration/
        └── test_end_to_end.py
```

#### Example Test:
```python
# backend/tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ..database import Base
from ..main import app

@pytest.fixture(scope="function")
def db_session():
    """Create test database session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()
    Base.metadata.drop_all(engine)

@pytest.fixture
def client():
    """Test client"""
    from fastapi.testclient import TestClient
    return TestClient(app)

# backend/tests/test_services/test_game_service.py
from ...services.game_service import GameService
from ...models import Game

def test_get_filtered_games(db_session):
    # Setup
    service = GameService(db_session)
    game1 = Game(title="Pandemic", mana_meeple_category="COOP_ADVENTURE")
    game2 = Game(title="Catan", mana_meeple_category="GATEWAY_STRATEGY")
    db_session.add_all([game1, game2])
    db_session.commit()

    # Test
    filters = GameFilters(category="COOP_ADVENTURE")
    games, total = service.get_filtered_games(filters)

    # Assert
    assert total == 1
    assert games[0].title == "Pandemic"

# backend/tests/test_api/test_public.py
def test_get_games_endpoint(client, db_session):
    response = client.get("/api/public/games")
    assert response.status_code == 200
    assert "items" in response.json()
    assert "total" in response.json()
```

**Run tests:**
```bash
pip install pytest pytest-cov pytest-asyncio
pytest tests/ --cov=backend --cov-report=html
```

### 4.2 Frontend Testing (6 hours)

#### Migrate to Vitest (faster than Jest):
```bash
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event
```

```javascript
// frontend/vite.config.js (NEW - for Vitest)
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
  },
});

// frontend/src/test/setup.js
import '@testing-library/jest-dom';

// frontend/src/components/public/__tests__/GameCardPublic.test.jsx
import { render, screen } from '@testing-library/react';
import GameCardPublic from '../GameCardPublic';

describe('GameCardPublic', () => {
  const mockGame = {
    id: 1,
    title: 'Pandemic',
    year: 2008,
    players_min: 2,
    players_max: 4,
    playtime_min: 45,
    complexity: 2.4
  };

  it('renders game title', () => {
    render(<GameCardPublic game={mockGame} />);
    expect(screen.getByText('Pandemic')).toBeInTheDocument();
  });

  it('displays player count', () => {
    render(<GameCardPublic game={mockGame} />);
    expect(screen.getByText('2-4')).toBeInTheDocument();
  });
});
```

### 4.3 CI/CD Pipeline (4 hours)

```yaml
# .github/workflows/test.yml (NEW)
name: Test & Deploy

on:
  push:
    branches: [ main, claude/* ]
  pull_request:
    branches: [ main ]

jobs:
  backend-tests:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
          ADMIN_TOKEN: test_token
        run: |
          cd backend
          pytest tests/ --cov --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./backend/coverage.xml

  frontend-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Node
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: |
          cd frontend
          npm ci

      - name: Run tests
        run: |
          cd frontend
          npm run test:ci

      - name: Build
        run: |
          cd frontend
          npm run build

      - name: Upload build artifacts
        uses: actions/upload-artifact@v3
        with:
          name: frontend-build
          path: frontend/build/

  lint:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Lint Python
        run: |
          pip install black flake8
          cd backend
          black --check .
          flake8 .

      - name: Lint JavaScript
        run: |
          cd frontend
          npm ci
          npm run lint
```

---

## Phase 5: Documentation & Polish (Days 12-13)

### 5.1 Code Documentation (4 hours)

**Add docstrings to all Python functions:**
```python
# backend/services/game_service.py
def get_filtered_games(
    self,
    filters: GameFilters,
    page: int = 1,
    page_size: int = 24
) -> tuple[List[Game], int]:
    """
    Retrieve games matching the given filters with pagination.

    Args:
        filters: Filter criteria (search, category, designer, etc.)
        page: Page number (1-indexed)
        page_size: Number of games per page

    Returns:
        Tuple of (list of Game objects, total count matching filters)

    Example:
        >>> service = GameService(db)
        >>> filters = GameFilters(category="COOP_ADVENTURE")
        >>> games, total = service.get_filtered_games(filters, page=1)
        >>> print(f"Found {total} co-op games")
    """
    # Implementation
```

**Add JSDoc to complex functions:**
```javascript
/**
 * Fetch games with filters and pagination
 * @param {Object} params - Query parameters
 * @param {string} params.q - Search query
 * @param {number} params.page - Page number (1-indexed)
 * @param {string} params.category - Category filter
 * @returns {Promise<{items: Array, total: number}>}
 */
export async function getGames(params) {
  // Implementation
}
```

### 5.2 Architecture Documentation (3 hours)

```markdown
# docs/ARCHITECTURE.md (NEW)

## System Architecture

### High-Level Overview

```
┌─────────────┐      HTTPS      ┌──────────────┐
│   Browser   │ ←──────────────→ │ React (SPA)  │
│             │                  │  (Render)    │
└─────────────┘                  └──────┬───────┘
                                        │
                                   API Calls
                                        │
                                        ▼
                                 ┌──────────────┐
                                 │  FastAPI     │
                                 │  (Render)    │
                                 └──────┬───────┘
                                        │
                                        ▼
                                 ┌──────────────┐
                                 │ PostgreSQL   │
                                 │  (Render)    │
                                 └──────────────┘
```

### Backend Architecture

**Layered Structure:**
```
Controllers (Routers)
    ↓
Services (Business Logic)
    ↓
Models (Database)
```

**Key Components:**

- **Routers** (`api/routers/`): Handle HTTP requests/responses
- **Services** (`services/`): Business logic, reusable operations
- **Models** (`models.py`): SQLAlchemy ORM models
- **Middleware**: Logging, performance monitoring, CORS
- **BGG Integration** (`bgg_service.py`): External API client

### Frontend Architecture

**Component Hierarchy:**
```
App
├── PublicCatalogue (Page)
│   ├── CategoryFilter
│   ├── SearchBox
│   ├── SortSelect
│   ├── GameCardPublic (repeated)
│   └── Pagination
├── GameDetails (Page)
│   └── GameImage
└── StaffView (Page)
    ├── LibraryCard
    ├── SearchBGGPanel
    └── BulkPanels
```

**State Management:**
- **URL State**: Filters, pagination (shareable links)
- **Context**: Staff view data
- **Local State**: UI state (modals, loading)

### Data Flow

**Public Game Browsing:**
1. User adjusts filters → URL params update
2. React detects URL change → triggers API call
3. FastAPI receives request → GameService filters database
4. Returns paginated results → React renders cards

**Admin Game Import:**
1. Admin enters BGG ID → API request to `/api/admin/import/bgg`
2. Backend fetches BGG data → Creates Game record
3. Background task downloads thumbnail
4. Frontend refreshes library → Shows new game

### Database Schema

See `backend/models.py` for full schema.

**Key Relationships:**
- Games are independent (no foreign keys currently)
- JSON columns for arrays (designers, mechanics, etc.)
- Indexes on: title, bgg_id, category, nz_designer

### External Integrations

- **BoardGameGeek XML API**: Game data sync
- **Image Proxy**: Caches external images
- **Render**: Hosting platform (auto-deploy from Git)
```

### 5.3 API Documentation (2 hours)

**Generate OpenAPI docs automatically:**
```python
# backend/main.py
app = FastAPI(
    title="Mana & Meeples Board Game Library API",
    description="Public game catalogue and admin management for board game library",
    version="2.0.0",
    docs_url="/api/docs",  # Swagger UI
    redoc_url="/api/redoc"  # ReDoc
)
```

**Add response models for better docs:**
```python
# backend/schemas/game.py
from pydantic import BaseModel, Field
from typing import Optional, List

class GameResponse(BaseModel):
    id: int
    title: str = Field(..., example="Pandemic")
    year: Optional[int] = Field(None, example=2008)
    players_min: Optional[int] = Field(None, example=2)
    players_max: Optional[int] = Field(None, example=4)
    complexity: Optional[float] = Field(None, example=2.43)
    # ... all fields

    class Config:
        from_attributes = True

class GameListResponse(BaseModel):
    items: List[GameResponse]
    total: int
    page: int
    page_size: int

# Use in routers:
@router.get("/games", response_model=GameListResponse)
async def get_public_games(...):
    ...
```

---

## Phase 6: Accessibility & Polish (Days 14-15)

### 6.1 Accessibility Audit (4 hours)

**Install tools:**
```bash
npm install -D @axe-core/react
```

**Add to development:**
```javascript
// frontend/src/index.js
if (process.env.NODE_ENV !== 'production') {
  import('@axe-core/react').then(axe => {
    axe.default(React, ReactDOM, 1000);
  });
}
```

**Fix identified issues:**

1. **Add ARIA labels to interactive elements:**
```jsx
<button
  onClick={() => setCategory(key)}
  aria-label={`Filter by ${CATEGORY_LABELS[key]}`}
  aria-pressed={category === key}
>
  {CATEGORY_LABELS[key]}
</button>
```

2. **Focus management in modals:**
```javascript
// CategorySelectModal.jsx
useEffect(() => {
  if (isOpen) {
    const firstButton = modalRef.current?.querySelector('button');
    firstButton?.focus();
  }
}, [isOpen]);

// Trap focus in modal
const handleKeyDown = (e) => {
  if (e.key === 'Escape') {
    onClose();
  }

  if (e.key === 'Tab') {
    // Trap focus logic
    const focusableElements = modalRef.current.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const first = focusableElements[0];
    const last = focusableElements[focusableElements.length - 1];

    if (e.shiftKey && document.activeElement === first) {
      last.focus();
      e.preventDefault();
    } else if (!e.shiftKey && document.activeElement === last) {
      first.focus();
      e.preventDefault();
    }
  }
};
```

3. **Color contrast fixes:**
```jsx
// Change low-contrast text
<p className="text-slate-500">  // Fails WCAG AA
// To:
<p className="text-slate-700">  // Passes WCAG AA
```

4. **Keyboard navigation for horizontal scroll:**
```jsx
const handleCategoryKeyNav = (e, currentCategory) => {
  const categories = ['all', ...CATEGORY_KEYS];
  const currentIndex = categories.indexOf(currentCategory);

  if (e.key === 'ArrowRight' && currentIndex < categories.length - 1) {
    setCategory(categories[currentIndex + 1]);
  } else if (e.key === 'ArrowLeft' && currentIndex > 0) {
    setCategory(categories[currentIndex - 1]);
  }
};

<button
  onKeyDown={(e) => handleCategoryKeyNav(e, 'all')}
  // ... rest
>
```

### 6.2 Mobile Optimization (3 hours)

**Touch target sizes (minimum 44x44px):**
```jsx
// Ensure all buttons meet minimum
<button className="min-h-[44px] min-w-[44px] px-4 py-2">
  {label}
</button>
```

**Responsive layouts:**
```jsx
// PublicCatalogue grid
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
  {games.map(game => <GameCardPublic key={game.id} game={game} />)}
</div>
```

**Performance: Lazy load images:**
```jsx
// GameImage.jsx
<img
  src={src}
  alt={alt}
  loading="lazy"  // Native lazy loading
  decoding="async"
  className={className}
/>
```

### 6.3 Error Messages (2 hours)

**User-friendly error displays:**
```jsx
// components/common/ErrorMessage.jsx (NEW)
export function ErrorMessage({ error, onRetry }) {
  const errorMessages = {
    'NETWORK_ERROR': 'Connection problem. Please check your internet and try again.',
    'BGG_FETCH_FAILED': 'Couldn\'t load game from BoardGameGeek. Try again in a moment.',
    'GAME_NOT_FOUND': 'Game not found. It may have been removed.',
    'UNAUTHORIZED': 'Admin access required. Please log in.',
  };

  const message = errorMessages[error.code] || error.message || 'Something went wrong';

  return (
    <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded" role="alert">
      <div className="flex items-start">
        <AlertCircle className="text-red-500 mr-3 flex-shrink-0" />
        <div className="flex-1">
          <h3 className="text-red-800 font-semibold">Error</h3>
          <p className="text-red-700 mt-1">{message}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="mt-3 text-red-700 underline hover:text-red-900"
            >
              Try again
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
```

---

## Phase 7: Dependency Updates (Days 16-17)

### 7.1 Backend Dependencies (6 hours)

**Major version upgrades require careful migration:**

#### SQLAlchemy 1.4 → 2.0
```bash
# Install new version
pip install SQLAlchemy==2.0.36

# Update imports
# Old:
from sqlalchemy.orm import Session
# New:
from sqlalchemy.orm import Session  # Same, but different behavior

# Update query syntax
# Old:
db.query(Game).filter_by(id=game_id).first()
# New (2.0 style):
from sqlalchemy import select
stmt = select(Game).where(Game.id == game_id)
db.scalars(stmt).first()

# Or keep 1.4 style with:
from sqlalchemy.orm import sessionmaker
Session = sessionmaker(bind=engine, future=False)
```

**Migration guide:**
```markdown
# docs/SQLALCHEMY_MIGRATION.md

## SQLAlchemy 2.0 Migration Checklist

- [ ] Update all `db.query()` to use `select()`
- [ ] Replace `.filter_by()` with `.where()`
- [ ] Update session configuration
- [ ] Test all database operations
- [ ] Update type hints
```

#### Pydantic 1.10 → 2.0
```python
# Old:
class GameCreate(BaseModel):
    class Config:
        orm_mode = True

# New:
from pydantic import ConfigDict

class GameCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
```

**Strategy:** Create separate branch for dependency updates, test thoroughly.

### 7.2 Frontend Dependencies (4 hours)

#### Migrate from Create React App to Vite

**Why:** CRA is deprecated, Vite is faster and actively maintained.

```bash
cd frontend

# Install Vite
npm install -D vite @vitejs/plugin-react

# Update scripts in package.json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "test": "vitest"
  }
}

# Create vite.config.js
```

```javascript
// frontend/vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    open: true
  },
  build: {
    outDir: 'build',
    sourcemap: true
  }
});
```

**Move index.html to root:**
```bash
mv public/index.html ./index.html
```

**Update index.html:**
```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Mana & Meeples Library</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/index.jsx"></script>
  </body>
</html>
```

**Remove CRA dependencies:**
```bash
npm uninstall react-scripts
rm -rf node_modules/.cache
```

---

## Phase 8: Monitoring & Observability (Day 18)

### 8.1 Error Tracking (3 hours)

**Add Sentry for production error tracking:**

```bash
# Backend
pip install sentry-sdk[fastapi]

# Frontend
npm install @sentry/react
```

```python
# backend/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

if os.getenv("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        integrations=[FastApiIntegration()],
        environment=os.getenv("ENVIRONMENT", "production"),
        traces_sample_rate=0.1,  # 10% of requests
    )
```

```javascript
// frontend/src/index.jsx
import * as Sentry from "@sentry/react";

if (process.env.REACT_APP_SENTRY_DSN) {
  Sentry.init({
    dsn: process.env.REACT_APP_SENTRY_DSN,
    environment: process.env.NODE_ENV,
    integrations: [new Sentry.BrowserTracing()],
    tracesSampleRate: 0.1,
  });
}
```

### 8.2 Performance Monitoring (2 hours)

**Add structured performance logging:**

```python
# backend/middleware/performance.py
import structlog

logger = structlog.get_logger()

class PerformanceMiddleware:
    async def dispatch(self, request, call_next):
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time

        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration * 1000,
            request_id=request.state.request_id
        )

        return response
```

**Frontend performance tracking:**
```javascript
// frontend/src/utils/performance.js
export function trackPageLoad() {
  if (window.performance) {
    const perfData = window.performance.timing;
    const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart;

    // Send to analytics
    console.log('Page load time:', pageLoadTime);
  }
}
```

---

## Implementation Timeline

### Week 1: Critical Fixes & Backend Refactoring
- **Day 1-2:** Phase 1 (Critical Fixes)
- **Day 3-5:** Phase 2 (Backend Reorganization)

### Week 2: Frontend & Testing
- **Day 6-8:** Phase 3 (Frontend Reorganization)
- **Day 9-11:** Phase 4 (Testing & CI/CD)

### Week 3: Polish & Updates
- **Day 12-13:** Phase 5 (Documentation)
- **Day 14-15:** Phase 6 (Accessibility)
- **Day 16-17:** Phase 7 (Dependencies)
- **Day 18:** Phase 8 (Monitoring)

---

## Success Metrics

### Code Quality
- [ ] Lighthouse score >90 (Performance, Accessibility, Best Practices, SEO)
- [ ] Test coverage >70%
- [ ] No critical security vulnerabilities (npm audit / pip-audit)
- [ ] All linting rules pass
- [ ] Bundle size <500KB (gzipped)

### Performance
- [ ] Page load time <2s (library.manaandmeeples.co.nz)
- [ ] API response time <200ms (p95)
- [ ] Database queries <100ms (p95)

### Maintainability
- [ ] All files <300 lines
- [ ] No function >50 lines
- [ ] All public functions documented
- [ ] Architecture diagram exists

---

## Risk Mitigation

### High-Risk Changes
1. **SQLAlchemy 2.0 upgrade:** Create feature branch, extensive testing
2. **CRA → Vite migration:** Test build process thoroughly on Render
3. **Admin auth refactor:** Ensure backward compatibility during transition

### Rollback Plan
- Keep old code in Git tags before each major phase
- Deploy phases incrementally (not all at once)
- Monitor error rates after each deployment

---

## Long-Term Recommendations

### After Refactoring

1. **TypeScript Migration** (4-6 weeks)
   - Start with new files
   - Gradually convert existing components
   - Full type safety across frontend

2. **GraphQL API** (2-3 weeks)
   - Replace REST with GraphQL
   - More efficient data fetching
   - Better frontend performance

3. **Server-Side Rendering** (3-4 weeks)
   - Next.js or similar
   - Improved SEO
   - Faster initial page loads

4. **Advanced Search** (2 weeks)
   - Elasticsearch integration
   - Full-text search across all fields
   - Faceted search UI

5. **User Accounts** (4-6 weeks)
   - OAuth integration
   - Wishlist functionality
   - Personal ratings

---

## Conclusion

This plan transforms the codebase from "hodgepodge" to well-organized, maintainable, and production-ready. The phased approach allows for incremental progress with minimal disruption.

**Immediate Priority:** Phase 1 (Critical Fixes) - these security and performance issues should be addressed ASAP.

**Next Steps:**
1. Review this plan
2. Decide which phases to tackle first
3. Create feature branch for chosen phase
4. Begin implementation

Would you like to proceed with any specific phase?
