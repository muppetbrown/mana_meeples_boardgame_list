# Board Game Library - Project Configuration

## Project Overview

**Mana & Meeples Board Game Library** - A public board game catalogue system connecting a FastAPI backend with a React frontend. Enables visitors to browse the café's complete game collection, filter by category and New Zealand designers, and view detailed game information including player counts, play time, release year, images, and BoardGameGeek links.

## Architecture

### Backend (Python FastAPI)
- **Platform**: Render.com hosting
- **Database**: PostgreSQL with BoardGameGeek API synchronization
- **Table**: `boardgames` (migrated from SQLite `games` table)
- **API Base**: `https://mana-meeples-boardgame-list.onrender.com`

### Frontend (React)
- **Platform**: Render.com static site hosting
- **Framework**: React 19 with React Router
- **Build Tool**: Vite 7 (migrated from Create React App)
- **Deployment**: Automatic deployment from Git via Render
- **Public URL**: `https://library.manaandmeeples.co.nz` (CNAME → `mana-meeples-library-web.onrender.com`)

## Database Schema

**Table Name**: `boardgames` (PostgreSQL)

```python
# SQLAlchemy Model Definition (models.py)
id = Column(Integer, primary_key=True, autoincrement=True)
title = Column(String(255), index=True, nullable=False)
categories = Column(Text, default="", nullable=False)  # BGG categories as text
year = Column(Integer, nullable=True)
players_min = Column(Integer, nullable=True)
players_max = Column(Integer, nullable=True)
playtime_min = Column(Integer, nullable=True)
playtime_max = Column(Integer, nullable=True)
thumbnail_url = Column(String(512), nullable=True)  # BGG thumbnail
image = Column(String(512), nullable=True)  # BGG full-size image (higher quality)
created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
bgg_id = Column(Integer, unique=True, nullable=True, index=True)
thumbnail_file = Column(String(256), nullable=True)  # Local cached thumbnail
mana_meeple_category = Column(String(50), nullable=True, index=True)  # Our 5 categories
description = Column(Text, nullable=True)
designers = Column(JSON, nullable=True)  # Array of designer names
publishers = Column(JSON, nullable=True)  # Array of publisher names
mechanics = Column(JSON, nullable=True)  # Array of game mechanics
artists = Column(JSON, nullable=True)  # Array of artist names
average_rating = Column(Float, nullable=True)  # BGG average rating
complexity = Column(Float, nullable=True)  # BGG complexity rating (1-5)
bgg_rank = Column(Integer, nullable=True)  # BGG overall rank
users_rated = Column(Integer, nullable=True)  # Number of BGG users who rated
min_age = Column(Integer, nullable=True)  # Minimum recommended age
is_cooperative = Column(Boolean, nullable=True)  # Cooperative game flag
nz_designer = Column(Boolean, nullable=True, default=False, index=True)  # New Zealand designer flag
has_sleeves = Column(String(20), nullable=True)  # Sleeve status: 'found', 'none', 'not_found', 'check', NULL, 'error', 'manual'
is_sleeved = Column(Boolean, nullable=True, default=False, index=True)  # Whether all sleeve requirements are fulfilled
```

### Sleeve Status Values (`has_sleeves`)
- **`found`**: Sleeve data exists in the `sleeves` table. Admin icon: 🃏 (when fully sleeved)
- **`none`**: Game checked, no sleeve requirements (no cards). Admin icon: 🚫🃏
- **`not_found`** / **`check`** / **`NULL`**: Needs investigation. Admin icon: ❓🃏
- **`error`**: Scraper error, may need retry
- **`manual`**: Sleeve data entered manually

## BoardGameGeek Integration

### BGG API Strategy
- **Manual sync only**: BGG data fetch triggered manually when adding games or on-demand
- **Single game calls**: Always fetch one game at a time for maximum data quality (batch calls return incomplete data)
- **Rate limiting**: Conservative approach to respect BGG API limits
- **Data prioritization**: Focus on thumbnail quality, complexity ratings, and core metadata

