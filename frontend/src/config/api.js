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
 * 4. Production fallback (if window.location suggests production)
 * 5. Development fallback (localhost)
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

  // 3. Build-time environment variable (check for both undefined and empty string)
  const viteApiBase = import.meta.env.VITE_API_BASE;
  if (viteApiBase && viteApiBase.trim() !== "") {
    console.log('[API Config] Using VITE_API_BASE:', viteApiBase);
    return viteApiBase;
  }

  // 4. Production fallback - if running on Render's domain
  if (typeof window !== "undefined" &&
      (window.location.hostname.includes('onrender.com') ||
       window.location.hostname.includes('manaandmeeples.co.nz'))) {
    const productionUrl = "https://mana-meeples-boardgame-list-opgf.onrender.com";
    console.warn('[API Config] VITE_API_BASE not set, using production fallback:', productionUrl);
    return productionUrl;
  }

  // 5. Development fallback
  console.log('[API Config] Using development fallback: http://127.0.0.1:8000');
  return "http://127.0.0.1:8000";
}

/**
 * API base URL (without trailing slash)
 * @type {string}
 */
export const API_BASE = resolveApiBase().replace(/\/+$/, "");

/**
 * API version to use
 * Set to null or empty string to use legacy (unversioned) endpoints
 * @type {string}
 */
export const API_VERSION = null;

/**
 * Get versioned API endpoint URL
 * @param {string} path - API path (with or without leading slash)
 * @returns {string} - Full versioned API URL
 * @example
 * getApiUrl('/public/games') -> 'http://api.example.com/api/v1/public/games'
 * getApiUrl('public/games') -> 'http://api.example.com/api/v1/public/games'
 */
export function getApiUrl(path) {
  // Remove leading slash if present
  const cleanPath = path.replace(/^\/+/, "");

  // If using versioned API
  if (API_VERSION) {
    return `${API_BASE}/api/${API_VERSION}/${cleanPath}`;
  }

  // Legacy (unversioned) API
  return `${API_BASE}/api/${cleanPath}`;
}

/**
 * Generate BGG image URL at specific size
 *
 * @param {string} url - The original image URL
 * @param {string} size - Size variant ('thumbnail'|'medium-thumb'|'medium'|'detail'|'original')
 * @returns {string} - URL with size suffix
 */
function getBGGImageVariant(url, size) {
  if (!url || !url.includes('cf.geekdo-images.com')) return url;

  // BGG uses two URL formats:
  // New format: https://cf.geekdo-images.com/HASH__SIZE/picID.EXT  (double underscore in path)
  // Old format: https://cf.geekdo-images.com/HASH_SIZE.EXT         (single underscore in filename)

  const sizeMap = {
    'thumbnail': '__t',
    'medium-thumb': '__mt',
    'medium': '__md',
    'detail': '__d',
    'original': '__original'
  };

  const targetSize = sizeMap[size] || '__md';  // Default to medium (confirmed working with BGG)

  // New format (most common): Replace __SIZE/ pattern
  // Example: /HASH__original/ → /HASH__d/
  if (url.match(/__[a-z]+\//)) {
    return url.replace(/__[a-z]+\//, `${targetSize}/`);
  }

  // Old format fallback: Replace _SIZE. pattern (legacy)
  // Example: /HASH_original.jpg → /HASH_d.jpg
  const oldSizeMap = {
    'thumbnail': '_t.',
    'medium-thumb': '_mt.',
    'medium': '_md.',
    'detail': '_d.',
    'original': '_original.'
  };

  const oldSuffix = oldSizeMap[size] || '_d.';

  return url
    .replace(/_t\./g, oldSuffix)
    .replace(/_mt\./g, oldSuffix)
    .replace(/_md\./g, oldSuffix)
    .replace(/_d\./g, oldSuffix)
    .replace(/_original\./g, oldSuffix);
}

/**
 * Enhanced image proxy URL with BGG image quality optimization
 *
 * IMPORTANT: BGG now blocks both __original and __d downloads with 400 Bad Request.
 * Default changed to 'medium' (__md, ~400px) which is less restrictive.
 * Priority order: __md (medium) > __mt (medium thumb) > __t (thumbnail)
 *
 * PERFORMANCE: If URL is already a Cloudinary URL, return it directly (skips backend proxy)
 *
 * @param {string} url - The original image URL
 * @param {string} size - Optional size variant for responsive images ('medium'|'medium-thumb'|'thumbnail')
 * @param {number} width - Optional width for Cloudinary transformation
 * @param {number} height - Optional height for Cloudinary transformation
 * @returns {string|null} - Proxied image URL or null if no URL provided
 */
export function imageProxyUrl(url, size = 'medium', width = null, height = null) {
  if (!url) return null;

  // PERFORMANCE OPTIMIZATION: If already a Cloudinary URL, use it directly (no proxy needed)
  if (url.includes('res.cloudinary.com')) {
    return url;
  }

  // For BGG images, optimize for requested quality
  if (url.includes('cf.geekdo-images.com')) {
    const optimizedUrl = getBGGImageVariant(url, size);
    let proxyUrl = `${API_BASE}/api/public/image-proxy?url=${encodeURIComponent(optimizedUrl)}`;

    // Add width/height parameters for Cloudinary transformations
    if (width) proxyUrl += `&width=${width}`;
    if (height) proxyUrl += `&height=${height}`;

    return proxyUrl;
  }

  // For non-BGG images, proxy as-is
  return `${API_BASE}/api/public/image-proxy?url=${encodeURIComponent(url)}`;
}

/**
 * Generate responsive image srcset for BGG images with Cloudinary
 *
 * When Cloudinary is enabled (backend), this generates srcset with width/height
 * parameters that the backend uses for Cloudinary transformations.
 * The backend handles automatic format conversion (WebP/AVIF) and optimization.
 *
 * @param {string} url - The original image URL
 * @returns {string|null} - srcset string with multiple resolutions
 */
export function generateSrcSet(url) {
  // Don't generate srcset for Cloudinary URLs (already optimized)
  if (!url || url.includes('res.cloudinary.com')) {
    return null;
  }

  // Only generate srcset for BGG images
  if (!url.includes('cf.geekdo-images.com')) {
    return null;
  }

  // IMPORTANT: Transform __original to __md BEFORE generating srcset
  // BGG may block __original and __d, use __md (medium) as safer option
  const baseUrl = getBGGImageVariant(url, 'medium');

  // Generate URLs for different sizes with Cloudinary transformations
  // The backend will handle uploading to Cloudinary and applying transformations
  const sizes = [
    { width: 200, height: 200 },   // Small mobile
    { width: 400, height: 400 },   // Large mobile / small tablet
    { width: 600, height: 600 },   // Tablet / small desktop
    { width: 800, height: 800 },   // Desktop
    { width: 1200, height: 1200 }  // High-DPI displays
  ];

  return sizes
    .map(({ width, height }) => {
      const proxyUrl = `${API_BASE}/api/public/image-proxy?url=${encodeURIComponent(baseUrl)}&width=${width}&height=${height}`;
      return `${proxyUrl} ${width}w`;
    })
    .join(', ');
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
