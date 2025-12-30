# Auto-Refresh System for Mobile Layouts

## Problem
Mobile browsers aggressively cache static assets (JavaScript, CSS), causing users to see old layouts even after new deployments. This is especially problematic for mobile users who may not know to clear their cache.

## Solution
Implemented a comprehensive auto-refresh system that:
1. Detects new deployments automatically
2. Notifies users when updates are available
3. Auto-refreshes on mobile devices after a countdown
4. Allows desktop users to manually refresh or dismiss

## How It Works

### 1. Build-Time Version Generation
**File**: `scripts/generate-version.js`

- Runs before every build via npm `prebuild` script
- Generates `public/version.json` with:
  - Git commit hash (unique identifier)
  - Build timestamp
  - Build date/time

```json
{
  "version": "a1b2c3d",
  "timestamp": 1234567890,
  "buildDate": "2025-12-30T12:00:00.000Z",
  "commitHash": "a1b2c3d"
}
```

### 2. Dynamic Service Worker Versioning
**File**: `public/service-worker.js`

- Fetches `version.json` on install
- Uses version as cache key: `mana-meeples-{version}-{type}`
- Automatically invalidates old caches when version changes
- New deployments trigger cache cleanup

### 3. Runtime Version Checking
**File**: `src/utils/versionCheck.js`

- Checks `/version.json` every 5 minutes
- Compares server version with cached version
- Triggers callbacks when update detected
- Includes manual refresh trigger function

### 4. User Notification Component
**File**: `src/components/UpdateNotification.jsx`

**Desktop Behavior**:
- Shows banner notification at top of screen
- User can click "Refresh" or dismiss
- No auto-refresh (user has control)

**Mobile Behavior**:
- Shows banner with 10-second countdown
- Auto-refreshes after countdown expires
- User can "Refresh Now" or "Cancel"
- Assumes mobile users want latest version ASAP

### 5. Cache Headers
**File**: `public/_headers`

Critical cache configuration:
```
# Never cache version.json
/version.json
  Cache-Control: no-cache, no-store, must-revalidate

# Cache JS/CSS forever (with hash busting)
/assets/*.js
  Cache-Control: public, max-age=31536000, immutable
```

## Integration

### App.jsx
```jsx
import UpdateNotification from './components/UpdateNotification';

export default function App() {
  return (
    <>
      <UpdateNotification />
      {/* Rest of app */}
    </>
  );
}
```

### Build Process
```json
{
  "scripts": {
    "prebuild": "node scripts/generate-version.js",
    "build": "vite build"
  }
}
```

## User Experience

### First Visit
1. User loads site
2. Service worker caches assets with version `v1.0.0`
3. Version check starts (checks every 5 minutes)

### New Deployment
1. New code deployed with version `v1.0.1`
2. User's browser checks `/version.json` (not cached)
3. Detects version mismatch (`v1.0.0` → `v1.0.1`)
4. Shows update notification:
   - **Mobile**: "Auto-refreshing in 10 seconds..."
   - **Desktop**: "Refresh to get the latest version"
5. On refresh:
   - Service worker installs new version
   - Old caches deleted automatically
   - Fresh layout loaded

## Configuration

### Change Check Interval
**File**: `src/utils/versionCheck.js`
```javascript
const CHECK_INTERVAL = 5 * 60 * 1000; // 5 minutes
```

### Change Auto-Refresh Countdown
**File**: `src/components/UpdateNotification.jsx`
```javascript
let secondsLeft = 10; // Auto-refresh countdown
```

### Disable Auto-Refresh on Mobile
**File**: `src/components/UpdateNotification.jsx`
```javascript
// Remove this block:
if (isMobileDevice()) {
  startAutoRefreshCountdown();
}
```

## Testing

### Test New Version Detection
1. Build the app: `npm run build`
2. Note the version in `public/version.json`
3. Make a code change
4. Rebuild: `npm run build`
5. Serve both builds on different ports
6. Load old version, wait 5 minutes (or trigger manually)
7. Should show update notification

### Manual Version Check
```javascript
import { checkNow } from './utils/versionCheck';

// Trigger immediate check
checkNow().then(hasUpdate => {
  console.log('Update available:', hasUpdate);
});
```

### Force Refresh
```javascript
import { reloadApp } from './utils/versionCheck';

// Force app refresh
reloadApp();
```

## Troubleshooting

### Users Still See Old Layout
1. Check that `prebuild` script ran during deployment
2. Verify `version.json` exists in deployed build
3. Check browser console for service worker errors
4. Verify `_headers` file is being respected by host

### Version Check Not Working
1. Check browser console for CORS errors
2. Verify `/version.json` is accessible (not 404)
3. Check that version.json has `Cache-Control: no-cache`
4. Ensure version check started (look for console logs)

### Service Worker Not Updating
1. Unregister old service worker in DevTools
2. Hard refresh (Cmd/Ctrl + Shift + R)
3. Clear cache and hard reload
4. Check service worker console for errors

## Production Deployment

### Render Configuration
The build command in `render.yaml` automatically runs `prebuild`:
```yaml
buildCommand: cd frontend && npm install && npm run build
```

### Verification After Deploy
1. Visit: `https://library.manaandmeeples.co.nz/version.json`
2. Should show latest commit hash
3. Should NOT be cached (check response headers)
4. Console should log: `[Service Worker] Using cache version: {hash}`

## Benefits

✅ **Mobile users always get latest layout** - Auto-refresh ensures they're never stuck on old version

✅ **No manual cache clearing** - Service worker handles cache invalidation automatically

✅ **Graceful desktop experience** - Users maintain control with manual refresh option

✅ **Build-time automation** - No manual version bumping needed

✅ **Git-based versioning** - Commit hash ensures unique version per deployment

✅ **Minimal network overhead** - Only checks small JSON file every 5 minutes

✅ **Works across instances** - Version stored in static file, not backend database

## Future Enhancements

- [ ] Show changelog/release notes in notification
- [ ] Track version update metrics (how many users update)
- [ ] A/B test auto-refresh countdown duration
- [ ] Add visual indicator of version in footer
- [ ] Implement version rollback detection
- [ ] Add WebSocket for instant update notifications (no 5-minute delay)
