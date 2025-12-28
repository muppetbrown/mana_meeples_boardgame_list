import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { MemoryStorage, SafeStorage, safeStorage, getItem, setItem, removeItem, clear } from '../storage';

describe('MemoryStorage', () => {
  let storage;

  beforeEach(() => {
    storage = new MemoryStorage();
  });

  describe('setItem and getItem', () => {
    it('stores and retrieves string values', () => {
      storage.setItem('key', 'value');
      expect(storage.getItem('key')).toBe('value');
    });

    it('converts values to strings', () => {
      storage.setItem('number', 123);
      expect(storage.getItem('number')).toBe('123');

      storage.setItem('boolean', true);
      expect(storage.getItem('boolean')).toBe('true');
    });

    it('returns null for non-existent keys', () => {
      expect(storage.getItem('nonexistent')).toBeNull();
    });

    it('overwrites existing values', () => {
      storage.setItem('key', 'value1');
      storage.setItem('key', 'value2');
      expect(storage.getItem('key')).toBe('value2');
    });
  });

  describe('removeItem', () => {
    it('removes stored items', () => {
      storage.setItem('key', 'value');
      storage.removeItem('key');
      expect(storage.getItem('key')).toBeNull();
    });

    it('does not throw when removing non-existent key', () => {
      expect(() => storage.removeItem('nonexistent')).not.toThrow();
    });
  });

  describe('clear', () => {
    it('removes all items', () => {
      storage.setItem('key1', 'value1');
      storage.setItem('key2', 'value2');
      storage.setItem('key3', 'value3');

      storage.clear();

      expect(storage.getItem('key1')).toBeNull();
      expect(storage.getItem('key2')).toBeNull();
      expect(storage.getItem('key3')).toBeNull();
    });

    it('resets length to 0', () => {
      storage.setItem('key1', 'value1');
      storage.setItem('key2', 'value2');
      storage.clear();

      expect(storage.length).toBe(0);
    });
  });

  describe('length', () => {
    it('returns 0 for empty storage', () => {
      expect(storage.length).toBe(0);
    });

    it('returns correct count of items', () => {
      storage.setItem('key1', 'value1');
      expect(storage.length).toBe(1);

      storage.setItem('key2', 'value2');
      expect(storage.length).toBe(2);
    });

    it('decreases when items are removed', () => {
      storage.setItem('key1', 'value1');
      storage.setItem('key2', 'value2');
      storage.removeItem('key1');

      expect(storage.length).toBe(1);
    });
  });

  describe('key', () => {
    it('returns key at given index', () => {
      storage.setItem('key1', 'value1');
      storage.setItem('key2', 'value2');

      const keys = [storage.key(0), storage.key(1)];
      expect(keys).toContain('key1');
      expect(keys).toContain('key2');
    });

    it('returns null for out-of-bounds index', () => {
      expect(storage.key(0)).toBeNull();

      storage.setItem('key1', 'value1');
      expect(storage.key(1)).toBeNull();
      expect(storage.key(-1)).toBeNull();
    });
  });
});

