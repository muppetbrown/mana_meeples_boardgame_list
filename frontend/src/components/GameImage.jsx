// src/components/GameImage.jsx
import React, { useState } from "react";
import { imageProxyUrl } from "../api/client";

/**
 * Optimized image component with progressive loading, error handling, and CLS prevention
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
  aspectRatio = "1/1" // Default to square for board game covers
}) {
  const [imageError, setImageError] = useState(false);
  const [imageLoaded, setImageLoaded] = useState(false);

  const handleImageError = () => {
    setImageError(true);
  };

  const handleImageLoad = () => {
    setImageLoaded(true);
  };

  if (!url || imageError) {
    return (
      <div
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
    <div className="relative" style={{ aspectRatio }}>
      {/* Loading placeholder */}
      {!imageLoaded && (
        <div className={`absolute inset-0 ${fallbackClass || "bg-slate-200 rounded-xl flex items-center justify-center"} animate-pulse`}>
          <svg className="w-8 h-8 text-slate-400" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
            <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
          </svg>
        </div>
      )}

      <img
        src={imageProxyUrl(url)}
        alt={alt || "Game cover image"}
        className={`${className} ${imageLoaded ? 'opacity-100' : 'opacity-0'} transition-opacity duration-300`}
        loading={loading}
        fetchpriority={fetchPriority}
        onError={handleImageError}
        onLoad={handleImageLoad}
        decoding="async"
        width={width}
        height={height}
        style={{ aspectRatio }}
      />
    </div>
  );
}
