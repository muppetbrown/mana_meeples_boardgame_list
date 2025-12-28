// frontend/src/hooks/__tests__/useInfiniteScroll.test.js
import { describe, test, expect, beforeEach, vi } from 'vitest';
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
    vi.clearAllMocks();
  });

  test('initializes with empty state', () => {
    const fetchMore = vi.fn();
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

    const fetchMore = vi.fn().mockResolvedValue({
      items: mockItems,
      total: 100,
      page: 2,
    });

    const { result } = renderHook(() =>
      useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
    );

    const observer = MockIntersectionObserver.instances[0];

    await act(async () => {
      observer.trigger(true);
      await waitFor(() => expect(fetchMore).toHaveBeenCalled());
    });

    await waitFor(() => {
      expect(result.current.allLoadedItems).toHaveLength(2);
    });
  });

  test('provides ref for load more trigger element', () => {
    const fetchMore = vi.fn();
    const { result } = renderHook(() =>
      useInfiniteScroll(fetchMore, { pageSize: 12, filters: {}, total: 100 })
    );

    expect(result.current.loadMoreTriggerRef).toBeDefined();
  });
});
