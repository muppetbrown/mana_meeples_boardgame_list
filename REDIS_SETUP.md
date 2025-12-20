# Redis Setup Guide - Sprint 8

Quick reference for setting up Redis for the Mana & Meeples Board Game Library.

## Local Development

### Option 1: Docker Compose (Recommended)

```bash
# Start Redis
docker compose up -d redis

# Verify Redis is running
docker compose ps redis
docker compose logs redis

# Test connection
redis-cli ping  # Should return: PONG

# Access Redis CLI
redis-cli
> PING
> KEYS *
> GET session:*
> exit

# Stop Redis
docker compose down redis
```

### Option 2: Redis Commander (Web GUI)

```bash
# Start Redis with GUI
docker compose --profile tools up -d

# Access Redis Commander
# Open browser: http://localhost:8081
# View/manage Redis keys in web interface

# Stop all services
docker compose --profile tools down
```

### Option 3: Native Installation

**macOS:**
```bash
brew install redis
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
```

**Windows:**
- Download from: https://redis.io/download
- Or use Docker (recommended)

## Production Deployment

### Render (Recommended)

1. **Create Redis Service:**
   - Go to Render Dashboard
   - Click "New +" → "Redis"
   - Name: `mana-meeples-redis`
   - Plan: Starter ($7/mo) or Free
   - Region: Singapore (same as backend)
   - Click "Create Redis"

2. **Update Backend Service:**
   - Go to Backend Service → Environment
   - Add environment variables:
     ```
     REDIS_URL: <connection-string-from-redis-service>
     REDIS_ENABLED: true
     ```
   - Or link via render.yaml (see commented section)

3. **Deploy:**
   - Render auto-deploys on Git push
   - Verify: https://mana-meeples-boardgame-list.onrender.com/api/health/redis

### Upstash (Alternative - Free Tier Available)

1. **Create Account:**
   - Visit: https://upstash.com/
   - Sign up (GitHub login available)

2. **Create Redis Database:**
   - Click "Create Database"
   - Name: `mana-meeples`
   - Region: Asia Pacific (Singapore)
   - Type: Regional
   - Plan: Free (10,000 commands/day)

3. **Get Connection URL:**
   - Copy "Redis URL" from dashboard
   - Format: `rediss://default:password@redis-host:port`

4. **Configure Backend:**
   - Add to Render environment variables:
     ```
     REDIS_URL: <upstash-connection-url>
     REDIS_ENABLED: true
     ```

### Redis Labs (Alternative)

1. **Create Account:**
   - Visit: https://redis.com/try-free/
   - Sign up for free tier

2. **Create Database:**
   - Follow wizard to create free Redis instance
   - Select cloud provider and region (choose closest to Singapore)

3. **Configure Backend:**
   - Copy connection string
   - Add to Render environment variables

## Environment Variables

### Required

```bash
# Redis connection URL
REDIS_URL=redis://localhost:6379/0

# Enable/disable Redis (default: true)
REDIS_ENABLED=true
```

### Optional

```bash
# Session timeout (default: 3600 = 1 hour)
SESSION_TIMEOUT_SECONDS=3600

# Rate limiting (default: 5 attempts per 300 seconds)
RATE_LIMIT_ATTEMPTS=5
RATE_LIMIT_WINDOW=300
```

## Testing

### Test Redis Connection

```bash
# Start backend
cd backend
uvicorn main:app --reload

# Test health endpoint
curl http://localhost:8000/api/health/redis
```

Expected response:
```json
{
  "status": "healthy",
  "message": "Redis is connected and responding"
}
```

### Run Integration Tests

```bash
# Ensure Redis is running
docker compose up -d redis

# Run test suite
cd backend
python test_redis_integration.py
```

Expected output:
```
✓ Redis Connection ............... PASSED
✓ Redis Operations ............... PASSED
✓ Session Storage ................ PASSED
✓ Rate Limiting .................. PASSED
```

## Monitoring

### Health Check Endpoints

