# Board Game Library - Project Configuration

## Project Overview

**Mana & Meeples Board Game Library** - A public board game catalogue system connecting a FastAPI backend with a React frontend. Enables visitors to browse the café's complete game collection, filter by category, and view detailed game information including player counts, play time, release year, images, and BoardGameGeek links.

## Architecture

### Backend (Python FastAPI)
- **Platform**: Render.com hosting
- **Database**: SQLite with BoardGameGeek API synchronization  
- **API Base**: `https://mana-meeples-boardgame-list.onrender.com`
- **Proxy**: `https://manaandmeeples.co.nz/library/api-proxy.php`

### Frontend (React)
- **Platform**: cPanel hosting at `/library/` path
- **Framework**: React 18 with React Router
- **Build Tool**: Create React App
- **Deployment**: Static build uploaded to cPanel

## Database Schema

```python
# SQLAlchemy Model Definition
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
```

## API Endpoints

### Public Endpoints
- `GET /api/public/games` - List games with filtering, search, pagination, and sorting
  - Query params: `q` (search), `page`, `page_size`, `sort`, `category`, `designer`
- `GET /api/public/games/{game_id}` - Individual game details  
- `GET /api/public/category-counts` - Category counts for filter buttons
- `GET /api/public/games/by-designer/{designer_name}` - Games by specific designer
- `GET /api/public/image-proxy` - Proxy external images with caching

### Admin Endpoints (X-Admin-Token Header Required)
- `POST /api/admin/games` - Create new game manually
- `POST /api/admin/import/bgg?bgg_id={id}&force={bool}` - Import from BoardGameGeek
- `GET /api/admin/games` - List all games (admin view)
- `GET /api/admin/games/{game_id}` - Get single game (admin view)
- `PUT /api/admin/games/{game_id}` - Update existing game
- `DELETE /api/admin/games/{game_id}` - Delete game
- `POST /api/admin/bulk-import-csv` - Bulk import games by BGG ID from CSV
- `POST /api/admin/bulk-categorize-csv` - Bulk categorize existing games from CSV
- `POST /api/admin/reimport-all-games` - Re-import all games with enhanced BGG data

### Health & Debug Endpoints
- `GET /api/health` - Basic health check
- `GET /api/health/db` - Database health check with game count
- `GET /api/debug/categories` - View all unique BGG categories in database
- `GET /api/debug/database-info` - Database structure and sample data
- `GET /api/debug/performance` - Performance monitoring stats (admin only)

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

```javascript
export const CATEGORY_KEYS = {
  GATEWAY_STRATEGY: "Gateway Strategy",
  KIDS_FAMILIES: "Kids & Families", 
  CORE_STRATEGY: "Core Strategy & Epics",
  COOP_ADVENTURE: "Co-op & Adventure",
  PARTY_ICEBREAKERS: "Party & Icebreakers"
};
```

**Category Usage**:
- **Gateway Strategy**: Accessible strategic games for new players
- **Kids & Families**: Age-appropriate games for all generations
- **Core Strategy & Epics**: Medium-heavy games for experienced players
- **Co-op & Adventure**: Collaborative and story-driven games
- **Party & Icebreakers**: Large group social games

## Frontend Structure

