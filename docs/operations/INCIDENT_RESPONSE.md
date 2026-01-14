# Incident Response Playbook

## Overview

This document provides step-by-step procedures for responding to incidents affecting the Mana & Meeples Board Game Library. Follow these procedures to minimize downtime and user impact.

---

## Severity Levels

| Level | Definition | Response Time | Examples |
|-------|------------|---------------|----------|
| **P0 (Critical)** | Complete service outage, data breach, security compromise | Immediate | Site down, database corrupted, credentials leaked |
| **P1 (High)** | Partial outage, degraded performance affecting users | < 1 hour | API errors, slow responses, auth failures |
| **P2 (Medium)** | Non-critical bug, minor degradation | < 4 hours | UI glitches, non-blocking errors |
| **P3 (Low)** | Cosmetic issue, feature request | Next business day | Styling issues, minor improvements |

---

## Quick Reference: Health Check Commands

```bash
# Basic health check
curl https://mana-meeples-boardgame-list.onrender.com/api/health

# Database health
curl https://mana-meeples-boardgame-list.onrender.com/api/health/db

# Redis health
curl https://mana-meeples-boardgame-list.onrender.com/api/health/redis

# Performance stats (admin only)
curl https://mana-meeples-boardgame-list.onrender.com/api/debug/performance
```

---

## P0: Complete Service Outage

### Symptoms
- Website returns 5xx errors or doesn't load
- API endpoints return errors or timeout
- Users report "site is down"

### Immediate Actions (First 5 Minutes)

1. **Verify the outage:**
   ```bash
   curl -I https://library.manaandmeeples.co.nz
   curl https://mana-meeples-boardgame-list.onrender.com/api/health
   ```