```bash
# Redis health
curl https://mana-meeples-boardgame-list.onrender.com/api/health/redis

# Database health
curl https://mana-meeples-boardgame-list.onrender.com/api/health/db

# Overall health
curl https://mana-meeples-boardgame-list.onrender.com/api/health
```

### Redis CLI Commands

```bash
# Connect to Redis
redis-cli

# View all keys
KEYS *

# View sessions
KEYS session:*

# View rate limits
KEYS ratelimit:*

# Get specific key
GET session:abc123...

# Check TTL (time to live)
TTL session:abc123...

# Monitor commands in real-time
MONITOR

# Check memory usage
INFO memory

# Check stats
INFO stats
```

## Troubleshooting

### Redis Not Connecting

**Error:** "Redis unavailable, falling back to in-memory"

**Solutions:**
1. Verify Redis is running: `docker compose ps redis`
2. Check logs: `docker compose logs redis`
3. Test connection: `redis-cli ping`
4. Verify REDIS_URL is correct
5. Check firewall/security groups

### Sessions Not Persisting

**Symptoms:** Users logged out after restart

**Solutions:**
1. Check Redis health: `/api/health/redis`
2. Verify REDIS_ENABLED=true
3. Check Redis memory: `redis-cli INFO memory`
4. Review backend logs for errors
5. Verify SESSION_TIMEOUT_SECONDS is set

### Performance Issues

**Symptoms:** Slow responses, high latency

**Solutions:**
1. Check Redis latency: `redis-cli --latency`
2. Monitor slow commands: `redis-cli SLOWLOG GET 10`
3. Check memory usage: `redis-cli INFO memory`
4. Review maxmemory policy
5. Consider upgrading Redis plan

## Fallback Mode

If Redis is unavailable or causing issues:

1. **Disable Redis:**
   ```bash
   REDIS_ENABLED=false
   ```

2. **System Behavior:**
   - Falls back to in-memory storage
   - Single instance only (no scaling)
   - Sessions lost on restart
   - Rate limiting per instance

3. **When to Use:**
   - Redis outage/maintenance
   - Testing/debugging
   - Single-instance deployments
   - Development without Docker

## Best Practices

1. **Production:**
   - Always use managed Redis (Render, Upstash, Redis Labs)
   - Enable persistence (AOF or RDB)
   - Set appropriate maxmemory-policy
   - Monitor memory and latency
   - Set up alerting

2. **Security:**
   - Use TLS/SSL for connections (rediss://)
   - Rotate passwords regularly
   - Restrict IP access when possible
   - Don't expose Redis publicly

3. **Performance:**
   - Use connection pooling (built-in)
   - Set appropriate TTLs
   - Monitor memory usage
   - Use pipelining for batch operations

4. **Monitoring:**
   - Track Redis health endpoint
   - Monitor memory usage
   - Track connection count
   - Alert on failures

## Resources

- **Redis Documentation:** https://redis.io/docs/
- **redis-py Library:** https://redis-py.readthedocs.io/
- **Render Redis:** https://render.com/docs/redis
- **Upstash:** https://docs.upstash.com/redis
- **Redis Labs:** https://docs.redis.com/

## Quick Commands Cheat Sheet

```bash
# Local Development
docker compose up -d redis              # Start Redis
docker compose logs -f redis            # View logs
redis-cli ping                          # Test connection
docker compose down redis               # Stop Redis

# Testing
python test_redis_integration.py       # Run tests
curl localhost:8000/api/health/redis   # Check health

# Production Monitoring
curl $API_URL/api/health/redis         # Check health
redis-cli -u $REDIS_URL INFO stats     # View stats
redis-cli -u $REDIS_URL DBSIZE         # Count keys

# Debugging
redis-cli -u $REDIS_URL KEYS *         # List all keys
redis-cli -u $REDIS_URL MONITOR        # Watch commands
redis-cli -u $REDIS_URL SLOWLOG GET    # Slow queries
```

---

**For detailed implementation information, see:** [SPRINT_8_REDIS_SUMMARY.md](SPRINT_8_REDIS_SUMMARY.md)
