// src/hooks/__tests__/useScrollBehavior.test.js
import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useScrollBehavior } from '../useScrollBehavior';

describe('useScrollBehavior Hook', () => {
  let scrollYValue = 0;

  beforeEach(() => {
    // Mock window.scrollY
    scrollYValue = 0;
    Object.defineProperty(window, 'scrollY', {
      configurable: true,
      get: () => scrollYValue,
    });

    // Mock window.scrollTo
    window.scrollTo = vi.fn();

    // Mock requestAnimationFrame - use setTimeout to properly handle async state updates
    global.requestAnimationFrame = vi.fn((cb) => {
      const id = setTimeout(() => cb(), 0);
      return id;
    });

    global.cancelAnimationFrame = vi.fn((id) => {
      clearTimeout(id);
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Initial state', () => {
    test('starts with header visible and no scroll-top button', () => {
      const { result } = renderHook(() => useScrollBehavior());

      expect(result.current.isHeaderVisible).toBe(true);
      expect(result.current.isSticky).toBe(false);
      expect(result.current.showScrollTop).toBe(false);
    });

    test('scrolls to top on mount', () => {
      renderHook(() => useScrollBehavior());

      expect(window.scrollTo).toHaveBeenCalledWith(0, 0);
    });

    test('provides header and toolbar refs', () => {
      const { result } = renderHook(() => useScrollBehavior());

      expect(result.current.headerRef).toBeDefined();
      expect(result.current.headerRef.current).toBeNull(); // Not attached yet
      expect(result.current.toolbarRef).toBeDefined();
      expect(result.current.toolbarRef.current).toBeNull();
    });
  });

  describe('Scroll to top button visibility', () => {
    test('shows button when scrolled past 450px', async () => {
      const { result } = renderHook(() => useScrollBehavior());

      act(() => {
        scrollYValue = 500;
        window.dispatchEvent(new Event('scroll'));
      });

      await waitFor(() => {
        expect(result.current.showScrollTop).toBe(true);
      });
    });

    test('hides button when scrolled below 350px', async () => {
      const { result } = renderHook(() => useScrollBehavior());

      // First scroll down
      act(() => {
        scrollYValue = 500;
        window.dispatchEvent(new Event('scroll'));
      });

      await waitFor(() => {
        expect(result.current.showScrollTop).toBe(true);
      });

      // Then scroll back up
      act(() => {
        scrollYValue = 300;
        window.dispatchEvent(new Event('scroll'));
      });

      await waitFor(() => {
        expect(result.current.showScrollTop).toBe(false);
      });
    });

    test('maintains state between 350px and 450px (hysteresis)', async () => {
      const { result } = renderHook(() => useScrollBehavior());

      // Scroll to 400px (in hysteresis zone)
      act(() => {
        scrollYValue = 400;
        window.dispatchEvent(new Event('scroll'));
      });

      await waitFor(() => {
        // Should remain false since we haven't crossed 450px yet
        expect(result.current.showScrollTop).toBe(false);
      });

      // Now scroll past 450px
      act(() => {
        scrollYValue = 500;
        window.dispatchEvent(new Event('scroll'));
      });

      await waitFor(() => {
        expect(result.current.showScrollTop).toBe(true);
      });

      // Scroll back into hysteresis zone
      act(() => {
        scrollYValue = 400;
        window.dispatchEvent(new Event('scroll'));
      });

      await waitFor(() => {
        // Should remain true since we haven't crossed 350px yet
        expect(result.current.showScrollTop).toBe(true);
      });
    });
  });

  describe('Header visibility on scroll', () => {
    test('hides header when scrolling down past threshold', async () => {
      const { result } = renderHook(() => useScrollBehavior());

      // Mock header height
      result.current.headerRef.current = { offsetHeight: 100 };

      // Scroll down significantly (past header height + 20 + scroll threshold)
      act(() => {
        scrollYValue = 200; // Past headerHeight (100) + 20 + SCROLL_THRESHOLD (15) + TOGGLE_BUFFER (50)
        window.dispatchEvent(new Event('scroll'));
      });

      await waitFor(() => {
        expect(result.current.isHeaderVisible).toBe(false);
        expect(result.current.isSticky).toBe(true);
      });
    });

    test('shows header when scrolling up past threshold', async () => {
      const { result } = renderHook(() => useScrollBehavior());

      result.current.headerRef.current = { offsetHeight: 100 };

      // First scroll down
      act(() => {
        scrollYValue = 200;
        window.dispatchEvent(new Event('scroll'));
      });

      await waitFor(() => {
        expect(result.current.isHeaderVisible).toBe(false);
      });

      // Then scroll up significantly
      act(() => {
        scrollYValue = 120;
        window.dispatchEvent(new Event('scroll'));
      });

      await waitFor(() => {
        expect(result.current.isHeaderVisible).toBe(true);
      });
    });

    test('always shows header when near top (< 50px)', async () => {
      const { result } = renderHook(() => useScrollBehavior());

      act(() => {
        scrollYValue = 30;
        window.dispatchEvent(new Event('scroll'));
      });

      await waitFor(() => {
        expect(result.current.isHeaderVisible).toBe(true);
        expect(result.current.isSticky).toBe(false);
      });
    });

    test('requires minimum scroll distance before toggling', async () => {
      const { result } = renderHook(() => useScrollBehavior());

      result.current.headerRef.current = { offsetHeight: 100 };

      // Small scroll (less than SCROLL_THRESHOLD of 15px)
      act(() => {
        scrollYValue = 150;
        window.dispatchEvent(new Event('scroll'));
      });

      await waitFor(() => {
        // Should not have changed
        expect(result.current.isHeaderVisible).toBe(true);
      });
    });
  });

  describe('Loading state handling', () => {
    test('skips scroll handling when loading', async () => {
      const { result } = renderHook(() => useScrollBehavior(true));

      const initialHeaderVisible = result.current.isHeaderVisible;

      act(() => {
        scrollYValue = 500;
        window.dispatchEvent(new Event('scroll'));
      });

      // Give it time to process (but it shouldn't)
      await new Promise((resolve) => setTimeout(resolve, 100));

      // State should not have changed
      expect(result.current.isHeaderVisible).toBe(initialHeaderVisible);
      expect(result.current.showScrollTop).toBe(false);
    });

    test('resumes scroll handling when loading completes', async () => {
      const { result, rerender } = renderHook(
        ({ isLoading }) => useScrollBehavior(isLoading),
        { initialProps: { isLoading: true } }
      );

      // Scroll while loading
      act(() => {
        scrollYValue = 500;
        window.dispatchEvent(new Event('scroll'));
      });

      // Should not update
      expect(result.current.showScrollTop).toBe(false);

      // Stop loading
      rerender({ isLoading: false });

      // Scroll again
      act(() => {
        scrollYValue = 500;
        window.dispatchEvent(new Event('scroll'));
      });

      await waitFor(() => {
        expect(result.current.showScrollTop).toBe(true);
      });
    });
  });

  describe('Request animation frame optimization', () => {
    test('uses requestAnimationFrame for scroll handling', () => {
      renderHook(() => useScrollBehavior());

      const rafCallsBefore = global.requestAnimationFrame.mock.calls.length;

      act(() => {
        scrollYValue = 100;
        window.dispatchEvent(new Event('scroll'));
      });

      const rafCallsAfter = global.requestAnimationFrame.mock.calls.length;

      expect(rafCallsAfter).toBeGreaterThan(rafCallsBefore);
    });

    test('prevents duplicate animation frames while ticking', async () => {
      renderHook(() => useScrollBehavior());

      // Reset the mock to track only calls from this test
      global.requestAnimationFrame.mockClear();

      act(() => {
        scrollYValue = 100;
        window.dispatchEvent(new Event('scroll'));
        window.dispatchEvent(new Event('scroll'));
        window.dispatchEvent(new Event('scroll'));
      });

      // Should only call rAF once despite multiple scroll events (while ticking is true)
      expect(global.requestAnimationFrame).toHaveBeenCalledTimes(1);

      // Wait for the frame to complete
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 10));
      });
    });
  });

  describe('Scroll event cleanup', () => {
    test('removes scroll listener on unmount', () => {
      const removeEventListenerSpy = vi.spyOn(window, 'removeEventListener');

      const { unmount } = renderHook(() => useScrollBehavior());

      unmount();

      expect(removeEventListenerSpy).toHaveBeenCalledWith('scroll', expect.any(Function));
    });
  });

  describe('Toggle buffer prevents oscillation', () => {
    test('prevents rapid toggling within buffer distance', async () => {
      const { result } = renderHook(() => useScrollBehavior());

      result.current.headerRef.current = { offsetHeight: 100 };

      // Initial scroll down past threshold
      act(() => {
        scrollYValue = 200;
        window.dispatchEvent(new Event('scroll'));
      });

      await waitFor(() => {
        expect(result.current.isHeaderVisible).toBe(false);
      });

      // Small scroll up (within TOGGLE_BUFFER of 50px)
      act(() => {
        scrollYValue = 180;
        window.dispatchEvent(new Event('scroll'));
      });

      // Should not toggle back yet
      expect(result.current.isHeaderVisible).toBe(false);

      // Larger scroll up (beyond TOGGLE_BUFFER)
      act(() => {
        scrollYValue = 140;
        window.dispatchEvent(new Event('scroll'));
      });

      await waitFor(() => {
        expect(result.current.isHeaderVisible).toBe(true);
      });
    });
  });

  describe('Passive event listener', () => {
    test('registers scroll listener with passive option', () => {
      const addEventListenerSpy = vi.spyOn(window, 'addEventListener');

      renderHook(() => useScrollBehavior());

      expect(addEventListenerSpy).toHaveBeenCalledWith(
        'scroll',
        expect.any(Function),
        { passive: true }
      );
    });
  });
});
