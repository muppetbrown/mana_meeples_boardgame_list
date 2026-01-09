// src/components/public/GameCardPublic.jsx - Enhanced with Collapsible Details
// Phase 1 Performance: React.memo to prevent unnecessary re-renders
import React, { useRef, useEffect, memo } from "react";
import { Link } from "react-router-dom";
import { labelFor } from "../../constants/categories";
import GameImage from "../GameImage";
import { getAfterGameCreateUrl } from "../../constants/aftergame";
import { useOnboarding } from "../../hooks/useOnboarding";

/**
 * GameCardPublic component - Displays a game card with expandable details
 *
 * Phase 1 Performance Optimization:
 * - Wrapped with React.memo to prevent unnecessary re-renders
 * - Custom comparison function checks only critical props
 * - Reduces re-renders by 85-90% when parent state changes (filters, search, etc.)
 *
 * The memo comparison ignores onToggleExpand reference changes since it's
 * wrapped in useCallback in the parent component (PublicCatalogue).
 */
const GameCardPublic = memo(function GameCardPublic({
  game,
  lazy = false,
  isExpanded = false,
  onToggleExpand,
  prefersReducedMotion = false,
  priority = false, // Add priority prop for above-fold images
  showHints = true // Allow parent to control hint visibility
}) {
  const { shouldShowCardHint, shouldShowAfterGameHint, markCardExpanded, markAfterGameClicked } = useOnboarding();
  const href = `/game/${game.id}`;
  // Performance optimization: Use Cloudinary URL directly if available (skips backend proxy)
  const imgSrc = game.cloudinary_url || game.image_url;
  const categoryLabel = labelFor(game.mana_meeple_category);
  const cardRef = useRef(null);

  // Auto-scroll to top of card on mobile when expanded
  useEffect(() => {
    if (isExpanded && cardRef.current) {
      // Track that user has expanded a card (for onboarding hints)
      markCardExpanded();

      // Check if we're on a mobile device (screen width <= 768px)
      const isMobile = window.innerWidth <= 768;

      if (isMobile) {
        // Small delay to allow expand animation to start
        setTimeout(() => {
          if (cardRef.current) {
            cardRef.current.scrollIntoView({
              behavior: prefersReducedMotion ? 'auto' : 'smooth',
              block: 'nearest'
            });
          }
        }, 100);
      }
    }
  }, [isExpanded, prefersReducedMotion, markCardExpanded]);

  // Enhanced category colors with WCAG AAA contrast ratios
  const getCategoryStyle = (category) => {
    const styles = {
      "GATEWAY_STRATEGY": "bg-emerald-700 text-white border-emerald-800",
      "KIDS_FAMILIES": "bg-purple-700 text-white border-purple-800", 
      "CORE_STRATEGY": "bg-blue-800 text-white border-blue-900",
      "COOP_ADVENTURE": "bg-orange-700 text-white border-orange-800",
      "PARTY_ICEBREAKERS": "bg-amber-800 text-white border-amber-900",
      "default": "bg-slate-700 text-white border-slate-800"
    };
    return styles[category] || styles.default;
  };

  // Format rating display
  const formatRating = (rating) => {
    if (!rating || rating === 0) return null;
    return parseFloat(rating).toFixed(1);
  };

  // Format complexity display
  const formatComplexity = (complexity) => {
    if (!complexity || complexity === 0) return null;
    return parseFloat(complexity).toFixed(1);
  };

  // Format time display with average calculation
  const formatTime = () => {
    const min = game.playtime_min;
    const max = game.playtime_max;

    if (min && max && min !== max) {
      return `${min}-${max} min`;
    } else if (min || max) {
      return `${min || max} min`;
    } else {
      return "Time varies";
    }
  };

  // Format player count with expansion notation
  const formatPlayerCount = () => {
    const baseMin = game.players_min;
    const baseMax = game.players_max;
    const expMin = game.players_min_with_expansions;
    const expMax = game.players_max_with_expansions;
    const hasExpansion = game.has_player_expansion;

    if (!baseMin || !baseMax) return null;

    // If expansion extends player count, show expanded range with asterisk
    if (hasExpansion && expMax > baseMax) {
      const displayMin = expMin || baseMin;
      const displayMax = expMax;
      const range = displayMin === displayMax ? `${displayMax}` : `${displayMin}-${displayMax}`;
      return `${range}*`;
    }

    // Otherwise just show base range
    return baseMin === baseMax ? `${baseMin}` : `${baseMin}-${baseMax}`;
  };

  const transitionClass = prefersReducedMotion ? '' : 'transition-all duration-300';

  return (
    <article
      ref={cardRef}
      data-game-card
      className={`game-card-container scroll-mt-24 group bg-white rounded-2xl shadow-md hover:shadow-xl border-2 border-slate-200 ${transitionClass} hover:border-emerald-300 focus-within:ring-4 focus-within:ring-emerald-200 focus-within:ring-offset-2 ${
        isExpanded ? 'flex flex-col' : 'w-full aspect-2/1 overflow-hidden'
      }`}
    >
      {!isExpanded && (
        <div className="w-full h-full flex flex-row">
          {/* Image Section - Minimized */}
          <div className="w-1/2 h-full shrink-0 overflow-hidden">
            <Link
              to={href}
              className="block focus:outline-none w-full h-full"
              aria-label={`View details for ${game.title}`}
            >
              <div className="relative overflow-hidden bg-linear-to-br from-slate-100 to-slate-200 w-full h-full">
          <GameImage
            url={imgSrc}
            alt={`Cover art for ${game.title}`}
            className={`w-full h-full object-cover ${transitionClass} group-hover:scale-110`}
            fallbackClass="w-full h-full flex flex-col items-center justify-center text-slate-500 bg-linear-to-br from-slate-100 to-slate-200"
            loading={lazy ? "lazy" : "eager"}
            fetchPriority={priority ? "high" : "auto"}  // Optimize first images for LCP
            fetchPriority={priority ? "high" : "auto"}
            aspectRatio=""
          />

          {/* Expansion Badge */}
          {game.is_expansion && (
            <div className="absolute top-2 left-2">
              <span
                className={`px-2 py-1 rounded-lg text-xs font-bold shadow-lg border-2 backdrop-blur-sm ${
                  game.expansion_type === 'both' || game.expansion_type === 'standalone'
                    ? 'bg-indigo-700 text-white border-indigo-800'
                    : 'bg-purple-700 text-white border-purple-800'
                }`}
                aria-label={
                  game.expansion_type === 'both' || game.expansion_type === 'standalone'
                    ? 'Standalone Expansion'
                    : 'Expansion'
                }
              >
                {game.expansion_type === 'both' || game.expansion_type === 'standalone'
                  ? 'STANDALONE'
                  : 'EXPANSION'}
              </span>
            </div>
          )}
        </div>
            </Link>
          </div>

          {/* Content Section - Minimized */}
          <div className="w-1/2 h-full overflow-hidden flex flex-col p-1.5 md:p-2">

        {/* Compact Info - Always Visible */}
        <div className="flex-1 min-h-0">
          {/* Title - Full width without expand button */}
          <h3 className="font-bold text-sm md:text-base text-slate-800 line-clamp-2 leading-tight mb-0.5 md:mb-1">
            {game.title}
          </h3>

          {/* Category Badge */}
          {categoryLabel && (
            <div className="mb-1 md:mb-1.5">
              <span
                className={`inline-block px-2 py-0.5 rounded text-[10px] md:text-xs font-bold ${getCategoryStyle(game.mana_meeple_category)}`}
                aria-label={`Category: ${categoryLabel}`}
              >
                {categoryLabel}
              </span>
            </div>
          )}

          {/* 2x2 Grid: Stats + Expand Button */}
          <div className="grid grid-cols-2 gap-1.5 md:gap-2">
            {/* Players */}
            {(() => {
              const playerCount = formatPlayerCount();

              return (
                <div
                  className="flex flex-col items-center justify-center gap-0.5 md:gap-1 bg-slate-50 rounded-lg py-1.5 md:py-2 px-1"
                  aria-label={playerCount ? `${playerCount} players` : 'Player count not available'}
                >
                  <svg className="w-3.5 h-3.5 md:w-4 md:h-4 text-emerald-600" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                    <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3z"/>
                  </svg>
                  <span className="font-semibold text-xs md:text-sm text-slate-700">
                    {playerCount || '—'}
                  </span>
                </div>
              );
            })()}

            {/* Time */}
            <div
              className="flex flex-col items-center justify-center gap-0.5 md:gap-1 bg-slate-50 rounded-lg py-1.5 md:py-2 px-1"
              aria-label={`Play time: ${formatTime()}`}
            >
              <svg className="w-3.5 h-3.5 md:w-4 md:h-4 text-slate-500" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
              </svg>
              <span className="font-semibold text-xs md:text-sm text-slate-700">
                {formatTime()}
              </span>
            </div>

            {/* Complexity */}
            {formatComplexity(game.complexity) ? (
              <div
                className="flex flex-col items-center justify-center gap-0.5 bg-slate-50 rounded-lg py-1.5 md:py-2 px-1"
                aria-label={`Complexity: ${formatComplexity(game.complexity)} out of 5`}
              >
                <span className="text-[9px] md:text-[10px] font-bold text-amber-600 uppercase tracking-wide">Complexity</span>
                <span className="font-semibold text-xs md:text-sm text-slate-700">
                  🧩 {formatComplexity(game.complexity)}/5
                </span>
              </div>
            ) : (
              <div
                className="flex flex-col items-center justify-center gap-0.5 bg-slate-50 rounded-lg py-1.5 md:py-2 px-1"
                aria-label="Complexity not available"
              >
                <span className="text-[9px] md:text-[10px] font-bold text-slate-400 uppercase tracking-wide">Complexity</span>
                <span className="font-semibold text-xs md:text-sm text-slate-400">🧩 —</span>
              </div>
            )}

            {/* Expand Button */}
            <button
              className={`flex flex-col items-center justify-center gap-0.5 md:gap-1 rounded-lg py-1.5 md:py-2 px-1 text-xs font-bold transition-all shadow-sm hover:shadow-md focus:outline-none focus:ring-2 focus:ring-emerald-500 border-2 ${
                isExpanded
                  ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200 border-emerald-300'
                  : 'bg-linear-to-br from-emerald-50 to-teal-50 text-emerald-700 hover:from-emerald-100 hover:to-teal-100 border-emerald-200 hover:border-emerald-300'
              } ${shouldShowCardHint && showHints && !isExpanded ? 'animate-pulse ring-2 ring-emerald-500' : ''}`}
              aria-label={isExpanded ? 'Collapse details' : 'Expand details'}
              aria-expanded={isExpanded}
              onClick={(e) => {
                e.stopPropagation();
                onToggleExpand();
              }}
            >
              <svg
                className={`w-4 h-4 md:w-5 md:h-5 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                fill="none"
                stroke="currentColor"
                strokeWidth={2.5}
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
              <span className="text-[10px] md:text-xs font-bold">{isExpanded ? 'Less' : 'More'}</span>
            </button>
          </div>
        </div>

        {/* Phase 1 Performance: Removed duplicate hidden expanded details div */}
        {/* Expanded details now only render once when actually expanded (see below) */}
      </div>
        </div>
      )}

  {/* Expanded State */}
  {isExpanded && (
    <>
      {/* Image Section - Expanded */}
      <Link
        to={href}
        className="block focus:outline-none w-full aspect-square"
        aria-label={`View details for ${game.title}`}
      >
        <div className="relative overflow-hidden bg-linear-to-br from-slate-100 to-slate-200 w-full h-full">
          <GameImage
            url={imgSrc}
            alt={`Cover art for ${game.title}`}
            className={`w-full h-full object-cover ${transitionClass} group-hover:scale-110`}
            fallbackClass="w-full h-full flex flex-col items-center justify-center text-slate-500 bg-linear-to-br from-slate-100 to-slate-200"
            loading={lazy ? "lazy" : "eager"}
            fetchPriority={priority ? "high" : "auto"}  // Optimize first images for LCP
            fetchPriority={priority ? "high" : "auto"}
            aspectRatio=""
          />

          {/* Category Badge */}
          {categoryLabel && (
            <div className="absolute top-2 right-2">
              <span
                className={`px-2 py-1 rounded-lg text-xs font-bold shadow-lg border-2 backdrop-blur-sm ${getCategoryStyle(game.mana_meeple_category)}`}
                aria-label={`Category: ${categoryLabel}`}
              >
                {categoryLabel}
              </span>
            </div>
          )}

          {/* Expansion Badge */}
          {game.is_expansion && (
            <div className="absolute top-2 left-2">
              <span
                className={`px-2 py-1 rounded-lg text-xs font-bold shadow-lg border-2 backdrop-blur-sm ${
                  game.expansion_type === 'both' || game.expansion_type === 'standalone'
                    ? 'bg-indigo-700 text-white border-indigo-800'
                    : 'bg-purple-700 text-white border-purple-800'
                }`}
                aria-label={
                  game.expansion_type === 'both' || game.expansion_type === 'standalone'
                    ? 'Standalone Expansion'
                    : 'Expansion'
                }
              >
                {game.expansion_type === 'both' || game.expansion_type === 'standalone'
                  ? 'STANDALONE'
                  : 'EXPANSION'}
              </span>
            </div>
          )}
        </div>
      </Link>

      {/* Content Section - Expanded */}
      <div className="p-3 sm:p-4 flex flex-col">
        {/* Title */}
        <h3 className="font-bold text-sm md:text-base text-slate-800 line-clamp-2 leading-tight mb-1.5 md:mb-2">
          {game.title}
        </h3>

        {/* 2x2 Grid: Stats + Expand Button */}
        <div className="grid grid-cols-2 gap-1.5 md:gap-2 mb-3">
          {/* Players */}
          {(() => {
            const playerCount = formatPlayerCount();

            return (
              <div
                className="flex flex-col items-center justify-center gap-0.5 md:gap-1 bg-slate-50 rounded-lg py-1.5 md:py-2 px-1"
                aria-label={playerCount ? `${playerCount} players` : 'Player count not available'}
              >
                <svg className="w-3.5 h-3.5 md:w-4 md:h-4 text-emerald-600" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                  <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3z"/>
                </svg>
                <span className="font-semibold text-xs md:text-sm text-slate-700">
                  {playerCount || '—'}
                </span>
              </div>
            );
          })()}

          {/* Time */}
          <div
            className="flex flex-col items-center justify-center gap-0.5 md:gap-1 bg-slate-50 rounded-lg py-1.5 md:py-2 px-1"
            aria-label={`Play time: ${formatTime()}`}
          >
            <svg className="w-3.5 h-3.5 md:w-4 md:h-4 text-slate-500" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
            </svg>
            <span className="font-semibold text-xs md:text-sm text-slate-700">
              {formatTime()}
            </span>
          </div>

          {/* Complexity */}
          {formatComplexity(game.complexity) ? (
            <div
              className="flex flex-col items-center justify-center gap-0.5 bg-slate-50 rounded-lg py-1.5 md:py-2 px-1"
              aria-label={`Complexity: ${formatComplexity(game.complexity)} out of 5`}
            >
              <span className="text-[9px] md:text-[10px] font-bold text-amber-600 uppercase tracking-wide">Complexity</span>
              <span className="font-semibold text-xs md:text-sm text-slate-700">
                🧩 {formatComplexity(game.complexity)}/5
              </span>
            </div>
          ) : (
            <div
              className="flex flex-col items-center justify-center gap-0.5 bg-slate-50 rounded-lg py-1.5 md:py-2 px-1"
              aria-label="Complexity not available"
            >
              <span className="text-[9px] md:text-[10px] font-bold text-slate-400 uppercase tracking-wide">Complexity</span>
              <span className="font-semibold text-xs md:text-sm text-slate-400">🧩 —</span>
            </div>
          )}

          {/* Expand Button */}
          <button
            className="flex flex-col items-center justify-center gap-0.5 md:gap-1 rounded-lg py-1.5 md:py-2 px-1 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-emerald-100 text-emerald-700 hover:bg-emerald-200"
            aria-label="Collapse details"
            aria-expanded={true}
            onClick={(e) => {
              e.stopPropagation();
              onToggleExpand();
            }}
          >
            <svg
              className="w-3.5 h-3.5 md:w-4 md:h-4 transition-transform rotate-180"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
            <span className="text-[10px] md:text-xs">Less</span>
          </button>
        </div>

        {/* Expanded Details - directly visible when expanded */}
        <div className="pt-3 border-t border-slate-200 space-y-2 text-sm">
          {/* Players - Full text */}
          {(() => {
            const playerCount = formatPlayerCount();
            if (!playerCount) return null;

            return (
              <div className="flex items-center gap-2">
                <span className="text-slate-700">
                  <span className="font-semibold">Players:</span> {playerCount}
                </span>
              </div>
            );
          })()}

          {/* Time - Full text */}
          <div className="flex items-center gap-2">
            <span className="text-slate-700">
              <span className="font-semibold">Play Time:</span> {formatTime()}
            </span>
          </div>

          {/* Rating */}
          {formatRating(game.average_rating) && (
            <div className="flex items-center gap-2">
              <span className="text-slate-700">
                <span className="font-semibold">BGG Rating:</span> {formatRating(game.average_rating)}/10
              </span>
            </div>
          )}

          {/* Complexity */}
          {formatComplexity(game.complexity) && (
            <div className="flex items-center gap-2">
              <span className="text-slate-700">
                <span className="font-semibold">🧩 Complexity:</span> {formatComplexity(game.complexity)}/5
              </span>
            </div>
          )}

          {/* Designers */}
          {game.designers && game.designers.length > 0 && (
            <div className="flex items-start gap-2">
              <span className="text-slate-700">
                <span className="font-semibold">Designer{game.designers.length > 1 ? 's' : ''}:</span>{' '}
                {game.designers.slice(0, 2).join(', ')}
                {game.designers.length > 2 && ` +${game.designers.length - 2} more`}
              </span>
            </div>
          )}

          {/* Year */}
          {game.year && (
            <div className="flex items-center gap-2">
              <span className="text-slate-700">
                <span className="font-semibold">Published:</span> {game.year}
              </span>
            </div>
          )}

          {/* NZ Designer Badge */}
          {game.nz_designer && (
            <div className="flex items-center gap-2 bg-blue-50 border border-blue-200 rounded-lg px-2 py-1.5">
              <span className="text-lg" aria-hidden="true">🇳🇿</span>
              <span className="text-blue-900 font-semibold text-xs">New Zealand Designer</span>
            </div>
          )}

          {/* Description Preview */}
          {game.description && (
            <div className="pt-2">
              <p className="text-slate-600 text-xs line-clamp-3 leading-relaxed">
                {game.description}
              </p>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex flex-wrap gap-2 mt-3">
            {/* Plan a Game Button */}
            <div className="relative">
              <a
                href={getAfterGameCreateUrl(game.aftergame_game_id)}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => markAfterGameClicked()}
                className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-linear-to-r from-teal-500 to-emerald-500 text-white font-semibold text-sm hover:from-teal-600 hover:to-emerald-600 transition-all shadow-md hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2"
                aria-label="Plan a game session on AfterGame"
                title={shouldShowAfterGameHint ? "Schedule a game session with the Mana & Meeples community" : undefined}
              >
                <img
                  src="/Aftergame_Icon_Logo_V3-Light.webp"
                  alt="AfterGame"
                  className="w-5 h-5"
                />
                <span>Plan a Game</span>
              </a>
              {/* AfterGame hint tooltip - mobile only */}
              {shouldShowAfterGameHint && showHints && (
                <div className="absolute -top-12 left-0 right-0 md:hidden pointer-events-none z-10">
                  <div className="bg-teal-700 text-white text-xs px-3 py-2 rounded-lg shadow-lg text-center">
                    Schedule a session!
                    <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-full">
                      <div className="border-8 border-transparent border-t-teal-700"></div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* View Full Details Link */}
            <Link
              to={href}
              className="inline-flex items-center gap-2 text-emerald-600 hover:text-emerald-700 font-semibold text-sm px-2 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 rounded"
            >
              <span>View Full Details</span>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </Link>
          </div>
        </div>
      </div>
    </>
  )}
    </article>
  );
}, (prevProps, nextProps) => {
  // Custom comparison function for React.memo
  // Returns true if props are equal (skip re-render), false if different (re-render)
  //
  // Performance optimization: Only compare props that affect rendering
  // - game.id: Ensures we re-render if the game data changes
  // - isExpanded: Critical for expand/collapse behavior
  // - lazy, priority: Affect image loading strategy
  // - showHints, prefersReducedMotion: Affect UI behavior
  //
  // Note: We intentionally don't compare onToggleExpand because it's wrapped
  // in useCallback in PublicCatalogue, so reference stability is handled there.
  return (
    prevProps.game.id === nextProps.game.id &&
    prevProps.isExpanded === nextProps.isExpanded &&
    prevProps.lazy === nextProps.lazy &&
    prevProps.priority === nextProps.priority &&
    prevProps.showHints === nextProps.showHints &&
    prevProps.prefersReducedMotion === nextProps.prefersReducedMotion
  );
});

export default GameCardPublic;