describe('SafeStorage', () => {
  let mockLocalStorage;
  let originalLocalStorage;

  beforeEach(() => {
    // Save original localStorage
    originalLocalStorage = global.localStorage;

    // Create mock localStorage
    mockLocalStorage = {
      store: {},
      getItem: vi.fn((key) => mockLocalStorage.store[key] || null),
      setItem: vi.fn((key, value) => {
        mockLocalStorage.store[key] = String(value);
      }),
      removeItem: vi.fn((key) => {
        delete mockLocalStorage.store[key];
      }),
      clear: vi.fn(() => {
        mockLocalStorage.store = {};
      }),
      get length() {
        return Object.keys(mockLocalStorage.store).length;
      },
      key: vi.fn((index) => Object.keys(mockLocalStorage.store)[index] || null),
    };

    global.localStorage = mockLocalStorage;
  });

  afterEach(() => {
    global.localStorage = originalLocalStorage;
    vi.clearAllMocks();
  });

  describe('initialization', () => {
    it('uses localStorage when available', () => {
      const storage = new SafeStorage();
      expect(storage.isAvailable()).toBe(true);
      expect(storage.isUsingMemoryFallback()).toBe(false);
    });

    it('falls back to memory storage when localStorage is blocked', () => {
      // Mock localStorage to throw SecurityError
      global.localStorage = {
        setItem: vi.fn(() => {
          throw new DOMException('SecurityError');
        }),
      };

      const storage = new SafeStorage();
      expect(storage.isAvailable()).toBe(false);
      expect(storage.isUsingMemoryFallback()).toBe(true);
    });
  });

  describe('getItem', () => {
    it('retrieves items from localStorage', () => {
      const storage = new SafeStorage();
      mockLocalStorage.store['test'] = 'value';

      expect(storage.getItem('test')).toBe('value');
    });

    it('returns null for non-existent keys', () => {
      const storage = new SafeStorage();
      expect(storage.getItem('nonexistent')).toBeNull();
    });

    it('handles errors gracefully', () => {
      const storage = new SafeStorage();
      mockLocalStorage.getItem.mockImplementation(() => {
        throw new Error('Storage error');
      });

      expect(storage.getItem('test')).toBeNull();
    });
  });

  describe('setItem', () => {
    it('stores items in localStorage', () => {
      const storage = new SafeStorage();
      storage.setItem('key', 'value');

      expect(mockLocalStorage.setItem).toHaveBeenCalledWith('key', 'value');
      expect(mockLocalStorage.store['key']).toBe('value');
    });

    it('falls back to memory storage on quota exceeded', () => {
      const storage = new SafeStorage();

      // First call succeeds
      storage.setItem('key1', 'value1');
      expect(storage.isAvailable()).toBe(true);

      // Mock quota exceeded error
      mockLocalStorage.setItem.mockImplementation(() => {
        throw new DOMException('QuotaExceededError');
      });

      // This should trigger fallback
      storage.setItem('key2', 'value2');
      expect(storage.isUsingMemoryFallback()).toBe(true);

      // Should now use memory storage
      expect(storage.getItem('key2')).toBe('value2');
    });
  });

  describe('removeItem', () => {
    it('removes items from localStorage', () => {
      const storage = new SafeStorage();
      storage.setItem('key', 'value');
      storage.removeItem('key');

      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('key');
    });

    it('handles errors gracefully', () => {
      const storage = new SafeStorage();
      mockLocalStorage.removeItem.mockImplementation(() => {
        throw new Error('Storage error');
      });

      expect(() => storage.removeItem('key')).not.toThrow();
    });
  });

  describe('clear', () => {
    it('clears all items from localStorage', () => {
      const storage = new SafeStorage();
      storage.setItem('key1', 'value1');
      storage.setItem('key2', 'value2');
      storage.clear();

      expect(mockLocalStorage.clear).toHaveBeenCalled();
    });

    it('handles errors gracefully', () => {
      const storage = new SafeStorage();
      mockLocalStorage.clear.mockImplementation(() => {
        throw new Error('Storage error');
      });

      expect(() => storage.clear()).not.toThrow();
    });
  });

  describe('length', () => {
    it('returns number of items in storage', () => {
      const storage = new SafeStorage();
      storage.setItem('key1', 'value1');
      storage.setItem('key2', 'value2');

      expect(storage.length).toBe(2);
    });

    it('returns 0 on error', () => {
      const storage = new SafeStorage();

      // Mock error
      Object.defineProperty(mockLocalStorage, 'length', {
        get: () => {
          throw new Error('Storage error');
        },
      });

      expect(storage.length).toBe(0);
    });
  });

  describe('key', () => {
    it('returns key at given index', () => {
      const storage = new SafeStorage();
      storage.setItem('key1', 'value1');
      storage.setItem('key2', 'value2');

      const key = storage.key(0);
      expect(['key1', 'key2']).toContain(key);
    });

    it('returns null on error', () => {
      const storage = new SafeStorage();
      mockLocalStorage.key.mockImplementation(() => {
        throw new Error('Storage error');
      });

      expect(storage.key(0)).toBeNull();
    });
  });

  describe('recheckAvailability', () => {
    it('switches to localStorage when it becomes available', () => {
      // Start with blocked localStorage
      global.localStorage = {
        setItem: vi.fn(() => {
          throw new DOMException('SecurityError');
        }),
      };

      const storage = new SafeStorage();
      expect(storage.isUsingMemoryFallback()).toBe(true);

      // Restore working localStorage
      global.localStorage = mockLocalStorage;

      const consoleInfoSpy = vi.spyOn(console, 'info').mockImplementation(() => {});
      storage.recheckAvailability();

      expect(storage.isAvailable()).toBe(true);
      expect(consoleInfoSpy).toHaveBeenCalledWith(
        expect.stringContaining('localStorage is now available')
      );

      consoleInfoSpy.mockRestore();
    });

    it('returns current availability status', () => {
      const storage = new SafeStorage();
      const isAvailable = storage.recheckAvailability();

      expect(isAvailable).toBe(storage.isAvailable());
    });
  });

  describe('error handling', () => {
    it('only warns once to avoid console spam', () => {
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      const storage = new SafeStorage();

      mockLocalStorage.getItem.mockImplementation(() => {
        throw new Error('Storage error');
      });

      storage.getItem('test1');
      storage.getItem('test2');
      storage.getItem('test3');

      expect(consoleWarnSpy).toHaveBeenCalledTimes(1);

      consoleWarnSpy.mockRestore();
    });
  });
});

