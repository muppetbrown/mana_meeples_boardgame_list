# Image Loading Fix Summary - Session History

**Date:** January 2, 2026
**Branch:** `claude/fix-image-loading-uAkGp` (merged to main)
**Status:** Code merged, frontend deployment pending verification

---

## Problems Identified

### 1. BGG API Rate Limiting (429 Errors)
**Symptom:** Re-import endpoint returning "Too Many Requests"
**Root Cause:** All games queued simultaneously, overwhelming BGG API

### 2. Cloudinary Pre-generation 404s
**Symptom:** Images showing 404 errors from Cloudinary
**Root Cause:** System cached Cloudinary URLs before images were uploaded

### 3. BGG URL Format Mismatch
**Symptom:** Backend using old format, BGG switched to new format
**Root Cause:** URL transformation used `_d.` but BGG now uses `__d/`

### 4. BGG Blocking `__original` Downloads
**Symptom:** 400 Bad Request errors from BGG
**Example:** `https://cf.geekdo-images.com/HASH__original/pic123.png`
**Root Cause:** BGG now blocks `__original` size downloads

### 5. Malformed URLs in Database
**Symptom:** URLs with embedded transformation parameters
**Example:** `https://cf.geekdo-images.com/HASH__original/img/JUNK=/0x0/filters:format(png)/pic123.png`
**Root Cause:** Historical data corruption during imports

### 6. Frontend srcset Not Transforming URLs
**Symptom:** `generateSrcSet()` sending raw `__original` URLs to backend
**Root Cause:** Function didn't transform URLs before encoding

---

## Changes Made

### Backend Changes

#### File: `backend/main.py`
**Change:** Added rate limiting to `_reimport_single_game()`
```python
async def _reimport_single_game(game_id: int, bgg_id: int, delay_seconds: float = 0):
    # Add delay to avoid overwhelming BGG API
    if delay_seconds > 0:
        await asyncio.sleep(delay_seconds)
```
**Added import:** `import asyncio`
**Commit:** `e66cfdc` + `5365576`

#### File: `backend/api/routers/bulk.py`
**Change:** Staggered delays in re-import endpoint
```python
DELAY_BETWEEN_REQUESTS = 2.0  # 2 seconds = ~30 games/minute

for index, game in enumerate(games):
    delay = index * DELAY_BETWEEN_REQUESTS
    background_tasks.add_task(_reimport_single_game, game.id, game.bgg_id, delay)
```
**Commit:** `e66cfdc`

#### File: `backend/services/game_service.py`
**Change 1:** Disabled Cloudinary URL pre-generation
```python
# DISABLED: Pre-generating Cloudinary URLs causes 404s because images aren't uploaded yet
# The image proxy endpoint will handle Cloudinary upload on first request
# self._pre_generate_cloudinary_url(game)
```
**Commit:** `e66cfdc`

**Change 2:** Fixed BGG URL format handling
```python
# BGG uses NEW format with double underscores in path: __SIZE/
quality_map_new = {
    'original': '__original/',
    'detail': '__d/',
    # ...
}

# Try new format first (most common)
if '__' in source_url:
    source_url = re.sub(r'__[a-z]+/', optimal_suffix_new, source_url)
```
**Commit:** `e66cfdc`

#### File: `backend/api/routers/public.py`
**Change 1:** Enhanced malformed URL detection
```python
# Check for common malformed patterns: /img/, /fit-in/, /filters:, /c_limit, /0x0/
if '/img/' in url or '/fit-in/' in url or '/filters:' in url or '/c_limit' in url or '/0x0/' in url:
    # Clean the URL by removing transformation parameters
```
**Commit:** `ffb42ff`

**Change 2:** Safety transformation for `__original`
```python
# Transform __original to __d before downloading
if 'cf.geekdo-images.com' in url and '__original/' in url:
    logger.warning(f"Transforming blocked __original URL to __d: {url[:100]}...")
    url = re.sub(r'__original/', '__d/', url)
```
**Commit:** `ffb42ff`

