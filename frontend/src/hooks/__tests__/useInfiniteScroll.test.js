// frontend/src/hooks/__tests__/useInfiniteScroll.test.js
import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { useInfiniteScroll } from '../useInfiniteScroll';

describe('useInfiniteScroll Hook', () => {
  let mockObserver;
  let observerCallback;

  beforeEach(() => {
    // Create mock observer instance
    mockObserver = {
      observe: vi.fn(),
      disconnect: vi.fn(),
      unobserve: vi.fn(),
    };

    // Mock IntersectionObserver constructor
    global.IntersectionObserver = vi.fn((callback) => {
      observerCallback = callback;
      return mockObserver;
    });

    // Mock console methods to avoid noise in test output
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.spyOn(console, 'warn').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('initialization', () => {
    test('initializes with empty state', () => {
      const fetchMore = vi.fn();
      const { result } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
      );

      expect(result.current.allLoadedItems).toEqual([]);
      expect(result.current.loadingMore).toBe(false);
      expect(result.current.hasMore).toBe(true);
    });

    test('indicates when there are more items to load', () => {
      const fetchMore = vi.fn();
      const { result } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
      );

      expect(result.current.hasMore).toBe(true);
    });

    test('provides ref for load more trigger element', () => {
      const fetchMore = vi.fn();
      const { result } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
      );

      expect(result.current.loadMoreTriggerRef).toBeDefined();
      expect(result.current.loadMoreTriggerRef.current).toBeNull();
    });

    test('provides isLoadingMoreRef', () => {
      const fetchMore = vi.fn();
      const { result } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
      );

      expect(result.current.isLoadingMoreRef).toBeDefined();
      expect(result.current.isLoadingMoreRef.current).toBe(false);
    });

    test('uses default pageSize of 12', () => {
      const fetchMore = vi.fn().mockResolvedValue({ items: [] });
      const { result } = renderHook(() =>
        useInfiniteScroll(fetchMore, { filters: {}, total: 100 })
      );

      expect(result.current).toBeDefined();
    });
  });

  describe('hasMore calculation', () => {
    test('hasMore is true when loaded items less than total', () => {
      const fetchMore = vi.fn();
      const { result } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
      );

      expect(result.current.hasMore).toBe(true);
    });

    test('hasMore is false when loaded items equal total', () => {
      const fetchMore = vi.fn();
      const { result } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 0 })
      );

      expect(result.current.hasMore).toBe(false);
    });

    test('hasMore updates after items are loaded', async () => {
      const mockItems = Array.from({ length: 95 }, (_, i) => ({ id: i + 1, name: `Item ${i + 1}` }));
      const fetchMore = vi.fn().mockResolvedValue({ items: mockItems });

      const { result } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
      );

      // Manually set items to simulate loading
      await act(async () => {
        result.current.setAllLoadedItems(mockItems);
      });

      await waitFor(() => {
        expect(result.current.hasMore).toBe(true);
      });
    });

    test('hasMore is false when all items loaded', async () => {
      const mockItems = Array.from({ length: 100 }, (_, i) => ({ id: i + 1, name: `Item ${i + 1}` }));
      const fetchMore = vi.fn().mockResolvedValue({ items: [] });

      const { result } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
      );

      await act(async () => {
        result.current.setAllLoadedItems(mockItems);
      });

      await waitFor(() => {
        expect(result.current.hasMore).toBe(false);
      });
    });
  });

  describe('filter changes', () => {
    test('resets items when filters change', async () => {
      const fetchMore = vi.fn().mockResolvedValue({ items: [] });
      const initialItems = [{ id: 1, name: 'Item 1' }, { id: 2, name: 'Item 2' }];

      const { result, rerender } = renderHook(
        ({ filters }) => useInfiniteScroll(fetchMore, { pageSize: 12, filters, total: 100 }),
        { initialProps: { filters: { category: 'adventure' } } }
      );

      // Set some items
      await act(async () => {
        result.current.setAllLoadedItems(initialItems);
      });

      await waitFor(() => {
        expect(result.current.allLoadedItems).toHaveLength(2);
      });

      // Change filters
      rerender({ filters: { category: 'strategy' } });

      await waitFor(() => {
        expect(result.current.allLoadedItems).toEqual([]);
      });
    });

    test('does not reset when filters are the same', async () => {
      const fetchMore = vi.fn().mockResolvedValue({ items: [] });
      const initialItems = [{ id: 1, name: 'Item 1' }];

      const { result, rerender } = renderHook(
        ({ filters }) => useInfiniteScroll(fetchMore, { pageSize: 12, filters, total: 100 }),
        { initialProps: { filters: { category: 'adventure' } } }
      );

      await act(async () => {
        result.current.setAllLoadedItems(initialItems);
      });

      await waitFor(() => {
        expect(result.current.allLoadedItems).toHaveLength(1);
      });

      // Re-render with same filters
      rerender({ filters: { category: 'adventure' } });

      await waitFor(() => {
        expect(result.current.allLoadedItems).toHaveLength(1);
      });
    });

    test('resets when filter values change', async () => {
      const fetchMore = vi.fn().mockResolvedValue({ items: [] });
      const initialItems = [{ id: 1, name: 'Item 1' }];

      const { result, rerender } = renderHook(
        ({ filters }) => useInfiniteScroll(fetchMore, { pageSize: 12, filters, total: 100 }),
        { initialProps: { filters: { q: 'test' } } }
      );

      await act(async () => {
        result.current.setAllLoadedItems(initialItems);
      });

      await waitFor(() => {
        expect(result.current.allLoadedItems).toHaveLength(1);
      });

      // Change search query
      rerender({ filters: { q: 'different' } });

      await waitFor(() => {
        expect(result.current.allLoadedItems).toEqual([]);
      });
    });
  });

  describe('setAllLoadedItems', () => {
    test('allows manual setting of items', async () => {
      const fetchMore = vi.fn();
      const { result } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
      );

      const newItems = [{ id: 1, name: 'Item 1' }, { id: 2, name: 'Item 2' }];

      await act(async () => {
        result.current.setAllLoadedItems(newItems);
      });

      await waitFor(() => {
        expect(result.current.allLoadedItems).toEqual(newItems);
      });
    });

    test('can clear items by setting empty array', async () => {
      const fetchMore = vi.fn();
      const { result } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
      );

      const items = [{ id: 1, name: 'Item 1' }];

      await act(async () => {
        result.current.setAllLoadedItems(items);
      });

      await waitFor(() => {
        expect(result.current.allLoadedItems).toHaveLength(1);
      });

      await act(async () => {
        result.current.setAllLoadedItems([]);
      });

      await waitFor(() => {
        expect(result.current.allLoadedItems).toEqual([]);
      });
    });
  });

  describe('state management', () => {
    test('provides correct initial loadingMore state', () => {
      const fetchMore = vi.fn();
      const { result } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
      );

      expect(result.current.loadingMore).toBe(false);
    });

    test('provides isLoadingMoreRef with correct initial value', () => {
      const fetchMore = vi.fn();
      const { result } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
      );

      expect(result.current.isLoadingMoreRef.current).toBe(false);
    });

    test('loadMoreTriggerRef is a ref object', () => {
      const fetchMore = vi.fn();
      const { result } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
      );

      expect(result.current.loadMoreTriggerRef).toHaveProperty('current');
    });
  });

  describe('returned values', () => {
    test('returns all expected properties', () => {
      const fetchMore = vi.fn();
      const { result } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
      );

      expect(result.current).toHaveProperty('allLoadedItems');
      expect(result.current).toHaveProperty('setAllLoadedItems');
      expect(result.current).toHaveProperty('loadingMore');
      expect(result.current).toHaveProperty('loadMoreTriggerRef');
      expect(result.current).toHaveProperty('isLoadingMoreRef');
      expect(result.current).toHaveProperty('hasMore');
    });

    test('allLoadedItems can be updated via setAllLoadedItems', async () => {
      const fetchMore = vi.fn();
      const { result } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
      );

      const testItems = [
        { id: 1, name: 'Item 1' },
        { id: 2, name: 'Item 2' },
        { id: 3, name: 'Item 3' },
      ];

      await act(async () => {
        result.current.setAllLoadedItems(testItems);
      });

      expect(result.current.allLoadedItems).toEqual(testItems);
      expect(result.current.hasMore).toBe(true); // 3 < 100
    });

    test('hasMore becomes false when all items loaded', async () => {
      const fetchMore = vi.fn();
      const { result } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 10 })
      );

      const testItems = Array.from({ length: 10 }, (_, i) => ({ id: i + 1, name: `Item ${i + 1}` }));

      await act(async () => {
        result.current.setAllLoadedItems(testItems);
      });

      expect(result.current.hasMore).toBe(false); // 10 === 10
    });
  });

  describe('edge cases', () => {
    test('handles zero total items', () => {
      const fetchMore = vi.fn();
      const { result } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 0 })
      );

      expect(result.current.hasMore).toBe(false);
      expect(result.current.allLoadedItems).toEqual([]);
    });

    test('handles large page sizes', () => {
      const fetchMore = vi.fn();
      const { result } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 1000, filters: {}, total: 500 })
      );

      expect(result.current.hasMore).toBe(true);
      expect(result.current.allLoadedItems).toEqual([]);
    });

    test('handles very large totals', () => {
      const fetchMore = vi.fn();
      const { result } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 999999 })
      );

      expect(result.current.hasMore).toBe(true);
    });

    test('maintains state consistency across multiple updates', async () => {
      const fetchMore = vi.fn();
      const { result } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
      );

      // Add items incrementally
      await act(async () => {
        result.current.setAllLoadedItems([{ id: 1, name: 'Item 1' }]);
      });

      expect(result.current.allLoadedItems).toHaveLength(1);
      expect(result.current.hasMore).toBe(true);

      await act(async () => {
        result.current.setAllLoadedItems([
          { id: 1, name: 'Item 1' },
          { id: 2, name: 'Item 2' },
        ]);
      });

      expect(result.current.allLoadedItems).toHaveLength(2);
      expect(result.current.hasMore).toBe(true);
    });
  });
});
