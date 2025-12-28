// frontend/src/hooks/__tests__/useInfiniteScroll.test.js
import { renderHook, act, waitFor } from '@testing-library/react';
import { useInfiniteScroll } from '../useInfiniteScroll';

// Mock IntersectionObserver
class MockIntersectionObserver {
  constructor(callback) {
    this.callback = callback;
    this.elements = new Set();
  }

  observe(element) {
    this.elements.add(element);
    MockIntersectionObserver.instances.push(this);
  }

  disconnect() {
    this.elements.clear();
  }

  trigger(isIntersecting) {
    this.callback([{ isIntersecting, target: Array.from(this.elements)[0] }]);
  }

  static instances = [];
  static reset() {
    MockIntersectionObserver.instances = [];
  }
}

global.IntersectionObserver = MockIntersectionObserver;

describe('useInfiniteScroll Hook', () => {
  beforeEach(() => {
    MockIntersectionObserver.reset();
    jest.clearAllMocks();
  });

  test('initializes with empty state', () => {
    const fetchMore = jest.fn();
    const { result } = renderHook(() =>
      useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
    );

    expect(result.current.allLoadedItems).toEqual([]);
    expect(result.current.loadingMore).toBe(false);
    expect(result.current.hasMore).toBe(true);
  });

  test('loads more items when triggered', async () => {
    const mockItems = [
      { id: 1, title: 'Game 1' },
      { id: 2, title: 'Game 2' },
    ];

    const fetchMore = jest.fn().mockResolvedValue({
      items: mockItems,
      total: 100,
      page: 2,
    });

    const { result } = renderHook(() =>
      useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
    );

    // Trigger intersection
    const observer = MockIntersectionObserver.instances[0];

    await act(async () => {
      observer.trigger(true);
      await waitFor(() => expect(fetchMore).toHaveBeenCalled());
    });

    await waitFor(() => {
      expect(result.current.allLoadedItems).toHaveLength(2);
      expect(result.current.allLoadedItems).toEqual(mockItems);
    });
  });

  test('prevents duplicate items from being added', async () => {
    const firstBatch = [
      { id: 1, title: 'Game 1' },
      { id: 2, title: 'Game 2' },
    ];

    const duplicateBatch = [
      { id: 2, title: 'Game 2' }, // Duplicate
      { id: 3, title: 'Game 3' }, // New
    ];

    const fetchMore = jest.fn()
      .mockResolvedValueOnce({ items: firstBatch, total: 100, page: 2 })
      .mockResolvedValueOnce({ items: duplicateBatch, total: 100, page: 3 });

    const { result } = renderHook(() =>
      useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
    );

    const observer = MockIntersectionObserver.instances[0];

    // First load
    await act(async () => {
      observer.trigger(true);
      await waitFor(() => expect(fetchMore).toHaveBeenCalledTimes(1));
    });

    await waitFor(() => {
      expect(result.current.allLoadedItems).toHaveLength(2);
    });

    // Wait for debounce interval
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 1100));
    });

    // Second load with duplicate
    await act(async () => {
      observer.trigger(true);
      await waitFor(() => expect(fetchMore).toHaveBeenCalledTimes(2));
    });

    await waitFor(() => {
      // Should have 3 unique items (not 4)
      expect(result.current.allLoadedItems).toHaveLength(3);
      expect(result.current.allLoadedItems.map(i => i.id)).toEqual([1, 2, 3]);
    });
  });

  test('resets state when filters change', async () => {
    const fetchMore = jest.fn().mockResolvedValue({
      items: [{ id: 1, title: 'Game 1' }],
      total: 100,
    });

    const { result, rerender } = renderHook(
      ({ filters }) => useInfiniteScroll(fetchMore, { pageSize: 12, filters, total: 100 }),
      { initialProps: { filters: { category: 'STRATEGY' } } }
    );

    const observer = MockIntersectionObserver.instances[0];

    // Load some items
    await act(async () => {
      observer.trigger(true);
      await waitFor(() => expect(fetchMore).toHaveBeenCalled());
    });

    await waitFor(() => {
      expect(result.current.allLoadedItems).toHaveLength(1);
    });

    // Change filters
    await act(async () => {
      rerender({ filters: { category: 'PARTY' } });
    });

    // Items should be reset
    expect(result.current.allLoadedItems).toEqual([]);
  });

  test('indicates when there are more items to load', () => {
    const fetchMore = jest.fn();

    const { result, rerender } = renderHook(
      ({ total, loadedCount }) => {
        const hook = useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total });
        // Simulate loaded items
        if (loadedCount > 0) {
          hook.allLoadedItems = Array.from({ length: loadedCount }, (_, i) => ({ id: i }));
        }
        return hook;
      },
      { initialProps: { total: 100, loadedCount: 0 } }
    );

    expect(result.current.hasMore).toBe(true);

    // Simulate loading all items
    rerender({ total: 100, loadedCount: 100 });
    expect(result.current.hasMore).toBe(false);
  });

  test('does not load more when already loading', async () => {
    const fetchMore = jest.fn().mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve({ items: [], total: 100 }), 100))
    );

    const { result } = renderHook(() =>
      useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
    );

    const observer = MockIntersectionObserver.instances[0];

    // Trigger multiple times quickly
    await act(async () => {
      observer.trigger(true);
      observer.trigger(true);
      observer.trigger(true);
      await new Promise(resolve => setTimeout(resolve, 150));
    });

    // Should only be called once
    expect(fetchMore).toHaveBeenCalledTimes(1);
  });

  test('does not load more when all items are loaded', async () => {
    const fetchMore = jest.fn();

    const { result } = renderHook(() =>
      useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 0 })
    );

    const observer = MockIntersectionObserver.instances[0];

    await act(async () => {
      observer.trigger(true);
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    expect(fetchMore).not.toHaveBeenCalled();
    expect(result.current.hasMore).toBe(false);
  });

  test('handles fetch errors gracefully', async () => {
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
    const fetchMore = jest.fn().mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() =>
      useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
    );

    const observer = MockIntersectionObserver.instances[0];

    await act(async () => {
      observer.trigger(true);
      await waitFor(() => expect(fetchMore).toHaveBeenCalled());
    });

    await waitFor(() => {
      expect(result.current.loadingMore).toBe(false);
      expect(consoleErrorSpy).toHaveBeenCalledWith('Failed to load more items:', expect.any(Error));
    });

    consoleErrorSpy.mockRestore();
  });

  test('passes correct parameters to fetchMore', async () => {
    const fetchMore = jest.fn().mockResolvedValue({
      items: [{ id: 1, title: 'Game 1' }],
      total: 100,
    });

    const filters = { category: 'STRATEGY', q: 'Catan' };

    renderHook(() =>
      useInfiniteScroll(fetchMore, { pageSize: 24, filters, total: 100 })
    );

    const observer = MockIntersectionObserver.instances[0];

    await act(async () => {
      observer.trigger(true);
      await waitFor(() => expect(fetchMore).toHaveBeenCalled());
    });

    expect(fetchMore).toHaveBeenCalledWith({
      category: 'STRATEGY',
      q: 'Catan',
      page: 2,
      page_size: 24,
    });
  });

  test('provides ref for load more trigger element', () => {
    const fetchMore = jest.fn();
    const { result } = renderHook(() =>
      useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
    );

    expect(result.current.loadMoreTriggerRef).toBeDefined();
    expect(result.current.loadMoreTriggerRef.current).toBeNull();
  });
});
