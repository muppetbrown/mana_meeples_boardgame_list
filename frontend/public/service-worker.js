// Mana & Meeples Board Game Library - Service Worker
// Handles caching for offline support and improved performance
// Auto-updates when new version is deployed

// Dynamic version fetching for automatic cache invalidation
let CACHE_VERSION = 'v1'; // Fallback if version fetch fails
let versionFetched = false;

// Fetch version from version.json (generated at build time)
async function fetchCacheVersion() {
  if (versionFetched) {
    return CACHE_VERSION;
  }

  try {
    const response = await fetch('/version.json');
    if (response.ok) {
      const versionData = await response.json();
      CACHE_VERSION = versionData.version || versionData.timestamp.toString();
      console.log('[Service Worker] Using cache version:', CACHE_VERSION);
    }
  } catch (error) {
    console.warn('[Service Worker] Failed to fetch version, using fallback:', error.message);
  }

  versionFetched = true;
  return CACHE_VERSION;
}

// Get cache name (async to support dynamic versioning)
async function getCacheName() {
  await fetchCacheVersion();
  return `mana-meeples-${CACHE_VERSION}`;
}

// Get cache names for different resource types
async function getCacheNames() {
  const baseName = await getCacheName();
  return {
    APP_SHELL: `${baseName}-app-shell`,
    API_DATA: `${baseName}-api-data`,
    IMAGES: `${baseName}-images`,
  };
}

// Resources to cache immediately on install (app shell)
const APP_SHELL_URLS = [
  '/',
  '/index.html',
  '/mana_meeples_logo.ico',
  '/manifest.json',
  '/version.json', // Include version file in cache
];

// Cache duration settings
const CACHE_DURATION = {
  API: 5 * 60 * 1000,      // 5 minutes for API responses
  IMAGES: 7 * 24 * 60 * 60 * 1000,  // 7 days for images
};

// Track if storage is available (Safari ITP may block it)
let storageAvailable = true;

// Test if Cache API is accessible
async function checkStorageAvailability() {
  try {
    const testCacheName = 'sw-storage-test';
    const cache = await caches.open(testCacheName);
    await caches.delete(testCacheName);
    storageAvailable = true;
    return true;
  } catch (error) {
    // Silently handle storage blocking (browser logs its own warnings)
    storageAvailable = false;
    return false;
  }
}

// Safe cache wrapper that handles blocked storage
async function safeOpenCache(cacheName) {
  if (!storageAvailable) {
    throw new Error('Storage unavailable');
  }
  try {
    return await caches.open(cacheName);
  } catch (error) {
    // Silently mark storage as unavailable
    storageAvailable = false;
    throw error;
  }
}

// Safe cache match wrapper
async function safeCacheMatch(request) {
  if (!storageAvailable) {
    return null;
  }
  try {
    return await caches.match(request);
  } catch (error) {
    // Silently mark storage as unavailable without logging
    // (browser already logs tracking prevention warnings)
    storageAvailable = false;
    return null;
  }
}