```
src/
├── pages/
│   ├── PublicCatalogue.jsx    # Main public game browser
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

## Search & Display Priorities

### Current Search Implementation
- **Search scope**: Title only (despite UI text mentioning "title, designers, or keyword")
- **KNOWN ISSUE**: Search description text doesn't match actual functionality
- **Performance consideration**: JSON column searches (designers, mechanics) need careful optimization

### Display Field Priorities
- **Catalogue cards**: Complexity rating is CRITICAL for user decision-making
- **Game detail pages**: Designer information is CRITICAL
- **BGG rank**: Nice-to-have feature, not essential for user experience
- **Future considerations**: mechanics, publishers, artists available but not currently prioritized

### Performance Requirements
- **Expected scale**: 400+ games minimum
- **Performance concern**: JSON column queries and search performance at scale
- **Optimization needed**: Careful indexing and query structure for JSON fields

- **IDE**: VS Code with Python virtual environment
- **Node.js**: Create React App development server
- **Python**: FastAPI with uvicorn for local backend development

## Design & UX Standards

### Accessibility Requirements
- **WCAG AAA compliance** as core requirement, not afterthought
- Semantic HTML structure for screen readers and SEO
- Proper ARIA labels and focus management
- High contrast ratios and scalable text

### Mobile-First Design
- **Touch-friendly interfaces** with adequate target sizes (44px minimum)
- **Responsive layouts** that work excellently on both mobile and desktop
- **Progressive enhancement** from mobile base to desktop features
- **Performance optimization** for mobile networks

### Visual Design Standards
- **Professional polish** with premium visual design quality
- **Micro-interactions** and smooth transitions for engagement
- **Modern React patterns** with clean component architecture
- **Consistent spacing** using design system principles

### Component Patterns
- **Clean component structure** with proper separation of concerns
- **React Hooks** for state management (useState, useEffect, useMemo)
- **Debounced search** for performance (300ms delay)
- **Proper error handling** with user-friendly messages
- **Loading states** with skeleton screens or spinners

## Technical Requirements

### Code Quality
- **Semantic HTML** structure for accessibility and SEO
- **Performance consciousness** with lazy loading and optimized renders
- **Error boundaries** and comprehensive error handling
- **TypeScript-style prop validation** where applicable

### API Integration
- **Proper HTTP status handling** (200, 404, 500, etc.)
- **Request debouncing** for search and filtering
- **Cache management** for repeated requests
- **CORS handling** through PHP proxy layer

### Deployment Considerations
- **Static build optimization** for cPanel hosting
- **URL rewriting** configuration for React Router
- **Environment variable management** for different deployments
- **Build verification** before deployment

## Current Implementation Status

## Current Implementation Status

### Working Features ✅
- **Enhanced BGG Integration**: Full sync with designers, mechanics, ratings, complexity, rank
- **Advanced filtering**: Category, designer, search with multiple sort options
- **Bulk operations**: CSV import and categorization workflows
- **Image handling**: Both thumbnail and full-size image support with local caching
- **Performance monitoring**: Request timing and slow query tracking
- **Comprehensive logging**: Structured logging with request IDs
- **Admin authentication**: Token-based with rate limiting
- **Database migrations**: Automatic schema updates on startup

### API Features
- **Advanced search**: Title search with designer filtering capability
- **Sorting options**: title_asc/desc, year_asc/desc, rating_asc/desc, time_asc/desc  
- **Pagination**: Configurable page sizes up to 1000 items
- **Category filtering**: Server-side filtering including "uncategorized" support
- **Image proxy**: External image caching with appropriate headers
- **Health endpoints**: Database health checks and performance stats

### Known Issues 🔧
- **Search functionality mismatch**: UI claims "title, designers, or keyword" but only searches title
- **Frontend category filtering**: Needs API integration (not client-side)
- **React Router configuration**: cPanel subdirectory hosting setup
- **URL rewriting setup**: Proper SPA routing configuration
- **Image quality**: thumbnail_url vs image field usage needs clarification
- **JSON search performance**: Optimize for 400+ game scale with designer/mechanic searches

### Future Roadmap 🚀
- **User accounts**: Wishlists and personal ratings system
- **Enhanced search**: Include designers, mechanics, and keyword search
- **Admin roles**: Multiple admin user system beyond single token
- **Performance optimization**: JSON field indexing and query optimization

## Development Workflow

1. **Backend changes**: Update Python code → Deploy to Render → Test API endpoints
2. **Frontend changes**: Update React code → `npm run build` → Upload to cPanel
3. **Database changes**: Apply migrations → Update API endpoints → Update frontend
4. **Category changes**: Update constants → Update both backend mapping and frontend displays

## Quality Assurance

- **Cross-device testing** on mobile, tablet, and desktop
- **Accessibility testing** with screen readers and keyboard navigation  
- **Performance monitoring** with lighthouse scores
- **Real user scenario testing** across different use cases

## Iterative Improvement Philosophy

Focus on **complete implementations** rather than partial fixes, following **web standards** consistently, testing in **real-world scenarios**, and being willing to **revisit and enhance** based on actual usage patterns.

The goal is production-ready code that serves real users in a café environment, not just portfolio demonstrations.
