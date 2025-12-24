# Deployment Guide - Mana & Meeples Board Game Library

Complete deployment guide for the full-stack application on Render.com.

## Overview

The application consists of two main services hosted on Render:

1. **Backend API** (Python FastAPI) - `mana-meeples-boardgame-list`
2. **Frontend Web** (React Static Site) - `mana-meeples-library-web`
3. **Database** (PostgreSQL) - `tcg_singles` database

All services are deployed automatically via Git integration with infrastructure-as-code using `render.yaml`.

---

## Quick Deployment Checklist

For routine deployments, follow this quick checklist:

- [ ] Make and test changes locally
- [ ] Run tests: `cd backend && pytest` and `cd frontend && npm test`
- [ ] Commit and push to Git
- [ ] Render auto-deploys from Git push (2-5 minutes)
- [ ] Verify deployment via health endpoints
- [ ] Test key functionality on production

---

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│  library.manaandmeeples.co.nz (CNAME)           │
│  → mana-meeples-library-web.onrender.com        │
│                                                  │
│  ┌────────────────────────────────────────┐    │
│  │  Frontend (React + Vite)               │    │
│  │  - Static site hosting                 │    │
│  │  - Automatic deployments from Git      │    │
│  │  - CDN caching                         │    │
│  └────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
                     │
                     │ HTTPS API calls
                     ▼
┌─────────────────────────────────────────────────┐
│  mana-meeples-boardgame-list.onrender.com      │
│                                                  │
│  ┌────────────────────────────────────────┐    │
│  │  Backend API (FastAPI)                 │    │
│  │  - REST API endpoints                  │    │
│  │  - JWT authentication                  │    │
│  │  - Rate limiting                       │    │
│  │  - Image proxy                         │    │
│  └────────────────────────────────────────┘    │
│                 │                                │
│                 │ PostgreSQL                     │
│                 ▼                                │
│  ┌────────────────────────────────────────┐    │
│  │  Database (PostgreSQL)                 │    │
│  │  - Table: boardgames                   │    │
│  │  - Connection pooling                  │    │
│  │  - Read replica support                │    │
│  └────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

---

## Initial Setup (One-Time)

### Prerequisites

