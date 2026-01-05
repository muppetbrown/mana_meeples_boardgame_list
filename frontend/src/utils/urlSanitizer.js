// utils/urlSanitizer.js
/**
 * URL sanitization utilities for XSS prevention.
 *
 * Defense-in-depth: Even though backend validates URLs, frontend should also validate
 * to prevent XSS attacks via javascript:, data:, or other malicious URL schemes.
 */

/**
 * Sanitize an image URL to prevent XSS attacks.
 *
 * Only allows http:// and https:// protocols.
 * Blocks javascript:, data:, vbscript:, and other potentially malicious schemes.
 *
 * @param {string} url - The URL to sanitize
 * @returns {string|null} - Sanitized URL or null if invalid
 */
export function sanitizeImageUrl(url) {
  // Return null for empty/null/undefined URLs
  if (!url || typeof url !== 'string') {
    return null;
  }

  // Trim whitespace
  url = url.trim();

  // Empty after trim
  if (!url) {
    return null;
  }

  try {
    // Parse URL to validate structure
    const parsed = new URL(url);

    // Only allow http and https protocols
    if (!['http:', 'https:'].includes(parsed.protocol)) {
      console.warn('[Security] Blocked unsafe image URL with protocol:', parsed.protocol, url.substring(0, 50));
      return null;
    }

    // Additional security checks

    // Block URLs with userinfo (e.g., http://user:pass@example.com)
    // These can be used for phishing attacks
    if (parsed.username || parsed.password) {
      console.warn('[Security] Blocked image URL with credentials:', url.substring(0, 50));
      return null;
    }

    // Block localhost and private IP ranges in production
    // (Allow in development for local testing)
    if (process.env.NODE_ENV === 'production') {
      const hostname = parsed.hostname.toLowerCase();

      // Block localhost
      if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '::1') {
        console.warn('[Security] Blocked localhost image URL in production:', url.substring(0, 50));
        return null;
      }

      // Block private IP ranges (RFC 1918)
      if (
        hostname.startsWith('192.168.') ||
        hostname.startsWith('10.') ||
        /^172\.(1[6-9]|2[0-9]|3[0-1])\./.test(hostname)
      ) {
        console.warn('[Security] Blocked private IP image URL in production:', url.substring(0, 50));
        return null;
      }
    }

    // URL is valid
    return url;

  } catch (error) {
    // Invalid URL format
    console.warn('[Security] Invalid image URL format:', url.substring(0, 50), error.message);
    return null;
  }
}

/**
 * Validate and sanitize multiple image URLs.
 *
 * @param {string[]} urls - Array of URLs to sanitize
 * @returns {string[]} - Array of sanitized URLs (excludes invalid ones)
 */
export function sanitizeImageUrls(urls) {
  if (!Array.isArray(urls)) {
    return [];
  }

  return urls
    .map(url => sanitizeImageUrl(url))
    .filter(url => url !== null);
}

/**
 * Check if a URL is safe for use in an iframe.
 * More restrictive than image URL validation.
 *
 * @param {string} url - The URL to check
 * @returns {boolean} - True if safe for iframe
 */
export function isSafeIframeUrl(url) {
  const sanitized = sanitizeImageUrl(url);

  if (!sanitized) {
    return false;
  }

  try {
    const parsed = new URL(sanitized);

    // Only allow specific trusted domains for iframes
    const trustedDomains = [
      'youtube.com',
      'www.youtube.com',
      'vimeo.com',
      'player.vimeo.com',
      // Add other trusted domains as needed
    ];

    const hostname = parsed.hostname.toLowerCase();
    const istrusted = trustedDomains.some(domain =>
      hostname === domain || hostname.endsWith('.' + domain)
    );

    if (!istrusted) {
      console.warn('[Security] Blocked untrusted iframe URL:', hostname);
      return false;
    }

    return true;

  } catch {
    return false;
  }
}