**Change 3:** Pass width/height to Cloudinary
```python
cloudinary_url = cloudinary_service.get_image_url(
    url,
    width=width,  # From query params
    height=height  # From query params
)
```
**Commit:** `5c3427c`

### Frontend Changes

#### File: `frontend/src/config/api.js`
**Change:** Transform URLs in `generateSrcSet()` before encoding
```javascript
export function generateSrcSet(url) {
  // IMPORTANT: Transform __original to __d BEFORE generating srcset
  const baseUrl = getBGGImageVariant(url, 'detail');

  return sizes.map(({ width, height }) => {
      const proxyUrl = `${API_BASE}/api/public/image-proxy?url=${encodeURIComponent(baseUrl)}&width=${width}&height=${height}`;
      return `${proxyUrl} ${width}w`;
    })
    .join(', ');
}
```
**Commit:** `ffb42ff`

### Supporting Files

#### File: `backend/scripts/clear_cloudinary_cache.py`
**Purpose:** Optional script to clear cached `cloudinary_url` values from database
**Usage:** `python backend/scripts/clear_cloudinary_cache.py`
**Commit:** `26772d3`

---

## Commits Summary

All commits merged to main via PRs #340-343:

1. **`e66cfdc`** - Rate limiting + URL format handling + disable pre-generation
2. **`5365576`** - Missing asyncio import
3. **`26772d3`** - Cleanup script for cached URLs
4. **`5c3427c`** - Responsive image sizing (width/height params)
5. **`ffb42ff`** - Transform `__original` URLs + detect `/img/` patterns (CRITICAL FRONTEND FIX)

---

## Image Loading Flow (After Fixes)

### Database (Unchanged)
```
game.image = "https://cf.geekdo-images.com/HASH__original/pic123.png"
```
**Note:** Database URLs stay as-is from BGG. Transformation happens in frontend.

### Frontend Transformation
1. `GameImage.jsx` calls `imageProxyUrl(url)` and `generateSrcSet(url)`
2. Both functions call `getBGGImageVariant(url, 'detail')`
3. Regex transforms: `__original/` → `__d/`
4. Encoded URL sent to backend

### Backend Processing
1. Receives already-transformed URL with `__d`
2. Safety check transforms any remaining `__original`
3. Cleans malformed URLs with `/img/` patterns
4. Downloads from BGG (now works, no 400 error)
5. Uploads to Cloudinary
6. Returns 302 redirect to Cloudinary URL

### Browser Rendering
1. Loads optimized image from Cloudinary CDN
2. Responsive srcset provides different sizes for mobile/desktop
3. Subsequent loads served from Cloudinary cache (fast)

---

## Current Status

### ✅ Completed
- All code changes committed and merged to main
- Backend auto-deployed by Render
- Branch `claude/fix-image-loading-uAkGp` fully merged

### ❓ Needs Verification
- **Frontend deployment status** - Check if Render rebuilt frontend after `ffb42ff` merge
- **Image loading in production** - Visit `https://library.manaandmeeples.co.nz` and check for errors
- **Re-import functionality** - Test bulk re-import without rate limit errors

---

## Testing Checklist

### Frontend Deployment Check
```javascript
// In browser console on live site:
// Check if new code is deployed (should include getBGGImageVariant in srcset)
fetch('https://library.manaandmeeples.co.nz/assets/index-*.js')
  .then(r => r.text())
  .then(code => console.log(code.includes('getBGGImageVariant') ? '✅ New code' : '❌ Old code'))
```

### Image Loading Test
1. Open `https://library.manaandmeeples.co.nz`
2. Hard refresh (Ctrl+Shift+R)
3. Open browser console (F12)
4. Look for errors:
   - ❌ Should NOT see: "400 Bad Request" errors
   - ❌ Should NOT see: `__original` in network tab
   - ✅ Should see: `__d` URLs in network requests
   - ✅ Should see: Images loading from Cloudinary

