# Secret Rotation Procedure

## Overview

This document outlines the quarterly secret rotation procedure for the Mana & Meeples Board Game Library. Regular rotation minimizes exposure risk if credentials are compromised.

**Rotation Schedule:** Quarterly (every 3 months)
**Estimated Time:** 30-45 minutes
**Required Access:** Render Dashboard admin access

---

## Secrets Inventory

| Secret | Location | Rotation Method |
|--------|----------|-----------------|
| `ADMIN_TOKEN` | Render Environment | Generate new hex token |
| `SESSION_SECRET` | Render Environment | Generate new hex token |
| `GITHUB_TOKEN` | Render Environment | Revoke & regenerate in GitHub |
| `CLOUDINARY_API_SECRET` | Render Environment | Regenerate in Cloudinary Console |
| `BGG_API_KEY` | Render Environment | Contact BGG support |
| `DATABASE_URL` | Render PostgreSQL | Change password in Render |
| `REDIS_URL` | Render Redis | Rotate via Render Dashboard |

---

## Step-by-Step Procedure

### Step 1: Generate New Application Secrets

```bash
# Generate new ADMIN_TOKEN (32 bytes = 64 hex characters)
python -c "import secrets; print('ADMIN_TOKEN:', secrets.token_hex(32))"

# Generate new SESSION_SECRET (32 bytes = 64 hex characters)
python -c "import secrets; print('SESSION_SECRET:', secrets.token_hex(32))"
```

**Save these values securely** - you'll need them in Step 2.

---

### Step 2: Update Render Environment Variables

1. Navigate to [Render Dashboard](https://dashboard.render.com/)
2. Select **mana-meeples-boardgame-list** service
3. Go to **Environment** tab
4. Click **Edit** for each secret:
   - `ADMIN_TOKEN` → Paste new token from Step 1
   - `SESSION_SECRET` → Paste new secret from Step 1
5. Click **Save Changes**
6. Service will auto-redeploy (wait ~2-3 minutes)

---

### Step 3: Rotate GitHub Token

1. Go to [GitHub Settings](https://github.com/settings/tokens)
2. Navigate to **Developer settings** → **Personal access tokens** → **Tokens (classic)**
3. Find the token used by this project
4. Click **Delete** to revoke the old token
5. Click **Generate new token (classic)**
6. Select the same scopes as before:
   - `repo` (if accessing private repos)
   - `read:packages` (if using GitHub packages)
7. Copy the new token
8. Update `GITHUB_TOKEN` in Render Environment variables

---

### Step 4: Rotate Cloudinary API Secret

1. Go to [Cloudinary Console](https://console.cloudinary.com/)
2. Navigate to **Settings** → **Security**
3. Under **API Keys**, find the current key
4. Click **Regenerate API Secret**
5. Copy the new API secret
6. Update `CLOUDINARY_API_SECRET` in Render Environment variables

**Note:** Cloudinary API Key (public) does not need rotation - only the API Secret.

---

### Step 5: Rotate BGG API Key (If Required)

BGG API keys are managed by BoardGameGeek. To rotate:

1. Email BGG support at support@boardgamegeek.com
2. Request API key rotation
3. Provide your current API key identifier
4. Wait for new key (typically 1-3 business days)
5. Update `BGG_API_KEY` in Render Environment variables

**Note:** BGG API key rotation is optional and only needed if compromise is suspected.

---

### Step 6: Rotate Database Password (If Required)

**Warning:** Database password rotation requires brief downtime (~30 seconds).

1. Navigate to [Render Dashboard](https://dashboard.render.com/)
2. Select your **PostgreSQL** database
3. Go to **Settings** tab
4. Click **Reset Password**
5. Copy the new connection string
6. Update `DATABASE_URL` in your web service Environment variables
7. Redeploy the web service

---

### Step 7: Verify Deployment

```bash
# Check service health
curl https://mana-meeples-boardgame-list.onrender.com/api/health

# Expected response:
# {"status":"healthy","timestamp":"..."}

# Check database connectivity
curl https://mana-meeples-boardgame-list.onrender.com/api/health/db

# Expected response:
# {"status":"healthy","game_count":XXX}

# Test admin login (replace with new token)
curl -X POST https://mana-meeples-boardgame-list.onrender.com/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{"token": "YOUR_NEW_ADMIN_TOKEN"}'

# Expected response:
# {"success":true,"message":"Login successful","token":"jwt...","expires_in_days":7}
```

---

### Step 8: Invalidate Old Sessions

**Automatic Expiration:**
- JWT tokens expire after `JWT_EXPIRATION_DAYS` (default: 7 days)
- Redis sessions expire based on `SESSION_TIMEOUT_SECONDS` (default: 1 hour)

**Manual Invalidation (if needed):**
```bash
# If using local Redis for testing
redis-cli FLUSHDB

# Production: Sessions auto-expire, no action needed
```

---

### Step 9: Update Team & Documentation

1. Notify team members of completed rotation
2. Update password manager entries (if applicable)
3. Log rotation in security audit trail
4. Schedule next rotation (3 months from today)

---

## Troubleshooting

### Service Won't Start After Rotation

1. Check Render logs for error messages
2. Verify all environment variables are set correctly
3. Ensure no trailing spaces or newlines in secrets
4. Rollback to previous deployment if needed:
   - Render Dashboard → Deploys → Select working version → Redeploy

### Admin Login Fails

1. Verify `ADMIN_TOKEN` matches what you're using to login
2. Check for rate limiting (wait 5 minutes if blocked)
3. Verify `SESSION_SECRET` is set (required for JWT signing)

### Database Connection Fails

1. Verify `DATABASE_URL` format: `postgresql://user:pass@host:port/dbname`
2. Check PostgreSQL service status in Render Dashboard
3. Verify network connectivity between services

---

## Security Best Practices

1. **Never commit secrets to git** - Use Render Environment variables
2. **Use `.env.example` for templates** - Never copy real secrets to local files
3. **Rotate immediately if compromise suspected** - Don't wait for scheduled rotation
4. **Use unique secrets per environment** - Don't share secrets between staging/production
5. **Monitor for unauthorized access** - Check logs for failed login attempts

---

## Rotation Log Template

```markdown
## Secret Rotation - [DATE]

**Performed by:** [Name]
**Secrets rotated:**
- [ ] ADMIN_TOKEN
- [ ] SESSION_SECRET
- [ ] GITHUB_TOKEN
- [ ] CLOUDINARY_API_SECRET
- [ ] BGG_API_KEY (if needed)
- [ ] DATABASE_URL (if needed)
- [ ] REDIS_URL (if needed)

**Verification:**
- [ ] Health check passed
- [ ] Admin login works
- [ ] API endpoints functional
- [ ] Frontend loads correctly

**Next rotation due:** [DATE + 3 months]
```
