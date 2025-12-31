# Documentation Index - Mana & Meeples Board Game Library

Complete navigation guide for all project documentation.

---

## 🚀 Getting Started

New to the project? Start here:

1. **[Project README](../README.md)** - Project overview, quick start, and key features
2. **[CLAUDE.md](../CLAUDE.md)** - Complete project configuration and architecture details
3. **[Architecture Overview](./ARCHITECTURE.md)** - System architecture and design decisions
4. **[Deployment Guide](./deployment/DEPLOYMENT_GUIDE.md)** - How to deploy to production

---

## 📖 Documentation by Role

### For Developers

**Essential Reading:**
- [Project README](../README.md) - Project overview and quick start
- [Architecture Overview](./ARCHITECTURE.md) - System design and architecture
- [API Reference](./API_REFERENCE.md) - Complete API endpoint documentation
- [Testing Guide](../TESTING.md) - How to run and write tests
- [CLAUDE.md](../CLAUDE.md) - Complete project configuration

**Development Guides:**
- [Improvement Roadmap](../PRIORITIZED_IMPROVEMENT_ROADMAP.md) - Development priorities and roadmap
- [AI Development Principles](./misc/ai_dev_principles.md) - Development philosophy and best practices

**Setup Guides:**
- [Redis Setup](../REDIS_SETUP.md) - Session management and caching configuration
- [Cloudinary Setup](../CLOUDINARY_SETUP.md) - Image hosting setup
- [Sleeve Fetch Setup](../SLEEVE_FETCH_SETUP.md) - Card sleeve data integration
- [Alembic Migration Guide](../ALEMBIC_MIGRATION_GUIDE.md) - Database migration setup and workflow
- [Frontend Test Guide](../FRONTEND_TEST_GUIDE.md) - Comprehensive frontend testing templates

### For Café Staff & Admins

