# Performance Analysis & Improvement Recommendations

**Generated:** 2026-01-04
**Branch:** `claude/improve-game-card-performance-csmXK`
**Focus Areas:** React rendering, pagination, image loading, API caching, database monitoring

---

## Executive Summary

This analysis evaluates five key performance improvement areas for the Mana & Meeples game library. The investigation reveals a **well-optimized system** with recent Sprint 12 improvements (window functions, cache warming, connection pooling). However, there are **tactical opportunities** for further optimization, particularly around React rendering and API response caching.

**Key Findings:**
- ✅ **Strong backend foundation**: Window functions, read replicas, connection pooling (Sprint 12)
- ✅ **Advanced image optimization**: Cloudinary CDN, IntersectionObserver, network-aware loading
- ⚠️ **Missing React.memo**: GameCardPublic re-renders unnecessarily on parent updates
- ⚠️ **No API response caching**: Every filter change triggers new API calls
- ⚠️ **Offset-based pagination acceptable**: Current dataset size (~400 games) doesn't justify cursor complexity
- ✅ **Performance monitoring exists**: Tracks slow queries (>2s), but no real-time alerting

---

## 1. React.memo on GameCardPublic

### Current State
**Status:** ❌ **Not Implemented**

The `GameCardPublic` component (`frontend/src/components/public/GameCardPublic.jsx`) renders without memoization:

```jsx
export default function GameCardPublic({
  game,
  lazy = false,
  isExpanded = false,
  onToggleExpand,
  prefersReducedMotion = false,
  priority = false,
  showHints = true
}) {
  // Component logic...
}
```

**Problem:**
- Every time `PublicCatalogue` re-renders (filter changes, search, etc.), ALL game cards re-render
- With 24 cards per page (default `page_size`), this means 24+ unnecessary renders per filter change
- Each card has complex conditional rendering (expanded vs minimized states, badges, stats)
- Re-renders happen even when `game` object hasn't changed

**Evidence from Code:**
```javascript
// PublicCatalogue.jsx:945-956
{allLoadedItems.map((game, index) => (
  <GameCardPublic
    key={game.id}  // Good: stable key
    game={game}
    isExpanded={expandedCards.has(game.id)}
    onToggleExpand={() => toggleCardExpansion(game.id)}
    prefersReducedMotion={prefersReducedMotion}
    priority={index < 8}
    lazy={index >= 8}
  />
))}
```

When filters change:
1. `PublicCatalogue` state updates (e.g., `category`, `sort`)
2. Entire component re-renders
3. ALL `GameCardPublic` instances re-render, even if their `game` prop is unchanged

### Recommended Solution

**Implementation: Wrap with React.memo and optimize prop comparison**

```jsx
// GameCardPublic.jsx
import React, { memo } from 'react';

const GameCardPublic = memo(function GameCardPublic({
  game,
  lazy = false,
  isExpanded = false,
  onToggleExpand,
  prefersReducedMotion = false,
  priority = false,
  showHints = true
}) {
  // Component logic unchanged...
}, (prevProps, nextProps) => {
  // Custom comparison: only re-render if these specific props change
  return (
    prevProps.game.id === nextProps.game.id &&
    prevProps.isExpanded === nextProps.isExpanded &&
    prevProps.lazy === nextProps.lazy &&
    prevProps.priority === nextProps.priority &&
    prevProps.showHints === nextProps.showHints &&
    prevProps.prefersReducedMotion === nextProps.prefersReducedMotion
    // Note: Deliberately omit onToggleExpand from comparison
    // (it's recreated via useCallback in parent, so reference changes are expected)
  );
});

export default GameCardPublic;
```

**In PublicCatalogue, ensure stable function references:**

```jsx
// PublicCatalogue.jsx (already uses useCallback - GOOD!)
const toggleCardExpansion = useCallback((gameId) => {
  setExpandedCards(prev => {
    const next = new Set(prev);
    if (next.has(gameId)) {
      next.delete(gameId);
    } else {
      next.clear();
      next.add(gameId);
    }
    return next;
  });
}, []); // ✅ No dependencies - stable reference
```

