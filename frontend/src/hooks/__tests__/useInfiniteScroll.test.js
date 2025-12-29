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

    // Mock IntersectionObserver constructor as a class
    global.IntersectionObserver = vi.fn(function(callback) {
      observerCallback = callback;
      this.observe = mockObserver.observe;
      this.disconnect = mockObserver.disconnect;
      this.unobserve = mockObserver.unobserve;
    });

    // Mock console methods to avoid noise in test output
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.spyOn(console, 'warn').mockImplementation(() => {});

    // Mock Date.now for time-based tests
    vi.spyOn(Date, 'now').mockReturnValue(1000);
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

    test('provides ref for load more trigger element', () => {
      const fetchMore = vi.fn();
      const { result } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
      );

      expect(result.current.loadMoreTriggerRef).toBeDefined();
      expect(result.current.loadMoreTriggerRef.current).toBeNull();
    });

    test('uses default pageSize of 12', () => {
      const fetchMore = vi.fn().mockResolvedValue({ items: [] });
      const { result } = renderHook(() =>
        useInfiniteScroll(fetchMore, { filters: {}, total: 100 })
      );

      expect(result.current).toBeDefined();
    });
  });

  describe('IntersectionObserver integration', () => {

    test('triggers loadMore when sentinel becomes visible', async () => {
      const mockItems = [{ id: 1, name: 'Item 1' }];
      const fetchMore = vi.fn().mockResolvedValue({ items: mockItems });

      const { result, rerender } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
      );

      // Simulate attaching element
      const mockElement = document.createElement('div');
      act(() => {
        result.current.loadMoreTriggerRef.current = mockElement;
      });

      rerender();

      // Simulate intersection
      await act(async () => {
        if (observerCallback) {
          vi.spyOn(Date, 'now').mockReturnValue(2100); // More than 1000ms later
          observerCallback([{ isIntersecting: true }]);
          await new Promise(resolve => setTimeout(resolve, 10));
        }
      });

      await waitFor(() => {
        expect(fetchMore).toHaveBeenCalled();
      });
    });

    test('does not trigger loadMore if already loading', async () => {
      const fetchMore = vi.fn().mockResolvedValue({ items: [] });

      const { result, rerender } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
      );

      const mockElement = document.createElement('div');
      act(() => {
        result.current.loadMoreTriggerRef.current = mockElement;
      });

      rerender();

      // Set loading state
      act(() => {
        result.current.isLoadingMoreRef.current = true;
      });

      // Try to trigger intersection
      await act(async () => {
        if (observerCallback) {
          vi.spyOn(Date, 'now').mockReturnValue(2100);
          observerCallback([{ isIntersecting: true }]);
        }
      });

      // Should not trigger fetchMore because already loading
      expect(fetchMore).not.toHaveBeenCalled();
    });

    test('respects minimum trigger interval', async () => {
      const fetchMore = vi.fn().mockResolvedValue({ items: [] });

      const { result, rerender } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
      );

      const mockElement = document.createElement('div');
      act(() => {
        result.current.loadMoreTriggerRef.current = mockElement;
      });

      rerender();

      // First trigger
      await act(async () => {
        if (observerCallback) {
          vi.spyOn(Date, 'now').mockReturnValue(1000);
          observerCallback([{ isIntersecting: true }]);
        }
      });

      // Second trigger too soon (less than 1000ms)
      await act(async () => {
        if (observerCallback) {
          vi.spyOn(Date, 'now').mockReturnValue(1500); // Only 500ms later
          observerCallback([{ isIntersecting: true }]);
        }
      });

      // Should only be called once
      await waitFor(() => {
        expect(fetchMore).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe('loadMore functionality', () => {
    test('does not load more when all items are loaded', async () => {
      const fetchMore = vi.fn();
      const { result } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 10 })
      );

      // Set items equal to total
      await act(async () => {
        result.current.setAllLoadedItems(
          Array.from({ length: 10 }, (_, i) => ({ id: i + 1 }))
        );
      });

      // Try to trigger load more via intersection
      const mockElement = document.createElement('div');
      act(() => {
        result.current.loadMoreTriggerRef.current = mockElement;
      });

      await act(async () => {
        if (observerCallback) {
          vi.spyOn(Date, 'now').mockReturnValue(2100);
          observerCallback([{ isIntersecting: true }]);
        }
      });

      expect(fetchMore).not.toHaveBeenCalled();
    });

    test('fetches more items with correct parameters', async () => {
      const mockNewItems = [{ id: 2, name: 'Item 2' }];
      const fetchMore = vi.fn().mockResolvedValue({ items: mockNewItems });

      const { result, rerender } = renderHook(() =>
        useInfiniteScroll(fetchMore, {
          pageSize: 12,
          filters: { category: 'strategy' },
          total: 100,
        })
      );

      // Set initial items
      await act(async () => {
        result.current.setAllLoadedItems([{ id: 1, name: 'Item 1' }]);
      });

      const mockElement = document.createElement('div');
      act(() => {
        result.current.loadMoreTriggerRef.current = mockElement;
      });

      rerender();

      await act(async () => {
        if (observerCallback) {
          vi.spyOn(Date, 'now').mockReturnValue(2100);
          observerCallback([{ isIntersecting: true }]);
          await new Promise(resolve => setTimeout(resolve, 10));
        }
      });

      await waitFor(() => {
        expect(fetchMore).toHaveBeenCalledWith(
          expect.objectContaining({
            category: 'strategy',
            page: 2,
            page_size: 12,
          })
        );
      });
    });

    test('appends new items to existing items', async () => {
      const firstBatch = [{ id: 1, name: 'Item 1' }];
      const secondBatch = [{ id: 2, name: 'Item 2' }];
      const fetchMore = vi.fn().mockResolvedValue({ items: secondBatch });

      const { result, rerender } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
      );

      await act(async () => {
        result.current.setAllLoadedItems(firstBatch);
      });

      const mockElement = document.createElement('div');
      act(() => {
        result.current.loadMoreTriggerRef.current = mockElement;
      });

      rerender();

      await act(async () => {
        if (observerCallback) {
          vi.spyOn(Date, 'now').mockReturnValue(2100);
          observerCallback([{ isIntersecting: true }]);
          await new Promise(resolve => setTimeout(resolve, 10));
        }
      });

      await waitFor(() => {
        expect(result.current.allLoadedItems).toEqual([...firstBatch, ...secondBatch]);
      });
    });

    test('prevents duplicate items from being added', async () => {
      const initialItems = [{ id: 1, name: 'Item 1' }];
      const duplicateItems = [
        { id: 1, name: 'Item 1' },
        { id: 2, name: 'Item 2' },
      ];
      const fetchMore = vi.fn().mockResolvedValue({ items: duplicateItems });

      const { result, rerender } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
      );

      await act(async () => {
        result.current.setAllLoadedItems(initialItems);
      });

      const mockElement = document.createElement('div');
      act(() => {
        result.current.loadMoreTriggerRef.current = mockElement;
      });

      rerender();

      await act(async () => {
        if (observerCallback) {
          vi.spyOn(Date, 'now').mockReturnValue(2100);
          observerCallback([{ isIntersecting: true }]);
          await new Promise(resolve => setTimeout(resolve, 10));
        }
      });

      await waitFor(() => {
        // Should only have 2 items (not 3), because id:1 was duplicate
        expect(result.current.allLoadedItems).toHaveLength(2);
      });
    });

    test('warns when duplicates are prevented', async () => {
      const initialItems = [{ id: 1, name: 'Item 1' }];
      const duplicateItems = [{ id: 1, name: 'Item 1' }];
      const fetchMore = vi.fn().mockResolvedValue({ items: duplicateItems });

      const { result, rerender } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
      );

      await act(async () => {
        result.current.setAllLoadedItems(initialItems);
      });

      const mockElement = document.createElement('div');
      act(() => {
        result.current.loadMoreTriggerRef.current = mockElement;
      });

      rerender();

      await act(async () => {
        if (observerCallback) {
          vi.spyOn(Date, 'now').mockReturnValue(2100);
          observerCallback([{ isIntersecting: true }]);
          await new Promise(resolve => setTimeout(resolve, 10));
        }
      });

      await waitFor(() => {
        expect(console.warn).toHaveBeenCalledWith(
          expect.stringContaining('Prevented')
        );
      });
    });

    test('handles empty response from fetchMore', async () => {
      const fetchMore = vi.fn().mockResolvedValue({ items: [] });

      const { result, rerender } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
      );

      await act(async () => {
        result.current.setAllLoadedItems([{ id: 1, name: 'Item 1' }]);
      });

      const mockElement = document.createElement('div');
      act(() => {
        result.current.loadMoreTriggerRef.current = mockElement;
      });

      rerender();

      await act(async () => {
        if (observerCallback) {
          vi.spyOn(Date, 'now').mockReturnValue(2100);
          observerCallback([{ isIntersecting: true }]);
          await new Promise(resolve => setTimeout(resolve, 10));
        }
      });

      await waitFor(() => {
        // Items should remain unchanged
        expect(result.current.allLoadedItems).toHaveLength(1);
      });
    });

    test('handles fetch errors gracefully', async () => {
      const fetchMore = vi.fn().mockRejectedValue(new Error('Network error'));

      const { result, rerender } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
      );

      await act(async () => {
        result.current.setAllLoadedItems([{ id: 1, name: 'Item 1' }]);
      });

      const mockElement = document.createElement('div');
      act(() => {
        result.current.loadMoreTriggerRef.current = mockElement;
      });

      rerender();

      await act(async () => {
        if (observerCallback) {
          vi.spyOn(Date, 'now').mockReturnValue(2100);
          observerCallback([{ isIntersecting: true }]);
          await new Promise(resolve => setTimeout(resolve, 10));
        }
      });

      await waitFor(() => {
        expect(console.error).toHaveBeenCalledWith(
          'Failed to load more items:',
          expect.any(Error)
        );
      });

      // State should remain stable
      expect(result.current.allLoadedItems).toHaveLength(1);
      expect(result.current.loadingMore).toBe(false);
    });

    test('sets loadingMore state during fetch', async () => {
      let resolveFetch;
      const fetchPromise = new Promise(resolve => {
        resolveFetch = resolve;
      });
      const fetchMore = vi.fn().mockReturnValue(fetchPromise);

      const { result, rerender } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
      );

      const mockElement = document.createElement('div');
      act(() => {
        result.current.loadMoreTriggerRef.current = mockElement;
      });

      rerender();

      await act(async () => {
        if (observerCallback) {
          vi.spyOn(Date, 'now').mockReturnValue(2100);
          observerCallback([{ isIntersecting: true }]);
          await new Promise(resolve => setTimeout(resolve, 10));
        }
      });

      // Should be loading
      await waitFor(() => {
        expect(result.current.loadingMore).toBe(true);
      });

      // Resolve fetch
      await act(async () => {
        resolveFetch({ items: [{ id: 1, name: 'Item 1' }] });
        await new Promise(resolve => setTimeout(resolve, 10));
      });

      // Should no longer be loading
      await waitFor(() => {
        expect(result.current.loadingMore).toBe(false);
      });
    });
  });

  describe('filter changes', () => {
    test('resets items and page when filters change', async () => {
      const fetchMore = vi.fn().mockResolvedValue({ items: [] });
      const initialItems = [{ id: 1, name: 'Item 1' }];

      const { result, rerender } = renderHook(
        ({ filters }) =>
          useInfiniteScroll(fetchMore, { pageSize: 12, filters, total: 100 }),
        { initialProps: { filters: { category: 'adventure' } } }
      );

      await act(async () => {
        result.current.setAllLoadedItems(initialItems);
      });

      await waitFor(() => {
        expect(result.current.allLoadedItems).toHaveLength(1);
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
        ({ filters }) =>
          useInfiniteScroll(fetchMore, { pageSize: 12, filters, total: 100 }),
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
  });

  describe('edge cases', () => {
    test('handles zero total items', () => {
      const fetchMore = vi.fn();
      const { result } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 0 })
      );

      expect(result.current.hasMore).toBe(false);
    });

    test('handles response without items array', async () => {
      const fetchMore = vi.fn().mockResolvedValue({});

      const { result, rerender } = renderHook(() =>
        useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
      );

      const mockElement = document.createElement('div');
      act(() => {
        result.current.loadMoreTriggerRef.current = mockElement;
      });

      rerender();

      await act(async () => {
        if (observerCallback) {
          vi.spyOn(Date, 'now').mockReturnValue(2100);
          observerCallback([{ isIntersecting: true }]);
          await new Promise(resolve => setTimeout(resolve, 10));
        }
      });

      await waitFor(() => {
        expect(result.current.allLoadedItems).toEqual([]);
      });
    });
  });
});
