# BGG API Authentication Required - Solution

## Critical Finding

Your logs show BGG is requiring authentication:
```
'www-authenticate': 'Bearer realm="xml api"'
```

This is NOT simple rate limiting - **BGG requires a Bearer token for API v2**.

## Immediate Workaround: Try XML API v1

BGG's older API might still work without authentication.

### Update `bgg_service.py` Line ~25:

**Current:**
```python
url = "https://boardgamegeek.com/xmlapi2/thing"
```

**Change to:**
```python
url = "https://boardgamegeek.com/xmlapi/boardgame"
```

**And update params (line ~26):**
```python
params = {"id": str(bgg_id)}  # Remove stats=1, not supported in v1
```

### Important: XML API v1 Differences

The v1 API has a different XML structure:
- No `stats` parameter
- Different XML element names
- Less data available

You'll need to update your parsing logic in `_extract_comprehensive_game_data()`.

## Long-term Solution: Get BGG API Access

### Step 1: Check BGG API Requirements

Visit: https://boardgamegeek.com/wiki/page/BGG_XML_API2

### Step 2: Request API Access

BGG may require:
- Account registration
- API key request
- Approval process
- Rate limit agreements

### Step 3: Add Bearer Token to Requests

Once you have a token, update your code (line ~35):

```python
headers = {
    "Authorization": f"Bearer {BGG_API_TOKEN}"
}

response = await client.get(url, params=params, headers=headers)
```

Add to `config.py`:
```python
BGG_API_TOKEN = os.getenv("BGG_API_TOKEN", "")
```

## Alternative: Use BGG's Geek API (if available)

BGG may have a different API endpoint that doesn't require auth. Check their documentation.

## Why This Happened

BGG likely:
- Tightened API access due to abuse
- Requiring authentication for all API v2 requests
- Rate limiting by IP + requiring tokens

## Test Without Code Changes

Try this from your server:

```bash
# Test v1 API (might work)
curl "https://boardgamegeek.com/xmlapi/boardgame/174430"

# Test v2 API (requires token)
curl "https://boardgamegeek.com/xmlapi2/thing?id=174430&stats=1"
```

If v1 works, you can switch to it temporarily.

## Recommendation

1. **Try XML API v1** as a quick workaround
2. **Request official BGG API access** for long-term
3. **Cache results** to minimize API calls
4. **Add rate limiting** to your admin interface

The 401 with `www-authenticate` header is definitive - this is an auth requirement, not rate limiting.