- GitHub account with repository access
- Render account (https://dashboard.render.com)
- Domain configured with DNS access (for custom domain)

### 1. Database Setup

The PostgreSQL database is already set up on Render.

**Connection Details:**
- Host: `dpg-d3i3387diees738trbg0-a.singapore-postgres.render.com`
- Database: `tcg_singles`
- Table: `boardgames`
- Region: Singapore

### 2. Backend API Setup

**Using render.yaml (Recommended):**

The backend is configured via `render.yaml`:

```yaml
services:
  - type: web
    name: mana-meeples-boardgame-list
    runtime: python
    region: singapore
    plan: starter
    buildCommand: pip install -r backend/requirements.txt
    startCommand: cd backend && python main.py
    healthCheckPath: /api/health
```

**Environment Variables (Set in Render Dashboard):**

```bash
# Required
DATABASE_URL=postgresql://tcg_admin:<password>@dpg-d3i3387diees738trbg0-a.singapore-postgres.render.com/tcg_singles
ADMIN_TOKEN=<your-secure-admin-token>
SESSION_SECRET=<your-secure-session-secret>

# CORS Configuration
CORS_ORIGINS=https://manaandmeeples.co.nz,https://www.manaandmeeples.co.nz,https://library.manaandmeeples.co.nz,https://mana-meeples-library-web.onrender.com

# Optional
PUBLIC_BASE_URL=https://mana-meeples-boardgame-list.onrender.com
JWT_EXPIRATION_DAYS=7
PYTHON_VERSION=3.11.9

# Redis (Optional - for session management and rate limiting)
REDIS_URL=redis://localhost:6379/0
REDIS_ENABLED=true

# Monitoring (Optional)
SENTRY_DSN=<your-sentry-dsn>
ENVIRONMENT=production
```

### 3. Frontend Setup

**Using render.yaml:**

```yaml
services:
  - type: web
    name: mana-meeples-library-web
    runtime: static
    region: singapore
    buildCommand: cd frontend && npm install && npm run build
    staticPublishPath: ./frontend/dist
```

**Environment Variables (Set in Render Dashboard):**

```bash
# API Configuration (build-time)
VITE_API_BASE=https://mana-meeples-boardgame-list.onrender.com

# Optional
NODE_VERSION=20.x
```

### 4. Custom Domain Setup

**For library.manaandmeeples.co.nz:**

1. **In Render Dashboard:**
   - Go to `mana-meeples-library-web` service
   - Settings → Custom Domains
   - Add custom domain: `library.manaandmeeples.co.nz`
   - Copy the CNAME target (usually `mana-meeples-library-web.onrender.com`)

2. **In DNS Provider (cPanel/Cloudflare):**
   - Add CNAME record:
     - Name: `library`
     - Target: `mana-meeples-library-web.onrender.com`
     - TTL: 14400

3. **Wait for DNS Propagation** (5-30 minutes)
   - Check with: `dig library.manaandmeeples.co.nz`

4. **SSL Certificate** (Automatic)
   - Render automatically provisions SSL certificates
   - Verify in Render Dashboard → Custom Domains

---

## Deployment Workflow

### Automatic Deployment (Recommended)

Render automatically deploys when you push to Git:

```bash
# 1. Make changes locally
git add .
git commit -m "Your commit message"

# 2. Push to repository
git push origin <branch-name>

# 3. Render auto-detects changes and deploys
# - Backend: ~2-3 minutes
# - Frontend: ~3-5 minutes

# 4. Monitor deployment in Render Dashboard
# - Go to service → "Events" or "Logs"
```

**Auto-Deploy Triggers:**
- Push to `main` branch → Production deployment
- Push to feature branches → Can be configured for preview deployments
- Pull request creation → Can trigger preview environments

### Manual Deployment

If needed, you can trigger manual deployments:

1. **In Render Dashboard:**
   - Navigate to service
   - Click "Manual Deploy" → "Deploy latest commit"
   - Or "Clear build cache & deploy" for fresh build

---

## Deployment Verification

### 1. Health Check Endpoints

**Backend API Health:**
```bash
# Basic health check
curl https://mana-meeples-boardgame-list.onrender.com/api/health

# Expected response:
{"status":"healthy"}

# Database health check
curl https://mana-meeples-boardgame-list.onrender.com/api/health/db

# Expected response:
{"status":"healthy","database":"connected","games_count":400}
```

**Redis Health (if enabled):**
```bash
curl https://mana-meeples-boardgame-list.onrender.com/api/health/redis

# Expected response:
{"status":"healthy","redis":"connected"}
```

### 2. Test API Endpoints

```bash
# List games
curl https://mana-meeples-boardgame-list.onrender.com/api/public/games

# Get specific game
curl https://mana-meeples-boardgame-list.onrender.com/api/public/games/1

# Category counts
curl https://mana-meeples-boardgame-list.onrender.com/api/public/category-counts
```

### 3. Test Frontend

Visit https://library.manaandmeeples.co.nz and verify:

- [ ] Games load correctly
- [ ] Category filters work
- [ ] Search functionality works
- [ ] Game details page loads
- [ ] Images display correctly
- [ ] No console errors (F12)
- [ ] Mobile responsive design works

### 4. Check Logs

**In Render Dashboard:**
- Navigate to service → "Logs"
- Look for startup messages:
  ```
  Using PostgreSQL database: dpg-d3i3387diees738trbg0-a.singapore-postgres.render.com/tcg_singles
  Database connection verified
  API startup complete
  Uvicorn running on http://0.0.0.0:10000
  ```

---

## Environment Management

### Environment Variables Best Practices

1. **Never commit secrets to Git**
   - Use `.env.example` as template
   - Set actual values in Render Dashboard

2. **Generate secure secrets:**
   ```bash
   # Generate secure admin token
   python -c "import secrets; print(secrets.token_hex(32))"

   # Generate secure session secret
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

3. **Update secrets in Render:**
   - Go to service → Environment
   - Edit variable value
   - Click "Save Changes" (triggers redeploy)

### Configuration Priority

The application loads configuration in this order (highest to lowest):

1. Environment variables (Render Dashboard)
2. `.env` file (local development only)
3. Default values in code

---

## Database Management

### Connection Pool Configuration

Current settings in `backend/database.py`:

```python
pool_size=15          # Permanent connections
max_overflow=20       # Additional connections when busy
pool_timeout=30       # Wait time for available connection
pool_recycle=3600     # Recycle connections hourly
pool_pre_ping=True    # Test connections before use
```

### Running Migrations

Migrations run automatically on startup. Database schema is managed in `backend/database.py`:

```python
def run_migrations(engine):
    """Run database migrations on startup"""
    # Migrations are applied automatically
    # No manual migration needed for deployments
```

### Accessing Database Directly

**Using psql:**
```bash
# From Render Dashboard → Database → Connection String
psql postgresql://tcg_admin:<password>@dpg-d3i3387diees738trbg0-a.singapore-postgres.render.com/tcg_singles

# List tables
\dt

# View boardgames table
SELECT id, title, year, mana_meeple_category FROM boardgames LIMIT 10;
```

**Using DataGrip, DBeaver, or pgAdmin:**
- Host: `dpg-d3i3387diees738trbg0-a.singapore-postgres.render.com`
- Port: `5432`
- Database: `tcg_singles`
- Username: `tcg_admin`
- Password: (from Render Dashboard)

---

## Monitoring & Debugging

### Sentry Integration

The application integrates with Sentry for error tracking:

```python
# backend/main.py
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    environment=os.getenv("ENVIRONMENT", "production"),
    traces_sample_rate=0.1,
)
```

**Configure Sentry:**
1. Create project at https://sentry.io
2. Copy DSN
3. Set `SENTRY_DSN` environment variable in Render
4. Errors automatically tracked and reported

### Performance Monitoring

**Performance Tracking Middleware:**
```python
# Tracks slow endpoints (>1s)
# Logs to console and Sentry
```

**Monitor in Render:**
- Dashboard → Service → Metrics
- CPU usage, memory, response times

**Monitor in Sentry:**
- Performance → Transactions
- Slow API endpoints highlighted

### Log Management

**Accessing Logs:**
1. Render Dashboard → Service → Logs
2. Filter by severity (Info, Warning, Error)
3. Search for specific messages
4. Download logs if needed

**Log Levels:**
- `INFO`: Normal operations
- `WARNING`: Potential issues (slow queries, rate limiting)
- `ERROR`: Errors that need attention

---

## Rollback Procedures

### Rolling Back Code

**Option 1: Revert Git Commit**
```bash
# Find the commit to revert
git log --oneline