### Backend Logs Check (Render)
Look for these patterns in logs:
- ✅ `"Transforming blocked __original URL to __d"` (safety check working)
- ✅ `"MALFORMED URL DETECTED"` + `"URL cleaned successfully"` (for corrupted URLs)
- ✅ `"✓ Cloudinary upload successful"` (uploads working)
- ❌ Should NOT see: "400 Bad Request" errors
- ❌ Should NOT see: "429 Too Many Requests" errors

### Re-import Test
1. Go to admin interface
2. Click "Re-import All Games"
3. Check response message includes estimated time
4. Monitor Render logs for steady progress (~30 games/minute)
5. Verify no rate limit errors

---

## Example Test Case: Star Wars Battle of Hoth

### Database URLs
```
thumbnail_url: https://cf.geekdo-images.com/C-nkGn4bUYSSJjf0J9uqyg__small/img/uWjHdIzNfPBv89XZ9MdORne5_Lk=/fit-in/200x150/filters:strip_icc()/pic8833062.png

image: https://cf.geekdo-images.com/C-nkGn4bUYSSJjf0J9uqyg__original/img/B3lhxKVRanaQq8heM93VTWuC-tQ=/0x0/filters:format(png)/pic8833062.png
```

### Expected Transformations

**Frontend transforms to:**
```
https://cf.geekdo-images.com/C-nkGn4bUYSSJjf0J9uqyg__d/pic8833062.png
```

**Backend cleans malformed parts:**
- Detects `/img/` pattern ✓
- Extracts `pic8833062.png` ✓
- Extracts base `C-nkGn4bUYSSJjf0J9uqyg__d` (already transformed by frontend) ✓
- Reconstructs clean URL ✓

**Final URL sent to BGG:**
```
https://cf.geekdo-images.com/C-nkGn4bUYSSJjf0J9uqyg__d/pic8833062.png
```

---

## If Still Seeing Errors

### Scenario 1: 400 Bad Request with `__original`
**Diagnosis:** Frontend not deployed with new code
**Fix:** Manually trigger frontend rebuild in Render dashboard

### Scenario 2: Malformed URL errors
**Diagnosis:** Backend not catching all patterns
**Next Step:** Check specific URL pattern in error logs and add to detection

### Scenario 3: Cloudinary 404s
**Diagnosis:** Upload failing silently
**Next Step:** Check Cloudinary credentials and quota in Render env vars

### Scenario 4: Rate limiting on re-import
**Diagnosis:** Delays not being applied
**Next Step:** Check backend logs for asyncio.sleep timing

---

## Environment Variables to Verify

### Backend (Render)
```
CLOUDINARY_CLOUD_NAME=<your-cloud-name>
CLOUDINARY_API_KEY=<your-api-key>
CLOUDINARY_API_SECRET=<your-api-secret>
PUBLIC_BASE_URL=https://mana-meeples-boardgame-list-opgf.onrender.com
```

### Frontend (Render)
```
VITE_API_BASE=https://mana-meeples-boardgame-list-opgf.onrender.com
```

---

## Key Files Reference

### Backend
- `backend/main.py` - Background task with rate limiting
- `backend/api/routers/bulk.py` - Re-import endpoint
- `backend/api/routers/public.py` - Image proxy with URL cleaning
- `backend/services/game_service.py` - BGG URL format handling
- `backend/services/cloudinary_service.py` - Cloudinary upload

### Frontend
- `frontend/src/config/api.js` - URL transformation logic
- `frontend/src/components/GameImage.jsx` - Image component using transformations

### Scripts
- `backend/scripts/clear_cloudinary_cache.py` - Optional cleanup

---

## Next Session Starting Points

1. **Check frontend deployment status** in Render dashboard
2. **Test one specific game** (e.g., Star Wars) and trace URL through network tab
3. **Review Render logs** for specific error patterns
4. **Verify env vars** are set correctly in Render
5. **Consider database cleanup** if many malformed URLs exist

---

## Questions for Next Session

- Is the frontend service showing a recent deployment after commit `ffb42ff`?
- Are images loading on the live site after hard refresh?
- What specific error messages appear in Render backend logs?
- What URLs appear in browser network tab when images fail?
- Has the re-import been tested with the new rate limiting?
