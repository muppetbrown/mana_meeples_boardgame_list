import React, { useState, useEffect, useMemo } from 'react';
import { Game } from '../../../types/game';
import { imageProxyUrl } from '../../../../../../frontend/src/utils/api';
import { labelFor } from '../../../../../../frontend/src/constants/categories';

interface RecentlyViewedCardsProps {
  className?: string;
  maxItems?: number;
  onGameSelect?: (game: Game) => void;
}

const RecentlyViewedCards: React.FC<RecentlyViewedCardsProps> = ({
  className = '',
  maxItems = 5,
  onGameSelect
}) => {
  const [recentlyViewed, setRecentlyViewed] = useState<Game[]>([]);
  const [loading, setLoading] = useState(true);

  // Load recently viewed games from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem('recentlyViewedGames');
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          setRecentlyViewed(parsed.slice(0, maxItems));
        }
      }
    } catch (error) {
      console.warn('Failed to load recently viewed games:', error);
    } finally {
      setLoading(false);
    }
  }, [maxItems]);

  // Listen for storage changes to sync across tabs
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'recentlyViewedGames' && e.newValue) {
        try {
          const parsed = JSON.parse(e.newValue);
          if (Array.isArray(parsed)) {
            setRecentlyViewed(parsed.slice(0, maxItems));
          }
        } catch (error) {
          console.warn('Failed to sync recently viewed games:', error);
        }
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, [maxItems]);

  // Enhanced category colors with WCAG AAA contrast ratios
  const getCategoryStyle = (category: string | undefined) => {
    const styles = {
      "GATEWAY_STRATEGY": "bg-emerald-700 text-white border-emerald-800",
      "KIDS_FAMILIES": "bg-purple-700 text-white border-purple-800",
      "CORE_STRATEGY": "bg-blue-800 text-white border-blue-900",
      "COOP_ADVENTURE": "bg-orange-700 text-white border-orange-800",
      "PARTY_ICEBREAKERS": "bg-amber-800 text-white border-amber-900",
      "default": "bg-slate-700 text-white border-slate-800"
    };
    return styles[category as keyof typeof styles] || styles.default;
  };

  const formatRating = (rating?: number | null): string | null => {
    if (!rating || rating === 0) return null;
    return parseFloat(String(rating)).toFixed(1);
  };

  const formatTime = (game: Game): string => {
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

  const handleGameClick = (game: Game) => {
    if (onGameSelect) {
      onGameSelect(game);
    }
  };

  const displayedGames = useMemo(() => recentlyViewed.slice(0, maxItems), [recentlyViewed, maxItems]);

  if (loading) {
    return (
      <div className={`space-y-4 ${className}`} role="region" aria-label="Recently viewed games loading">
        {Array.from({ length: 3 }).map((_, index) => (
          <div key={index} className="animate-pulse">
            <div className="flex items-center gap-4 p-4 bg-white rounded-lg shadow-sm border border-slate-200">
              <div className="w-16 h-16 bg-slate-200 rounded-md flex-shrink-0"></div>
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-slate-200 rounded w-3/4"></div>
                <div className="h-3 bg-slate-200 rounded w-1/2"></div>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (displayedGames.length === 0) {
    return (
      <div className={`text-center py-8 ${className}`} role="region" aria-label="Recently viewed games">
        <div className="w-16 h-16 mx-auto bg-slate-100 rounded-full flex items-center justify-center mb-4">
          <svg className="w-8 h-8 text-slate-400" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-slate-900 mb-2">No recently viewed games</h3>
        <p className="text-slate-600">Games you view will appear here for quick access.</p>
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className}`} role="region" aria-label="Recently viewed games">
      <h2 className="text-xl font-bold text-slate-900 mb-4">Recently Viewed</h2>
      <div className="space-y-3">
        {displayedGames.map((game) => {
          const imgSrc = game.image_url ? imageProxyUrl(game.image_url) : null;
          const categoryLabel = labelFor(game.mana_meeple_category);

          return (
            <article
              key={game.id}
              className="group flex items-center gap-4 p-4 bg-white rounded-lg shadow-sm border border-slate-200 hover:shadow-md hover:border-emerald-300 transition-all duration-200 cursor-pointer"
              onClick={() => handleGameClick(game)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  handleGameClick(game);
                }
              }}
              aria-label={`View details for ${game.title}`}
            >
              {/* Game Image */}
              <div className="relative overflow-hidden bg-gradient-to-br from-slate-100 to-slate-200 w-16 h-16 rounded-md flex-shrink-0">
                {imgSrc ? (
                  <img
                    src={imgSrc}
                    alt={`Cover art for ${game.title}`}
                    className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-110"
                    loading="lazy"
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      target.style.display = 'none';
                      if (target.nextElementSibling) {
                        (target.nextElementSibling as HTMLElement).style.display = 'flex';
                      }
                    }}
                  />
                ) : null}

                {/* Fallback when no image */}
                <div className={`w-full h-full flex items-center justify-center text-slate-400 ${imgSrc ? 'hidden' : 'flex'}`}>
                  <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                    <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
                  </svg>
                </div>
              </div>

              {/* Game Info */}
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-slate-900 group-hover:text-emerald-700 transition-colors duration-200 truncate mb-1">
                  {game.title}
                </h3>
                <div className="flex items-center gap-4 text-sm text-slate-600">
                  {game.min_players && game.max_players && (
                    <span className="flex items-center gap-1">
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                        <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3z"/>
                      </svg>
                      {game.min_players}-{game.max_players}
                    </span>
                  )}
                  <span className="flex items-center gap-1">
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd"/>
                    </svg>
                    {formatTime(game)}
                  </span>
                  {formatRating(game.average_rating) && (
                    <span className="flex items-center gap-1">
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                      </svg>
                      {formatRating(game.average_rating)}
                    </span>
                  )}
                </div>
              </div>

              {/* Category Badge */}
              {categoryLabel && (
                <div className="flex-shrink-0">
                  <span
                    className={`px-2 py-1 rounded text-xs font-bold ${getCategoryStyle(game.mana_meeple_category)}`}
                    aria-label={`Category: ${categoryLabel}`}
                  >
                    {categoryLabel}
                  </span>
                </div>
              )}

              {/* Arrow Indicator */}
              <div className="flex-shrink-0 text-slate-400 group-hover:text-emerald-600 transition-colors duration-200">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
};

export default RecentlyViewedCards;