**Admin Operations:**
- [Admin Guide](./admin/ADMIN_GUIDE.md) - Complete admin interface guide
- [Game Management](./admin/ADMIN_GUIDE.md#game-management) - Adding, editing, and organizing games
- [Bulk Operations](./admin/ADMIN_GUIDE.md#bulk-operations) - CSV import and bulk categorization

### For DevOps & Operations

**Deployment & Infrastructure:**
- [Deployment Guide](./deployment/DEPLOYMENT_GUIDE.md) - Production deployment on Render
- [Alembic Deployment Guide](./deployment/ALEMBIC.md) - Database migration deployment
- [Health & Monitoring](./deployment/DEPLOYMENT_GUIDE.md#monitoring--debugging) - Health checks and monitoring
- [Rollback Procedures](./deployment/DEPLOYMENT_GUIDE.md#rollback-procedures) - How to rollback deployments
- [Scaling Guide](./deployment/DEPLOYMENT_GUIDE.md#scaling--performance) - Horizontal and vertical scaling

**Troubleshooting:**
- [Deployment Guide - Troubleshooting](./deployment/DEPLOYMENT_GUIDE.md#troubleshooting) - Common deployment issues
- [Testing Guide - Troubleshooting](../TESTING.md#troubleshooting) - Test-related issues

---

## 📚 Documentation by Topic

### Architecture & Design

- **[Architecture Overview](./ARCHITECTURE.md)** - System architecture, components, data flow
- **[CLAUDE.md](../CLAUDE.md)** - Complete project configuration and technical specifications
- **[API Reference](./API_REFERENCE.md)** - REST API endpoint documentation
- **[Database Schema](../CLAUDE.md#database-schema)** - PostgreSQL table structure and indexes

### Development

- **[Testing Guide](../TESTING.md)** - Comprehensive testing documentation
  - Backend testing with pytest
  - Frontend testing with Vitest
  - CI/CD integration
  - Writing tests best practices

- **[Improvement Roadmap](../PRIORITIZED_IMPROVEMENT_ROADMAP.md)** - Development priorities
  - Current sprint status
  - Future enhancements
  - Technical debt tracking

### Deployment & Operations

- **[Deployment Guide](./deployment/DEPLOYMENT_GUIDE.md)** - Production deployment
  - Initial setup (one-time)
  - Deployment workflow
  - Environment management
  - Monitoring and debugging
  - Rollback procedures
  - Scaling and performance

### Configuration & Setup

- **[Redis Setup](../REDIS_SETUP.md)** - Session management and rate limiting
  - Local development with Docker
  - Production configuration
  - Health monitoring

- **[Cloudinary Setup](../CLOUDINARY_SETUP.md)** - Image hosting configuration
  - Account setup
  - API integration
  - Image optimization

- **[Sleeve Fetch Setup](../SLEEVE_FETCH_SETUP.md)** - Card sleeve data
  - Data source integration
  - API configuration

### Admin & Operations

- **[Admin Guide](./admin/ADMIN_GUIDE.md)** - Admin interface operations
  - Authentication and access
  - Game management (CRUD operations)
  - BoardGameGeek integration
  - Bulk operations (CSV import/export)
  - Category management
  - NZ designer tagging

---

## 🔍 Quick Reference

### Common Tasks

| Task | Documentation |
|------|---------------|
| Add a new game | [Admin Guide - Game Management](./admin/ADMIN_GUIDE.md#game-management) |
| Import games from BGG | [Admin Guide - BGG Integration](./admin/ADMIN_GUIDE.md#boardgamegeek-integration) |
| Bulk categorize games | [Admin Guide - Bulk Operations](./admin/ADMIN_GUIDE.md#bulk-operations) |
| Deploy to production | [Deployment Guide](./deployment/DEPLOYMENT_GUIDE.md) |
| Run tests | [Testing Guide](../TESTING.md) |
| Fix deployment issues | [Deployment Guide - Troubleshooting](./deployment/DEPLOYMENT_GUIDE.md#troubleshooting) |
| Check API health | [Deployment Guide - Health Checks](./deployment/DEPLOYMENT_GUIDE.md#deployment-verification) |
| Configure Redis | [Redis Setup](../REDIS_SETUP.md) |
| Setup image hosting | [Cloudinary Setup](../CLOUDINARY_SETUP.md) |

### API Endpoints Quick Reference

| Endpoint | Purpose | Documentation |
|----------|---------|---------------|
| `GET /api/public/games` | List games with filters | [API Reference](./API_REFERENCE.md) |
| `GET /api/public/games/{id}` | Get game details | [API Reference](./API_REFERENCE.md) |
| `POST /api/admin/login` | Admin authentication | [API Reference](./API_REFERENCE.md) |
| `POST /api/admin/games` | Create new game | [API Reference](./API_REFERENCE.md) |
| `POST /api/admin/import/bgg` | Import from BGG | [API Reference](./API_REFERENCE.md) |
| `GET /api/health` | Health check | [Deployment Guide](./deployment/DEPLOYMENT_GUIDE.md) |

---

## 📁 Component Documentation

Individual component README files:

- **[Frontend README](../frontend/README.md)** - Frontend-specific documentation
- **[Frontend Config README](../frontend/src/config/README.md)** - API configuration
- **[Frontend Hooks README](../frontend/src/hooks/README.md)** - Custom React hooks
- **[Backend Tests README](../backend/tests/README.md)** - Backend testing details
- **[Scripts README](../scripts/README.md)** - Utility scripts documentation
- **[Root Tests README](../tests/README.md)** - Integration test documentation

---

## 🗄️ Historical Documentation

Archive of historical documentation (for context and reference):

- **[Archive Index](./archive/README.md)** - Overview of archived documentation
- **[Implementation Summaries](./archive/implementations/)** - Completed feature implementations
  - Alembic Migration Complete
  - Code Quality Improvements
  - Accessibility Improvements
  - Tracking Prevention Fix
  - Priority 1 Enhancements
  - Auto-Refresh System
- **[Sprint Summaries](./archive/sprints/)** - Historical sprint development summaries
  - Sprint 1: Initial development
  - Sprint 4: Performance optimization
  - Sprint 5: Error handling improvements
  - Sprint 6: SQLAlchemy 2.0 migration
  - Sprint 7: Pydantic v2 migration
  - Sprint 8: Redis integration
  - Sprint 11: Testing infrastructure
  - Sprint 12: Performance monitoring
- **[Code Reviews](./archive/reviews/)** - Previous comprehensive code reviews

**Note**: Historical documentation provides valuable context about architectural decisions and implementation details but may be outdated. Always refer to current documentation above for active development.

---

## 🔗 External Resources

### Technology Documentation

- **FastAPI**: https://fastapi.tiangolo.com/
- **React**: https://react.dev/
- **Vite**: https://vitejs.dev/
- **Vitest**: https://vitest.dev/
- **React Router**: https://reactrouter.com/
- **Tailwind CSS**: https://tailwindcss.com/
- **SQLAlchemy**: https://docs.sqlalchemy.org/
- **Pydantic**: https://docs.pydantic.dev/
- **PostgreSQL**: https://www.postgresql.org/docs/
- **Redis**: https://redis.io/docs/
- **Render**: https://render.com/docs

### Testing Tools

- **pytest**: https://docs.pytest.org/
- **React Testing Library**: https://testing-library.com/react
- **Playwright**: https://playwright.dev/

### Monitoring & Debugging

- **Sentry**: https://docs.sentry.io/
- **Codecov**: https://docs.codecov.com/

---

## 📝 Documentation Maintenance

### Contributing to Documentation

When updating documentation:

1. **Keep it current**: Update docs when code changes
2. **Be specific**: Include code examples and command-line instructions
3. **Cross-reference**: Link to related documentation
4. **Test instructions**: Verify commands work before documenting
5. **Update this index**: Add new documentation to this index

### Documentation Standards

- Use markdown format (`.md`)
- Include table of contents for long documents
- Use code blocks with language syntax highlighting
- Include "Last Updated" date at bottom
- Add examples for complex topics
- Keep line length reasonable (~100 characters)

### Requesting Documentation

Missing documentation? Need clarification?

1. Check this index first
2. Search existing documentation
3. Check archived documentation for historical context
4. Create GitHub issue with "documentation" label
5. Describe what documentation would be helpful

---

## 🆘 Need Help?

**Can't find what you're looking for?**

1. **Search this index** - Use Ctrl+F/Cmd+F to search keywords
2. **Check the main README** - [README.md](../README.md)
3. **Review CLAUDE.md** - [CLAUDE.md](../CLAUDE.md) - Most comprehensive single file
4. **Browse by role** - See "Documentation by Role" section above
5. **Check component READMEs** - Individual components may have their own docs
6. **Ask the team** - Create a GitHub issue or reach out to maintainers

---

**Last Updated**: December 2025
**Maintainer**: Development Team
**Version**: 1.0
