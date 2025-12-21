// src/hooks/useInfiniteScroll.js
import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Custom hook for implementing infinite scroll with load more functionality
 * Uses Intersection Observer to detect when to load more items
 *
 * @param {Function} fetchMore - Async function to fetch more data (receives params object)
 * @param {Object} options - Configuration options
 * @param {number} options.pageSize - Number of items per page
 * @param {Object} options.filters - Current filter values
 * @param {number} options.total - Total number of items available
 * @returns {Object} Infinite scroll state and controls
 */
export function useInfiniteScroll(fetchMore, { pageSize = 12, filters = {}, total = 0 }) {
  const [allLoadedItems, setAllLoadedItems] = useState([]);
  const [page, setPage] = useState(1);
  const [loadingMore, setLoadingMore] = useState(false);
  const loadMoreTriggerRef = useRef(null);
  const isLoadingMoreRef = useRef(false);

  // Reset to page 1 and clear loaded items when filters change
  useEffect(() => {
    setPage(1);
    setAllLoadedItems([]);
  }, [JSON.stringify(filters)]); // eslint-disable-line react-hooks/exhaustive-deps

  // Load more function - Memoized to ensure Intersection Observer has latest filter values
  const loadMore = useCallback(async () => {
    // Prevent duplicate loads with multiple safety checks
    if (isLoadingMoreRef.current || allLoadedItems.length >= total) return;

    isLoadingMoreRef.current = true;
    setLoadingMore(true);
    const nextPage = page + 1;

    try {
      const params = { ...filters, page: nextPage, page_size: pageSize };
      const data = await fetchMore(params);

      // Prevent adding duplicate items by checking IDs
      if (data.items && data.items.length > 0) {
        setAllLoadedItems(prev => {
          const existingIds = new Set(prev.map(item => item.id));
          const newItems = data.items.filter(item => !existingIds.has(item.id));

          // Log if duplicates were prevented (helps with debugging)
          const duplicateCount = data.items.length - newItems.length;
          if (duplicateCount > 0) {
            console.warn(`Prevented ${duplicateCount} duplicate item(s) from being added to the list`);
          }

          // Only update if we have new items
          if (newItems.length > 0) {
            return [...prev, ...newItems];
          }
          return prev;
        });
        setPage(nextPage);
      }
    } catch (e) {
      console.error("Failed to load more items:", e);
    } finally {
      isLoadingMoreRef.current = false;
      setLoadingMore(false);
    }
  }, [page, filters, total, allLoadedItems.length, fetchMore, pageSize]);

  // Infinite scroll: Intersection Observer for auto-loading more items
  useEffect(() => {
    const sentinel = loadMoreTriggerRef.current;
    if (!sentinel) return;

    // Use a ref to track when the observer last triggered to prevent rapid-fire calls
    let lastTriggerTime = 0;
    const MIN_TRIGGER_INTERVAL = 1000; // 1000ms to prevent freeze during loading

    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        const now = Date.now();

        // CRITICAL: Only trigger if NOT currently loading AND enough time has passed
        // This prevents the freeze/jump issue during scroll
        if (
          entry.isIntersecting &&
          !isLoadingMoreRef.current &&
          (now - lastTriggerTime) > MIN_TRIGGER_INTERVAL
        ) {
          lastTriggerTime = now;
          loadMore();
        }
      },
      {
        root: null, // viewport
        rootMargin: '200px', // Trigger 200px before reaching sentinel
        threshold: 0,
      }
    );

    observer.observe(sentinel);

    return () => {
      observer.disconnect();
    };
  }, [loadMore]);

  return {
    allLoadedItems,
    setAllLoadedItems,
    loadingMore,
    loadMoreTriggerRef,
    isLoadingMoreRef,
    hasMore: allLoadedItems.length < total,
  };
}
