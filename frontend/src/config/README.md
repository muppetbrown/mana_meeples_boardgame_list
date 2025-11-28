# Configuration

Centralized configuration for the frontend application.

## Files

### `api.js`

Single source of truth for API configuration and related utilities.

**Exports:**
- `API_BASE` - Resolved API base URL
- `imageProxyUrl(url)` - Helper for proxying and optimizing images

**API Base URL Resolution:**

The API base URL is resolved using multiple fallback strategies (in priority order):

1. **Runtime window variable** - `window.__API_BASE__`
   - For dynamic configuration at runtime
   - Set in index.html or by server

2. **Meta tag** - `<meta name="api-base" content="...">`
   - For static sites with injected configuration
   - Allows different configs per deployment

3. **Build-time environment variable** - `REACT_APP_API_BASE`
   - Set during build via `.env` files or build system
   - Baked into the bundle at compile time

4. **Development fallback** - `http://127.0.0.1:8000`
   - Used when no configuration is provided
   - Assumes local backend during development

**Usage:**

```jsx
import { API_BASE, imageProxyUrl } from '../config/api';

// Use API_BASE directly if needed
console.log(`Connecting to: ${API_BASE}`);

// Optimize and proxy images
const optimizedUrl = imageProxyUrl(game.thumbnail_url);
```

**Image Proxy Optimization:**

The `imageProxyUrl` function enhances BoardGameGeek images by:
- Attempting to upgrade to highest resolution (`_original`)
- Falling back gracefully if higher resolution unavailable
- Proxying through backend for caching and security

Priority order for BGG images:
1. `_original` - Highest quality
2. `_d` - Detail size
3. `_md` - Medium detail
4. `_mt` - Medium thumbnail
5. `_t` - Thumbnail (smallest)

## Environment Variables

Set these in your deployment environment or `.env` files:

```bash
# Production API
REACT_APP_API_BASE=https://mana-meeples-boardgame-list.onrender.com

# Staging API
REACT_APP_API_BASE=https://staging-api.example.com

# Local development (automatic fallback)
# REACT_APP_API_BASE=http://127.0.0.1:8000
```

## Dynamic Configuration

For runtime configuration, add to your `public/index.html`:

```html
<!-- Method 1: Window variable -->
<script>
  window.__API_BASE__ = 'https://api.example.com';
</script>

<!-- Method 2: Meta tag -->
<meta name="api-base" content="https://api.example.com">
```

## Adding New Configuration

When adding new configuration values:

1. Add to this `api.js` file (or create new config file if unrelated to API)
2. Use the same resolution strategy pattern
3. Document in this README
4. Add to `.env.example` for reference

## Related Files

- `../api/client.js` - Uses `API_BASE` for axios instance
- `../../public/index.html` - Can set runtime configuration
- `../../.env.example` - Example environment variables
