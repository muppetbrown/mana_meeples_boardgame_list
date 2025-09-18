// src/components/public/GameCardPublic.jsx
import React from "react";
import { Link } from "react-router-dom";
import { imageProxyUrl } from "../../utils/api";
import { labelFor } from "../../constants/categories";

export default function GameCardPublic({ game, lazy = false, onShare }) {
  const href = `/game/${game.id}`;
  const imgSrc = game.image_url ? imageProxyUrl(game.image_url) : null;
  const categoryLabel = labelFor(game.mana_meeple_category);

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

  // Format time display with average calculation
  const formatTime = () => {
    const min = game.playtime_min || game.playing_time;
    const max = game.playtime_max;
    
    if (min && max && min !== max) {
      const avg = Math.round((min + max) / 2);
      return `${avg} min avg`;
    } else if (min || max) {
      return `${min || max} min`;
    } else {
      return "Time varies";
    }
  };

  // Create structured data for screen readers
  const gameDetails = [
    game.min_players && game.max_players 
      ? `${game.min_players} to ${game.max_players} players`
      : "Player count unknown",
    formatTime(),
    game.year ? `Published ${game.year}` : "Publication year unknown",
    formatRating(game.average_rating) 
      ? `Rated ${formatRating(game.average_rating)} out of 10`
      : "No rating available"
  ].filter(Boolean);

  return (
    <article className="group bg-white rounded-2xl overflow-hidden shadow-md hover:shadow-2xl border-2 border-slate-200 transition-all duration-300 hover:scale-[1.02] hover:border-emerald-300 focus-within:ring-4 focus-within:ring-emerald-200 focus-within:ring-offset-2 touch-manipulation">
      {/* Main Link */}
      <Link
        to={href}
        className="block focus:outline-none"
        aria-label={`View details for ${game.title}. ${gameDetails.join('. ')}`}
      >
        {/* Image Container */}
        <div className="relative overflow-hidden bg-gradient-to-br from-slate-100 to-slate-200 aspect-square">
          {imgSrc ? (
            <img
              src={imgSrc}
              alt={`Cover art for ${game.title}`}
              className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
              loading={lazy ? "lazy" : "eager"}
              onError={(e) => {
                e.target.style.display = 'none';
                e.target.nextElementSibling.style.display = 'flex';
              }}
            />
          ) : null}
          
          {/* Fallback when no image */}
          <div className={`w-full h-full flex flex-col items-center justify-center text-slate-500 ${imgSrc ? 'hidden' : 'flex'}`}>
            <div className="w-16 h-16 rounded-full bg-slate-300 flex items-center justify-center mb-3 group-hover:bg-slate-400 transition-colors">
              <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
              </svg>
            </div>
            <span className="text-sm font-medium">No Image Available</span>
          </div>
          
          {/* Category Badge */}
          {categoryLabel && (
            <div className="absolute top-2 right-2 sm:top-3 sm:right-3">
              <span 
                className={`px-2 py-1 sm:px-3 sm:py-1.5 rounded-lg text-xs font-bold shadow-lg border-2 backdrop-blur-sm ${getCategoryStyle(game.mana_meeple_category)}`}
                aria-label={`Category: ${categoryLabel}`}
              >
                {categoryLabel}
              </span>
            </div>
          )}

          {/* Rating Badge - Top Left */}
          {formatRating(game.average_rating) && (
            <div className="absolute top-2 left-2 sm:top-3 sm:left-3">
              <div className="bg-white/95 backdrop-blur-sm border-2 border-yellow-400 rounded-lg px-2 py-1 sm:px-2.5 sm:py-1.5 shadow-lg">
                <div className="flex items-center gap-1">
                  <svg className="w-3 h-3 sm:w-4 sm:h-4 text-yellow-500" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                  <span className="text-xs sm:text-sm font-bold text-slate-800">{formatRating(game.average_rating)}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Content Section */}
        <div className="p-3 sm:p-4">
          {/* Title */}
          <h3 className="font-bold text-base sm:text-lg text-slate-800 mb-2 sm:mb-3 group-hover:text-emerald-700 transition-colors duration-300 line-clamp-2 leading-tight min-h-[3rem] sm:min-h-[3.5rem]">
            {game.title}
          </h3>
          
          {/* Game Info Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 sm:gap-3 mb-3 sm:mb-4">
            {/* Players */}
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-emerald-100 flex items-center justify-center flex-shrink-0">
                <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-emerald-700" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                  <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3z"/>
                </svg>
              </div>
              <div className="min-w-0">
                <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">Players</div>
                <div className="text-sm font-bold text-slate-800 truncate">
                  {game.min_players && game.max_players 
                    ? `${game.min_players}-${game.max_players}`
                    : "Unknown"
                  }
                </div>
              </div>
            </div>

            {/* Time */}
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-amber-100 flex items-center justify-center flex-shrink-0">
                <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-amber-700" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd"/>
                </svg>
              </div>
              <div className="min-w-0">
                <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">Time</div>
                <div className="text-sm font-bold text-slate-800 truncate">
                  {formatTime()}
                </div>
              </div>
            </div>

            {/* Year */}
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-blue-700" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                  <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd"/>
                </svg>
              </div>
              <div className="min-w-0">
                <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">Year</div>
                <div className="text-sm font-bold text-slate-800 truncate">
                  {game.year || "Unknown"}
                </div>
              </div>
            </div>

            {/* Rating */}
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-yellow-100 flex items-center justify-center flex-shrink-0">
                <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-yellow-700" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
              </div>
              <div className="min-w-0">
                <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">Rating</div>
                <div className="text-sm font-bold text-slate-800 truncate">
                  {formatRating(game.average_rating) || "Unrated"}
                </div>
              </div>
            </div>
          </div>

          {/* Action Indicator */}
          <div className="flex items-center justify-between pt-2 sm:pt-3 border-t border-slate-200">
            <span className="text-emerald-600 font-semibold text-sm opacity-0 group-hover:opacity-100 transition-all duration-300 transform translate-x-2 group-hover:translate-x-0">
              View Details
            </span>
            <svg 
              className="w-4 h-4 sm:w-5 sm:h-5 text-emerald-600 opacity-0 group-hover:opacity-100 transition-all duration-300 transform translate-x-2 group-hover:translate-x-0" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24" 
              aria-hidden="true"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </div>
        </div>
      </Link>

      {/* Share Button - Positioned outside the main link for separate focus */}
      {onShare && (
        <div className="absolute top-2 right-2 sm:top-3 sm:right-3 z-10">
          <button
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onShare(game);
            }}
            className="
              w-9 h-9 sm:w-8 sm:h-8 rounded-full bg-white/90 backdrop-blur-sm border-2 border-slate-300 
              hover:border-emerald-400 hover:bg-white shadow-lg
              flex items-center justify-center transition-all duration-200
              focus:outline-none focus:ring-3 focus:ring-emerald-300 focus:ring-offset-2
              opacity-0 group-hover:opacity-100 touch-manipulation
              min-h-[44px] sm:min-h-[32px]
            "
            aria-label={`Share ${game.title}`}
            type="button"
          >
            <svg className="w-4 h-4 text-slate-700 hover:text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.367 2.684 3 3 0 00-5.367-2.684z" />
            </svg>
          </button>
        </div>
      )}

      {/* Hidden content for screen readers */}
      <div className="sr-only">
        Game details: {gameDetails.join('. ')}.
        {categoryLabel && ` Category: ${categoryLabel}.`}
        Press enter to view full game details.
      </div>
    </article>
  );
}