# Troubleshooting Guide - Mana & Meeples Board Game Library

Common issues and their solutions for the board game library system.

---

## Table of Contents

1. [Deployment Issues](#deployment-issues)
2. [Backend API Problems](#backend-api-problems)
3. [Frontend Issues](#frontend-issues)
4. [Database Problems](#database-problems)
5. [Authentication & Authorization](#authentication--authorization)
6. [Performance Issues](#performance-issues)
7. [Testing Problems](#testing-problems)
8. [Development Environment](#development-environment)

---

## Deployment Issues

### Backend Deploy Failed on Render

**Symptoms:**
- Render shows "Deploy failed" status
- Build logs show errors
- Service won't start

**Solutions:**

1. **Check build logs first:**
   - Render Dashboard → Service → Events → Click on failed deploy
   - Read complete build log for error messages

2. **Common Python dependency errors:**
   ```bash
   # Error: "Could not find a version that satisfies the requirement..."
   # Solution: Check requirements.txt for typos or incompatible versions

   # Verify locally:
   pip install -r backend/requirements.txt
   ```

3. **Missing environment variables:**
   ```bash
   # Error: "KeyError: 'DATABASE_URL'"
   # Solution: Set required environment variables in Render Dashboard

   # Required variables:
   - DATABASE_URL
   - ADMIN_TOKEN
   - SESSION_SECRET
   - CORS_ORIGINS
   ```

4. **Build command issues:**
   ```yaml
   # Ensure build command includes correct path:
   buildCommand: pip install -r backend/requirements.txt

   # Not:
   buildCommand: pip install -r requirements.txt  # Wrong path!
   ```

5. **Python version mismatch:**
   ```bash
   # Set correct Python version in Render Dashboard
   # Environment → PYTHON_VERSION = 3.11.9
   ```

### Frontend Build Failing

**Symptoms:**
- Static site build fails on Render
- npm install errors
- Build takes too long and times out

**Solutions:**

1. **Check Node.js version:**
   ```bash
   # Render Dashboard → Environment
   # NODE_VERSION = 20.x
   ```

2. **Clear build cache:**
   - Render Dashboard → Service → "Clear build cache & deploy"

3. **Verify build command:**
   ```yaml
   buildCommand: cd frontend && npm install && npm run build
   staticPublishPath: ./frontend/dist  # Vite uses dist, not build
   ```

4. **Check for npm errors locally:**
   ```bash
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   npm run build
   ```

5. **Environment variable not set:**
   ```bash
   # Error: API calls going to wrong endpoint
   # Solution: Set VITE_API_BASE in Render
   VITE_API_BASE=https://mana-meeples-boardgame-list.onrender.com
   ```

---

## Backend API Problems

### API Returns 500 Internal Server Error

**Symptoms:**
- All or most endpoints return 500
- Logs show database connection errors
- API worked before, now broken

**Solutions:**

1. **Check database connection:**
   ```bash
   # Test health endpoint:
   curl https://mana-meeples-boardgame-list.onrender.com/api/health/db

   # Should return: {"status":"healthy","database":"connected"}
   # If not, check DATABASE_URL environment variable
   ```

2. **Review logs for stack traces:**
   ```bash
   # Render Dashboard → Logs
   # Look for Python tracebacks
   # Common errors:
   # - psycopg2.OperationalError (database connection)
   # - KeyError (missing environment variable)
   # - AttributeError (code bug)
   ```

3. **Check Sentry for detailed errors:**
   - If Sentry is configured, check dashboard for full error context

4. **Verify migrations ran successfully:**
   ```bash
   # Look in logs for:
   "Database connection verified"
   "Running migrations..."
   "All migrations applied successfully"
   ```

### API Endpoint Returns 404

**Symptoms:**
- Specific endpoint returns 404
- Other endpoints work fine
- Frontend can't reach API

**Solutions:**

1. **Verify endpoint path:**
   ```bash
   # Correct paths:
   GET /api/public/games         ✅
   GET /api/public/games/123     ✅

   # Wrong paths:
   GET /public/games             ❌ Missing /api
   GET /api/games                ❌ Missing /public
   ```

2. **Check API documentation:**
   ```bash
   # Visit OpenAPI docs:
   https://mana-meeples-boardgame-list.onrender.com/docs

   # Or ReDoc:
   https://mana-meeples-boardgame-list.onrender.com/redoc
   ```

3. **CORS issues (check browser console):**
   ```bash
   # Error: "CORS policy: No 'Access-Control-Allow-Origin' header"
   # Solution: Add frontend domain to CORS_ORIGINS

   CORS_ORIGINS=https://library.manaandmeeples.co.nz,...
   ```

### Rate Limiting Issues

**Symptoms:**
- API returns 429 "Too Many Requests"
- Legitimate users being blocked
- Admin operations failing

**Solutions:**

1. **Check rate limit headers:**
   ```bash
   curl -I https://mana-meeples-boardgame-list.onrender.com/api/public/games

   # Look for:
   X-RateLimit-Limit: 100
   X-RateLimit-Remaining: 42
   X-RateLimit-Reset: 1640000000
   ```

2. **Wait for rate limit reset:**
   - Rate limits reset every minute
   - Admin endpoints: 60 req/min
   - Public endpoints: 100 req/min

3. **For development, adjust rate limits:**
   ```python
   # backend/api/routers/public.py
   @limiter.limit("100/minute")  # Increase if needed for testing
   ```

4. **Check if IP is being rate limited incorrectly:**
   ```bash
   # If behind proxy/load balancer, ensure X-Forwarded-For is trusted
   # This is configured in slowapi settings
   ```

---

## Frontend Issues

### Games Not Loading / Blank Page

**Symptoms:**
- Page loads but no games displayed
- Loading spinner never stops
- Browser console shows errors

**Solutions:**

1. **Check browser console (F12):**
   ```javascript
   // Common errors:

   // CORS error:
   "CORS policy: No 'Access-Control-Allow-Origin' header"
   // Solution: Check CORS_ORIGINS includes frontend domain

   // Network error:
   "Failed to fetch"
   // Solution: Check API is running, verify API_BASE URL

   // 404 error:
   "GET /api/public/games 404"
   // Solution: Verify API endpoint path is correct
   ```

2. **Verify API_BASE configuration:**
   ```javascript
   // frontend/src/config/api.js
   // Should resolve to: https://mana-meeples-boardgame-list.onrender.com

   // Check in browser console:
   console.log(window.__API_BASE__)
   ```

3. **Test API directly:**
   ```bash
   # If API works directly but not from frontend, it's a CORS issue:
   curl https://mana-meeples-boardgame-list.onrender.com/api/public/games
   ```

4. **Clear browser cache:**
   ```bash
   # Hard refresh:
   # Chrome/Firefox: Ctrl+Shift+R or Cmd+Shift+R
   # Or clear site data in DevTools → Application → Clear storage
   ```

### Images Not Displaying

**Symptoms:**
- Games load but images show "No Image" placeholder
- Some images load, others don't
- Image URLs returning 404 or CORS errors

**Solutions:**

1. **Check image proxy endpoint:**
   ```bash
   # Test image proxy:
   curl "https://mana-meeples-boardgame-list.onrender.com/api/public/image-proxy?url=https://cf.geekdo-images.com/..."

   # Should return image data or redirect
   ```

2. **BoardGameGeek image issues:**
   ```bash
   # BGG sometimes changes image URLs
   # Solution: Re-import game from BGG to get updated URLs

   # Admin panel → Game details → "Reimport from BGG"
   ```

3. **Check CORS for images:**
   ```bash
   # If loading images directly (not via proxy), may hit CORS
   # Solution: Ensure all images go through image proxy
   ```

4. **Cloudinary configuration (if using):**
   ```bash
   # Verify CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY set
   # Check Cloudinary dashboard for quota/errors
   ```

### Filters Not Working

**Symptoms:**
- Category filter doesn't filter games
- Search returns no results when it should
- URL parameters not updating

**Solutions:**

1. **Check URL parameters:**
   ```bash
   # URL should update when filtering:
   https://library.manaandmeeples.co.nz/?category=COOP_ADVENTURE

   # If URL doesn't change, JavaScript error likely
   # Check browser console
   ```

2. **Verify API supports filter:**
   ```bash
   # Test API directly:
   curl "https://mana-meeples-boardgame-list.onrender.com/api/public/games?category=COOP_ADVENTURE"

   # Should return filtered games
   ```

3. **Case sensitivity issues:**
   ```bash
   # Category keys are uppercase:
   category=COOP_ADVENTURE      ✅
   category=coop_adventure      ❌ Wrong case
   ```

---

## Database Problems

### Database Connection Errors

**Symptoms:**
- "could not connect to server"
- "connection refused"
- "no pg_hba.conf entry for host"

**Solutions:**

1. **Verify DATABASE_URL is correct:**
   ```bash
   # Format:
   postgresql://username:password@host:5432/database

   # Check in Render Dashboard → Environment
   # Should match PostgreSQL connection string from database service
   ```

2. **Check database service is running:**
   ```bash
   # Render Dashboard → PostgreSQL service
   # Status should be "Available"
   # If suspended, click "Resume"
   ```

3. **Connection pool exhausted:**
   ```python
   # Error: "QueuePool limit exceeded"
   # Solution: Increase pool_size in database.py

   pool_size=20,  # Increase from 15
   max_overflow=30,  # Increase from 20
   ```

4. **Network/firewall issues:**
   ```bash
   # Render services should automatically connect
   # If using external database, verify:
   # - Database accepts connections from Render IPs
   # - SSL mode is correct (usually "require")
   ```

### Database Migrations Failing

**Symptoms:**
- "relation does not exist"
- "column does not exist"
- Migrations not running automatically

**Solutions:**

1. **Check migration logs:**
   ```bash
   # Render Dashboard → Logs → Search for "migration"

   # Should see:
   "Running migrations..."
   "All migrations applied successfully"
   ```

2. **Manual migration (if needed):**
   ```bash
   # Connect to database via psql or DataGrip
   # Check table structure:
   \d boardgames

   # Verify all columns exist
   # If missing, migrations didn't run
   ```

3. **Schema mismatch:**
   ```python
   # If code expects columns that don't exist:
   # - Check models.py for expected schema
   # - Check database for actual schema
   # - Ensure migrations ran successfully
   ```

### Slow Database Queries

**Symptoms:**
- API endpoints taking >2 seconds
- Timeouts on large queries
- High database CPU usage

**Solutions:**

1. **Check indexes exist:**
   ```sql
   -- View indexes:
   SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'boardgames';

   -- Should have indexes on:
   -- - title
   -- - bgg_id
   -- - mana_meeple_category
   -- - nz_designer
   ```

2. **Analyze slow queries:**
   ```sql
   -- Enable query logging in PostgreSQL
   -- Review slow query log in Render Database → Metrics
   ```

3. **Connection pool settings:**
   ```python
   # Ensure pool_pre_ping is enabled (it is):
   pool_pre_ping=True  # Tests connections before use
   ```

4. **Consider caching:**
   ```python
   # Enable Redis caching for common queries
   # See REDIS_SETUP.md
   ```

---

## Authentication & Authorization

### Cannot Login to Admin Panel

**Symptoms:**
- Admin token rejected
- "Unauthorized" error
- Can't access admin endpoints

**Solutions:**

1. **Verify admin token:**
   ```bash
   # Check ADMIN_TOKEN environment variable in Render
   # Should be long, secure hex string (64 characters)

   # Test login:
   curl -X POST https://mana-meeples-boardgame-list.onrender.com/api/admin/login \
     -H "Content-Type: application/json" \
     -d '{"admin_token":"YOUR_TOKEN_HERE"}'

   # Should return: {"message":"Login successful","token":"JWT_TOKEN"}
   ```

2. **Rate limiting on login:**
   ```bash
   # Error: "Too many login attempts"
   # Wait 1 minute for rate limit to reset
   ```

3. **JWT token expired:**
   ```bash
   # JWTs expire after JWT_EXPIRATION_DAYS (default: 7 days)
   # Solution: Login again to get new token
   ```

4. **Session cookie issues:**
   ```bash
   # Clear browser cookies for site
   # Try logging in again
   ```

### JWT Token Validation Failing

**Symptoms:**
- "Invalid token" error
- Previously working token now rejected
- Admin operations failing with 401

**Solutions:**

1. **Check SESSION_SECRET hasn't changed:**
   ```bash
   # If SESSION_SECRET changed, all old JWTs become invalid
   # Solution: Re-login to get new JWT with new secret
   ```

2. **Token expired:**
   ```bash
   # Check token expiration:
   # JWT payload contains "exp" field
   # Decode at: https://jwt.io

   # Solution: Login again
   ```

3. **Verify token format:**
   ```bash
   # JWT should be in header:
   Authorization: Bearer YOUR_JWT_TOKEN

   # Not:
   Authorization: YOUR_JWT_TOKEN  # Missing "Bearer"
   ```

---

## Performance Issues

### API Response Times Slow (>2 seconds)

**Symptoms:**
- Endpoints taking 2-5+ seconds
- Users complaining of slowness
- Render metrics show high response times

**Solutions:**

1. **Check database query performance:**
   ```bash
   # Look in logs for slow queries
   # Anything >1s is logged as slow

   # Enable query logging to find N+1 queries
   ```

2. **Enable Redis caching:**
   ```bash
   # See REDIS_SETUP.md
   # Caching reduces database load significantly
   ```

3. **Check Render instance resources:**
   ```bash
   # Render Dashboard → Service → Metrics
   # High CPU/memory? Consider upgrading plan:
   # Starter → Standard → Pro
   ```

4. **BGG API circuit breaker triggered:**
   ```bash
   # If importing many games, BGG API may be slow
   # Circuit breaker prevents cascade failures
   # Wait for circuit to reset (check logs)
   ```

### Frontend Loading Slowly

**Symptoms:**
- Initial page load takes >3 seconds
- Large JavaScript bundles
- Lighthouse score <80

**Solutions:**

1. **Check bundle size:**
   ```bash
   cd frontend
   npm run build

   # Check dist/ for bundle sizes
   # Largest files should be code-split
   ```

2. **Enable code splitting:**
   ```javascript
   // Already implemented with React.lazy
   // Verify in Network tab that chunks load separately
   ```

3. **Optimize images:**
   ```bash
   # Ensure using image proxy with proper caching
   # Check image sizes aren't too large (>500KB)
   ```

4. **CDN caching:**
   ```bash
   # Render automatically provides CDN
   # Check Cache-Control headers in Network tab
   ```

---

## Testing Problems

### Backend Tests Failing Locally

**Symptoms:**
- `pytest` fails with import errors
- Database connection errors in tests
- Tests pass in CI but fail locally

**Solutions:**

1. **Run from backend directory:**
   ```bash
   # Must be in backend/ directory:
   cd backend
   pytest

   # Not from root:
   pytest backend/tests/  # May have import issues
   ```

2. **Install test dependencies:**
   ```bash
   pip install -r backend/requirements.txt
   pip install pytest pytest-cov pytest-asyncio
   ```

3. **Database connection in tests:**
   ```bash
   # Tests use in-memory SQLite by default (see conftest.py)
   # If getting PostgreSQL errors, check conftest.py
   ```

4. **Import errors:**
   ```python
   # Ensure imports are relative within backend/:
   from models import Game  # ✅
   from backend.models import Game  # ❌ Wrong when running from backend/
   ```

### Frontend Tests Failing

**Symptoms:**
- `npm test` fails
- "Cannot find module" errors
- Tests timeout

**Solutions:**

1. **Install dependencies:**
   ```bash
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   ```

2. **Mocking issues:**
   ```javascript
   // Ensure API calls are mocked in tests
   // vi.mock('../../api/client')
   ```

3. **Router errors:**
   ```javascript
   // Wrap components in test router:
   import { MemoryRouter } from 'react-router-dom'

   render(
     <MemoryRouter>
       <Component />
     </MemoryRouter>
   )
   ```

---

## Development Environment

### Local Backend Won't Start

**Symptoms:**
- `python main.py` fails
- Import errors
- Port already in use

**Solutions:**

1. **Port 8000 in use:**
   ```bash
   # Error: "Address already in use"
   # Find process:
   lsof -i :8000

   # Kill process:
   kill -9 <PID>
   ```

2. **Missing dependencies:**
   ```bash
   pip install -r backend/requirements.txt
   ```

3. **Environment variables not set:**
   ```bash
   # Copy example env file:
   cp .env.example .env

   # Edit .env with your local values:
   DATABASE_URL=sqlite:///./local.db  # For local development
   ADMIN_TOKEN=your_local_token
   ```

### Local Frontend Won't Start

**Symptoms:**
- `npm start` fails
- Compilation errors
- Can't connect to backend

**Solutions:**

1. **Port 3000 in use:**
   ```bash
   # Use different port:
   PORT=3001 npm start
   ```

2. **API connection issues:**
   ```bash
   # Verify backend is running on http://localhost:8000
   curl http://localhost:8000/api/health

   # Check frontend API configuration points to localhost
   ```

3. **Node modules issues:**
   ```bash
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   ```

---

## Getting More Help

### Still Having Issues?

1. **Check logs thoroughly:**
   - Render Dashboard → Service → Logs
   - Browser DevTools → Console
   - Browser DevTools → Network tab

2. **Enable detailed logging:**
   ```python
   # backend/main.py
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

3. **Check Sentry (if configured):**
   - Full error context with stack traces
   - Performance monitoring data

4. **Review documentation:**
   - [Deployment Guide](./deployment/DEPLOYMENT_GUIDE.md)
   - [Testing Guide](../TESTING.md)
   - [API Reference](./API_REFERENCE.md)
   - [CLAUDE.md](../CLAUDE.md)

5. **Create GitHub issue:**
   - Include error messages
   - Include steps to reproduce
   - Include relevant logs
   - Tag with appropriate label (bug, deployment, etc.)

---

**Last Updated**: December 2025
**Maintainer**: Development Team
