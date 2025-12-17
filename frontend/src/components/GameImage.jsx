// src/components/GameImage.jsx
import React, { useState } from "react";
import { imageProxyUrl, generateSrcSet } from "../config/api";
import { useImageLazyLoad } from "../hooks/useLazyLoad";

/**
 * Optimized image component with progressive loading, error handling, and CLS prevention
 *
 * Phase 2 enhancements:
 * - Responsive images with srcset for different screen sizes
 * - Advanced Intersection Observer lazy loading (loads 100px before visible)
 * - Blur-up loading effect for smoother perceived performance
 *
 * @param {string} url - Image URL to load
 * @param {string} alt - Alt text for accessibility
 * @param {string} className - CSS classes for the image element
 * @param {string} fallbackClass - CSS classes for fallback/placeholder
 * @param {string} loading - Native lazy loading ("lazy" | "eager")
 * @param {string} fetchPriority - Resource fetch priority ("high" | "low" | "auto")
 * @param {number} width - Explicit width to prevent layout shift
 * @param {number} height - Explicit height to prevent layout shift
 * @param {string} aspectRatio - CSS aspect ratio (e.g., "1/1" for square)
 * @param {string} sizes - Sizes attribute for responsive images (e.g., "(max-width: 640px) 100vw, 400px")
 * @param {boolean} useResponsive - Enable responsive images with srcset (default: true)
 * @param {boolean} useIntersectionObserver - Use Intersection Observer for lazy loading (default: true for lazy images)
 */
export default function GameImage({
  url,
  alt,
  className,
  fallbackClass,
  loading = "lazy",
  fetchPriority = "auto",
  width,
  height,
  aspectRatio = "1/1", // Default to square for board game covers
  sizes = "(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 400px",
  useResponsive = true,
  useIntersectionObserver = true
}) {
  const [imageError, setImageError] = useState(false);
  const [imageLoaded, setImageLoaded] = useState(false);

  // Advanced lazy loading with Intersection Observer
  const isLazy = loading === "lazy";
  const { ref: lazyRef, shouldLoad } = useImageLazyLoad({
    enabled: isLazy && useIntersectionObserver
  });

  // For eager loading or when IntersectionObserver is disabled, always load
  const shouldLoadImage = !isLazy || !useIntersectionObserver || shouldLoad;

  const handleImageError = () => {
    setImageError(true);
  };

  const handleImageLoad = () => {
    setImageLoaded(true);
  };

  // Generate responsive srcset if enabled and URL is BGG image
  const srcSet = useResponsive ? generateSrcSet(url) : null;

  if (!url || imageError) {
    return (
      <div
        ref={lazyRef}
        className={fallbackClass || "w-16 h-16 sm:w-20 sm:h-20 bg-slate-200 rounded-xl flex flex-col items-center justify-center text-slate-700 text-xs sm:text-sm transition-colors hover:bg-slate-300"}
        style={{ aspectRatio }}
      >
        <svg className="w-6 h-6 sm:w-8 sm:h-8 mb-1 sm:mb-2" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
          <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
        </svg>
        <span className="font-medium">No Image</span>
      </div>
    );
  }

  return (
    <div ref={lazyRef} className="relative" style={{ aspectRatio }}>
      {/* Blur-up loading placeholder with gradient */}
      {!imageLoaded && shouldLoadImage && (
        <div
          className={`absolute inset-0 ${fallbackClass || "bg-gradient-to-br from-slate-200 via-slate-100 to-slate-200 rounded-xl flex items-center justify-center"}`}
          style={{
            animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
            backdropFilter: 'blur(10px)'
          }}
        >
          <svg className="w-8 h-8 text-slate-400" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
            <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
          </svg>
        </div>
      )}

      {/* Only render img when shouldLoadImage is true (for IntersectionObserver) */}
      {shouldLoadImage && (
        <img
          src={imageProxyUrl(url)}
          srcSet={srcSet}
          sizes={srcSet ? sizes : undefined}
          alt={alt || "Game cover image"}
          className={`${className} ${imageLoaded ? 'opacity-100' : 'opacity-0'} transition-opacity duration-500 ease-out`}
          loading={loading}
          fetchpriority={fetchPriority}
          onError={handleImageError}
          onLoad={handleImageLoad}
          decoding="async"
          width={width}
          height={height}
          style={{ aspectRatio }}
        />
      )}
    </div>
  );
}