// Install event - cache app shell
self.addEventListener('install', (event) => {
  console.log('[Service Worker] Installing...');

  event.waitUntil(
    (async () => {
      try {
        const available = await checkStorageAvailability();
        if (!available) {
          console.warn('[Service Worker] Storage unavailable, skipping cache');
          return self.skipWaiting();
        }

        // Fetch and use dynamic cache version
        const cacheNames = await getCacheNames();
        const cache = await safeOpenCache(cacheNames.APP_SHELL);

        console.log('[Service Worker] Caching app shell');
        await cache.addAll(APP_SHELL_URLS);

        console.log('[Service Worker] App shell cached');
        return self.skipWaiting();
      } catch (error) {
        console.warn('[Service Worker] Install failed:', error.message);
        // Silently continue without cache if setup fails
        return self.skipWaiting();
      }
    })()
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[Service Worker] Activating...');

  event.waitUntil(
    (async () => {
      try {
        if (!storageAvailable) {
          console.warn('[Service Worker] Storage unavailable, skipping cache cleanup');
          return self.clients.claim();
        }

        // Get current cache names for this version
        const currentCacheNames = await getCacheNames();
        const currentCacheValues = Object.values(currentCacheNames);

        // Get all cache names and delete old ones
        const allCacheNames = await caches.keys();
        await Promise.all(
          allCacheNames
            .filter((cacheName) => {
              // Remove caches from different versions
              return cacheName.startsWith('mana-meeples-') &&
                     !currentCacheValues.includes(cacheName);
            })
            .map((cacheName) => {
              console.log('[Service Worker] Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            })
        );

        console.log('[Service Worker] Activated with cache version:', CACHE_VERSION);
        return self.clients.claim();
      } catch (error) {
        console.warn('[Service Worker] Activation error:', error.message);
        // Silently continue activation even if cache cleanup fails
        return self.clients.claim();
      }
    })()
  );
});

// Fetch event - handle different caching strategies
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip chrome-extension and other non-http(s) requests
  if (!url.protocol.startsWith('http')) {
    return;
  }

  // If storage is unavailable, just pass through to network immediately
  // This prevents browser warnings about blocked storage access
  if (!storageAvailable) {
    event.respondWith(
      fetch(request).catch(() => {
        // Return offline response for failed network requests
        return new Response('Offline - no cache available', {
          status: 503,
          statusText: 'Service Unavailable',
        });
      })
    );
    return;
  }

  // Determine caching strategy based on request type
  // Use async handlers to get cache names dynamically
  if (isAPIRequest(url)) {
    event.respondWith((async () => {
      const cacheNames = await getCacheNames();
      return networkFirstStrategy(request, cacheNames.API_DATA);
    })());
  } else if (isImageRequest(url)) {
    event.respondWith((async () => {
      const cacheNames = await getCacheNames();
      return cacheFirstStrategy(request, cacheNames.IMAGES);
    })());
  } else if (isAppShellRequest(url)) {
    event.respondWith((async () => {
      const cacheNames = await getCacheNames();
      return cacheFirstStrategy(request, cacheNames.APP_SHELL);
    })());
  } else {
    // Default: network first with cache fallback
    event.respondWith((async () => {
      const cacheNames = await getCacheNames();
      return networkFirstStrategy(request, cacheNames.APP_SHELL);
    })());
  }
});

// Helper: Check if request is an API call
function isAPIRequest(url) {
  return url.pathname.startsWith('/api/') ||
         url.hostname.includes('mana-meeples-boardgame-list');
}

// Helper: Check if request is an image
function isImageRequest(url) {
  // Cloudinary images, BGG images, or local images
  return url.pathname.match(/\.(jpg|jpeg|png|gif|webp|avif|svg|ico)$/i) ||
         url.hostname.includes('cloudinary.com') ||
         url.hostname.includes('geekdo-images.com') ||
         url.pathname.includes('/image-proxy');
}

// Helper: Check if request is app shell
function isAppShellRequest(url) {
  return url.pathname === '/' ||
         url.pathname === '/index.html' ||
         url.pathname.match(/\.(js|css|woff2?|ttf)$/i);
}

// Helper: Check if cached response is still fresh
function isCacheFresh(response, maxAge) {
  if (!response) return false;

  const cachedTime = response.headers.get('sw-cached-time');
  if (!cachedTime) return true; // No timestamp, assume fresh

  const age = Date.now() - parseInt(cachedTime, 10);
  return age < maxAge;
}

// Strategy: Network first, fall back to cache (good for API calls)
async function networkFirstStrategy(request, cacheName) {
  try {
    // Try network first
    const networkResponse = await fetch(request);

    // Clone the response before caching
    const responseToCache = networkResponse.clone();

    // Cache successful responses (only if storage is available)
    if (networkResponse.ok && storageAvailable) {
      try {
        const cache = await safeOpenCache(cacheName);

        // Add timestamp header for cache freshness checking
        const headers = new Headers(responseToCache.headers);
        headers.append('sw-cached-time', Date.now().toString());

        const modifiedResponse = new Response(responseToCache.body, {
          status: responseToCache.status,
          statusText: responseToCache.statusText,
          headers: headers,
        });

        await cache.put(request, modifiedResponse);
      } catch (cacheError) {
        // Silently fail cache put - network response is still good
        storageAvailable = false;
      }
    }

    return networkResponse;
  } catch (error) {
    // Network failed, try cache
    console.log('[Service Worker] Network failed, trying cache:', request.url);
    const cachedResponse = await safeCacheMatch(request);

    if (cachedResponse) {
      console.log('[Service Worker] Serving from cache:', request.url);
      return cachedResponse;
    }

    // No cache available, return error
    console.error('[Service Worker] No cache available for:', request.url);
    return new Response('Offline - content not cached', {
      status: 503,
      statusText: 'Service Unavailable',
      headers: new Headers({
        'Content-Type': 'text/plain',
      }),
    });
  }
}

// Strategy: Cache first, fall back to network (good for images and static assets)
async function cacheFirstStrategy(request, cacheName) {
  // Try cache first (only if storage is available)
  const cachedResponse = await safeCacheMatch(request);

  if (cachedResponse) {
    // Check if cache is still fresh for images
    if (cacheName.includes('-images')) {
      if (isCacheFresh(cachedResponse, CACHE_DURATION.IMAGES)) {
        return cachedResponse;
      }
      // Cache expired, fetch fresh copy in background
      if (storageAvailable) {
        fetchAndCache(request, cacheName);
      }
    }
    return cachedResponse;
  }

  // Not in cache, fetch from network
  try {
    const networkResponse = await fetch(request);

    // Cache successful responses (only if storage is available)
    if (networkResponse.ok && storageAvailable) {
      try {
        const cache = await safeOpenCache(cacheName);
        const headers = new Headers(networkResponse.headers);
        headers.append('sw-cached-time', Date.now().toString());

        const responseToCache = new Response(networkResponse.clone().body, {
          status: networkResponse.status,
          statusText: networkResponse.statusText,
          headers: headers,
        });

        await cache.put(request, responseToCache);
      } catch (cacheError) {
        // Silently fail cache put - network response is still good
        storageAvailable = false;
      }
    }

    return networkResponse;
  } catch (error) {
    console.error('[Service Worker] Failed to fetch:', request.url, error);

    // For image requests, return a placeholder
    if (isImageRequest(new URL(request.url))) {
      return new Response('', {
        status: 404,
        statusText: 'Image not available offline',
      });
    }

    throw error;
  }
}

// Helper: Fetch and cache in background (fire and forget)
function fetchAndCache(request, cacheName) {
  if (!storageAvailable) {
    return;
  }

  fetch(request)
    .then((response) => {
      if (response.ok) {
        return safeOpenCache(cacheName).then((cache) => {
          const headers = new Headers(response.headers);
          headers.append('sw-cached-time', Date.now().toString());

          const responseToCache = new Response(response.body, {
            status: response.status,
            statusText: response.statusText,
            headers: headers,
          });

          return cache.put(request, responseToCache);
        });
      }
    })
    .catch(() => {
      // Silently fail background cache updates
      storageAvailable = false;
    });
}

// Message handling for cache control from the app
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data && event.data.type === 'CLEAR_CACHE') {
    event.waitUntil(
      (async () => {
        try {
          if (!storageAvailable) {
            console.warn('[Service Worker] Storage unavailable, cannot clear cache');
            const clients = await self.clients.matchAll();
            clients.forEach((client) => {
              client.postMessage({ type: 'CACHE_CLEARED', error: 'Storage unavailable' });
            });
            return;
          }

          const cacheNames = await caches.keys();
          await Promise.all(
            cacheNames
              .filter((cacheName) => cacheName.startsWith('mana-meeples-'))
              .map((cacheName) => caches.delete(cacheName))
          );

          console.log('[Service Worker] All caches cleared');
          const clients = await self.clients.matchAll();
          clients.forEach((client) => {
            client.postMessage({ type: 'CACHE_CLEARED' });
          });
        } catch (error) {
          // Silently handle cache clear failures
          const clients = await self.clients.matchAll();
          clients.forEach((client) => {
            client.postMessage({ type: 'CACHE_CLEARED', error: error.message });
          });
        }
      })()
    );
  }
});

console.log('[Service Worker] Loaded');
