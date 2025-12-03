# Reverting to Old Working Code

## What to Revert

Based on your logs showing the extensive debug logging, it looks like someone added debugging code. Here's what needs to be reverted in `backend/bgg_service.py`:

---

## Changes to Make in `bgg_service.py`

### 1. Remove Special Debug Logging (Lines ~30-50)

**Find and REMOVE this entire block:**
```python
# DEBUG: Special logging for game 314421
if bgg_id == 314421:
    logger.info(f"=== SPECIAL DEBUG FOR BGG ID 314421 ===")
    logger.info(f"Request URL: {url}")
    logger.info(f"Request params: {params}")
    # ... more debug logging
    logger.info(f"=== END SPECIAL DEBUG FOR BGG ID 314421 ===")
```

### 2. Remove Verbose Response Logging (Lines ~50-100)

**Find and REMOVE these lines:**
```python
# COMPREHENSIVE RESPONSE DEBUGGING
logger.info(f"BGG response status: {response.status_code}")
logger.info(f"BGG response content-type: {content_type}")
logger.info(f"BGG response length: {len(response_text)} chars")
logger.info(f"BGG response first 200 chars: {repr(response_text[:200])}")
logger.info(f"BGG response last 200 chars: {repr(response_text[-200:])}")
```

### 3. Simplify to Basic Error Handling

**Keep it simple like this:**

```python
async def fetch_bgg_thing(bgg_id: int, retries: int = HTTP_RETRIES) -> Dict:
    """
    Fetch game data from BoardGameGeek XML API.
    """
    url = "https://boardgamegeek.com/xmlapi2/thing"
    params = {"id": str(bgg_id), "stats": "1"}
    
    response = None
    
    async with httpx.AsyncClient(timeout=float(HTTP_TIMEOUT)) as client:
        for attempt in range(retries):
            try:
                logger.info(f"Fetching BGG data for game {bgg_id} (attempt {attempt + 1})")
                response = await client.get(url, params=params)
                
                # Handle BGG's queue system and rate limiting
                if response.status_code in (202, 401, 500, 503):
                    delay = (2 ** attempt) + (attempt * 0.5)
                    logger.warning(f"BGG returned {response.status_code}, retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                    continue
                
                if response.status_code == 400:
                    raise BGGServiceError(f"Invalid BGG ID: {bgg_id}")
                
                response.raise_for_status()
                break
                
            except httpx.TimeoutException:
                if attempt == retries - 1:
                    raise BGGServiceError(f"Timeout fetching game {bgg_id}")
                await asyncio.sleep((2 ** attempt) + (attempt * 0.5))
                
            except httpx.HTTPError as e:
                if attempt == retries - 1:
                    raise BGGServiceError(f"Failed to fetch game {bgg_id}: {e}")
                await asyncio.sleep((2 ** attempt) + (attempt * 0.5))
    
    # Check if we got a valid response
    if response is None:
        raise BGGServiceError(
            f"Failed to get response from BGG after {retries} attempts. "
            f"BGG may be rate limiting or requiring authentication."
        )
    
    # Parse XML response
    try:
        root = ET.fromstring(response.text)
        _strip_namespace(root)
        
        item = root.find("item")
        if item is None:
            raise BGGServiceError(f"No game data found for BGG ID {bgg_id}")
        
        return _extract_comprehensive_game_data(item, bgg_id)
        
    except ET.ParseError as e:
        logger.error(f"XML parse error for game {bgg_id}: {e}")
        raise BGGServiceError(f"Failed to parse BGG response for game {bgg_id}")
```

---

## OR Use Git to Revert

If you have git commits, you can revert to a working version:

```bash
# See your commit history
git log --oneline -20

# Find the commit hash of the working version (before changes)
git log --oneline --grep="debug" -i

# Revert to that commit for just bgg_service.py
git checkout <commit-hash> -- backend/bgg_service.py

# Or create a new branch from the working commit
git checkout -b working-version <commit-hash>
```

---

## Quick Way: Replace the Entire File

If you have a backup or can find the old working version, just replace the entire `backend/bgg_service.py` file.

The key is to:
1. **Remove all the extensive debug logging**
2. **Keep the simple retry logic**
3. **Keep the basic error messages**

---

## After Reverting

The BGG authentication issue will still exist (401 errors), but at least your logs won't be cluttered with debug messages.

**For the 401 issue, you need to:**
1. Contact BGG for API access
2. Or switch to XML API v1 (see `BGG_AUTH_REQUIRED.md`)
3. Or wait for BGG to restore open access

---

## Alternative: Keep New Code But Remove Debug

If you want to keep improvements but remove debug spam, just search for and delete:
- Any line with `logger.info(f"=== SPECIAL DEBUG`
- Any line with `logger.info(f"Raw response`
- Any line with `logger.info(f"COMPREHENSIVE`

Keep only the essential logging:
- `logger.info(f"Fetching BGG data...`
- `logger.warning(f"BGG returned 401...`
- `logger.error(f"Failed to...`
