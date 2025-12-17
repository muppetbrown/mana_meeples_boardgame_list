// frontend/src/hooks/useLazyLoad.js
/**
 * Custom hook for advanced lazy loading with Intersection Observer
 * Loads images slightly before they enter the viewport for smoother UX
 */
import { useEffect, useRef, useState } from 'react';

/**
 * Hook for lazy loading images with Intersection Observer
 *
 * @param {Object} options - Configuration options
 * @param {string} options.rootMargin - Margin around root (e.g., '50px' loads 50px before visible)
 * @param {number} options.threshold - Percentage of visibility to trigger (0.0 to 1.0)
 * @param {boolean} options.enabled - Whether lazy loading is enabled
 * @returns {Object} - { ref, isVisible, hasBeenVisible }
 */
export function useLazyLoad({
  rootMargin = '50px',
  threshold = 0.01,
  enabled = true
} = {}) {
  const ref = useRef(null);
  const [isVisible, setIsVisible] = useState(!enabled); // If disabled, always visible
  const [hasBeenVisible, setHasBeenVisible] = useState(!enabled);

  useEffect(() => {
    // Skip if not enabled or no IntersectionObserver support
    if (!enabled || !ref.current || typeof IntersectionObserver === 'undefined') {
      return;
    }

    const element = ref.current;

    const observer = new IntersectionObserver(
      ([entry]) => {
        const visible = entry.isIntersecting;
        setIsVisible(visible);

        // Once visible, mark as "has been visible" (for one-time loading)
        if (visible && !hasBeenVisible) {
          setHasBeenVisible(true);
        }
      },
      {
        rootMargin,
        threshold
      }
    );

    observer.observe(element);

    return () => {
      if (element) {
        observer.unobserve(element);
      }
    };
  }, [rootMargin, threshold, enabled, hasBeenVisible]);

  return { ref, isVisible, hasBeenVisible };
}

/**
 * Hook specifically for image lazy loading
 * Returns whether the image should be loaded (once visible, always true)
 *
 * @param {Object} options - Configuration options
 * @returns {Object} - { ref, shouldLoad }
 */
export function useImageLazyLoad(options = {}) {
  const { ref, hasBeenVisible } = useLazyLoad({
    rootMargin: '400px', // Load images 400px before visible for smooth scrolling
    threshold: 0.01,
    ...options
  });

  return { ref, shouldLoad: hasBeenVisible };
}