### Image Handling
- **thumbnail_url**: Standard BGG thumbnail (may be low quality)
- **image**: Full-size BGG image URL (higher quality solution for display issues)
- **thumbnail_file**: Local cached copy for performance

### BGG Data Fields
- **complexity**: BGG complexity rating (1-5) - **CRITICAL for catalogue cards**
- **average_rating**: BGG community rating
- **bgg_rank**: Overall BGG ranking (nice-to-have, not critical)
- **designers**: JSON array - **CRITICAL for game detail pages**
- **mechanics**: JSON array of game mechanics
- **publishers, artists**: JSON arrays for completeness

## Game Categories

```javascript
export const CATEGORY_KEYS = [
  "COOP_ADVENTURE",
  "CORE_STRATEGY",
  "GATEWAY_STRATEGY",
  "KIDS_FAMILIES",
  "PARTY_ICEBREAKERS",
];

export const CATEGORY_LABELS = {
  COOP_ADVENTURE: "Co-op & Adventure",
  CORE_STRATEGY: "Core Strategy & Epics",
  GATEWAY_STRATEGY: "Gateway Strategy",
  KIDS_FAMILIES: "Kids & Families",
  PARTY_ICEBREAKERS: "Party & Icebreakers",
};
```

**Category System**: 
- **FINAL and proven**: 5-category system has received excellent user feedback
- **No auto-mapping rules**: Manual curation ensures café/convention/team-building suitability
- **Expanded categories exist**: Additional internal categorization beyond the public 5

**Category Usage**:
- **Gateway Strategy**: Accessible strategic games for new players
- **Kids & Families**: Age-appropriate games for all generations
- **Core Strategy & Epics**: Medium-heavy games for experienced players
- **Co-op & Adventure**: Collaborative and story-driven games
- **Party & Icebreakers**: Large group social games

## Content Curation Philosophy

**Quality Control**: Manual review ensures only café/convention/team-building appropriate games
**Accidental additions**: Some games may slip through but systematic curation is the goal
**Use case focus**: Every game should serve at least one of: café play, conventions, corporate team-building
**New Zealand Focus**: Special attention to highlighting local game designers with `nz_designer` field

## API Endpoints

### Public Endpoints
- `GET /api/public/games` - List games with filtering, search, pagination, and sorting
  - Query params: `q` (search), `page`, `page_size`, `sort`, `category`, `designer`, `nz_designer`
- `GET /api/public/games/{game_id}` - Individual game details  
- `GET /api/public/category-counts` - Category counts for filter buttons
- `GET /api/public/games/by-designer/{designer_name}` - Games by specific designer
- `GET /api/public/image-proxy` - Proxy external images with caching

### Admin Endpoints (JWT Authentication Required)
**Authentication**: Admin endpoints require JWT token in `Authorization: Bearer <token>` header. Login via `/api/admin/login` to receive JWT token.

**Auth Endpoints**:
- `POST /api/admin/login` - Login with admin token, returns JWT
- `POST /api/admin/logout` - Logout (client-side token removal)
- `GET /api/admin/validate` - Validate current JWT token

**Game Management**:
- `POST /api/admin/games` - Create new game manually
- `POST /api/admin/import/bgg?bgg_id={id}&force={bool}` - Import from BoardGameGeek
- `GET /api/admin/games` - List all games (admin view)
- `GET /api/admin/games/{game_id}` - Get single game (admin view)
- `PUT /api/admin/games/{game_id}` - Update existing game
- `DELETE /api/admin/games/{game_id}` - Delete game
- `POST /api/admin/bulk-import-csv` - Bulk import games by BGG ID from CSV
- `POST /api/admin/bulk-categorize-csv` - Bulk categorize existing games from CSV
- `POST /api/admin/bulk-update-nz-designers` - Bulk update NZ designer status from CSV
- `POST /api/admin/reimport-all-games` - Re-import all games with enhanced BGG data

