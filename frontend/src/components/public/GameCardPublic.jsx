// src/components/public/GameCardPublic.jsx - Enhanced with Collapsible Details
import React, { useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import { labelFor } from "../../constants/categories";
import GameImage from "../GameImage";
import { getAfterGameCreateUrl } from "../../constants/aftergame";
import { useOnboarding } from "../../hooks/useOnboarding";

export default function GameCardPublic({
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
  const imgSrc = game.image_url;
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
    const min = game.playtime_min || game.playing_time;
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
    const baseMin = game.min_players;
    const baseMax = game.max_players;
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
      className={`game-card-container scroll-mt-24 group bg-white rounded-2xl overflow-hidden shadow-md hover:shadow-xl border-2 border-slate-200 ${transitionClass} hover:border-emerald-300 focus-within:ring-4 focus-within:ring-emerald-200 focus-within:ring-offset-2 ${isExpanded ? 'col-span-2 sm:col-span-1' : ''}`}
    >

      {/* Image Section - Always Visible */}
      <Link
        to={href}
        className="block focus:outline-none"
        aria-label={`View details for ${game.title}`}
      >
        <div className="relative overflow-hidden bg-gradient-to-br from-slate-100 to-slate-200 aspect-square">
          <GameImage
            url={imgSrc}
            alt={`Cover art for ${game.title}`}
            className={`w-full h-full object-cover ${transitionClass} group-hover:scale-110`}
            fallbackClass="w-full h-full flex flex-col items-center justify-center text-slate-500 bg-gradient-to-br from-slate-100 to-slate-200"
            loading={lazy ? "lazy" : "eager"}
            fetchPriority={priority ? "high" : "auto"}
            aspectRatio="1/1"
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

      {/* Content Section - Collapsible */}
      <div className="p-3">
        
        {/* Compact Info - Always Visible */}
        <div 
          onClick={onToggleExpand}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              onToggleExpand();
            }
          }}
          className="cursor-pointer"
          role="button"
          tabIndex={0}
          aria-expanded={isExpanded}
          aria-label={`${isExpanded ? 'Collapse' : 'Expand'} details for ${game.title}`}
        >
          {/* Title & Expand Button */}
          <div className="flex items-start justify-between gap-2 mb-2">
            <h3 className="font-bold text-base text-slate-800 line-clamp-2 leading-tight flex-1">
              {game.title}
            </h3>
            <div className="relative flex-shrink-0">
              <button
                className={`p-1 rounded-full hover:bg-slate-100 ${transitionClass} focus:outline-none focus:ring-2 focus:ring-emerald-500 ${shouldShowCardHint && showHints ? 'animate-pulse' : ''}`}
                aria-label={isExpanded ? 'Collapse details' : 'Expand details'}
                onClick={(e) => {
                  e.stopPropagation();
                  onToggleExpand();
                }}
              >
                <svg
                  className={`w-5 h-5 text-slate-600 ${transitionClass} ${isExpanded ? 'rotate-180' : ''}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {/* Tap to expand hint - mobile only */}
              {shouldShowCardHint && showHints && !isExpanded && (
                <div className="absolute -bottom-6 right-0 md:hidden">
                  <span className="text-[10px] text-emerald-700 font-semibold whitespace-nowrap bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200 shadow-sm">
                    Tap to expand
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Compact Stats - Always Visible */}
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-slate-600">
            {/* Players - Icon only */}
            {(() => {
              const playerCount = formatPlayerCount();
              if (!playerCount) return null;

              return (
                <div
                  className="flex items-center gap-1"
                  aria-label={`${playerCount} players`}
                >
                  <svg className="w-4 h-4 text-emerald-600" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                    <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3z"/>
                  </svg>
                  <span className="font-semibold">{playerCount}</span>
                </div>
              );
            })()}

            {/* Time - Icon only */}
            <div className="flex items-center gap-1" aria-label={`Play time: ${formatTime()}`}>
              <svg className="w-4 h-4 text-slate-500" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
              </svg>
              <span className="font-semibold">{formatTime()}</span>
            </div>
          </div>
        </div>

        {/* Expanded Details */}
        <div
          className={`overflow-hidden ${transitionClass}`}
          style={{
            maxHeight: isExpanded ? '500px' : '0',
            opacity: isExpanded ? 1 : 0
          }}
        >
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
                  <span className="font-semibold">Complexity:</span> {formatComplexity(game.complexity)}/5
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
                  className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-gradient-to-r from-teal-500 to-emerald-500 text-white font-semibold text-sm hover:from-teal-600 hover:to-emerald-600 transition-all shadow-md hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2"
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
      </div>
    </article>
  );
}
