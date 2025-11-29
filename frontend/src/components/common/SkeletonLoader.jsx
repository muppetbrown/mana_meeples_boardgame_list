// src/components/common/SkeletonLoader.jsx
/**
 * Skeleton loading components for content placeholders
 * Provides visual feedback while content is loading
 */
import React from 'react';

/**
 * GameCardSkeleton - Placeholder for game card while loading
 */
export function GameCardSkeleton() {
  return (
    <div className="bg-white rounded-lg shadow-sm p-4 animate-pulse">
      {/* Image placeholder */}
      <div className="w-full h-48 bg-slate-200 rounded mb-3" />

      {/* Title placeholder */}
      <div className="h-4 bg-slate-200 rounded w-3/4 mb-2" />

      {/* Metadata placeholders */}
      <div className="space-y-2">
        <div className="h-3 bg-slate-200 rounded w-1/2" />
        <div className="h-3 bg-slate-200 rounded w-2/3" />
      </div>

      {/* Stats placeholders */}
      <div className="flex gap-2 mt-3">
        <div className="h-6 bg-slate-200 rounded w-16" />
        <div className="h-6 bg-slate-200 rounded w-16" />
      </div>
    </div>
  );
}

/**
 * GameCardSkeletonGrid - Grid of skeleton cards
 */
export function GameCardSkeletonGrid({ count = 12 }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <GameCardSkeleton key={i} />
      ))}
    </div>
  );
}

/**
 * ListSkeleton - Generic list item skeleton
 */
export function ListSkeleton({ count = 5 }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 p-4 bg-white rounded-lg shadow-sm animate-pulse">
          <div className="w-16 h-16 bg-slate-200 rounded" />
          <div className="flex-1 space-y-2">
            <div className="h-4 bg-slate-200 rounded w-2/3" />
            <div className="h-3 bg-slate-200 rounded w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * TextSkeleton - Generic text content placeholder
 */
export function TextSkeleton({ lines = 3, className = '' }) {
  return (
    <div className={`space-y-2 animate-pulse ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="h-4 bg-slate-200 rounded"
          style={{ width: i === lines - 1 ? '60%' : '100%' }}
        />
      ))}
    </div>
  );
}

/**
 * DetailsSkeleton - Skeleton for game details page
 */
export function GameDetailsSkeleton() {
  return (
    <div className="max-w-4xl mx-auto p-6 animate-pulse">
      {/* Header */}
      <div className="mb-6">
        <div className="h-8 bg-slate-200 rounded w-2/3 mb-2" />
        <div className="h-4 bg-slate-200 rounded w-1/3" />
      </div>

      {/* Image and info grid */}
      <div className="grid md:grid-cols-2 gap-6 mb-6">
        <div className="aspect-square bg-slate-200 rounded-lg" />
        <div className="space-y-4">
          <div className="h-4 bg-slate-200 rounded w-full" />
          <div className="h-4 bg-slate-200 rounded w-5/6" />
          <div className="h-4 bg-slate-200 rounded w-4/6" />
        </div>
      </div>

      {/* Description */}
      <div className="space-y-2">
        <div className="h-4 bg-slate-200 rounded w-full" />
        <div className="h-4 bg-slate-200 rounded w-full" />
        <div className="h-4 bg-slate-200 rounded w-3/4" />
      </div>
    </div>
  );
}

export default GameCardSkeleton;
