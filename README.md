# Mana & Meeples Board Game Library

[![CI/CD](https://github.com/muppetbrown/mana_meeples_boardgame_list/actions/workflows/ci.yml/badge.svg)](https://github.com/muppetbrown/mana_meeples_boardgame_list/actions)
[![codecov](https://codecov.io/gh/muppetbrown/mana_meeples_boardgame_list/branch/main/graph/badge.svg)](https://codecov.io/gh/muppetbrown/mana_meeples_boardgame_list)
[![Frontend Tests](https://img.shields.io/badge/Frontend%20Coverage-62.77%25-success)](frontend/coverage)
[![Backend Tests](https://img.shields.io/badge/Backend%20Tests-190%2B-success)](backend/tests)

A comprehensive board game catalogue system connecting a FastAPI backend with a React frontend, enabling visitors to browse the café's complete game collection with advanced filtering, search, and BoardGameGeek integration.

## 🎯 Project Overview

**Live Site**: [library.manaandmeeples.co.nz](https://library.manaandmeeples.co.nz)
**Backend API**: [mana-meeples-boardgame-list.onrender.com](https://mana-meeples-boardgame-list.onrender.com)
**Platform**: Render.com (auto-deploy from Git)

### Key Features
- 🎲 Browse 400+ board games with detailed information
- 🔍 Advanced search and filtering (category, designer, players, complexity)
- 🇳🇿 Special highlighting for New Zealand designers
- 📊 BoardGameGeek integration for ratings, complexity, and metadata
- 🖼️ Image proxying and caching for optimal performance
- 🔐 Secure admin interface for game management

## 📁 Project Structure

```
mana_meeples_boardgame_list/
├── 📄 README.md                 # You are here
├── 📄 CLAUDE.md                 # Project configuration and architecture
├── 📄 render.yaml               # Deployment configuration
│
├── 📁 backend/                  # Python FastAPI backend
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Configuration management
│   ├── database.py              # Database connection & migrations
│   ├── models.py                # SQLAlchemy models
│   ├── schemas.py               # Pydantic schemas
│   ├── exceptions.py            # Custom exceptions
│   ├── bgg_service.py           # BoardGameGeek API integration
│   ├── requirements.txt         # Python dependencies
│   ├── runtime.txt              # Python version
│   │
│   ├── 📁 api/                  # API routers (modular endpoints)
│   │   ├── dependencies.py      # Shared dependencies & auth
│   │   └── routers/             # Organized by function
│   │       ├── public.py        # Public game browsing
│   │       ├── admin.py         # Admin CRUD & auth
│   │       ├── bulk.py          # Bulk operations
│   │       └── health.py        # Health & debug endpoints
│   │
│   ├── 📁 middleware/           # Request/response middleware
│   │   ├── logging.py           # Request logging
│   │   └── performance.py       # Performance monitoring
│   │
│   ├── 📁 utils/                # Shared utilities
│   │   └── helpers.py           # Helper functions
│   │
│   └── 📁 services/             # Business logic services
│
├── 📁 frontend/                 # React 19 frontend (deployed separately)
│   ├── src/                     # React source code
│   ├── public/                  # Static assets
│   └── dist/                    # Production build (Vite)
│
├── 📁 docs/                     # All documentation
│   ├── admin/                   # Admin guides
│   ├── deployment/              # Deployment guides
│   ├── refactoring/             # Code review & refactoring docs
│   └── misc/                    # Other documentation
│
├── 📁 backend/tests/            # Backend test suite (pytest)
│
└── 📁 scripts/                  # Repo-level utility scripts
    ├── fetch_all_sleeves.py     # Used by the fetch_sleeves GitHub workflow
    └── game_cats.csv            # Category data for bulk categorize
```

## 🚀 Quick Start

### Backend Development

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Run development server
cd backend && python main.py
```

Access API docs at: `http://localhost:8000/docs`

### Frontend Development

```bash
cd frontend
npm install
npm start
```

Access frontend at: `http://localhost:3000`

## 📚 Documentation

### Core Documentation
- **[CLAUDE.md](CLAUDE.md)** - Complete project configuration and architecture
- **[Testing Guide](TESTING.md)** - Comprehensive testing documentation
- **[Improvement Roadmap](PRIORITIZED_IMPROVEMENT_ROADMAP.md)** - Development roadmap and priorities

### Guides & References
- **[Deployment Guide](docs/deployment/DEPLOYMENT_GUIDE.md)** - Production deployment on Render
- **[Admin Guide](docs/admin/ADMIN_GUIDE.md)** - Admin interface operations
- **[API Reference](docs/API_REFERENCE.md)** - Complete API endpoint documentation
- **[Architecture](docs/ARCHITECTURE.md)** - System architecture overview

### Setup Guides
- **[Redis Setup](REDIS_SETUP.md)** - Session management and caching
- **[Cloudinary Setup](CLOUDINARY_SETUP.md)** - Image hosting configuration
- **[Sleeve Fetch Setup](SLEEVE_FETCH_SETUP.md)** - Card sleeve data integration

## 🏗️ Architecture

### Backend (Python FastAPI)
- **Database**: PostgreSQL (Render managed)
- **Authentication**: Session-based with httpOnly cookies
- **Rate Limiting**: Per-endpoint limits (60-200 req/min)
- **Caching**: Image proxy with cache headers
- **Monitoring**: Performance metrics and structured logging

### Frontend (React)
- **Framework**: React 19 with React Router v7
- **Styling**: Tailwind CSS
- **Build Tool**: Vite 7
- **Deployment**: Static site on Render with automatic Git deployment

### Key Integrations
- **BoardGameGeek API**: Game metadata, ratings, complexity
- **Render PostgreSQL**: Production database
- **Image Proxying**: BGG image caching and optimization

## 🔒 Security Features

- ✅ JWT authentication with secure token validation
- ✅ Session management with Redis (optional) or in-memory fallback
- ✅ Rate limiting on all endpoints (IP-based with slowapi)
- ✅ XSS protection with DOMPurify (frontend)
- ✅ CSRF protection (SameSite cookies)
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ Input validation (Pydantic v2 schemas)
- ✅ CORS whitelist configuration
- ✅ Security headers middleware
- ✅ Circuit breaker for external API calls
- ✅ Sentry integration for error tracking

## 🧪 Testing

### Backend Tests
```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html --cov-report=term

# Run specific test
pytest tests/test_api/test_public.py
```

### Frontend Tests
```bash
cd frontend

# Run all tests
npm test

# Run with coverage
npm run test:ci
```

**Test Coverage**: 190+ backend tests, 45 frontend tests, 60%+ overall coverage

See [Testing Guide](TESTING.md) for detailed testing documentation.

## 🚢 Deployment

Both backend and frontend auto-deploy from Git via Render:

```bash
# Commit changes
git add .
git commit -m "Your changes"
git push origin main

# Render automatically:
# 1. Detects push
# 2. Builds application
# 3. Runs migrations
# 4. Deploys to production
```

See [Deployment Guide](docs/deployment/DEPLOYMENT_GUIDE.md) for details.

## 📊 Project Stats

- **Games in Database**: 400+
- **API Endpoints**: 20+ (public + admin)
- **Test Coverage**: 60%+ overall
- **Backend Tests**: 190+
- **Frontend Tests**: 45
- **Documentation Files**: 20+ organized guides
- **Technology Stack**: FastAPI, React 19, PostgreSQL, Redis (optional)
- **Deployment**: Fully automated via Git push

See [Improvement Roadmap](PRIORITIZED_IMPROVEMENT_ROADMAP.md) for development priorities.

## 🤝 Contributing

1. Create feature branch from `main`
2. Make changes and test thoroughly
3. Commit with clear, descriptive messages
4. Push and create pull request
5. Wait for automatic deployment to preview environment

## 📝 License

Proprietary - Mana & Meeples Café

## 🔗 Links

- **Live Site**: https://library.manaandmeeples.co.nz
- **API Docs**: https://mana-meeples-boardgame-list.onrender.com/docs
- **Café Website**: https://manaandmeeples.co.nz
