# Documentation - Mana & Meeples Board Game Library

Welcome to the project documentation! This directory contains comprehensive guides for developers, administrators, and operations teams.

---

## 🗺️ Start Here

**New to the project?** Check out the **[Complete Documentation Index](INDEX.md)** for organized navigation to all documentation.

---

## 📁 Documentation Structure

### Essential Reading

- **[Documentation Index](INDEX.md)** - Complete navigation to all documentation
- **[Project README](../README.md)** - Project overview and quick start
- **[CLAUDE.md](../CLAUDE.md)** - Complete project configuration and architecture
- **[Architecture Overview](ARCHITECTURE.md)** - System architecture and design

### Guides by Category

#### 🛠️ Development
- **[Testing Guide](../TESTING.md)** - Comprehensive testing documentation
- **[API Reference](API_REFERENCE.md)** - Complete API endpoint documentation
- **[Improvement Roadmap](../PRIORITIZED_IMPROVEMENT_ROADMAP.md)** - Development priorities

#### 🚀 Deployment & Operations
- **[Deployment Guide](deployment/DEPLOYMENT_GUIDE.md)** - Production deployment on Render
- **[Troubleshooting Guide](TROUBLESHOOTING.md)** - Common issues and solutions
- **[Security Guide](SECURITY.md)** - Security best practices

#### 👨‍💼 Admin & Management
- **[Admin Guide](admin/ADMIN_GUIDE.md)** - Admin interface operations
- **[Game Management](admin/ADMIN_GUIDE.md#game-management)** - Adding and organizing games
- **[Bulk Operations](admin/ADMIN_GUIDE.md#bulk-operations)** - CSV import and categorization

#### ⚙️ Setup & Configuration
- **[Redis Setup](../REDIS_SETUP.md)** - Session management and caching
- **[Cloudinary Setup](../CLOUDINARY_SETUP.md)** - Image hosting configuration
- **[Sleeve Fetch Setup](../SLEEVE_FETCH_SETUP.md)** - Card sleeve data integration

---

## 🗂️ Directory Organization

```
docs/
├── INDEX.md                    # Complete documentation index
├── README.md                   # This file
├── ARCHITECTURE.md             # System architecture overview
├── API_REFERENCE.md            # API endpoint documentation
├── TROUBLESHOOTING.md          # Common issues and solutions
├── SECURITY.md                 # Security best practices
│
├── admin/                      # Admin guides
│   └── ADMIN_GUIDE.md          # Complete admin operations guide
│
├── deployment/                 # Deployment documentation
│   └── DEPLOYMENT_GUIDE.md     # Production deployment guide
│
├── misc/                       # Miscellaneous documentation
│   └── ai_dev_principles.md    # AI development philosophy
│
└── archive/                    # Historical documentation
    ├── README.md               # Archive overview
    ├── sprints/                # Sprint summaries (historical)
    └── reviews/                # Previous code reviews
```

---

## 🔍 Find What You Need

### By Role

| Role | Start Here |
|------|-----------|
| **New Developer** | [Project README](../README.md) → [Architecture](ARCHITECTURE.md) → [Testing](../TESTING.md) |
| **Café Staff** | [Admin Guide](admin/ADMIN_GUIDE.md) |
| **DevOps** | [Deployment Guide](deployment/DEPLOYMENT_GUIDE.md) → [Troubleshooting](TROUBLESHOOTING.md) |
| **Security Reviewer** | [Security Guide](SECURITY.md) → [Architecture](ARCHITECTURE.md) |

### By Task

| Task | Documentation |
|------|---------------|
| Set up development environment | [README Quick Start](../README.md#quick-start) |
| Deploy to production | [Deployment Guide](deployment/DEPLOYMENT_GUIDE.md) |
| Add a new game | [Admin Guide - Game Management](admin/ADMIN_GUIDE.md#game-management) |
| Fix deployment issue | [Troubleshooting](TROUBLESHOOTING.md#deployment-issues) |
| Understand API endpoints | [API Reference](API_REFERENCE.md) |
| Configure Redis | [Redis Setup](../REDIS_SETUP.md) |
| Write tests | [Testing Guide](../TESTING.md) |
| Review security | [Security Guide](SECURITY.md) |

---

## 📚 Component Documentation

Individual component README files:

- **[Frontend README](../frontend/README.md)** - Frontend-specific documentation
- **[Backend Tests README](../backend/tests/README.md)** - Backend testing details
- **[Scripts README](../scripts/README.md)** - Utility scripts

---

## 🗄️ Historical Documentation

Archived documentation provides valuable historical context:

- **[Archive Index](archive/README.md)** - Overview of archived documentation
- **[Sprint Summaries](archive/sprints/)** - Development sprint summaries
- **[Code Reviews](archive/reviews/)** - Previous comprehensive reviews

**Note:** Historical documents may be outdated. Always refer to current documentation above.

---

## 📝 Documentation Standards

When contributing to documentation:

1. **Update relevant docs** when changing code
2. **Use clear examples** with code snippets
3. **Link related documents** for easy navigation
4. **Keep INDEX.md current** when adding new docs
5. **Add "Last Updated" dates** at bottom of documents
6. **Test all commands** before documenting them

See [Documentation Index](INDEX.md) for full standards.

---

## 🆘 Need Help?

**Can't find what you're looking for?**

1. Check **[Documentation Index](INDEX.md)** - Complete navigation
2. Search this directory with Ctrl+F/Cmd+F
3. Review **[CLAUDE.md](../CLAUDE.md)** - Most comprehensive single file
4. Check component-specific READMEs
5. Create GitHub issue with "documentation" label

---

**Last Updated**: December 2025
**Maintainer**: Development Team
