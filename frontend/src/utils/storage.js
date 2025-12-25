// frontend/src/utils/storage.js
/**
 * Safe storage utility that handles tracking prevention and blocked storage access
 *
 * When Safari/Firefox tracking prevention or private browsing blocks localStorage,
 * this utility gracefully falls back to in-memory storage without throwing errors.
 *
 * Features:
 * - Automatic detection of storage availability
 * - In-memory fallback when storage is blocked
 * - Silent error handling (no console spam)
 * - Same API as localStorage
 */

/**
 * In-memory storage fallback for when localStorage is unavailable
 */
class MemoryStorage {
  constructor() {
    this.store = new Map();
  }

  getItem(key) {
    return this.store.get(key) ?? null;
  }

  setItem(key, value) {
    this.store.set(key, String(value));
  }

  removeItem(key) {
    this.store.delete(key);
  }

  clear() {
    this.store.clear();
  }

  get length() {
    return this.store.size;
  }

  key(index) {
    return Array.from(this.store.keys())[index] ?? null;
  }
}

/**
 * Check if localStorage is available and working
 * @returns {boolean} True if localStorage is accessible
 */
function checkStorageAvailable() {
  try {
    const testKey = '__storage_test__';
    localStorage.setItem(testKey, '1');
    localStorage.removeItem(testKey);
    return true;
  } catch (e) {
    // SecurityError, QuotaExceededError, or other storage-related errors
    return false;
  }
}

/**
 * Safe storage wrapper that automatically uses localStorage or falls back to memory
 */
class SafeStorage {
  constructor() {
    this.storageAvailable = checkStorageAvailable();
    this.backend = this.storageAvailable ? localStorage : new MemoryStorage();

    // Track if we've warned about unavailable storage (avoid console spam)
    this.hasWarned = false;
  }

  /**
   * Re-check storage availability (useful if user changes browser settings)
   */
  recheckAvailability() {
    const wasAvailable = this.storageAvailable;
    this.storageAvailable = checkStorageAvailable();

    // If storage became available, switch to localStorage
    if (!wasAvailable && this.storageAvailable) {
      console.info('[Storage] localStorage is now available');
      this.backend = localStorage;
    }

    return this.storageAvailable;
  }

  /**
   * Get item from storage
   * @param {string} key - Storage key
   * @returns {string|null} Stored value or null
   */
  getItem(key) {
    try {
      return this.backend.getItem(key);
    } catch (e) {
      // Storage might have become unavailable
      this.handleStorageError(e);
      return null;
    }
  }

  /**
   * Set item in storage
   * @param {string} key - Storage key
   * @param {string} value - Value to store
   */
  setItem(key, value) {
    try {
      this.backend.setItem(key, value);
    } catch (e) {
      // Storage might have become unavailable or quota exceeded
      this.handleStorageError(e);

      // If we were using localStorage, fall back to memory
      if (this.storageAvailable) {
        this.storageAvailable = false;
        this.backend = new MemoryStorage();
        this.backend.setItem(key, value);
      }
    }
  }

  /**
   * Remove item from storage
   * @param {string} key - Storage key
   */
  removeItem(key) {
    try {
      this.backend.removeItem(key);
    } catch (e) {
      this.handleStorageError(e);
    }
  }

  /**
   * Clear all items from storage
   */
  clear() {
    try {
      this.backend.clear();
    } catch (e) {
      this.handleStorageError(e);
    }
  }

  /**
   * Get number of items in storage
   * @returns {number} Number of stored items
   */
  get length() {
    try {
      return this.backend.length;
    } catch (e) {
      this.handleStorageError(e);
      return 0;
    }
  }

  /**
   * Get key by index
   * @param {number} index - Index of key
   * @returns {string|null} Key at index or null
   */
  key(index) {
    try {
      return this.backend.key(index);
    } catch (e) {
      this.handleStorageError(e);
      return null;
    }
  }

  /**
   * Check if storage is currently available
   * @returns {boolean} True if using localStorage, false if using memory fallback
   */
  isAvailable() {
    return this.storageAvailable;
  }

  /**
   * Check if we're using memory storage (fallback mode)
   * @returns {boolean} True if using in-memory storage
   */
  isUsingMemoryFallback() {
    return !this.storageAvailable;
  }

  /**
   * Handle storage errors without spamming console
   * @param {Error} error - Storage error
   */
  handleStorageError(error) {
    // Only log the first error to avoid console spam
    if (!this.hasWarned) {
      console.warn(
        '[Storage] Browser storage blocked (tracking prevention or private browsing). Using in-memory fallback.',
        error.name
      );
      this.hasWarned = true;
    }
  }
}

// Create and export singleton instance
export const safeStorage = new SafeStorage();

// Export convenience functions with same API as localStorage
export const getItem = (key) => safeStorage.getItem(key);
export const setItem = (key, value) => safeStorage.setItem(key, value);
export const removeItem = (key) => safeStorage.removeItem(key);
export const clear = () => safeStorage.clear();

// Export class for testing
export { SafeStorage, MemoryStorage };
