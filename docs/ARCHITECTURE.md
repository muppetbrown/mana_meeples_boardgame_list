# System Architecture

Comprehensive architecture documentation for the Mana & Meeples Board Game Library.

## High-Level Overview

```
┌─────────────┐      HTTPS      ┌──────────────────┐
│   Browser   │ ←──────────────→ │   React SPA      │
│             │                  │   (Render.com)   │
└─────────────┘                  └────────┬─────────┘
                                          │
                                     API Calls
                                     (axios)
                                          │
                                          ▼
                                 ┌────────────────────┐
                                 │   FastAPI Backend  │
                                 │   (Render.com)     │
                                 └────────┬───────────┘
                                          │
                                    SQLAlchemy
                                          │
                                          ▼
                                 ┌────────────────────┐
                                 │   PostgreSQL DB    │
                                 │   (Render.com)     │
                                 └────────────────────┘

                                 ┌────────────────────┐
                                 │  BoardGameGeek API │
                                 │   (External)       │
                                 └────────────────────┘
```

## Technology Stack

### Backend
- **Framework**: FastAPI 0.110.0 (async Python web framework)
- **Server**: Uvicorn 0.30.6 (ASGI server)
- **Database**: PostgreSQL 15 via SQLAlchemy 1.4.52
- **Validation**: Pydantic 1.10.15 (data models and validation)
- **HTTP Client**: httpx 0.27.0 (async HTTP for BGG API)
- **Rate Limiting**: SlowAPI 0.1.9
- **Testing**: pytest 7.4.3, pytest-asyncio, pytest-cov
- **Hosting**: Render.com (auto-deploy from Git)

### Frontend
- **Framework**: React 19.1.1
- **Routing**: React Router v7.8.2
- **HTTP Client**: Axios 1.11.0
- **Styling**: Tailwind CSS 3.4.17
- **Build Tool**: Create React App (react-scripts 5.0.1)
- **Icons**: Lucide React 0.542.0
- **Sanitization**: DOMPurify 3.3.0 (XSS protection)
- **Testing**: Jest + React Testing Library
- **Hosting**: Render.com Static Site

### Infrastructure
- **CI/CD**: GitHub Actions
- **Version Control**: Git + GitHub
- **Deployment**: Render.com (auto-deploy on push to main)
- **Database**: Render PostgreSQL (managed service)
- **File Storage**: Ephemeral disk (/var/data/thumbs on Render)

## Backend Architecture

### Layered Structure

```
┌─────────────────────────────────────┐
│         API Routers                 │  HTTP endpoints, request/response
│  (public, admin, bulk, health)      │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│         Services (future)           │  Business logic, data operations
│  (game_service, image_service)      │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│    Models & Database Access         │  ORM models, database queries
│      (SQLAlchemy)                   │
└─────────────────────────────────────┘
```

### Directory Structure

```
backend/
├── main.py                     # App initialization, middleware setup
├── config.py                   # Environment variables & settings
├── database.py                 # Database connection & session management
├── models.py                   # SQLAlchemy ORM models
├── schemas.py                  # Pydantic request/response schemas
├── exceptions.py               # Custom exception classes
├── bgg_service.py              # BoardGameGeek API integration
│
├── api/
│   ├── dependencies.py         # Shared dependencies (auth, helpers)
│   └── routers/
│       ├── public.py           # Public game browsing endpoints
│       ├── admin.py            # Admin CRUD & authentication
│       ├── bulk.py             # Bulk import/categorization
│       └── health.py           # Health checks & debug endpoints
│
├── middleware/
│   ├── logging.py              # Request logging with IDs
│   └── performance.py          # Performance monitoring
│
├── services/                   # Business logic (future expansion)
├── utils/
│   └── helpers.py              # Utility functions
│
└── tests/                      # Test suite
    ├── conftest.py             # pytest fixtures
    ├── test_api/               # API endpoint tests
    ├── test_services/          # Service tests (future)
    └── test_integration/       # E2E tests (future)
```

### Key Components

#### 1. Routers (API Endpoints)
Handle HTTP requests and responses, delegate to services/models.

- **public.py**: Public game browsing, search, filters
  - GET /api/public/games (list with pagination/filters)
  - GET /api/public/games/{id} (single game details)
  - GET /api/public/category-counts
  - GET /api/public/image-proxy (external image caching)

