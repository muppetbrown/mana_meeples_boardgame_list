// src/hooks/useScrollBehavior.js
import { useState, useEffect, useRef } from 'react';

/**
 * Custom hook for managing scroll-based UI behaviors
 * Handles:
 * - Header visibility (hide/show on scroll)
 * - Sticky toolbar state
 * - Scroll to top button visibility
 *
 * @param {boolean} isLoading - Whether content is currently loading (prevents scroll jank)
 * @returns {Object} Scroll behavior state and refs
 */
export function useScrollBehavior(isLoading = false) {
  const [showScrollTop, setShowScrollTop] = useState(false);
  const [isHeaderVisible, setIsHeaderVisible] = useState(true);
  const [isSticky, setIsSticky] = useState(false);

  const lastScrollY = useRef(0);
  const lastToggleY = useRef(0); // Track where we last toggled to prevent oscillation
  const headerRef = useRef(null);
  const toolbarRef = useRef(null);
  const ticking = useRef(false);
  const isLoadingRef = useRef(isLoading);

  // Update loading ref when loading state changes
  useEffect(() => {
    isLoadingRef.current = isLoading;
  }, [isLoading]);

  // Scroll to top on initial mount
  useEffect(() => {
    // Force scroll to top on mount to prevent browser scroll restoration
    window.scrollTo(0, 0);
    setIsHeaderVisible(true);
    setIsSticky(false);
  }, []);

  // Handle scroll for header hide/show and sticky toolbar
  useEffect(() => {
    const handleScroll = () => {
      // CRITICAL: Skip ALL scroll handling during loading to prevent freeze/jump
      if (isLoadingRef.current) {
        return;
      }

      if (!ticking.current) {
        window.requestAnimationFrame(() => {
          const currentScrollY = window.scrollY;
          const scrollDelta = currentScrollY - lastScrollY.current;
          const headerHeight = headerRef.current?.offsetHeight || 0;
          const SCROLL_THRESHOLD = 15; // Minimum scroll distance before toggling
          const TOGGLE_BUFFER = 50; // Prevent toggling again until we've scrolled this far

          // Show/hide scroll to top button with hysteresis to prevent flicker
          if (currentScrollY > 450) {
            setShowScrollTop(true);
          } else if (currentScrollY < 350) {
            setShowScrollTop(false);
          }
          // Between 350-450px: maintain current state (no flicker)

          // Always show header when at the very top of the page
          if (currentScrollY < 50) {
            setIsHeaderVisible(true);
            setIsSticky(false);
            lastToggleY.current = currentScrollY;
          }
          // Header hide/show on scroll direction with threshold
          else if (currentScrollY > headerHeight + 20) {
            // Only toggle if we've scrolled enough since last toggle
            const distanceFromLastToggle = Math.abs(currentScrollY - lastToggleY.current);

            if (distanceFromLastToggle > TOGGLE_BUFFER) {
              if (scrollDelta > SCROLL_THRESHOLD) {
                // Scrolling down significantly
                setIsHeaderVisible(false);
                setIsSticky(true);
                lastToggleY.current = currentScrollY;
              } else if (scrollDelta < -SCROLL_THRESHOLD) {
                // Scrolling up significantly
                setIsHeaderVisible(true);
                lastToggleY.current = currentScrollY;
              }
            }
          } else {
            // Near top - always show header
            setIsHeaderVisible(true);
            setIsSticky(false);
            lastToggleY.current = currentScrollY;
          }

          lastScrollY.current = currentScrollY;
          ticking.current = false;
        });

        ticking.current = true;
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return {
    showScrollTop,
    isHeaderVisible,
    isSticky,
    headerRef,
    toolbarRef,
  };
}
