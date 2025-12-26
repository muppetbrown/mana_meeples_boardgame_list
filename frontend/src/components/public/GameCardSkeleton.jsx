// src/components/public/GameCardSkeleton.jsx
import React from "react";

/**
 * Skeleton loader for GameCardPublic
 * Matches exact dimensions to prevent Cumulative Layout Shift (CLS)
 * Shows while games are loading
 */
export default function GameCardSkeleton() {
  return (
    <article
      className="game-card-container bg-white rounded-2xl overflow-hidden shadow-md border-2 border-slate-200 animate-pulse flex flex-row aspect-[2/1]"
      aria-hidden="true"
    >
      {/* Image Skeleton - Square aspect ratio, matches GameCardPublic minimized state */}
      <div className="relative overflow-hidden bg-gradient-to-br from-slate-200 via-slate-100 to-slate-200 h-full aspect-square flex-shrink-0">
        <div className="w-full h-full flex items-center justify-center">
          <svg className="w-12 h-12 text-slate-300" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
          </svg>
        </div>
      </div>

      {/* Content Skeleton */}
      <div className="p-3 flex-1 flex flex-col">
        {/* Title Skeleton */}
        <div className="space-y-2 mb-3">
          <div className="h-4 bg-slate-200 rounded w-3/4"></div>
          <div className="h-4 bg-slate-200 rounded w-1/2"></div>
        </div>

        {/* Stats Grid Skeleton - 2x2 */}
        <div className="grid grid-cols-2 gap-1.5 md:gap-2">
          <div className="bg-slate-100 rounded-lg p-2 h-12"></div>
          <div className="bg-slate-100 rounded-lg p-2 h-12"></div>
          <div className="bg-slate-100 rounded-lg p-2 h-12"></div>
          <div className="bg-slate-100 rounded-lg p-2 h-12"></div>
        </div>
      </div>
    </article>
  );
}
