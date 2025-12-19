// Mana & Meeples Board Game Library - Service Worker
// Handles caching for offline support and improved performance

const CACHE_VERSION = 'v1';
const CACHE_NAME = `mana-meeples-${CACHE_VERSION}`;

// Cache different types of resources with different strategies
const CACHES = {
  APP_SHELL: `${CACHE_NAME}-app-shell`,
  API_DATA: `${CACHE_NAME}-api-data`,
  IMAGES: `${CACHE_NAME}-images`,
};

// Resources to cache immediately on install (app shell)
const APP_SHELL_URLS = [
  '/',
  '/index.html',
  '/mana_meeples_logo.ico',
  '/manifest.json',
];

// Cache duration settings
const CACHE_DURATION = {
  API: 5 * 60 * 1000,      // 5 minutes for API responses
  IMAGES: 7 * 24 * 60 * 60 * 1000,  // 7 days for images
};

// Install event - cache app shell
self.addEventListener('install', (event) => {
  console.log('[Service Worker] Installing...');

  event.waitUntil(
    caches.open(CACHES.APP_SHELL)
      .then((cache) => {
        console.log('[Service Worker] Caching app shell');
        return cache.addAll(APP_SHELL_URLS);
      })
      .then(() => {
        console.log('[Service Worker] App shell cached');
        return self.skipWaiting(); // Activate immediately
      })
      .catch((error) => {
        console.error('[Service Worker] Failed to cache app shell:', error);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[Service Worker] Activating...');

  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((cacheName) => {
              // Remove caches from different versions
              return cacheName.startsWith('mana-meeples-') &&
                     !Object.values(CACHES).includes(cacheName);
            })
            .map((cacheName) => {
              console.log('[Service Worker] Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            })
        );
      })
      .then(() => {
        console.log('[Service Worker] Activated');
        return self.clients.claim(); // Take control immediately
      })
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

  // Determine caching strategy based on request type
  if (isAPIRequest(url)) {
    event.respondWith(networkFirstStrategy(request, CACHES.API_DATA));
  } else if (isImageRequest(url)) {
    event.respondWith(cacheFirstStrategy(request, CACHES.IMAGES));
  } else if (isAppShellRequest(url)) {
    event.respondWith(cacheFirstStrategy(request, CACHES.APP_SHELL));
  } else {
    // Default: network first with cache fallback
    event.respondWith(networkFirstStrategy(request, CACHES.APP_SHELL));
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

    // Cache successful responses
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName);

      // Add timestamp header for cache freshness checking
      const headers = new Headers(responseToCache.headers);
      headers.append('sw-cached-time', Date.now().toString());

      const modifiedResponse = new Response(responseToCache.body, {
        status: responseToCache.status,
        statusText: responseToCache.statusText,
        headers: headers,
      });

      cache.put(request, modifiedResponse);
    }

    return networkResponse;
  } catch (error) {
    // Network failed, try cache
    console.log('[Service Worker] Network failed, trying cache:', request.url);
    const cachedResponse = await caches.match(request);

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
  // Try cache first
  const cachedResponse = await caches.match(request);

  if (cachedResponse) {
    // Check if cache is still fresh for images
    if (cacheName === CACHES.IMAGES) {
      if (isCacheFresh(cachedResponse, CACHE_DURATION.IMAGES)) {
        return cachedResponse;
      }
      // Cache expired, fetch fresh copy in background
      fetchAndCache(request, cacheName);
    }
    return cachedResponse;
  }

  // Not in cache, fetch from network
  try {
    const networkResponse = await fetch(request);

    // Cache successful responses
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName);
      const headers = new Headers(networkResponse.headers);
      headers.append('sw-cached-time', Date.now().toString());

      const responseToCache = new Response(networkResponse.clone().body, {
        status: networkResponse.status,
        statusText: networkResponse.statusText,
        headers: headers,
      });

      cache.put(request, responseToCache);
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
  fetch(request)
    .then((response) => {
      if (response.ok) {
        return caches.open(cacheName).then((cache) => {
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
    .catch((error) => {
      console.error('[Service Worker] Background fetch failed:', error);
    });
}

// Message handling for cache control from the app
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data && event.data.type === 'CLEAR_CACHE') {
    event.waitUntil(
      caches.keys().then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((cacheName) => cacheName.startsWith('mana-meeples-'))
            .map((cacheName) => caches.delete(cacheName))
        );
      }).then(() => {
        console.log('[Service Worker] All caches cleared');
        return self.clients.matchAll();
      }).then((clients) => {
        clients.forEach((client) => {
          client.postMessage({ type: 'CACHE_CLEARED' });
        });
      })
    );
  }
});

console.log('[Service Worker] Loaded');
