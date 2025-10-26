import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { Game, GameFilters, PaginatedGamesResponse, CategoryCounts } from '../../types/game';
import {
  getPublicGames,
  getPublicCategoryCounts,
  getPublicGame
} from '../../../../../frontend/src/api/client.js';
import { CATEGORY_KEYS, CATEGORY_LABELS, labelFor } from '../../../../../frontend/src/constants/categories';
import { imageProxyUrl } from '../../../../../frontend/src/utils/api';
import RecentlyViewedCards from './components/RecentlyViewedCards';

interface ShopPageProps {
  className?: string;
}

// Utility function to manage recently viewed games
const addToRecentlyViewed = (game: Game) => {
  try {
    const existing = localStorage.getItem('recentlyViewedGames');
    let recentlyViewed: Game[] = existing ? JSON.parse(existing) : [];

    // Remove if already exists to avoid duplicates
    recentlyViewed = recentlyViewed.filter(item => item.id !== game.id);

    // Add to beginning
    recentlyViewed.unshift(game);

    // Keep only the most recent 10
    recentlyViewed = recentlyViewed.slice(0, 10);

    localStorage.setItem('recentlyViewedGames', JSON.stringify(recentlyViewed));

    // Trigger storage event for cross-tab sync
    window.dispatchEvent(new StorageEvent('storage', {
      key: 'recentlyViewedGames',
      newValue: JSON.stringify(recentlyViewed)
    }));
  } catch (error) {
    console.warn('Failed to save recently viewed game:', error);
  }
};