### Health & Debug Endpoints
- `GET /api/health` - Basic health check
- `GET /api/health/db` - Database health check with game count
- `GET /api/debug/categories` - View all unique BGG categories in database
- `GET /api/debug/database-info?limit={n}` - Database structure and sample data
- `GET /api/debug/export-games-csv?limit={n}` - Export all game data as CSV
- `GET /api/debug/performance` - Performance monitoring stats (admin only)

## Search & Display Priorities

### Current Search Implementation
- **Search scope**: Title, designers, and description (comprehensive search across key fields)
- **UI text**: Accurately shows "Search by title..." to manage user expectations
- **Performance consideration**: JSON column searches (designers, mechanics) need careful optimization

### Display Field Priorities
- **Catalogue cards**: Complexity rating is CRITICAL for user decision-making
- **Game detail pages**: Designer information is CRITICAL
- **BGG rank**: Nice-to-have feature, not essential for user experience
- **NZ Designer filter**: Special prominence for local content discovery
- **Future considerations**: mechanics, publishers, artists available but not currently prioritized

### Performance Requirements
- **Expected scale**: 400+ games minimum
- **Performance concern**: JSON column queries and search performance at scale
- **Optimization needed**: Careful indexing and query structure for JSON fields

## Configuration & Environment

### Backend Environment Variables (Render)
```
ADMIN_TOKEN=<secure-token-set-in-render-dashboard>
SESSION_SECRET=<secure-secret-for-jwt-signing>
JWT_EXPIRATION_DAYS=7
CORS_ORIGINS=https://manaandmeeples.co.nz,https://www.manaandmeeples.co.nz,https://library.manaandmeeples.co.nz,https://mana-meeples-library-web.onrender.com
DATABASE_URL=postgresql://tcg_admin:<password>@dpg-d3i3387diees738trbg0-a.singapore-postgres.render.com/tcg_singles
PUBLIC_BASE_URL=https://mana-meeples-boardgame-list.onrender.com
PYTHON_VERSION=3.11.9
```

**Important**: Sensitive credentials should be set securely in Render dashboard, not hardcoded in code.
Use the `render.yaml` blueprint for infrastructure-as-code deployment with secure secret management.

**JWT Authentication**: The system uses JWT (JSON Web Tokens) for admin authentication, which are stateless and persist across server restarts. The `SESSION_SECRET` is used to sign JWTs. Generate a secure secret with: `python -c "import secrets; print(secrets.token_hex(32))"`

### Frontend API Configuration
API base resolution in `config/api.js` with multiple fallback strategies:
1. **Runtime window variable**: `window.__API_BASE__` for dynamic configuration
2. **Meta tag**: `<meta name="api-base">` in index.html (hardcoded production URL)
3. **Build-time env**: `import.meta.env.VITE_API_BASE` (set in render.yaml)
4. **Production domain detection**: Auto-detects production domains and uses hardcoded API URL
5. **Dev fallback**: `http://127.0.0.1:8000` for local development

**Production setup**: The frontend is deployed as a separate static site on Render with `VITE_API_BASE` environment variable pointing to the backend API service.

**Important**: Environment variables in Vite must be prefixed with `VITE_` to be exposed to the client code. The build process replaces `import.meta.env.VITE_*` with the actual values at build time.

### Image Optimization Strategy
Advanced BGG image quality enhancement in `imageProxyUrl()`:
- **Priority order**: `_original` > `_d` (detail) > `_md` (medium) > `_mt` (medium thumb) > `_t` (thumbnail)
- **Automatic upscaling**: Frontend requests highest quality, backend handles fallback chain
- **Proxy caching**: All external images routed through `/api/public/image-proxy`

### Database Infrastructure

**PostgreSQL Configuration**:
- **Provider**: Render PostgreSQL (Singapore region)
- **Database**: `tcg_singles`
- **Table**: `boardgames` (migrated from SQLite November 2025)
- **Connection pooling**: QueuePool with 15 permanent connections, 20 overflow
- **Health checks**: Pool pre-ping enabled for connection validation
- **Driver**: psycopg2-binary 2.9.9

