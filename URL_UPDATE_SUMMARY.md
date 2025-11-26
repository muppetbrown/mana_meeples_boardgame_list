# Backend URL Update - Summary

## Issue
The backend service URL changed from:
- **Old**: `https://mana-meeples-boardgame-list.onrender.com`
- **New**: `https://mana-meeples-boardgame-list-opgf.onrender.com`

This caused CORS errors and 503 errors because the frontend was trying to access the old, non-existent URL.

## Files Updated

### 1. render.yaml
Updated both environment variables:
- `PUBLIC_BASE_URL`: Now points to `https://mana-meeples-boardgame-list-opgf.onrender.com`
- `REACT_APP_API_BASE`: Now points to `https://mana-meeples-boardgame-list-opgf.onrender.com`

### 2. .env.example
Updated the example PUBLIC_BASE_URL to the new backend URL.

### 3. frontend/src/config.js
Updated the API_BASE constant to point to the new backend URL.

## Next Steps

1. **Commit and push these changes**:
   ```bash
   git add .
   git commit -m "Update backend URL to mana-meeples-boardgame-list-opgf.onrender.com"
   git push
   ```

2. **Render will automatically redeploy** your frontend service with the new API_BASE URL.

3. **Test the site** once deployed:
   - Visit https://library.manaandmeeples.co.nz
   - Check that games load properly
   - Verify no CORS errors in browser console (F12)

## Why This Happened

Render services get a new URL when:
- Service is deleted and recreated
- Service name changes
- Service is migrated to a new infrastructure

The `-opgf` suffix is Render's way of creating a unique identifier for your service.

## Alternative: Use a Custom Domain

To avoid this issue in the future, consider setting up a custom domain for your backend (e.g., `api.manaandmeeples.co.nz`) in Render's dashboard. This way, the URL won't change even if the service is recreated.
