// frontend/src/hooks/__tests__/useInfiniteScroll.test.js
import { describe, test, expect, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useInfiniteScroll } from '../useInfiniteScroll';

describe('useInfiniteScroll Hook', () => {
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
  });
});
