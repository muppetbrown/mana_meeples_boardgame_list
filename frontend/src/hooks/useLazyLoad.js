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
 * Detect network connection quality and return appropriate rootMargin
 * Uses Network Information API with fallback to default values
 *
 * @returns {string} - rootMargin value based on connection quality
 */
function getNetworkAwareMargin() {
  // Check if Network Information API is available
  if (typeof navigator === 'undefined' || !navigator.connection) {
    return '400px'; // Default for browsers without Network Information API
  }

  const connection = navigator.connection;

  // Check for Save Data mode (user has enabled data saving)
  if (connection.saveData) {
    return '100px'; // Minimal pre-loading for data saver mode
  }

  // Check effective connection type
  const effectiveType = connection.effectiveType;

  // Adjust margin based on connection speed
  // slow-2g, 2g: 100px (very conservative)
  // 3g: 200px (moderate pre-loading)
  // 4g: 400px (aggressive pre-loading for smooth UX)
  switch (effectiveType) {
    case 'slow-2g':
    case '2g':
      return '100px';
    case '3g':
      return '200px';
    case '4g':
    default:
      return '400px';
  }
}

/**
 * Hook specifically for image lazy loading
 * Returns whether the image should be loaded (once visible, always true)
 * Network-aware: adjusts pre-loading distance based on connection quality
 *
 * @param {Object} options - Configuration options
 * @returns {Object} - { ref, shouldLoad }
 */
export function useImageLazyLoad(options = {}) {
  const networkAwareMargin = getNetworkAwareMargin();

  const { ref, hasBeenVisible } = useLazyLoad({
    rootMargin: networkAwareMargin, // Network-aware pre-loading distance
    threshold: 0.01,
    ...options
  });

  return { ref, shouldLoad: hasBeenVisible };
}
