# Security Best Practices - Mana & Meeples Board Game Library

Comprehensive security guidelines for developers, administrators, and operations teams.

---

## Table of Contents

1. [Security Overview](#security-overview)
2. [Authentication & Authorization](#authentication--authorization)
3. [Secrets Management](#secrets-management)
4. [Input Validation](#input-validation)
5. [Database Security](#database-security)
6. [API Security](#api-security)
7. [Frontend Security](#frontend-security)
8. [HTTPS & TLS](#https--tls)
9. [Rate Limiting](#rate-limiting)
10. [Monitoring & Incident Response](#monitoring--incident-response)
11. [Security Checklist](#security-checklist)

---

## Security Overview

### Defense-in-Depth Strategy

The application implements multiple layers of security:

```
┌─────────────────────────────────────────┐
│  🌐 HTTPS/TLS                           │  ← Transport Security
├─────────────────────────────────────────┤
│  🛡️  Security Headers (CSP, HSTS, etc.)│  ← Header Protection
├─────────────────────────────────────────┤
│  🚦 Rate Limiting (IP-based)            │  ← DoS Protection
├─────────────────────────────────────────┤
│  🔐 Authentication (JWT + Sessions)     │  ← Identity Verification
├─────────────────────────────────────────┤
│  ✅ Input Validation (Pydantic)         │  ← Data Validation
├─────────────────────────────────────────┤
│  🔒 CORS Whitelist                      │  ← Origin Control
├─────────────────────────────────────────┤
│  💾 ORM (SQLAlchemy)                    │  ← SQL Injection Prevention
├─────────────────────────────────────────┤
│  🧹 XSS Protection (DOMPurify)          │  ← Frontend Sanitization
└─────────────────────────────────────────┘
```

### Security Principles

1. **Least Privilege**: Grant minimum necessary permissions
2. **Defense in Depth**: Multiple security layers
3. **Fail Securely**: Default to deny, not allow
4. **Never Trust Input**: Validate and sanitize all inputs
5. **Encrypt Sensitive Data**: Use HTTPS, encrypt secrets
6. **Log Security Events**: Monitor for suspicious activity

---

## Authentication & Authorization

### JWT (JSON Web Tokens)

**Implementation:**

```python
# backend/utils/auth.py
def generate_jwt_token(client_ip: str) -> str:
    """Generate JWT token with secure signing"""
    payload = {
        "ip": client_ip,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(days=JWT_EXPIRATION_DAYS)
    }
    return jwt.encode(payload, SESSION_SECRET, algorithm="HS256")
```

**Best Practices:**

✅ **DO:**
- Use strong secrets (32+ bytes, cryptographically random)
- Set appropriate expiration times (7 days default)
- Include IP address in payload for additional validation
- Use HS256 algorithm (secure and fast)
- Verify signature on every request

❌ **DON'T:**
- Store sensitive data in JWT payload (it's not encrypted, only signed)
- Use predictable secrets
- Set very long expiration times (>30 days)
- Accept tokens from untrusted sources
- Expose secret key in logs or errors

**Token Storage:**

```javascript
// Frontend: Store in memory or httpOnly cookie
// ✅ Good: httpOnly cookie (protected from XSS)
// ✅ Good: In-memory state (cleared on refresh)
// ❌ Bad: localStorage (vulnerable to XSS)
// ❌ Bad: sessionStorage (vulnerable to XSS)
```

### Session Management

**Redis-Based Sessions (Recommended):**

```python
# backend/shared/rate_limiting.py
class SessionStorage:
    async def set_session(self, token: str, data: dict, ttl: int):
        """Store session in Redis with TTL"""
        redis = get_redis_client()
        if redis:
            await redis.setex(
                f"session:{token}",
                ttl,
                json.dumps(data)
            )
```

**Best Practices:**

✅ **DO:**
- Use Redis for distributed session storage
- Set reasonable TTLs (1 hour default)
- Include IP address in session data
- Rotate session tokens periodically
- Invalidate sessions on logout

❌ **DON'T:**
- Store sensitive data in sessions
- Use predictable session IDs
- Allow sessions to persist indefinitely
- Share sessions across different IPs (unless necessary)

### Admin Authentication

**Two-Factor Approach:**

1. **Initial login**: Admin token → JWT token
2. **Subsequent requests**: JWT token validation

```python
# backend/api/dependencies.py
def require_admin_auth(
    authorization: Optional[str] = Header(None),
    admin_session: Optional[str] = Cookie(None),
):
    """Validate JWT token or session cookie"""
    # 1. Try JWT (preferred)
    if jwt_token and verify_jwt_token(jwt_token):
        return  # Authenticated

    # 2. Try session cookie (backward compat)
    if admin_session and validate_session(admin_session):
        return  # Authenticated

    # 3. Deny access
    raise HTTPException(status_code=401)
```

**Best Practices:**

✅ **DO:**
- Require strong admin tokens (64+ hex characters)
- Rate limit login attempts (10 attempts per hour per IP)
- Log all authentication attempts
- Use JWT for stateless authentication
- Implement token refresh mechanism

❌ **DON'T:**
- Hardcode admin credentials
- Allow brute force attacks
- Expose authentication errors (don't reveal if user exists)
- Allow weak tokens
- Skip authentication on "internal" endpoints

---

## Secrets Management

### Environment Variables

**Secure Secret Generation:**

```bash
# Generate secure secrets:
python -c "import secrets; print(secrets.token_hex(32))"

# Output: 64 character hex string
# Example: b2f6f6f7af1e4db9a43a8ed5e0d86a38a22fdad8a1e7b4730f9207d767fab1cc
```

**Required Secrets:**

```bash
# Production environment (Render Dashboard)
ADMIN_TOKEN=<64-char-hex>        # Admin authentication
SESSION_SECRET=<64-char-hex>     # JWT signing key
DATABASE_URL=postgresql://...     # Database connection
REDIS_URL=redis://...            # Redis connection (optional)
SENTRY_DSN=https://...           # Error tracking (optional)
```

**Best Practices:**

✅ **DO:**
- Use Render Dashboard for secret management (not in code)
- Generate cryptographically random secrets
- Rotate secrets quarterly (minimum)
- Use different secrets for dev/staging/production
- Use `sync: false` in render.yaml for sensitive vars
- Document what each secret is for

❌ **DON'T:**
- Commit secrets to Git (even in .env.example)
- Share secrets via email/Slack
- Reuse secrets across environments
- Use default/example secrets in production
- Log secrets (even accidentally)
- Expose secrets in error messages

**Secret Rotation Procedure:**

1. **Generate new secret:**
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **Update in Render Dashboard:**
   - Go to Service → Environment
   - Update secret value
   - Click "Save Changes" (triggers redeploy)

3. **Verify deployment:**
   - Check health endpoints
   - Test authentication
   - Monitor logs for errors

4. **Invalidate old sessions** (for SESSION_SECRET rotation):
   - All users must re-login
   - Clear Redis sessions (if applicable)

---

## Input Validation

### Pydantic Schemas

**Example Validation:**

```python
# backend/schemas.py
from pydantic import BaseModel, Field, field_validator

class GameCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    bgg_id: Optional[int] = Field(None, ge=1, le=999999)
    year: Optional[int] = Field(None, ge=1900, le=2100)

    @field_validator("title")
    @classmethod
    def validate_title(cls, v):
        if not v.strip():
            raise ValueError("Title cannot be empty")
        # Sanitize: Remove dangerous characters
        dangerous_chars = ["<", ">", "\"", "'", "&"]
        for char in dangerous_chars:
            if char in v:
                raise ValueError(f"Title contains invalid character: {char}")
        return v.strip()
```

**Best Practices:**

✅ **DO:**
- Validate all user inputs with Pydantic
- Set appropriate min/max lengths
- Use field_validator for complex validation
- Sanitize inputs (strip whitespace, remove dangerous chars)
- Reject invalid data early (at request parsing)
- Return clear error messages

❌ **DON'T:**
- Trust client-side validation alone
- Accept unbounded string lengths
- Allow HTML/script tags in text fields (unless explicitly needed)
- Skip validation on "trusted" inputs
- Validate after database insertion (too late!)

### SQL Injection Prevention

**Using SQLAlchemy ORM:**

```python
# ✅ SAFE: Using ORM (parameterized queries)
from sqlalchemy import select

game = session.execute(
    select(Game).where(Game.id == game_id)
).scalar_one_or_none()

# ❌ DANGEROUS: Raw SQL with user input
raw_sql = f"SELECT * FROM games WHERE id = {game_id}"  # DON'T DO THIS!
```

**Best Practices:**

✅ **DO:**
- Always use SQLAlchemy ORM for queries
- Use parameterized queries for raw SQL (if absolutely necessary)
- Escape user inputs when building queries
- Review all database queries during code review

❌ **DON'T:**
- Concatenate user input into SQL strings
- Use `text()` without proper parameterization
- Trust user input for table/column names
- Disable ORM protections

---

## Database Security

### Connection Security

**Secure Connection String:**

```python
# Use SSL/TLS for database connections:
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require

# Connection pooling with security:
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_pre_ping=True,  # Detect stale connections
    pool_recycle=3600,   # Prevent long-lived connections
)
```

**Best Practices:**

✅ **DO:**
- Use SSL/TLS for database connections (`sslmode=require`)
- Use connection pooling to prevent exhaustion
- Set connection timeouts
- Use `pool_pre_ping` to validate connections
- Recycle connections periodically
- Restrict database access to application servers only

❌ **DON'T:**
- Expose database publicly to the internet
- Use weak database passwords
- Allow connections without SSL
- Create too many connections (exhaust pool)
- Use root/superuser credentials for application

### Database Credentials

**Best Practices:**

✅ **DO:**
- Use strong passwords (32+ characters)
- Create application-specific database user
- Grant minimum necessary permissions (SELECT, INSERT, UPDATE, DELETE on specific tables)
- Rotate database passwords quarterly
- Use managed database services (Render PostgreSQL) for automatic security updates

❌ **DON'T:**
- Use default passwords (postgres/postgres)
- Grant superuser privileges to application
- Share database credentials across applications
- Store credentials in code
- Allow password authentication from untrusted hosts

### Backup Security

**Automated Backups (Render):**

- Daily automatic backups
- Encrypted at rest
- 7-day retention (Starter plan)
- Access via Render Dashboard only

**Best Practices:**

✅ **DO:**
- Verify backups regularly
- Test restore procedures
- Encrypt backups
- Restrict access to backups
- Monitor backup success/failure

---

## API Security

### CORS Configuration

**Whitelist Configuration:**

```python
# backend/main.py
CORS_ORIGINS = [
    "https://manaandmeeples.co.nz",
    "https://www.manaandmeeples.co.nz",
    "https://library.manaandmeeples.co.nz",
    "https://mana-meeples-library-web.onrender.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,  # Whitelist only
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Explicit list
    allow_headers=["Content-Type", "Authorization"],  # Explicit list
    max_age=3600,  # Cache preflight for 1 hour
)
```

**Best Practices:**

✅ **DO:**
- Use explicit origin whitelist
- Avoid wildcard `*` in production
- List allowed methods explicitly
- List allowed headers explicitly
- Set reasonable `max_age` for preflight caching

❌ **DON'T:**
- Use `allow_origins=["*"]` in production
- Allow all methods (`allow_methods=["*"]`)
- Allow all headers (`allow_headers=["*"]`)
- Add untrusted origins to whitelist

### Security Headers

**Implementation:**

```python
# backend/middleware/security.py
class SecurityHeadersMiddleware:
    async def __call__(self, scope, receive, send):
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                headers.extend([
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"x-xss-protection", b"1; mode=block"),
                    (b"strict-transport-security", b"max-age=31536000"),
                ])
            await send(message)
        await self.app(scope, receive, send_wrapper)
```

**Recommended Headers:**

- `X-Content-Type-Options: nosniff` - Prevent MIME type sniffing
- `X-Frame-Options: DENY` - Prevent clickjacking
- `X-XSS-Protection: 1; mode=block` - Enable XSS filter
- `Strict-Transport-Security: max-age=31536000` - Force HTTPS
- `Content-Security-Policy` - Control resource loading

### Circuit Breaker Pattern

**For External APIs (BGG):**

```python
# backend/services/bgg_service.py
class BGGService:
    MAX_RETRIES = 3
    CIRCUIT_OPEN_THRESHOLD = 5
    CIRCUIT_RESET_TIMEOUT = 300  # 5 minutes

    async def fetch_with_circuit_breaker(self, url):
        """Prevent cascade failures from BGG API"""
        if self.circuit_open:
            if time.time() - self.circuit_opened_at > self.CIRCUIT_RESET_TIMEOUT:
                self.circuit_open = False  # Try again
            else:
                raise CircuitBreakerOpenError("BGG API circuit breaker open")

        # Attempt request with retries...
```

**Best Practices:**

✅ **DO:**
- Implement circuit breakers for external APIs
- Set reasonable timeouts (5-10 seconds)
- Retry with exponential backoff
- Log circuit breaker events
- Monitor external API health

---

## Frontend Security

### XSS Protection

**DOMPurify Integration:**

```javascript
// frontend/src/utils/sanitize.js
import DOMPurify from 'dompurify';

export function sanitizeHTML(dirty) {
  return DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br'],
    ALLOWED_ATTR: ['href', 'title']
  });
}

// Usage:
<div dangerouslySetInnerHTML={{ __html: sanitizeHTML(userContent) }} />
```

**Best Practices:**

✅ **DO:**
- Use DOMPurify for all user-generated HTML
- Configure allowed tags/attributes explicitly
- Sanitize before rendering, not before storage
- Use React's built-in escaping (don't use `dangerouslySetInnerHTML` unless necessary)

❌ **DON'T:**
- Trust user input to be safe HTML
- Allow all HTML tags
- Use `dangerouslySetInnerHTML` without sanitization
- Disable XSS protection headers

### Content Security Policy

**Recommended CSP:**

```html
<!-- frontend/public/index.html -->
<meta http-equiv="Content-Security-Policy" content="
  default-src 'self';
  script-src 'self';
  style-src 'self' 'unsafe-inline';
  img-src 'self' https://cf.geekdo-images.com data:;
  connect-src 'self' https://mana-meeples-boardgame-list.onrender.com;
  font-src 'self';
  object-src 'none';
  base-uri 'self';
  form-action 'self';
">
```

**Best Practices:**

✅ **DO:**
- Start with strict CSP and relax as needed
- Use `'self'` for same-origin resources
- Whitelist specific external domains (BGG images)
- Use `'nonce-'` for inline scripts (if needed)
- Monitor CSP violations

❌ **DON'T:**
- Use `'unsafe-eval'` (allows code injection)
- Use `'unsafe-inline'` for scripts (use for styles sparingly)
- Allow `*` wildcards
- Disable CSP entirely

---

## HTTPS & TLS

### Automatic SSL Certificates

**Render Configuration:**

- Automatic SSL certificate provisioning via Let's Encrypt
- Auto-renewal before expiration
- HTTPS enforcement (HTTP → HTTPS redirect)

**Best Practices:**

✅ **DO:**
- Use HTTPS for all environments (even development with self-signed certs)
- Enable HSTS headers
- Set secure cookie flags (`Secure`, `HttpOnly`, `SameSite`)
- Test SSL configuration: https://www.ssllabs.com/ssltest/

❌ **DON'T:**
- Allow HTTP in production
- Use self-signed certificates in production
- Ignore SSL certificate expiration warnings
- Disable certificate validation (even in development)

### Cookie Security

**Secure Cookie Configuration:**

```python
# backend/api/routers/admin.py
response.set_cookie(
    key="admin_session",
    value=session_token,
    httponly=True,        # Prevent JavaScript access (XSS protection)
    secure=True,          # HTTPS only
    samesite="strict",    # CSRF protection
    max_age=3600,         # 1 hour expiration
)
```

**Cookie Flags:**

- `HttpOnly`: Prevents JavaScript access (XSS protection)
- `Secure`: HTTPS only (prevents interception)
- `SameSite=Strict`: Prevents CSRF attacks
- `Max-Age`: Limits cookie lifetime
- `Domain`: Restricts to specific domain
- `Path`: Restricts to specific path

---

## Rate Limiting

### Implementation

**Using Slowapi:**

```python
# backend/api/routers/public.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.get("/games")
@limiter.limit("100/minute")
async def get_public_games(...):
    """Rate limited to 100 requests per minute per IP"""
```

**Rate Limits by Endpoint:**

- **Public endpoints**: 100 req/min per IP
- **Admin login**: 10 req/hour per IP (brute force protection)
- **Admin CRUD**: 60 req/min per IP
- **Health checks**: 200 req/min per IP

**Best Practices:**

✅ **DO:**
- Set per-endpoint rate limits
- Use IP-based rate limiting
- Return `429 Too Many Requests` with `Retry-After` header
- Log rate limit violations
- Adjust limits based on legitimate traffic patterns

❌ **DON'T:**
- Set rate limits too low (hurts legitimate users)
- Skip rate limiting on "internal" endpoints
- Allow unlimited requests on authentication endpoints
- Block IPs permanently (use temporary blocks)

### DDoS Protection

**Render Provides:**

- DDoS protection at infrastructure level
- Automatic scaling (within plan limits)
- Traffic filtering

**Additional Measures:**

```python
# Custom rate limiting for burst protection
@limiter.limit("10/second")  # Burst protection
async def expensive_operation():
    pass
```

---

## Monitoring & Incident Response

### Sentry Integration

**Error Tracking:**

```python
# backend/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    environment=os.getenv("ENVIRONMENT", "production"),
    traces_sample_rate=0.1,  # 10% performance monitoring
    before_send=filter_sensitive_data,  # Remove secrets from errors
)

def filter_sensitive_data(event, hint):
    """Remove sensitive data from Sentry events"""
    # Remove authorization headers
    if "request" in event and "headers" in event["request"]:
        headers = event["request"]["headers"]
        headers.pop("Authorization", None)
        headers.pop("Cookie", None)
    return event
```

**Best Practices:**

✅ **DO:**
- Configure Sentry with proper environment
- Filter sensitive data before sending
- Set appropriate sample rates
- Monitor error frequency
- Set up alerts for critical errors

### Security Logging

**What to Log:**

```python
# Successful authentication
logger.info(f"Admin login successful from IP: {client_ip}")

# Failed authentication
logger.warning(f"Failed login attempt from IP: {client_ip}")

# Rate limit violations
logger.warning(f"Rate limit exceeded for IP: {client_ip} on endpoint: {endpoint}")

# Suspicious activity
logger.error(f"SQL injection attempt detected from IP: {client_ip}")
```

**Best Practices:**

✅ **DO:**
- Log security events (auth, rate limits, errors)
- Include timestamps, IP addresses, user agents
- Log to centralized system (Sentry, CloudWatch)
- Set up alerts for suspicious patterns
- Retain logs for 90+ days (compliance)

❌ **DON'T:**
- Log secrets (passwords, tokens, API keys)
- Log full request/response bodies (may contain secrets)
- Log personally identifiable information (PII) unnecessarily
- Ignore security logs

### Incident Response Plan

**1. Detection:**
- Sentry alerts for unusual errors
- Render metrics for traffic spikes
- User reports of suspicious activity

**2. Assessment:**
- Review logs for attack patterns
- Identify affected systems
- Estimate impact (data breach, service disruption)

**3. Containment:**
- Block malicious IPs (temporarily)
- Disable compromised accounts
- Rotate compromised secrets
- Scale up resources if DDoS

**4. Eradication:**
- Fix vulnerability
- Deploy patch
- Clear malicious data (if any)

**5. Recovery:**
- Restore from backup (if needed)
- Verify system integrity
- Monitor for continued attacks

**6. Post-Mortem:**
- Document incident timeline
- Identify root cause
- Implement preventive measures
- Update runbooks

---

## Security Checklist

### Development

- [ ] All user inputs validated with Pydantic schemas
- [ ] SQL queries use ORM (no raw SQL with user input)
- [ ] Secrets not committed to Git
- [ ] Dependencies up to date (no known vulnerabilities)
- [ ] Error messages don't expose sensitive information
- [ ] Code reviewed for security issues

### Deployment

- [ ] Environment variables set in Render Dashboard
- [ ] Strong secrets generated (64+ characters)
- [ ] CORS origins whitelist configured
- [ ] Rate limiting enabled on all endpoints
- [ ] HTTPS enforced (SSL certificate active)
- [ ] Security headers configured
- [ ] Sentry configured for error tracking

### Operations

- [ ] Secrets rotated quarterly (minimum)
- [ ] Database backups verified
- [ ] Security logs monitored
- [ ] Incident response plan documented
- [ ] Admin access limited to authorized users
- [ ] Rate limit thresholds reviewed and adjusted

### Periodic Review (Quarterly)

- [ ] Review and rotate all secrets
- [ ] Update dependencies to latest secure versions
- [ ] Review access logs for suspicious activity
- [ ] Test backup restore procedure
- [ ] Review and update CORS origins
- [ ] Audit admin user list (remove inactive)
- [ ] Penetration testing (if budget allows)

---

## Additional Resources

### Security Tools

- **OWASP ZAP**: Web application security scanner
- **Snyk**: Dependency vulnerability scanning
- **Safety**: Python dependency security checker
- **npm audit**: Node.js dependency checker

### Security Standards

- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **SANS Top 25**: https://www.sans.org/top25-software-errors/
- **CWE**: Common Weakness Enumeration

### Security Training

- **OWASP WebGoat**: Hands-on security training
- **HackerOne CTF**: Capture the flag challenges
- **Web Security Academy**: PortSwigger training

---

## Reporting Security Vulnerabilities

If you discover a security vulnerability, please:

1. **DO NOT** create a public GitHub issue
2. Email security contact: [Add email]
3. Include:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if known)

We will respond within 48 hours and work with you to address the issue.

---

**Last Updated**: December 2025
**Next Security Review**: March 2026
**Maintainer**: Development Team