**Connection Pool Settings** (database.py):
```python
pool_size=15         # Permanent connections (default)
max_overflow=20      # Additional connections when busy (default)
pool_timeout=30      # Wait time for available connection
pool_recycle=900     # Recycle connections every 15 min (conservative for cloud PostgreSQL)
pool_pre_ping=True   # Test connections before use
```

**Note**: The 15-minute recycle interval is conservative for cloud PostgreSQL services (like Render or AWS RDS) which may have shorter idle connection timeouts. This prevents stale connections while avoiding excessive reconnection overhead.

**Deployment with Render Blueprint**:
- **File**: `render.yaml` - Infrastructure as code configuration
- **Security**: Sensitive credentials managed via Render dashboard (not in code)
- **Health checks**: Automatic monitoring via `/api/health` endpoint
- **Auto-deploy**: Enabled from Git repository

**Migration Notes**:
- Data migrated from SQLite `games` table to PostgreSQL `boardgames` table
- All JSON columns (designers, mechanics, publishers, artists) use native PostgreSQL JSON type
- Removed SQLite-specific PRAGMA-based migrations
- Indexes maintained for performance (title, bgg_id, mana_meeple_category, nz_designer)

### Redis Infrastructure (Sprint 8-9: Horizontal Scaling)

**Status**: ✅ COMPLETED (December 2025)

**Redis Configuration**:
- **Purpose**: Session storage and rate limiting for multi-instance horizontal scaling
- **Provider**: Configurable (Render Redis, Upstash, Redis Labs, or self-hosted)
- **Fallback**: Automatic in-memory fallback when Redis unavailable
- **Driver**: redis 5.0.1 (async-compatible Python client)

**Architecture Features**:
- **Graceful degradation**: System works with or without Redis
- **Connection pooling**: Automatic connection management with health checks
- **TTL-based expiration**: Automatic cleanup of expired sessions and rate limit data
- **Dual-mode operation**: Redis-first with in-memory fallback

**Redis Client Settings** (redis_client.py):
```python
socket_connect_timeout=5    # Connection timeout
socket_timeout=5            # Operation timeout
retry_on_timeout=True       # Auto-retry on timeout
health_check_interval=30    # Connection health check frequency
decode_responses=True       # Auto-decode to strings
```

**Environment Variables**:
```bash
REDIS_URL=redis://localhost:6379/0  # Redis connection URL
REDIS_ENABLED=true                   # Enable/disable Redis (fallback to memory)
SESSION_TIMEOUT_SECONDS=3600         # Session expiration (1 hour default)
```

**Session Storage** (shared/rate_limiting.py):
- **Class**: `SessionStorage` - Handles admin sessions with Redis backend
- **Storage**: `session:{token}` keys with automatic TTL expiration
- **Data**: JSON-serialized session data (created_at, IP, etc.)
- **Methods**: `set_session()`, `get_session()`, `delete_session()`

**Rate Limiting** (shared/rate_limiting.py):
- **Class**: `RateLimitTracker` - Tracks authentication attempts per IP
- **Storage**: `ratelimit:admin:{ip}` keys with automatic TTL expiration
- **Data**: JSON arrays of attempt timestamps
- **Methods**: `get_attempts()`, `set_attempts()`

**Health Monitoring**:
- **Endpoint**: `GET /api/health/redis`
- **Response Statuses**:
  - `healthy` - Redis connected and responding
  - `disabled` - Redis disabled, using in-memory storage
  - `unhealthy` - Redis not responding
  - `error` - Redis health check failed

**Local Development** (Docker Compose):
```yaml
services:
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes: [redis_data:/data]
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3
```

**Testing**:
- **Script**: `backend/test_redis_integration.py`
- **Test Coverage**: Connection, operations, session storage, rate limiting
- **Usage**: `python backend/test_redis_integration.py` (requires Redis running)

**Production Deployment**:
- **Recommended**: Render Redis or Upstash (managed Redis services)
- **Configuration**: Set `REDIS_URL` and `REDIS_ENABLED=true` in environment
- **Monitoring**: Health check endpoint + Redis metrics (memory, connections, keys)
- **Benefits**: Multi-instance deployment, session persistence across restarts