- **admin.py**: Admin game management
  - POST /api/admin/login (session creation)
  - GET /api/admin/validate (token validation)
  - CRUD operations for games
  - POST /api/admin/import/bgg (import from BGG)

- **bulk.py**: Bulk operations
  - POST /api/admin/bulk-import-csv
  - POST /api/admin/bulk-categorize-csv
  - POST /api/admin/bulk-update-nz-designers
  - POST /api/admin/reimport-all-games

- **health.py**: Monitoring endpoints
  - GET /api/health (basic health)
  - GET /api/health/db (database connection check)
  - GET /api/debug/* (debug information)

#### 2. Middleware
Process every request/response.

- **RequestLoggingMiddleware**: Logs requests with unique IDs, timing
- **PerformanceMonitor**: Tracks endpoint performance, slow queries
- **CacheThumbsMiddleware**: Adds cache headers to thumbnail responses
- **CORSMiddleware**: Handles cross-origin requests

#### 3. Database Layer
SQLAlchemy ORM for database access.

**Models** (models.py):
- `Game` model with 30+ fields
- JSON columns for arrays (designers, mechanics, publishers, artists)
- Indexes on: title, bgg_id, mana_meeple_category, nz_designer

**Database** (database.py):
- Connection pooling (5 permanent + 10 overflow)
- Session management with dependency injection
- Automatic migrations on startup
- Health check with ping

#### 4. External Integrations

**BoardGameGeek API** (bgg_service.py):
- Fetches game metadata (XML API)
- Rate-limited to respect BGG servers
- Parses: title, year, players, complexity, ratings, designers, mechanics
- Image URLs (thumbnail and full-size)

**Image Proxy**:
- Caches external BGG images
- Optimizes image quality (requests highest resolution)
- Adds appropriate cache headers

## Frontend Architecture

### Component Hierarchy

```
App.js (Router)
│
├── / (Public Catalogue)
│   ├── CategoryFilter
│   ├── SearchBox
│   ├── SortSelect
│   ├── Pagination
│   └── GameCardPublic (repeated)
│
├── /games/:id (Game Details)
│   ├── GameImage
│   └── Game information display
│
└── /staff (Admin Interface)
    ├── AdminLogin
    ├── LibraryCard (game management)
    ├── SearchBGGPanel
    ├── BulkPanels
    └── CategorySelectModal
```

### Directory Structure

```
frontend/src/
├── App.js                      # Main router, top-level state
├── index.js                    # React entry point
│
├── pages/
│   ├── PublicCatalogue.jsx     # Main public game browser
│   ├── GameDetails.jsx         # Single game detail page
│   └── AdminLogin.jsx          # Admin authentication
│
├── components/
│   ├── public/
│   │   ├── GameCardPublic.jsx  # Game display card
│   │   ├── Pagination.jsx      # Page navigation
│   │   ├── SortSelect.jsx      # Sort dropdown
│   │   └── SearchBox.jsx       # Search input
│   │
│   ├── staff/
│   │   ├── LibraryCard.jsx     # Admin game card
│   │   ├── SearchBGGPanel.jsx  # BGG search
│   │   └── BulkPanels.jsx      # Bulk operations
│   │
│   ├── CategoryFilter.jsx      # Category buttons
│   ├── CategorySelectModal.jsx # Category selection
│   ├── ErrorBoundary.jsx       # Error handling
│   └── GameImage.jsx           # Image with fallbacks
│
├── api/
│   └── client.js               # API methods (axios)
│
├── config/
│   └── api.js                  # API configuration
│
├── hooks/
│   ├── useToast.js             # Toast notifications
│   └── useAuth.js              # Authentication state
│
├── constants/
│   └── categories.js           # Category definitions
│
└── __tests__/                  # Test files
```

### State Management

**1. URL State (React Router)**
- Primary source of truth for filters
- Enables shareable links
- Browser back/forward navigation
- Query parameters: q, category, page, sort, designer, nz_designer

**2. Local Component State (useState)**
- UI state (modals, loading, errors)
- Form inputs
- Transient data

**3. Future: Context API**
- Planned for admin panel state
- Authentication state
- Shared data across components

### Data Flow

#### Public Game Browsing Flow

```
1. User Action
   ├── Adjusts filter (category, search, etc.)
   └── Updates URL params via setSearchParams()

2. URL Change Detected
   ├── useEffect triggers on searchParams change
   └── Parses URL params

3. API Request
   ├── Calls getPublicGames() from api/client.js
   └── axios GET /api/public/games?params

4. Backend Processing
   ├── Router receives request
   ├── Applies filters (category, search, sort)
   ├── Paginates results
   └── Returns JSON

5. Frontend Update
   ├── Sets loading state
   ├── Updates games list state
   ├── Renders GameCardPublic components
   └── Updates pagination
```

#### Admin Game Import Flow

```
1. Admin Input
   └── Enters BGG ID in SearchBGGPanel

2. BGG Search
   ├── POST /api/admin/import/bgg?bgg_id=12345
   └── Backend fetches from BGG XML API

3. Game Creation
   ├── Parses BGG data
   ├── Creates Game record in database
   └── Queues thumbnail download (background task)

4. Response
   ├── Returns created game data
   └── Frontend adds to library list

5. Background Processing
   ├── Downloads thumbnail from BGG
   ├── Saves to /var/data/thumbs
   └── Updates game.thumbnail_file
```

## Database Schema

### Game Model

**Table**: `boardgames`

**Primary Key**: `id` (auto-increment)

**Core Fields**:
- `title` (string, indexed) - Game name
- `year` (integer) - Publication year
- `bgg_id` (integer, unique, indexed) - BoardGameGeek ID
- `mana_meeple_category` (string, indexed) - Our categorization
- `nz_designer` (boolean, indexed) - New Zealand designer flag

**Game Mechanics**:
- `players_min`, `players_max` (integer) - Player count range
- `playtime_min`, `playtime_max` (integer) - Playtime in minutes
- `min_age` (integer) - Minimum age
- `is_cooperative` (boolean) - Cooperative game flag

**BGG Data**:
- `complexity` (float) - BGG complexity rating (1-5)
- `average_rating` (float) - BGG average rating
- `bgg_rank` (integer) - BGG overall rank
- `users_rated` (integer) - Number of BGG ratings

**Content**:
- `description` (text) - Game description (HTML)
- `categories` (text) - BGG categories (comma-separated)
- `designers` (JSON array) - Designer names
- `publishers` (JSON array) - Publisher names
- `mechanics` (JSON array) - Game mechanics
- `artists` (JSON array) - Artist names

**Images**:
- `thumbnail_url` (string) - BGG thumbnail URL
- `image` (string) - BGG full-size image URL
- `thumbnail_file` (string) - Local cached thumbnail filename

**Metadata**:
- `created_at` (datetime) - Record creation timestamp

### Indexes

- `ix_boardgames_title` - Fast title searches
- `ix_boardgames_bgg_id` - BGG lookups
- `ix_boardgames_mana_meeple_category` - Category filtering
- `ix_boardgames_nz_designer` - NZ designer filtering

### Relationships

Currently: No foreign key relationships (flat structure)

Future considerations:
- Separate `designers` table with many-to-many relationship
- `categories` table for normalized categorization
- `images` table for multi-image support

## API Design

### RESTful Endpoints

**Public API** (No authentication required):
- GET /api/public/games - List games with filters
- GET /api/public/games/{id} - Get single game
- GET /api/public/category-counts - Category statistics
- GET /api/public/games/by-designer/{name} - Games by designer
- GET /api/public/image-proxy - Cached image proxy

**Admin API** (X-Admin-Token header required):
- POST /api/admin/login - Create admin session
- GET /api/admin/validate - Validate token
- GET /api/admin/games - List all games (admin view)
- POST /api/admin/games - Create new game
- PUT /api/admin/games/{id} - Update game
- DELETE /api/admin/games/{id} - Delete game
- POST /api/admin/import/bgg - Import from BGG
- POST /api/admin/bulk-* - Bulk operations

**Health API** (Public):
- GET /api/health - Basic health check
- GET /api/health/db - Database health
- GET /api/debug/* - Debug information (some admin-only)

### Authentication

**Method**: Token-based with session cookies

**Flow**:
1. Admin provides token via POST /api/admin/login
2. Backend validates against ADMIN_TOKEN env var
3. Creates session, returns httpOnly cookie
4. Future requests include cookie automatically
5. Fallback: X-Admin-Token header for legacy support

**Rate Limiting**:
- Admin endpoints: 5 attempts per minute per IP
- Public endpoints: 100 requests per minute per IP

## Security Measures

### Backend
- ✅ httpOnly session cookies (XSS prevention)
- ✅ CSRF protection via SameSite cookies
- ✅ Rate limiting on all endpoints
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ Input validation (Pydantic schemas)
- ✅ Admin authentication required for sensitive operations
- ✅ CORS configured for specific origins only

### Frontend
- ✅ XSS protection with DOMPurify (sanitizes BGG HTML)
- ✅ No sensitive data in localStorage
- ✅ HTTPS-only in production
- ✅ Content Security Policy headers

## Performance Optimizations

### Backend
- **Connection Pooling**: 5 permanent + 10 overflow connections
- **Database Indexes**: On frequently queried columns
- **Background Tasks**: Thumbnail downloads don't block responses
- **Image Proxy Caching**: Cache-Control headers for CDN caching

### Frontend
- **Code Splitting**: React Router lazy loading (future)
- **Image Optimization**: Progressive loading, lazy loading
- **API Caching**: Axios response caching (future)
- **Debounced Search**: 150ms delay reduces API calls
- **URL State**: Prevents unnecessary re-renders

## Deployment

### Backend Deployment (Render)

**Build Command**: `pip install -r backend/requirements.txt`
**Start Command**: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
**Health Check**: GET /api/health

**Environment Variables**:
- DATABASE_URL (Render PostgreSQL connection string)
- ADMIN_TOKEN (secure random token)
- CORS_ORIGINS (comma-separated allowed origins)
- PUBLIC_BASE_URL (backend URL for absolute URLs)
- THUMBS_DIR (/var/data/thumbs on Render disk)

**Disk Storage**: 1GB persistent disk at /var/data

### Frontend Deployment (Render)

**Build Command**: `cd frontend && npm install && npm run build`
**Publish Directory**: `frontend/build`

**Environment Variables**:
- REACT_APP_API_BASE (backend API URL)

**Routing**: Rewrite all routes to /index.html (SPA support)

### CI/CD Pipeline

**Trigger**: Push to main or claude/* branches
**Jobs**:
1. Backend tests (pytest with PostgreSQL)
2. Frontend tests (Jest with coverage)
3. Linting (flake8 + black)

**Deployment**: Automatic on successful merge to main

## Monitoring & Observability

### Current Monitoring
- Request logging with unique IDs
- Performance monitoring (response times, slow queries)
- Database health checks
- Error logging with stack traces

### Future Enhancements
- Sentry for error tracking
- Structured logging (JSON format)
- Performance dashboards
- Uptime monitoring
- Database query performance tracking

## Scalability Considerations

### Current Limitations
- Single-instance deployment (Render free tier)
- Ephemeral file storage (thumbnails lost on restart)
- In-memory session storage (doesn't scale across instances)

### Future Improvements
- **Horizontal Scaling**: Deploy multiple backend instances
- **Session Storage**: Move to Redis or database
- **File Storage**: Use S3 or Cloudinary for thumbnails
- **Caching**: Redis for frequently accessed data
- **Database**: Read replicas for scaling reads
- **CDN**: CloudFlare for static assets and API caching

## Development Workflow

1. **Local Development**:
   - Backend: `cd backend && python main.py`
   - Frontend: `cd frontend && npm start`
   - Database: Local PostgreSQL or SQLite

2. **Feature Development**:
   - Create feature branch from main
   - Implement changes with tests
   - Run tests locally
   - Push to GitHub
   - CI runs automated tests
   - Code review
   - Merge to main

3. **Deployment**:
   - Merge to main triggers auto-deploy
   - Render builds and deploys
   - Health checks verify deployment
   - Monitor logs for errors

## Best Practices

### Code Organization
- ✅ Backend: Modular routers, separation of concerns
- ✅ Frontend: Component-based architecture
- ✅ Shared utilities in dedicated directories
- ✅ Tests alongside implementation

### Error Handling
- ✅ Custom exception classes
- ✅ Graceful degradation
- ✅ User-friendly error messages
- ✅ Error boundaries in React

### Documentation
- ✅ Code comments for complex logic
- ✅ Docstrings for public functions
- ✅ README files in each major directory
- ✅ Architecture documentation (this file)

---

**Last Updated**: Phase 5 (Documentation & Polish)
**Version**: 2.0.0
**Maintainer**: Development Team
