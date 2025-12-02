# APPLY THIS FIX TO bgg_service.py

## Location
File: `backend/bgg_service.py`
Line: ~108 (after the httpx retry loop, before XML parsing)

## Current Code (BROKEN):
```python
            except httpx.HTTPError as e:
                logger.error(f"HTTP error fetching BGG data for game {bgg_id}: {e}")
                if attempt == retries - 1:
                    raise BGGServiceError(f"Failed to fetch game {bgg_id}: {e}")
                delay = (2 ** attempt) + (attempt * 0.5)
                await asyncio.sleep(delay)

    # Parse XML response with comprehensive error handling
    try:
        logger.info(f"Attempting to parse XML response for game {bgg_id}...")
```

## Fixed Code (ADD THE CHECK):
```python
            except httpx.HTTPError as e:
                logger.error(f"HTTP error fetching BGG data for game {bgg_id}: {e}")
                if attempt == retries - 1:
                    raise BGGServiceError(f"Failed to fetch game {bgg_id}: {e}")
                delay = (2 ** attempt) + (attempt * 0.5)
                await asyncio.sleep(delay)

    # CRITICAL FIX: Check if we got a valid response after all retries
    if response is None or response_text is None:
        logger.error(f"No valid response received for game {bgg_id} after {retries} retry attempts")
        raise BGGServiceError(
            f"BGG is rate limiting requests (HTTP 401). "
            f"All {retries} retry attempts failed. "
            f"Please wait 10-15 minutes before trying again."
        )

    # Parse XML response with comprehensive error handling
    try:
        logger.info(f"Attempting to parse XML response for game {bgg_id}...")
```

## What This Fixes

**Before Fix:**
- Gets 401 three times
- `response_text` stays `None`
- Tries to parse `None`
- Crashes with confusing error

**After Fix:**
- Gets 401 three times
- Checks if `response_text` is `None`
- Raises clear error: "BGG is rate limiting requests"
- User knows to wait and try again

## Additional Improvements (Optional)

### Increase Retries
In `backend/config.py`, change:
```python
HTTP_RETRIES = 5  # From 3 to 5
```

### Longer Delays
In line ~43 of `bgg_service.py`, change:
```python
delay = (3 ** attempt) + (attempt * 1.0)  # Longer exponential backoff
```

This will wait: 3s, 10s, 28s instead of 1s, 2.5s, 5s