describe('Convenience functions', () => {
  beforeEach(() => {
    // Clear any existing state
    clear();
  });

  it('getItem retrieves from safeStorage', () => {
    setItem('test', 'value');
    expect(getItem('test')).toBe('value');
  });

  it('setItem stores in safeStorage', () => {
    setItem('key', 'value');
    expect(safeStorage.getItem('key')).toBe('value');
  });

  it('removeItem removes from safeStorage', () => {
    setItem('key', 'value');
    removeItem('key');
    expect(getItem('key')).toBeNull();
  });

  it('clear removes all items from safeStorage', () => {
    setItem('key1', 'value1');
    setItem('key2', 'value2');
    clear();

    expect(getItem('key1')).toBeNull();
    expect(getItem('key2')).toBeNull();
  });
});

describe('Integration scenarios', () => {
  it('handles transition from localStorage to memory fallback', () => {
    let callCount = 0;
    const mockLocalStorage = {
      store: {},
      getItem: vi.fn((key) => mockLocalStorage.store[key] || null),
      setItem: vi.fn((key, value) => {
        callCount++;
        // Allow the test write to succeed (first call)
        if (callCount === 1) {
          mockLocalStorage.store[key] = String(value);
          return;
        }
        // Also allow the first user write to succeed
        if (callCount === 2) {
          mockLocalStorage.store[key] = String(value);
          return;
        }
        // Third call (second user write) fails with quota exceeded
        if (callCount === 3) {
          throw new DOMException('QuotaExceededError');
        }
        mockLocalStorage.store[key] = String(value);
      }),
      removeItem: vi.fn((key) => {
        delete mockLocalStorage.store[key];
      }),
      clear: vi.fn(() => {
        mockLocalStorage.store = {};
      }),
      get length() {
        return Object.keys(mockLocalStorage.store).length;
      },
      key: vi.fn((index) => Object.keys(mockLocalStorage.store)[index] || null),
    };

    global.localStorage = mockLocalStorage;

    const storage = new SafeStorage();

    // First write succeeds
    storage.setItem('key1', 'value1');
    expect(storage.isAvailable()).toBe(true);

    // Second write triggers fallback
    storage.setItem('key2', 'value2');
    expect(storage.isUsingMemoryFallback()).toBe(true);

    // Both values should still be accessible (key2 from memory)
    expect(storage.getItem('key2')).toBe('value2');
  });
});
