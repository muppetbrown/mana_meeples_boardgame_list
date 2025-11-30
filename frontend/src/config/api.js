// frontend/src/config/api.js
/**
 * Centralized API configuration
 * Single source of truth for API base URL and related utilities
 */

/**
 * Resolves the API base URL using multiple fallback strategies
 * Priority order:
 * 1. Runtime window variable (for dynamic configuration)
 * 2. Meta tag in index.html (for static site with injected config)
 * 3. Build-time environment variable (VITE_API_BASE)
 * 4. Development fallback (localhost)
 */
function resolveApiBase() {
  // 1. Runtime window variable
  try {
    if (typeof window !== "undefined" && window.__API_BASE__) {
      return String(window.__API_BASE__);
    }
  } catch {
    // Ignore errors in SSR or restricted environments
  }

  // 2. Meta tag in index.html
  const metaTag = document.querySelector('meta[name="api-base"]');
  if (metaTag && metaTag.content) {
    return metaTag.content;
  }

  // 3. Build-time environment variable
  if (import.meta.env.VITE_API_BASE) {
    return import.meta.env.VITE_API_BASE;
  }

  // 4. Development fallback
  return "http://127.0.0.1:8000";
}

/**
 * API base URL (without trailing slash)
 * @type {string}
 */
export const API_BASE = resolveApiBase().replace(/\/+$/, "");

/**
 * Enhanced image proxy URL with BGG image quality optimization
 *
 * For BoardGameGeek images, attempts to get the highest resolution available.
 * Priority order: _original > _d (detail) > _md (medium) > _mt (medium thumb) > _t (thumbnail)
 *
 * @param {string} url - The original image URL
 * @returns {string|null} - Proxied image URL or null if no URL provided
 */
export function imageProxyUrl(url) {
  if (!url) return null;

  // For BGG images, optimize for best quality
  if (url.includes('cf.geekdo-images.com')) {
    let optimizedUrl = url;

    // Try to upgrade to original size (best quality)
    if (!optimizedUrl.includes('_original.')) {
      optimizedUrl = optimizedUrl
        .replace('_t.', '_original.')      // from thumbnail
        .replace('_mt.', '_original.')     // from medium thumb
        .replace('_md.', '_original.')     // from medium detail
        .replace('_d.', '_original.');     // from detail
    }

    // Backend will handle fallback chain if _original doesn't exist
    return `${API_BASE}/api/public/image-proxy?url=${encodeURIComponent(optimizedUrl)}`;
  }

  // For non-BGG images, proxy as-is
  return `${API_BASE}/api/public/image-proxy?url=${encodeURIComponent(url)}`;
}

/**
 * Log the configured API base on load (helps with debugging)
 */
if (import.meta.env.DEV) {
  console.log(`[API Config] Using base: ${API_BASE}`);
}

/**
 * Validate configuration
 */
if (!API_BASE) {
  console.error('[API Config] API_BASE not configured! Using fallback.');
}
