# Debugging BGG Import for ID 393892

## Status

✅ Game EXISTS on BGG website: https://boardgamegeek.com/boardgame/393892
❌ Import still failing with "Failed to parse BGG response"

This means the issue is in the XML API response or parsing, not that the game doesn't exist.

---

## Method 1: Add Debug Endpoint (RECOMMENDED)

### Step 1: Add Debug Endpoint to Your Code

Open `backend/api/routers/admin.py` and add this at the END of the file (before any final comments):

```python
from datetime import datetime

@router.get("/debug/bgg-raw/{bgg_id}")
async def debug_bgg_raw_response(
    bgg_id: int,
    _: None = Depends(require_admin_auth)
):
    """Debug endpoint to see what BGG XML API returns"""
    import httpx
    from bgg_service import fetch_bgg_thing, BGGServiceError
    
    result = {
        "bgg_id": bgg_id,
        "timestamp": datetime.now().isoformat(),
    }
    
    # Test 1: Raw HTTP request
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://boardgamegeek.com/xmlapi2/thing",
                params={"id": str(bgg_id), "stats": "1"}
            )
            
            result["http_status"] = response.status_code
            result["xml_length"] = len(response.text)
            result["xml_full"] = response.text
            
    except Exception as e:
        result["http_error"] = {
            "type": type(e).__name__,
            "message": str(e)
        }
        return result
    
    # Test 2: Try to parse
    try:
        parsed_data = await fetch_bgg_thing(bgg_id)
        result["parse_success"] = True
        result["parsed_data"] = parsed_data
    except Exception as e:
        result["parse_success"] = False
        result["parse_error"] = {
            "type": type(e).__name__,
            "message": str(e)
        }
    
    return result
```

### Step 2: Deploy and Test

1. Commit and push to trigger Render deployment
2. Once deployed, call the debug endpoint:

```bash
curl "https://your-api.onrender.com/api/admin/debug/bgg-raw/393892" \
  -H "X-Admin-Token: your-token" \
  | jq . > bgg_debug_response.json
```

3. Look at `bgg_debug_response.json` to see:
   - What HTTP status BGG returned
   - The actual XML content
   - Where parsing failed (if it did)

---

## Method 2: Check Render Logs (QUICK)

### Step 1: Try the Import Again

Go to your admin interface and try importing BGG ID 393892 again.

### Step 2: Check Render Logs Immediately

In Render dashboard:
1. Go to your backend service
2. Click "Logs" tab
3. Look for the error - it should show:
   - "Fetching BGG data for game 393892 (attempt 1)"
   - Any retry attempts
   - **The full stack trace showing which line failed**

### What to Look For:

The logs will show something like:
```
ERROR - Failed to import BGG game 393892: <actual error message>
```

Share that FULL error message with me.

---

## Method 3: Check BGG API Response Manually

You can also test what BGG returns by running this on YOUR computer (should work since you can access BGG):

```bash
curl "https://boardgamegeek.com/xmlapi2/thing?id=393892&stats=1" > bgg_393892.xml
```

Then:
1. Open `bgg_393892.xml` in a text editor
2. Check if:
   - The `<items>` tag has content
   - There's an `<item>` tag inside
   - The item has `type="boardgame"` (not expansion)
   - There's a `<name type="primary">` tag with a value

---

## Most Likely Scenarios

Based on "game exists but import fails":

### Scenario A: BGG Rate Limiting
BGG XML API might be blocking your server's IP temporarily.

**Signs:**
- HTTP 401 or 503 status
- Retries all failing
- Works fine after waiting

**Solution:** Wait 10-15 minutes and try again

### Scenario B: Incomplete Game Data
The game might be new/pre-order with missing required fields.

**Signs:**
- HTTP 200 but missing `<name>` or other critical fields
- Parse error about missing title

**Solution:** Wait for BGG to complete the listing

### Scenario C: Special Characters in Data
Game title or description might have XML characters causing parse issues.

**Signs:**
- XML parse error
- Error mentions "malformed" or "encoding"

**Solution:** Need to improve XML parsing (I can help if this is the case)

---

## Next Steps

1. **Quick check:** Look at Render logs RIGHT NOW for the last failed import
2. **Full debug:** Add the debug endpoint and test
3. **Share results:** Tell me what you find in either the logs or debug response

Once I see the actual error or XML response, I can give you the exact fix!