const ShopPage: React.FC<ShopPageProps> = ({ className = '' }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // State management
  const [games, setGames] = useState<Game[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [categoryCounts, setCategoryCounts] = useState<CategoryCounts | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalGames, setTotalGames] = useState(0);
  const [pageSize] = useState(12);

  // Search and filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedSort, setSelectedSort] = useState<GameFilters['sort']>('title_asc');
  const [nzDesignerFilter, setNzDesignerFilter] = useState(false);

  // View state
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [selectedGame, setSelectedGame] = useState<Game | null>(null);

  // Debounced search
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');

  // Initialize filters from URL params
  useEffect(() => {
    const q = searchParams.get('q') || '';
    const category = searchParams.get('category') || '';
    const sort = (searchParams.get('sort') as GameFilters['sort']) || 'title_asc';
    const nzDesigner = searchParams.get('nz_designer') === 'true';
    const page = parseInt(searchParams.get('page') || '1');

    setSearchQuery(q);
    setDebouncedSearchQuery(q);
    setSelectedCategory(category);
    setSelectedSort(sort);
    setNzDesignerFilter(nzDesigner);
    setCurrentPage(page);
  }, [searchParams]);

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery);
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Update URL when filters change
  const updateURL = useCallback((filters: Partial<GameFilters>) => {
    const newParams = new URLSearchParams(searchParams);

    if (filters.q !== undefined) {
      if (filters.q) {
        newParams.set('q', filters.q);
      } else {
        newParams.delete('q');
      }
    }

    if (filters.category !== undefined) {
      if (filters.category) {
        newParams.set('category', filters.category);
      } else {
        newParams.delete('category');
      }
    }

    if (filters.sort) {
      newParams.set('sort', filters.sort);
    }

    if (filters.nz_designer !== undefined) {
      if (filters.nz_designer) {
        newParams.set('nz_designer', 'true');
      } else {
        newParams.delete('nz_designer');
      }
    }

    if (filters.page !== undefined && filters.page > 1) {
      newParams.set('page', String(filters.page));
    } else {
      newParams.delete('page');
    }

    setSearchParams(newParams, { replace: true });
  }, [searchParams, setSearchParams]);

  // Load games
  const loadGames = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const filters: GameFilters = {
        q: debouncedSearchQuery || undefined,
        category: selectedCategory || undefined,
        sort: selectedSort,
        nz_designer: nzDesignerFilter || undefined,
        page: currentPage,
        page_size: pageSize
      };

      const [gamesResponse, countsResponse] = await Promise.all([
        getPublicGames(filters),
        getPublicCategoryCounts()
      ]);

      setGames(gamesResponse.items || []);
      setTotalGames(gamesResponse.total || 0);
      setCategoryCounts(countsResponse);

    } catch (err) {
      console.error('Failed to load games:', err);
      setError('Failed to load games. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [debouncedSearchQuery, selectedCategory, selectedSort, nzDesignerFilter, currentPage, pageSize]);

  // Load games when filters change
  useEffect(() => {
    loadGames();
  }, [loadGames]);

  // Handle search
  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
    setCurrentPage(1);
    updateURL({ q: query, page: 1 });
  }, [updateURL]);

  // Handle category filter
  const handleCategoryFilter = useCallback((category: string) => {
    const newCategory = category === selectedCategory ? '' : category;
    setSelectedCategory(newCategory);
    setCurrentPage(1);
    updateURL({ category: newCategory, page: 1 });
  }, [selectedCategory, updateURL]);

  // Handle sort change
  const handleSortChange = useCallback((sort: GameFilters['sort']) => {
    setSelectedSort(sort);
    setCurrentPage(1);
    updateURL({ sort, page: 1 });
  }, [updateURL]);

  // Handle NZ designer filter
  const handleNzDesignerFilter = useCallback(() => {
    const newValue = !nzDesignerFilter;
    setNzDesignerFilter(newValue);
    setCurrentPage(1);
    updateURL({ nz_designer: newValue, page: 1 });
  }, [nzDesignerFilter, updateURL]);

  // Handle pagination
  const handlePageChange = useCallback((page: number) => {
    setCurrentPage(page);
    updateURL({ page });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [updateURL]);

  // Handle game selection
  const handleGameSelect = useCallback(async (game: Game) => {
    setSelectedGame(game);
    addToRecentlyViewed(game);

    // Optionally navigate to game detail page
    navigate(`/game/${game.id}`);
  }, [navigate]);

  // Enhanced category colors
  const getCategoryStyle = (category: string | undefined) => {
    const styles = {
      "GATEWAY_STRATEGY": "bg-emerald-700 text-white border-emerald-800 hover:bg-emerald-800",
      "KIDS_FAMILIES": "bg-purple-700 text-white border-purple-800 hover:bg-purple-800",
      "CORE_STRATEGY": "bg-blue-800 text-white border-blue-900 hover:bg-blue-900",
      "COOP_ADVENTURE": "bg-orange-700 text-white border-orange-800 hover:bg-orange-800",
      "PARTY_ICEBREAKERS": "bg-amber-800 text-white border-amber-900 hover:bg-amber-900",
      "default": "bg-slate-700 text-white border-slate-800 hover:bg-slate-800"
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

  const totalPages = Math.ceil(totalGames / pageSize);

  const activeFiltersCount = useMemo(() => {
    let count = 0;
    if (debouncedSearchQuery) count++;
    if (selectedCategory) count++;
    if (nzDesignerFilter) count++;
    return count;
  }, [debouncedSearchQuery, selectedCategory, nzDesignerFilter]);

  return (
    <div className={`max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 ${className}`}>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-4">Board Game Shop</h1>
        <p className="text-slate-600 max-w-2xl">
          Discover amazing board games from our curated collection. Perfect for cafés, conventions, and team-building events.
        </p>
        {categoryCounts && (
          <div className="text-sm text-slate-500 mt-2">
            {totalGames} games available {activeFiltersCount > 0 && `(${activeFiltersCount} filters active)`}
          </div>
        )}
      </div>

      {/* Search and Filters */}
      <div className="mb-8 space-y-6">
        {/* Search Bar */}
        <div className="relative max-w-md">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <svg className="h-5 w-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            placeholder="Search games by title..."
            className="block w-full pl-10 pr-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          {searchQuery && (
            <button
              onClick={() => handleSearch('')}
              className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600"
              type="button"
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Category Filters */}
        <div className="flex flex-wrap gap-2">
          {CATEGORY_KEYS.map((category) => (
            <button
              key={category}
              onClick={() => handleCategoryFilter(category)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                selectedCategory === category
                  ? getCategoryStyle(category)
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-300'
              }`}
              type="button"
            >
              {CATEGORY_LABELS[category]}
              {categoryCounts?.[category] && (
                <span className="ml-2 opacity-75">({categoryCounts[category]})</span>
              )}
            </button>
          ))}
        </div>

        {/* Additional Filters */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex flex-wrap gap-4">
            {/* NZ Designer Filter */}
            <button
              onClick={handleNzDesignerFilter}
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                nzDesignerFilter
                  ? 'bg-green-600 text-white hover:bg-green-700'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-300'
              }`}
              type="button"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z" clipRule="evenodd" />
              </svg>
              NZ Designers
              {categoryCounts?.nz_designers && (
                <span className="opacity-75">({categoryCounts.nz_designers})</span>
              )}
            </button>
          </div>

          <div className="flex items-center gap-4">
            {/* View Mode Toggle */}
            <div className="flex rounded-lg border border-slate-300 overflow-hidden">
              <button
                onClick={() => setViewMode('grid')}
                className={`px-3 py-2 text-sm font-medium ${
                  viewMode === 'grid'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-slate-700 hover:bg-slate-50'
                }`}
                type="button"
              >
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5zM11 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zM11 13a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                </svg>
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`px-3 py-2 text-sm font-medium ${
                  viewMode === 'list'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-slate-700 hover:bg-slate-50'
                }`}
                type="button"
              >
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
                </svg>
              </button>
            </div>

            {/* Sort Select */}
            <select
              value={selectedSort}
              onChange={(e) => handleSortChange(e.target.value as GameFilters['sort'])}
              className="px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
            >
              <option value="title_asc">Title A-Z</option>
              <option value="title_desc">Title Z-A</option>
              <option value="year_desc">Newest First</option>
              <option value="year_asc">Oldest First</option>
              <option value="rating_desc">Highest Rated</option>
              <option value="rating_asc">Lowest Rated</option>
              <option value="time_asc">Shortest Games</option>
              <option value="time_desc">Longest Games</option>
            </select>
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-8 bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <svg className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <div className="flex-1">
              <h3 className="text-sm font-medium text-red-800">Error</h3>
              <p className="text-sm text-red-700 mt-1">{error}</p>
            </div>
            <button
              onClick={() => setError(null)}
              className="text-red-400 hover:text-red-600"
              type="button"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Content Layout */}
      <div className="flex flex-col lg:flex-row gap-8">
        {/* Main Games Grid/List */}
        <div className="flex-1">
          {loading && games.length === 0 ? (
            <div className={`${viewMode === 'grid' ? 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6' : 'space-y-4'}`}>
              {Array.from({ length: pageSize }).map((_, index) => (
                <div key={index} className="animate-pulse">
                  {viewMode === 'grid' ? (
                    <div className="bg-white rounded-2xl overflow-hidden shadow-md border-2 border-slate-200">
                      <div className="w-full aspect-square bg-slate-200"></div>
                      <div className="p-4 space-y-3">
                        <div className="h-6 bg-slate-200 rounded w-3/4"></div>
                        <div className="space-y-2">
                          <div className="h-4 bg-slate-200 rounded w-1/2"></div>
                          <div className="h-4 bg-slate-200 rounded w-2/3"></div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center gap-4 p-4 bg-white rounded-lg shadow-sm border border-slate-200">
                      <div className="w-16 h-16 bg-slate-200 rounded-md flex-shrink-0"></div>
                      <div className="flex-1 space-y-2">
                        <div className="h-6 bg-slate-200 rounded w-3/4"></div>
                        <div className="h-4 bg-slate-200 rounded w-1/2"></div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : games.length === 0 ? (
            <div className="text-center py-12">
              <div className="w-24 h-24 mx-auto bg-slate-100 rounded-full flex items-center justify-center mb-6">
                <svg className="w-12 h-12 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <h3 className="text-xl font-medium text-slate-900 mb-2">No games found</h3>
              <p className="text-slate-600 mb-6">
                {activeFiltersCount > 0
                  ? 'Try adjusting your search filters to find more games.'
                  : 'No games available at the moment.'}
              </p>
              {activeFiltersCount > 0 && (
                <button
                  onClick={() => {
                    setSearchQuery('');
                    setSelectedCategory('');
                    setNzDesignerFilter(false);
                    updateURL({ q: '', category: '', nz_designer: false, page: 1 });
                  }}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                  type="button"
                >
                  Clear All Filters
                </button>
              )}
            </div>
          ) : (
            <>
              {/* Games Display */}
              <div className={`${viewMode === 'grid' ? 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6' : 'space-y-4'}`}>
                {games.map((game) => (
                  <GameCard
                    key={game.id}
                    game={game}
                    viewMode={viewMode}
                    onSelect={handleGameSelect}
                    getCategoryStyle={getCategoryStyle}
                    formatRating={formatRating}
                    formatTime={formatTime}
                  />
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-2 mt-12">
                  <button
                    onClick={() => handlePageChange(currentPage - 1)}
                    disabled={currentPage <= 1}
                    className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    type="button"
                  >
                    Previous
                  </button>

                  <div className="flex gap-1">
                    {Array.from({ length: Math.min(7, totalPages) }, (_, i) => {
                      const page = Math.max(1, Math.min(totalPages - 6, currentPage - 3)) + i;
                      return (
                        <button
                          key={page}
                          onClick={() => handlePageChange(page)}
                          className={`px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                            currentPage === page
                              ? 'bg-blue-600 text-white'
                              : 'text-slate-700 bg-white border border-slate-300 hover:bg-slate-50'
                          }`}
                          type="button"
                        >
                          {page}
                        </button>
                      );
                    })}
                  </div>

                  <button
                    onClick={() => handlePageChange(currentPage + 1)}
                    disabled={currentPage >= totalPages}
                    className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    type="button"
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          )}
        </div>

        {/* Sidebar */}
        <div className="w-full lg:w-80 space-y-6">
          <RecentlyViewedCards
            maxItems={5}
            onGameSelect={handleGameSelect}
          />
        </div>
      </div>
    </div>
  );
};

// Individual game card component
interface GameCardProps {
  game: Game;
  viewMode: 'grid' | 'list';
  onSelect: (game: Game) => void;
  getCategoryStyle: (category: string | undefined) => string;
  formatRating: (rating?: number | null) => string | null;
  formatTime: (game: Game) => string;
}

const GameCard: React.FC<GameCardProps> = ({
  game,
  viewMode,
  onSelect,
  getCategoryStyle,
  formatRating,
  formatTime
}) => {
  const imgSrc = game.image_url ? imageProxyUrl(game.image_url) : null;
  const categoryLabel = labelFor(game.mana_meeple_category);

  if (viewMode === 'list') {
    return (
      <article
        className="group flex items-center gap-4 p-4 bg-white rounded-lg shadow-sm border border-slate-200 hover:shadow-md hover:border-emerald-300 transition-all duration-200 cursor-pointer"
        onClick={() => onSelect(game)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onSelect(game);
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
  }

  // Grid view
  return (
    <article className="group bg-white rounded-2xl overflow-hidden shadow-md hover:shadow-2xl border-2 border-slate-200 transition-all duration-300 hover:scale-[1.02] hover:border-emerald-300 focus-within:ring-4 focus-within:ring-emerald-200 focus-within:ring-offset-2 cursor-pointer touch-manipulation">
      <button
        onClick={() => onSelect(game)}
        className="w-full text-left focus:outline-none"
        aria-label={`View details for ${game.title}`}
        type="button"
      >
        {/* Image Container */}
        <div className="relative overflow-hidden bg-gradient-to-br from-slate-100 to-slate-200 aspect-square">
          {imgSrc ? (
            <img
              src={imgSrc}
              alt={`Cover art for ${game.title}`}
              className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
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
        </div>

        {/* Content Section */}
        <div className="p-3 sm:p-4">
          {/* Title */}
          <h3 className="font-bold text-base sm:text-lg text-slate-800 mb-2 sm:mb-3 group-hover:text-emerald-700 transition-colors duration-300 line-clamp-2 leading-tight min-h-[3rem] sm:min-h-[3.5rem]">
            {game.title}
          </h3>

          {/* Game Info Grid */}
          <div className="grid grid-cols-2 gap-3 mb-3 sm:mb-4">
            {/* Players */}
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-full bg-emerald-100 flex items-center justify-center flex-shrink-0">
                <svg className="w-4 h-4 text-emerald-700" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
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
              <div className="w-7 h-7 rounded-full bg-amber-100 flex items-center justify-center flex-shrink-0">
                <svg className="w-4 h-4 text-amber-700" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd"/>
                </svg>
              </div>
              <div className="min-w-0">
                <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">Time</div>
                <div className="text-sm font-bold text-slate-800 truncate">
                  {formatTime(game)}
                </div>
              </div>
            </div>

            {/* Rating */}
            {formatRating(game.average_rating) && (
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-full bg-yellow-100 flex items-center justify-center flex-shrink-0">
                  <svg className="w-4 h-4 text-yellow-700" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                </div>
                <div className="min-w-0">
                  <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">Rating</div>
                  <div className="text-sm font-bold text-slate-800 truncate">
                    {formatRating(game.average_rating)}
                  </div>
                </div>
              </div>
            )}

            {/* Year */}
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                <svg className="w-4 h-4 text-blue-700" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
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
      </button>
    </article>
  );
};

export default ShopPage;