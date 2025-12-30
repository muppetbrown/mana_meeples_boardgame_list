/**
 * Version checking utility for automatic app updates
 * Checks for new deployments and prompts users to refresh
 */

const CHECK_INTERVAL = 5 * 60 * 1000; // Check every 5 minutes
const VERSION_ENDPOINT = '/version.json';

let currentVersion = null;
let checkTimer = null;
let updateCallbacks = [];

/**
 * Fetch current version info from server
 */
async function fetchServerVersion() {
  try {
    // Add cache-busting query param to ensure fresh data
    const response = await fetch(`${VERSION_ENDPOINT}?t=${Date.now()}`, {
      cache: 'no-cache',
      headers: {
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
      },
    });

    if (!response.ok) {
      console.warn('[VersionCheck] Failed to fetch version:', response.status);
      return null;
    }

    return await response.json();
  } catch (error) {
    console.warn('[VersionCheck] Error fetching version:', error.message);
    return null;
  }
}

/**
 * Check if a new version is available
 */
async function checkForUpdate() {
  const serverVersion = await fetchServerVersion();

  if (!serverVersion) {
    return false;
  }

  // First check - store current version
  if (!currentVersion) {
    currentVersion = serverVersion;
    console.log('[VersionCheck] Current version:', currentVersion.version);
    return false;
  }

  // Compare versions
  const hasUpdate = serverVersion.version !== currentVersion.version;

  if (hasUpdate) {
    console.log('[VersionCheck] New version detected!');
    console.log('  Current:', currentVersion.version);
    console.log('  New:', serverVersion.version);

    // Notify all registered callbacks
    updateCallbacks.forEach((callback) => {
      try {
        callback(serverVersion, currentVersion);
      } catch (error) {
        console.error('[VersionCheck] Callback error:', error);
      }
    });

    return true;
  }

  return false;
}

/**
 * Start periodic version checking
 */
export function startVersionCheck(onUpdate) {
  if (onUpdate && typeof onUpdate === 'function') {
    updateCallbacks.push(onUpdate);
  }

  // Initial check
  checkForUpdate();

  // Set up periodic checks
  if (!checkTimer) {
    checkTimer = setInterval(checkForUpdate, CHECK_INTERVAL);
    console.log('[VersionCheck] Started periodic checks (every 5 minutes)');
  }

  return () => stopVersionCheck(onUpdate);
}

/**
 * Stop version checking
 */
export function stopVersionCheck(callback) {
  if (callback) {
    updateCallbacks = updateCallbacks.filter((cb) => cb !== callback);
  }

  if (updateCallbacks.length === 0 && checkTimer) {
    clearInterval(checkTimer);
    checkTimer = null;
    console.log('[VersionCheck] Stopped periodic checks');
  }
}

/**
 * Manually trigger an update check
 */
export async function checkNow() {
  return await checkForUpdate();
}

/**
 * Force reload the application
 */
export function reloadApp() {
  console.log('[VersionCheck] Reloading application...');

  // Clear service worker cache if available
  if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
    navigator.serviceWorker.controller.postMessage({ type: 'CLEAR_CACHE' });
  }

  // Hard reload after a short delay to allow cache clear
  setTimeout(() => {
    window.location.reload(true);
  }, 100);
}

/**
 * Get current version info
 */
export function getCurrentVersion() {
  return currentVersion;
}