# Revert specific commit
git revert <commit-hash>
git push origin main

# Render auto-deploys reverted code
```

**Option 2: Deploy Specific Commit**
1. Render Dashboard → Service
2. Click "Manual Deploy"
3. Select specific commit from dropdown
4. Click "Deploy"

### Rolling Back Database

**Important**: Database changes require careful planning.

**For Schema Changes:**
```python
# Always write reversible migrations
# Include both upgrade and downgrade logic
```

**For Data Issues:**
```bash
# Use PostgreSQL backups
# Render provides automated daily backups
# Restore from backup in Render Dashboard → Database → Backups
```

---

## Scaling & Performance

### Horizontal Scaling

**Backend Scaling:**
1. Render Dashboard → Service → Settings
2. Update instance count
3. Save changes

**Note**: With multiple instances, ensure:
- Redis is enabled for session sharing
- Database connection pool sized appropriately
- Rate limiting works across instances

### Vertical Scaling

**Upgrade Instance Type:**
1. Render Dashboard → Service → Settings
2. Change plan (Starter → Standard → Pro)
3. More CPU and memory allocated

### Performance Optimization

**Backend:**
- Connection pooling configured (15 base + 20 overflow)
- Query caching with 5-second TTL
- Image proxy with cache headers
- Circuit breaker for BGG API

**Frontend:**
- Code splitting with React.lazy
- Vite build optimization
- Static asset caching
- CDN delivery via Render

**Database:**
- Indexes on frequently queried columns
- Composite indexes for complex queries
- Read replica support (configure in Render)

---

## Troubleshooting

### Backend Not Starting

**Symptoms:** Service shows "Deploy failed" in Render

**Solutions:**
1. Check build logs in Render Dashboard
2. Verify all dependencies in `requirements.txt`
3. Check Python version matches `PYTHON_VERSION` env var
4. Ensure `buildCommand` path is correct: `cd backend && ...`

### Frontend Build Failures

**Symptoms:** Static site build fails

**Solutions:**
1. Check build logs for errors
2. Verify Node.js version (20.x)
3. Ensure `cd frontend` in build command
4. Check `VITE_API_BASE` environment variable is set
5. Try "Clear build cache & deploy"

### Database Connection Errors

**Symptoms:** API returns 500 errors, logs show database connection issues

**Solutions:**
1. Verify `DATABASE_URL` is correct in environment variables
2. Check database is running in Render Dashboard
3. Verify connection pool settings
4. Check for connection leaks in code
5. Review database connection limits

### CORS Errors

**Symptoms:** Browser console shows CORS errors

**Solutions:**
1. Verify `CORS_ORIGINS` includes frontend domain
2. Ensure no trailing slashes in CORS_ORIGINS
3. Redeploy backend after updating CORS_ORIGINS
4. Clear browser cache

### SSL Certificate Issues

**Symptoms:** "Not secure" warning in browser

**Solutions:**
1. Verify custom domain is added in Render
2. Check DNS CNAME is correct
3. Wait for DNS propagation (up to 30 minutes)
4. Click "Retry" in Render → Custom Domains if certificate provisioning failed

### Slow Response Times

**Symptoms:** API responses taking >2 seconds

**Solutions:**
1. Check Render metrics for CPU/memory usage
2. Review slow query logs in database
3. Verify connection pool not exhausted
4. Check for N+1 query problems
5. Enable Redis caching
6. Consider upgrading instance type

---

## Security Best Practices

### 1. Secrets Management

- ✅ All secrets in Render Dashboard (never in code)
- ✅ Use `sync: false` in render.yaml for sensitive vars
- ✅ Rotate secrets periodically (quarterly recommended)
- ✅ Use strong, randomly generated tokens

### 2. Database Security

- ✅ Use strong passwords (32+ characters)
- ✅ Restrict database access to Render services only
- ✅ Regular backups enabled (daily)
- ✅ Monitor for unusual query patterns

### 3. API Security

- ✅ Rate limiting enabled on all endpoints
- ✅ JWT authentication for admin endpoints
- ✅ Input validation via Pydantic schemas
- ✅ SQL injection prevention via ORM
- ✅ XSS protection in frontend

### 4. HTTPS/TLS

- ✅ Automatic SSL certificates via Render
- ✅ Force HTTPS (redirect HTTP → HTTPS)
- ✅ HSTS headers enabled
- ✅ Secure cookie flags (HttpOnly, Secure, SameSite)

---

## Backup & Disaster Recovery

### Automated Backups

**PostgreSQL Backups:**
- Render provides automated daily backups
- Retention: 7 days (Starter plan), 30 days (Standard/Pro)
- Access in: Render Dashboard → Database → Backups

**Code Backups:**
- Git repository is source of truth
- All deployments tracked via Git commits
- Can redeploy any previous commit

### Disaster Recovery Plan

**In case of complete service failure:**

1. **Restore Database:**
   - Render Dashboard → Database → Backups
   - Select most recent backup
   - Restore to new database instance

2. **Redeploy Services:**
   - Render auto-deploys from Git
   - Or manually trigger deployment
   - Update DATABASE_URL if needed

3. **Verify Functionality:**
   - Run health checks
   - Test critical user flows
   - Verify data integrity

**Recovery Time Objective (RTO):** ~30 minutes
**Recovery Point Objective (RPO):** 24 hours (last backup)

---

## Additional Resources

### Documentation

- [Render Documentation](https://render.com/docs)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Vite Deployment](https://vitejs.dev/guide/static-deploy.html)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

### Project Documentation

- [Architecture Overview](../ARCHITECTURE.md)
- [API Reference](../API_REFERENCE.md)
- [Testing Guide](../../TESTING.md)
- [Redis Setup](../../REDIS_SETUP.md)
- [Cloudinary Setup](../../CLOUDINARY_SETUP.md)

### Support

- **Render Support**: https://render.com/support
- **Project Issues**: GitHub repository issues
- **Emergency Contacts**: [Add your team contacts]

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| Dec 2025 | Initial comprehensive deployment guide | Claude Code |
| Nov 2025 | PostgreSQL migration completed | Development Team |
| Nov 2025 | Frontend migrated to Vite 7 | Development Team |
| Oct 2025 | Redis integration added | Development Team |

---

**Last Updated**: December 2025
**Next Review**: March 2026