### Expected Impact
- **Render reduction:** ~85-90% fewer renders during filter changes
  - Example: 24 cards/page → only 1-2 cards re-render when filters change (if game data unchanged)
- **Perceived performance:** Faster filter/search responsiveness
- **Battery/CPU savings:** Significant reduction on mobile devices with 100+ loaded cards (infinite scroll)

### Implementation Effort
- **Time:** 15-30 minutes
- **Risk:** Low (memo doesn't change functionality, only optimization)
- **Testing:** Verify expanded/collapse behavior still works correctly

---

## 2. Cursor-Based Pagination

### Current State
**Status:** ✅ **Offset-Based (Optimized with Window Functions)**

Current implementation (`backend/services/game_service.py:66-265`):

```python
def get_filtered_games(
    self,
    search: Optional[str] = None,
    category: Optional[str] = None,
    # ... other filters
    sort: str = "title_asc",
    page: int = 1,
    page_size: int = 24,
) -> Tuple[List[Game], int]:
    """
    Sprint 12: Performance Optimization - Uses window function for count + pagination
    to eliminate duplicate queries and reduce DB round trips from 2 to 1.
    """
    # Step 1: ID subquery with window function
    id_query = select(
        Game.id,
        func.count().over().label('total_count')
    ).where(...)

    # Apply pagination
    offset = (page - 1) * page_size
    id_query_paginated = id_query.offset(offset).limit(page_size)

    # Execute (SINGLE DATABASE ROUND TRIP)
    id_results = self.db.execute(id_query_paginated).all()

    # Step 2: Fetch full objects for these IDs
    games = self.db.execute(
        select(Game)
        .options(selectinload(Game.expansions))
        .where(Game.id.in_(game_ids))
    ).scalars().all()
```

**Strengths:**
- ✅ Single database round trip (window function eliminates count query)
- ✅ Eager loading prevents N+1 queries
- ✅ Stable pagination with multi-level sorting (primary → title → id)
- ✅ Read replica support for scalability

**Limitations:**
- Offset scans increase with page number (page 1: scan 0 rows, page 10: scan 240 rows)
- Not suitable for real-time feeds (rows can shift between pages)

### Cursor-Based Pagination Analysis

**What it would look like:**

```python
def get_filtered_games_cursor(
    self,
    cursor: Optional[str] = None,  # Base64-encoded (sort_value, game_id)
    page_size: int = 24,
    # ... filters
):
    query = select(Game).where(...)

    if cursor:
        # Decode cursor to get last seen values
        sort_value, last_id = decode_cursor(cursor)

        # WHERE (sort_column, id) > (cursor_sort_value, cursor_id)
        # Uses composite index for efficient seeking
        query = query.where(
            or_(
                Game.year > sort_value,
                and_(Game.year == sort_value, Game.id > last_id)
            )
        )

    query = query.order_by(Game.year, Game.id).limit(page_size)
    games = db.execute(query).scalars().all()

    # Generate next cursor from last item
    if games:
        last_game = games[-1]
        next_cursor = encode_cursor(last_game.year, last_game.id)

    return games, next_cursor
```

**Frontend changes required:**

```javascript
// Current: page-based
const [page, setPage] = useState(1);
api.get('/games', { params: { page: 1, page_size: 24 } });

// Cursor-based
const [cursor, setCursor] = useState(null);
api.get('/games', { params: { cursor: 'eyJ5ZWFyIjo...', page_size: 24 } });
```

### Recommendation: **KEEP OFFSET-BASED PAGINATION**

**Rationale:**

1. **Dataset Size:** ~400 games total
   - Offset scan overhead is negligible (even page 10 = 240 row scan is <10ms with indexes)
   - Cursor pagination shines at 10,000+ rows where offset(5000) becomes expensive

2. **User Experience:**
   - Users can jump to specific pages (page 1, 2, 5, etc.)
   - Cursor-based requires sequential navigation only (no "jump to page X")
   - URL sharing works better (`?page=3` vs `?cursor=eyJzb3J...`)

3. **Already Optimized:**
   - Window function eliminates separate count query (Sprint 12)
   - Read replica support offloads query pressure
   - Connection pooling handles concurrent requests (15 permanent + 20 overflow connections)

4. **Implementation Complexity:**
   - Cursor encoding/decoding for multiple sort fields (title, year, rating, time)
   - Frontend infinite scroll UI already works well with offset pagination
   - Migration effort doesn't justify marginal gains

**When to Revisit:**
- Library grows to 5,000+ games (unlikely for a single café)
- Real-time feed requirements (e.g., games auto-update while browsing)
- Offset queries exceed 100ms (monitor via `/api/debug/performance`)

---

## 3. Image Prefetching on Card Hover

### Current State
**Status:** ✅ **Advanced Lazy Loading (No Prefetch)**

Current implementation (`frontend/src/components/GameImage.jsx`):

```jsx
// Uses IntersectionObserver with network-aware root margins
export function useImageLazyLoad(options = {}) {
  const networkAwareMargin = getNetworkAwareMargin(); // 100-400px based on connection

  const { ref, hasBeenVisible } = useLazyLoad({
    rootMargin: networkAwareMargin, // Loads BEFORE visible
    threshold: 0.01,
    ...options
  });

  return { ref, shouldLoad: hasBeenVisible };
}
```

**Network-Aware Pre-loading:**
```javascript
function getNetworkAwareMargin() {
  const connection = navigator.connection;

  if (connection?.saveData) return '100px';  // Data saver mode

  switch (connection?.effectiveType) {
    case 'slow-2g':
    case '2g': return '100px';  // Conservative
    case '3g': return '200px';   // Moderate
    case '4g':
    default: return '400px';     // Aggressive pre-loading
  }
}
```

**Cloudinary CDN Integration:**
- All BGG images uploaded to Cloudinary on first request
- Cached `cloudinary_url` stored in database for future fast-path
- Responsive images with `srcset` for different screen sizes
- WebP/AVIF format conversion for 40-60% size reduction

**Image Optimization Pipeline:**
```
User Request → Backend Proxy → Cloudinary Upload (if needed) → CDN Cache → Browser Cache
                                         ↓
                                 Database: cloudinary_url saved
                                         ↓
                                 Next Request: Fast-path redirect
```

### Hover Prefetch Analysis

**What it would involve:**

```jsx
// GameCardPublic.jsx
const GameCardPublic = memo(function GameCardPublic({ game, ... }) {
  const [prefetchTriggered, setPrefetchTriggered] = useState(false);

  const handleMouseEnter = useCallback(() => {
    if (!prefetchTriggered && game.image) {
      // Prefetch full-size image for game detail page
      const link = document.createElement('link');
      link.rel = 'prefetch';
      link.href = imageProxyUrl(game.image);
      link.as = 'image';
      document.head.appendChild(link);

      setPrefetchTriggered(true);
    }
  }, [game.image, prefetchTriggered]);

  return (
    <article onMouseEnter={handleMouseEnter}>
      {/* Card content */}
    </article>
  );
});
```

**Challenges:**

1. **Mobile Users (70% of traffic?):**
   - No hover events on touch devices
   - Prefetch would need touch start/long press heuristics
   - Risk of wasted bandwidth on accidental taps

2. **Already Pre-loaded:**
   - IntersectionObserver loads cards 100-400px before visible
   - By the time user can hover, image is likely already loading/loaded
   - Hover → Click delay is typically 200-500ms (not enough time for new fetch)

3. **Cloudinary Fast-Path:**
   - Images already cached in database (`cloudinary_url`)
   - CDN + browser cache make subsequent loads <50ms
   - Prefetch savings would be minimal on actual game detail page load

4. **Browser Limits:**
   - Browsers limit concurrent connections (6-8 per domain)
   - Aggressive prefetching can block critical resources
   - HTTP/2 multiplexing helps but still has practical limits

### Recommendation: **DO NOT IMPLEMENT HOVER PREFETCH**

**Rationale:**

1. **Diminishing Returns:**
   - Existing IntersectionObserver already pre-loads 100-400px ahead
   - Cloudinary CDN + browser cache make subsequent loads near-instant
   - Hover → click delay (200-500ms) likely shorter than image fetch time

2. **Mobile-First Design:**
   - Library is mobile-friendly (`min-h-[44px]` touch targets, responsive grid)
   - Hover prefetch doesn't work on 50-70% of users (mobile/tablet)
   - Adding mobile-specific heuristics (long press, scroll velocity) adds complexity

3. **Bandwidth Considerations:**
   - Users on 2G/3G (data saver mode already detected)
   - Prefetching images for cards user may never click wastes data
   - Current lazy loading respects `saveData` preference

**Alternative: Optimize What's Already There**

Instead of hover prefetch, consider:

- ✅ **Keep Cloudinary integration** (already implemented)
- ✅ **Keep network-aware loading** (already implemented)
- ⚠️ **Optimize Cloudinary transformations:**
  - List view: Use `w_400,h_400,c_fill` (smaller thumbnails)
  - Detail view: Use `w_800,h_800,c_fit` (full quality)
  - Currently uses same size for both contexts

```javascript
// config/api.js enhancement
export function imageProxyUrl(url, context = 'list') {
  const base = `${API_BASE}/api/public/image-proxy?url=${encodeURIComponent(url)}`;

  if (context === 'list') {
    return `${base}&width=400&height=400`; // Thumbnail for cards
  } else if (context === 'detail') {
    return `${base}&width=800&height=800`; // Full size for detail page
  }

  return base;
}
```

---

## 4. API Response Caching (React Query / SWR)

### Current State
**Status:** ❌ **No Client-Side Caching**

Current implementation (`frontend/src/api/client.js`):

```javascript
export const api = axios.create({
  baseURL: getApiUrl(''),
  withCredentials: true,
  timeout: 300000,
});

// Every call hits the network
export async function getPublicGames(params = {}) {
  const r = await api.get("/public/games", { params });
  return r.data;
}
```

**Backend Caching:**
- ✅ Server-side cache with 30s TTL (`utils/cache.py`)
- ✅ Probabilistic early expiration prevents cache stampedes
- ✅ Cache warming on startup (popular queries)

**Problem:**
Even with backend caching, every filter/search change triggers a new HTTP request:

```javascript
// PublicCatalogue.jsx:177-236
useEffect(() => {
  const fetchGames = async () => {
    setRefreshing(true);

    // NEW HTTP REQUEST EVERY TIME
    const data = await getPublicGames(params);

    setItems(data.items || []);
    setTotal(data.total || 0);
    setRefreshing(false);
  };

  const timer = setTimeout(fetchGames, 150); // Debounced, but still new request
  return () => clearTimeout(timer);
}, [q, category, designer, nzDesigner, players, ...]);
```

**Inefficiencies:**

1. **Redundant Network Calls:**
   - User filters by "Gateway Strategy" → API call
   - User changes sort from "Title A-Z" to "Year ↓" → NEW API call (even though data is same)
   - User goes back to "All Games" → NEW API call (could be cached from earlier)

2. **No Offline Support:**
   - If backend cache expires (30s TTL), user gets loading spinner
   - No stale-while-revalidate pattern

3. **Loading States Unnecessary:**
   - Backend cache hit = <50ms response time
   - But frontend shows loading spinner every time

### Recommended Solution: **React Query**

**Why React Query over SWR:**

| Feature | React Query | SWR |
|---------|-------------|-----|
| **Cache key management** | ✅ Automatic by query params | ✅ Manual key generation |
| **Devtools** | ✅ Built-in browser devtools | ❌ Requires separate package |
| **Prefetching** | ✅ `queryClient.prefetchQuery()` | ⚠️ Limited support |
| **Infinite scroll** | ✅ `useInfiniteQuery` hook | ⚠️ Manual implementation |
| **Bundle size** | 13KB gzipped | 4.5KB gzipped |
| **TypeScript** | ✅ Excellent | ✅ Good |
| **Adoption** | 40K+ GitHub stars | 28K+ stars |

**React Query wins for:**
- Built-in infinite scroll support (existing feature)
- Better devtools for debugging cache behavior
- Larger ecosystem and community

**Implementation:**

```bash
npm install @tanstack/react-query @tanstack/react-query-devtools
```

```javascript
// App.jsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000,        // Consider data fresh for 30s
      cacheTime: 5 * 60 * 1000,    // Keep unused data in cache for 5 minutes
      refetchOnWindowFocus: false, // Don't refetch on tab switch
      retry: 2,                    // Retry failed requests twice
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        {/* Routes */}
      </Router>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
```

```javascript
// PublicCatalogue.jsx
import { useQuery } from '@tanstack/react-query';

export default function PublicCatalogue() {
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("all");
  // ... other filters

  // React Query automatically:
  // 1. Caches by filter combination
  // 2. Deduplicates simultaneous requests
  // 3. Returns cached data instantly while revalidating
  const { data, isLoading, isRefetching, error } = useQuery({
    queryKey: ['games', { q, category, designer, nzDesigner, players, complexityRange, sort, page }],
    queryFn: () => getPublicGames({ q, page, page_size: pageSize, sort, category, designer, nz_designer: nzDesigner, players, complexity_min, complexity_max, recently_added }),
    staleTime: 30 * 1000, // Match backend cache TTL
    keepPreviousData: true, // Show old data while fetching new (smooth UX)
  });

  const games = data?.items || [];
  const total = data?.total || 0;

  // No manual useEffect needed!
  // React Query handles all fetching/caching/deduplication
}
```

**For Infinite Scroll:**

```javascript
import { useInfiniteQuery } from '@tanstack/react-query';

const {
  data,
  fetchNextPage,
  hasNextPage,
  isFetchingNextPage,
} = useInfiniteQuery({
  queryKey: ['games', filters],
  queryFn: ({ pageParam = 1 }) => getPublicGames({ ...filters, page: pageParam }),
  getNextPageParam: (lastPage, pages) => {
    const totalPages = Math.ceil(lastPage.total / lastPage.page_size);
    return pages.length < totalPages ? pages.length + 1 : undefined;
  },
});

// In IntersectionObserver callback
if (entry.isIntersecting && hasNextPage) {
  fetchNextPage();
}
```

### Expected Impact

**Performance:**
- ✅ **Instant filter changes** when returning to previous filters (cached)
- ✅ **Fewer backend requests** (30s stale time + 5min cache time)
- ✅ **Automatic deduplication** (rapid filter changes don't trigger multiple requests)
- ✅ **Background revalidation** (user sees cached data immediately, fresh data loads in background)

**Developer Experience:**
- ✅ **Remove manual useEffect** (1000+ lines → ~200 lines in PublicCatalogue)
- ✅ **Better error handling** (built-in retry and error states)
- ✅ **Debugging tools** (React Query devtools show cache state)

**User Experience:**
- ✅ **Faster perceived performance** (no loading spinners for cached data)
- ✅ **Smoother filter transitions** (previous data shown while fetching)
- ✅ **Reduced data usage** (mobile users benefit from caching)

### Implementation Effort
- **Time:** 2-4 hours
  - Install dependencies: 5 minutes
  - Wrap app with provider: 10 minutes
  - Refactor PublicCatalogue: 1-2 hours
  - Refactor GameDetails: 30 minutes
  - Testing: 1 hour
- **Risk:** Medium (requires testing all filter combinations)
- **Breaking Changes:** None (internal refactor, same API)

---

## 5. Database Query Monitoring & Real-Time Alerts

### Current State
**Status:** ✅ **Monitoring Exists, ❌ No Real-Time Alerts**

Current monitoring (`backend/middleware/performance.py`):

```python
class PerformanceMonitor:
    def __init__(self):
        self.request_times = deque(maxlen=1000)  # Last 1000 requests
        self.endpoint_stats = OrderedDict()      # Endpoint averages
        self.slow_queries = deque(maxlen=100)    # Queries > 2 seconds

    def record_request(self, path: str, method: str, duration: float, status_code: int):
        # ... record metrics

        # Record slow queries (>2 seconds)
        if duration > 2.0:
            self.slow_queries.append({
                "path": path,
                "method": method,
                "duration": duration,
                "timestamp": time.time(),
            })
```

**Access via API:**
```bash
GET /api/debug/performance
Authorization: Bearer <admin_jwt>
```

**Response:**
```json
{
  "total_requests": 1543,
  "avg_response_time_ms": 127.5,
  "slowest_endpoints": [
    {
      "endpoint": "POST /api/admin/bulk-import-csv",
      "avg_time_ms": 3421.2,
      "requests": 5,
      "errors": 0
    }
  ],
  "recent_slow_queries": [
    {
      "path": "/api/public/games",
      "method": "GET",
      "duration": 2.3,
      "timestamp": 1735975200
    }
  ]
}
```

**Limitations:**

1. **Manual Polling Required:**
   - Admins must remember to check `/api/debug/performance`
   - No alerts when queries exceed thresholds

2. **No Database-Level Tracking:**
   - Monitors HTTP request duration
   - Doesn't track individual SQL query performance
   - Can't identify which specific query is slow (joins? indexes?)

3. **No Alerting:**
   - Slow queries silently recorded
   - No notifications to Slack/email/Sentry

### Recommended Solutions

#### 5A. SQLAlchemy Query Logging (Immediate Win)

**Add database query logging:**

```python
# database.py
import logging
from sqlalchemy import event
from sqlalchemy.engine import Engine

# Configure query logger
query_logger = logging.getLogger('sqlalchemy.queries')
query_logger.setLevel(logging.WARNING)  # Only log slow queries

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - conn.info['query_start_time'].pop(-1)

    # Log slow queries (>1 second)
    if total > 1.0:
        query_logger.warning(
            f"SLOW QUERY ({total:.2f}s): {statement[:200]}...",
            extra={"duration": total, "query": statement}
        )

        # Optional: Send to Sentry
        if os.getenv("SENTRY_DSN"):
            sentry_sdk.capture_message(
                f"Slow database query: {total:.2f}s",
                level="warning",
                extras={"query": statement, "duration": total}
            )
```

**Benefits:**
- ✅ Identifies exact slow SQL queries (not just HTTP endpoints)
- ✅ Captures query text for debugging
- ✅ Integrates with existing Sentry setup (if enabled)

#### 5B. Real-Time Alerts via Sentry

**Already integrated** (`main.py:109-136`), but can enhance:

```python
# middleware/performance.py
def record_request(self, path: str, method: str, duration: float, status_code: int):
    # Existing logic...

    # Send to Sentry for slow API requests (>3 seconds)
    if duration > 3.0 and os.getenv("SENTRY_DSN"):
        sentry_sdk.capture_message(
            f"Slow API request: {method} {path} took {duration:.2f}s",
            level="warning",
            extras={
                "endpoint": f"{method} {path}",
                "duration_seconds": duration,
                "status_code": status_code,
            }
        )
```

**Configure Sentry Alerts:**
1. Go to Sentry project settings
2. Create alert rule: "If event contains 'Slow API request' → Notify Slack/email"
3. Set threshold: "More than 5 slow requests in 10 minutes"

#### 5C. PostgreSQL Query Monitoring (Advanced)

**Enable pg_stat_statements extension:**

```sql
-- Run in PostgreSQL (requires superuser or RDS parameter group)
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
```

**Query via API endpoint:**

```python
# api/routers/debug.py
@router.get("/debug/database-performance")
async def get_database_performance(db: Session = Depends(get_read_db)):
    """Get PostgreSQL query statistics"""
    result = db.execute(text("""
        SELECT
            query,
            calls,
            mean_exec_time,
            max_exec_time,
            total_exec_time
        FROM pg_stat_statements
        WHERE mean_exec_time > 100  -- Queries averaging >100ms
        ORDER BY mean_exec_time DESC
        LIMIT 20;
    """))

    return [dict(row) for row in result]
```

**Example output:**
```json
[
  {
    "query": "SELECT * FROM boardgames WHERE mana_meeple_category = $1 OFFSET $2",
    "calls": 1234,
    "mean_exec_time": 145.3,
    "max_exec_time": 523.1,
    "total_exec_time": 179273.2
  }
]
```

### Recommendations

**Implement Immediately:**
1. ✅ **SQLAlchemy query logging** (5A) - 30 minutes
2. ✅ **Sentry slow request alerts** (5B) - 15 minutes

**Implement Later (if performance degrades):**
3. ⚠️ **pg_stat_statements** (5C) - Requires database permissions, 1 hour

**Why this order:**
- 5A + 5B are **zero-cost, high-value** (no infrastructure changes)
- 5C requires RDS configuration changes and deeper PostgreSQL knowledge
- Current performance is good (Sprint 12 optimizations), so defer 5C until needed

---

## Implementation Priority

| # | Improvement | Impact | Effort | Priority | Est. Time |
|---|-------------|--------|--------|----------|-----------|
| 1 | **React.memo on GameCardPublic** | High | Low | 🔴 **Critical** | 30 min |
| 2 | **React Query (API caching)** | High | Medium | 🔴 **Critical** | 2-4 hours |
| 3 | **SQLAlchemy query logging** | Medium | Low | 🟡 **High** | 30 min |
| 4 | **Sentry slow request alerts** | Medium | Low | 🟡 **High** | 15 min |
| 5 | ~~Cursor pagination~~ | Low | High | ⚪ **Skip** | N/A |
| 6 | ~~Hover prefetch~~ | Low | Medium | ⚪ **Skip** | N/A |

**Recommended Sprint Plan:**

**Phase 1 (Day 1): Quick Wins - 1.5 hours**
- ✅ Add React.memo to GameCardPublic (30 min)
- ✅ Add SQLAlchemy query logging (30 min)
- ✅ Configure Sentry slow request alerts (15 min)
- ✅ Test and validate improvements (15 min)

**Phase 2 (Day 2-3): React Query Migration - 4 hours**
- ✅ Install and configure React Query (30 min)
- ✅ Refactor PublicCatalogue to use useInfiniteQuery (2 hours)
- ✅ Refactor GameDetails to use useQuery (30 min)
- ✅ Comprehensive testing (1 hour)

**Total Effort:** ~5.5 hours for significant performance improvements

---

## Performance Metrics to Track

**Before Implementation:**
```bash
# Measure baseline
1. Time to render 24 game cards (Chrome DevTools > Performance)
2. Number of re-renders on filter change (React DevTools > Profiler)
3. API request count over 5 minutes of browsing
4. Backend slow query count (GET /api/debug/performance)
```

**After Implementation:**
```bash
# Compare improvements
1. Card render time (expect 60-80% reduction)
2. Re-render count (expect 85-90% reduction)
3. API request count (expect 40-60% reduction)
4. Slow query alerts in Sentry (proactive monitoring)
```

**Success Criteria:**
- ✅ Filter changes feel instant (<100ms perceived latency)
- ✅ No more loading spinners for cached data
- ✅ Slow queries automatically reported to Sentry
- ✅ Mobile users report smoother scrolling (less CPU usage)

---

## Conclusion

The Mana & Meeples library is **already well-optimized** at the database and infrastructure layers (Sprint 12 work). The proposed improvements focus on **frontend rendering and API caching**, which have the highest impact-to-effort ratio.

**Key Takeaways:**
- ✅ **React.memo** - Low-hanging fruit, massive render reduction
- ✅ **React Query** - Industry standard, eliminates redundant API calls
- ✅ **Query logging** - Proactive monitoring without infrastructure changes
- ⚪ **Skip cursor pagination** - Offset-based is fine for current scale
- ⚪ **Skip hover prefetch** - Existing lazy loading is excellent

**Next Steps:**
1. Review this analysis with team
2. Approve Phase 1 quick wins (1.5 hours)
3. Schedule Phase 2 React Query migration (4 hours)
4. Monitor performance metrics post-implementation

---

**Document Version:** 1.0
**Author:** Claude (Automated Performance Analysis)
**Review Status:** Pending Team Review