**Migration Impact**:
- **Backward compatible**: System works with or without Redis
- **No data loss**: In-memory fallback for development and single-instance deployments
- **Zero downtime**: Can enable/disable Redis without service interruption
- **Multi-instance ready**: Supports horizontal scaling with shared session state

**Documentation**:
- **Setup Guide**: `REDIS_SETUP.md` - Comprehensive Redis deployment instructions
- **Sprint Summary**: `SPRINT_8_REDIS_SUMMARY.md` - Implementation details and testing
- **Roadmap**: `PRIORITIZED_IMPROVEMENT_ROADMAP.md` - Sprint 8-9 completion tracking

## Component Architecture Details

### Error Handling System
**ErrorBoundary.jsx**: Production-ready React error boundary with:
- **Graceful fallback UI** with retry and refresh options
- **Development mode debugging** with full error stack traces
- **User-friendly error messages** without technical jargon
- **Accessibility-compliant design** with proper ARIA attributes and focus management

### Image Management System
**GameImage.jsx**: Sophisticated image component featuring:
- **Progressive loading** with opacity transitions and loading placeholders
- **Automatic fallback** to styled "No Image" placeholder on errors
- **Loading states** with skeleton animation using Tailwind's `animate-pulse`
- **Lazy loading** support with configurable loading strategy
- **BGG image optimization** integration with `imageProxyUrl()` from config/api.js

### API Architecture
**config/api.js**: Core API configuration utilities handling:
- **Multi-environment configuration** with 5-tier fallback system
- **BGG image quality enhancement** with automatic resolution upgrading
- **JSON validation** with comprehensive error handling
- **Proxy integration** for all external image requests

**api/client.js**: Higher-level API communication layer (separate from utils/api.js)

### Category System
**constants/categories.js**: Centralized category management with:
- **Backend synchronization**: CATEGORY_KEYS match main.py exactly
- **UI-friendly labels**: Human-readable category names for display
- **Backward compatibility**: Legacy aliases for gradual migration

### Filter System
**PublicCatalogue.jsx**: Advanced filtering with:
- **URL parameter persistence**: All filters maintain state in URL for sharing/bookmarking
- **Debounced search**: 150ms delay for optimal performance
- **Multi-filter support**: Category, search, designer, NZ designer, sort combinations
- **Active filter display**: Visual chips showing current filters with individual remove buttons
- **Mobile-optimized**: Responsive button layouts with proper touch targets

## Frontend Structure

```
src/
├── pages/
│   ├── PublicCatalogue.jsx    # Main public game browser with advanced filtering
│   ├── GameDetails.jsx        # Individual game details
│   └── AdminLogin.jsx         # Staff authentication
├── components/
│   ├── public/
│   │   ├── GameCardPublic.jsx # Game display cards
│   │   ├── Pagination.jsx     # Page navigation
│   │   ├── SortSelect.jsx     # Sort options
│   │   └── SearchBox.jsx      # Search functionality
│   ├── staff/
│   │   ├── LibraryCard.jsx    # Admin game management
│   │   ├── SearchBGGPanel.jsx # BGG search integration
│   │   └── BulkPanels.jsx     # Bulk import/categorize
│   ├── CategoryFilter.jsx     # Category filter buttons
│   ├── CategorySelectModal.jsx # Category assignment modal
│   ├── ErrorBoundary.jsx      # Error handling wrapper
│   └── GameImage.jsx          # Image component with fallbacks
├── utils/
│   └── api.js                 # API communication utilities
├── api/
│   └── client.js              # API communication layer
├── constants/
│   └── categories.js          # Category definitions
└── App.js                     # Main router and state
```

## Cross-Platform Requirements

### Desktop vs Mobile Considerations
**Critical deployment requirement**: The library must work excellently on both desktop and mobile with different UX requirements:

**Desktop Focus:**
- **Larger screens**: More information density, grid layouts, hover interactions
- **Mouse interactions**: Precise clicking, hover states, right-click context menus
- **Keyboard navigation**: Full accessibility with tab navigation and shortcuts
- **Performance**: Can handle larger images and more complex interactions

**Mobile Focus:**  
- **Touch interfaces**: Minimum 44px touch targets, swipe gestures, touch-friendly spacing
- **Smaller screens**: Single-column layouts, prioritized information hierarchy
- **Performance**: Optimized images, lazy loading, efficient rendering
- **Network considerations**: Works well on slower mobile connections

**Shared Requirements:**
- **Accessibility**: WCAG AAA compliance across all devices
- **Performance**: Fast loading and smooth interactions on both platforms
- **Visual consistency**: Cohesive design that adapts appropriately to each platform

## Current Implementation Status

### Working Features ✅
- **Enhanced BGG Integration**: Full sync with designers, mechanics, ratings, complexity, rank
- **Advanced filtering**: Category, designer, NZ designer, search with multiple sort options
- **Bulk operations**: CSV import, categorization, and NZ designer status workflows
- **Image handling**: Both thumbnail and full-size image support with local caching
- **Performance monitoring**: Request timing and slow query tracking
- **Comprehensive logging**: Structured logging with request IDs
- **Admin authentication**: Token-based with rate limiting
- **Database migrations**: Automatic schema updates on startup
- **URL state persistence**: All filters maintain state in URL for sharing/bookmarking

### API Features
- **Advanced search**: Title search with designer filtering capability
- **Sorting options**: title_asc/desc, year_asc/desc, rating_asc/desc, time_asc/desc  
- **Pagination**: Configurable page sizes up to 1000 items
- **Category filtering**: Server-side filtering including "uncategorized" support
- **NZ Designer filtering**: Boolean filter for highlighting local content
- **Image proxy**: External image caching with appropriate headers
- **Health endpoints**: Database health checks and performance stats
- **CSV export**: Complete data export functionality with configurable limits

### Known Issues 🔧
- **Frontend category filtering**: Needs API integration (not client-side)
- **React Router configuration**: cPanel subdirectory hosting setup
- **URL rewriting setup**: Proper SPA routing configuration
- **Image quality**: thumbnail_url vs image field usage needs clarification
- **JSON search performance**: Optimize for 400+ game scale with designer/mechanic searches

### Future Roadmap 🚀
- **User accounts**: Wishlists and personal ratings system
- **Enhanced search**: Include mechanics search (currently covers title, designers, description)
- **Admin roles**: Multiple admin user system beyond single token
- **Performance optimization**: JSON field indexing and query optimization
- **Advanced NZ content**: Designer profiles and local game showcase features

## Development Workflow

1. **Backend changes**: Update Python code → Push to Git → Auto-deploy to Render → Test API endpoints
2. **Frontend changes**: Update React code → Push to Git → Auto-deploy to Render → Test on library.manaandmeeples.co.nz
3. **Database changes**: Apply migrations → Update API endpoints → Update frontend
4. **Category changes**: Update constants → Update both backend mapping and frontend displays
5. **NZ Designer updates**: Use bulk CSV endpoint or individual game admin interface

**Note**: Both frontend and backend are now hosted on Render with automatic deployments from Git. No manual build/upload steps required!

## Quality Assurance

- **Cross-device testing** on mobile, tablet, and desktop
- **Accessibility testing** with screen readers and keyboard navigation  
- **Performance monitoring** with lighthouse scores
- **Real user scenario testing** across different use cases
- **Filter combination testing** ensuring all combinations work properly
- **URL sharing verification** that bookmarked filter states work correctly

## Iterative Improvement Philosophy

Focus on **complete implementations** rather than partial fixes, following **web standards** consistently, testing in **real-world scenarios**, and being willing to **revisit and enhance** based on actual usage patterns.

The goal is production-ready code that serves real users in a café environment, not just portfolio demonstrations. Special emphasis on making New Zealand content discoverable while maintaining the proven 5-category system that users love.