2. **Check Render status:**
   - Visit [Render Status Page](https://status.render.com/)
   - Check for platform-wide issues

3. **Check recent deployments:**
   - Render Dashboard → Your Service → Deploys
   - Look for failed deployments in last 24 hours

4. **Review logs:**
   - Render Dashboard → Your Service → Logs
   - Look for error patterns, exceptions, connection failures

### Investigation (5-15 Minutes)

5. **Check database:**
   ```bash
   curl https://mana-meeples-boardgame-list.onrender.com/api/health/db
   ```
   - If unhealthy: See "Database Issues" section below

6. **Check Redis:**
   ```bash
   curl https://mana-meeples-boardgame-list.onrender.com/api/health/redis
   ```
   - If unhealthy: Service should fallback to in-memory (check logs)

7. **Check for resource exhaustion:**
   - Render Dashboard → Metrics
   - Look for CPU/Memory spikes
   - Check for connection pool exhaustion

### Resolution

8. **If deployment issue - Rollback:**
   - Render Dashboard → Deploys
   - Find last working deployment
   - Click "Redeploy" on that version

9. **If database issue:**
   - Check PostgreSQL service status in Render
   - Verify connection credentials haven't expired
   - See "Database Issues" section

10. **If external service (BGG/Cloudinary):**
    - Enable graceful degradation (service should handle this automatically)
    - Check BGG/Cloudinary status pages

### Post-Resolution

11. Document the incident using template below
12. Schedule retrospective meeting
13. Update runbooks with lessons learned

---

## P1: Database Issues

### Symptoms
- Slow API responses (>5 seconds)
- Timeout errors in logs
- 503 Service Unavailable
- Health check returns unhealthy

### Connection Pool Exhaustion

**Symptoms:** "Connection pool exhausted" or timeout errors

**Resolution:**
1. Check current connections:
   - Render Dashboard → PostgreSQL → Metrics
   - Look for connection count near pool limit

2. Identify slow queries:
   ```bash
   curl https://mana-meeples-boardgame-list.onrender.com/api/debug/performance
   ```

3. Temporary fix - increase pool size:
   - Render Dashboard → Web Service → Environment
   - Update `DB_POOL_SIZE` (default: 15) to higher value
   - Update `DB_MAX_OVERFLOW` (default: 20) to higher value

4. Long-term fix:
   - Identify and optimize slow queries
   - Add missing indexes
   - Review connection handling code

### Database Unreachable

**Symptoms:** Connection refused or timeout errors

**Resolution:**
1. Check PostgreSQL status:
   - Render Dashboard → PostgreSQL service
   - Verify status is "Running"

2. If PostgreSQL is down:
   - Wait for Render to auto-recover (usually < 5 minutes)
   - Check Render status page for incidents

3. If credentials issue:
   - Verify `DATABASE_URL` is correct
   - Check if password was rotated recently

---

## P1: Authentication Failures

### Symptoms
- Users can't log in as admin
- 401 errors on admin endpoints
- Rate limiting errors (429)

### Rate Limiting Issues

**Resolution:**
1. Check if user is rate-limited:
   - 429 errors indicate too many failed attempts
   - Wait 5 minutes for rate limit to reset

2. If Redis is down, rate limiting uses in-memory storage:
   - Restart service to clear in-memory rate limits
   - Fix Redis connection for persistent tracking

### JWT Token Issues

**Resolution:**
1. Verify `SESSION_SECRET` is set in environment
2. Check token format in Authorization header
3. Tokens expire after `JWT_EXPIRATION_DAYS` (default: 7)
4. Generate new token via login endpoint

---

## P1: High Error Rate

### Symptoms
- Sentry alerts for increased error rate
- Multiple users reporting issues
- Error rate > 1% of requests

### Investigation Steps

1. Check Sentry for error patterns:
   - Group errors by type
   - Identify common stack traces
   - Check for new error types

2. Check logs for patterns:
   - Render Dashboard → Logs
   - Filter by error level
   - Look for correlation with deployments

3. Check external dependencies:
   - BGG API status
   - Cloudinary status
   - Render platform status

### Resolution

1. If bug introduced in recent deploy → Rollback
2. If external service issue → Enable graceful degradation
3. If data issue → Fix data, deploy fix
4. If traffic spike → Scale up resources

---

## P2: Performance Degradation

### Symptoms
- Slow page loads (>3 seconds)
- High latency on API calls
- User complaints about speed

### Investigation

1. Check performance endpoint:
   ```bash
   curl https://mana-meeples-boardgame-list.onrender.com/api/debug/performance
   ```

2. Check for slow queries in logs

3. Check resource utilization:
   - Render Dashboard → Metrics
   - Look for CPU/Memory spikes

4. Check cache hit rates:
   - Look for cache miss patterns
   - Verify Redis is operational

### Resolution

1. Optimize slow queries (add indexes)
2. Scale up resources if needed
3. Review caching strategy
4. Enable more aggressive caching

---

## Communication Templates

### Initial Notification (P0/P1)

```
Subject: [INCIDENT] Mana & Meeples Library - Service Degradation

Team,

We are investigating an issue affecting [SERVICE/FEATURE].

**Status:** Investigating
**Impact:** [Description of user impact]
**Started:** [Time]

We will provide updates every [15/30] minutes until resolved.

-- [Your Name]
```

### Update Template

```
Subject: [UPDATE] Mana & Meeples Library - Service Degradation

**Status:** [Investigating/Identified/Monitoring/Resolved]
**Update:** [What we know now]
**Next steps:** [What we're doing]
**ETA:** [If known]

-- [Your Name]
```

### Resolution Notification

```
Subject: [RESOLVED] Mana & Meeples Library - Service Restored

Team,

The incident affecting [SERVICE/FEATURE] has been resolved.

**Root cause:** [Brief explanation]
**Resolution:** [What was done]
**Duration:** [Start time] to [End time] ([X] minutes)
**Impact:** [Number of affected users/requests if known]

A full post-incident review will be scheduled.

-- [Your Name]
```

---

## Incident Report Template

```markdown
# Incident Report: [Brief Title]

## Summary
- **Severity:** P0/P1/P2/P3
- **Duration:** [Start time] to [End time] ([X] minutes)
- **Impact:** [Affected users/features]
- **Detection:** [How was it detected - monitoring, user report, etc.]

## Timeline (UTC)
- HH:MM - [Event 1 - e.g., "Deployment triggered"]
- HH:MM - [Event 2 - e.g., "First error alerts"]
- HH:MM - [Event 3 - e.g., "Investigation started"]
- HH:MM - [Event 4 - e.g., "Root cause identified"]
- HH:MM - [Event 5 - e.g., "Fix deployed"]
- HH:MM - [Event 6 - e.g., "Service restored"]

## Root Cause
[Technical explanation of what caused the incident]

## Resolution
[What was done to fix the immediate issue]

## Contributing Factors
- [Factor 1]
- [Factor 2]

## Lessons Learned
### What went well
- [Positive 1]
- [Positive 2]

### What could be improved
- [Improvement 1]
- [Improvement 2]

## Action Items
- [ ] [Action 1] - Owner: [Name] - Due: [Date]
- [ ] [Action 2] - Owner: [Name] - Due: [Date]
- [ ] [Action 3] - Owner: [Name] - Due: [Date]

## Appendix
- [Link to relevant logs]
- [Link to Sentry issue]
- [Link to related PRs/commits]
```

---

## Useful Links

- **Render Dashboard:** https://dashboard.render.com/
- **Render Status:** https://status.render.com/
- **Sentry Dashboard:** [Your Sentry URL]
- **BGG API Status:** https://boardgamegeek.com/wiki/page/BGG_XML_API2
- **Cloudinary Status:** https://status.cloudinary.com/

---

## Contact Information

- **Primary On-Call:** [Name/Contact]
- **Backup On-Call:** [Name/Contact]
- **Escalation:** [Name/Contact]
