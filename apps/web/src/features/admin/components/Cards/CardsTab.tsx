import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Game, GameFilters, PaginatedGamesResponse, CategoryCounts } from '../../../types/game';
import {
  getPublicGames,
  getPublicCategoryCounts,
  updateGame,
  deleteGame,
  bulkImportCsv,
  bulkCategorizeCsv,
  bulkUpdateNZDesigners
} from '../../../../../../../frontend/src/api/client.js';
import { CATEGORY_KEYS, CATEGORY_LABELS, labelFor } from '../../../../../../../frontend/src/constants/categories';
import { imageProxyUrl } from '../../../../../../../frontend/src/utils/api';

interface CardsTabProps {
  className?: string;
}

interface BulkOperation {
  type: 'import' | 'categorize' | 'nz_designers';
  isVisible: boolean;
  isLoading: false;
}

const CardsTab: React.FC<CardsTabProps> = ({ className = '' }) => {
  const [games, setGames] = useState<Game[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [categoryCounts, setCategoryCounts] = useState<CategoryCounts | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalGames, setTotalGames] = useState(0);
  const [pageSize] = useState(20);

  // Filters
  const [filters, setFilters] = useState<GameFilters>({
    page: 1,
    page_size: 20,
    sort: 'title_asc'
  });

  // Bulk operations state
  const [bulkOperation, setBulkOperation] = useState<BulkOperation>({
    type: 'import',
    isVisible: false,
    isLoading: false
  });
  const [csvInput, setCsvInput] = useState('');

  // Load games and category counts
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [gamesResponse, countsResponse] = await Promise.all([
        getPublicGames(filters),
        getPublicCategoryCounts()
      ]);

      setGames(gamesResponse.items || []);
      setTotalGames(gamesResponse.total || 0);
      setCurrentPage(gamesResponse.page || 1);
      setCategoryCounts(countsResponse);

    } catch (err) {
      console.error('Failed to load admin data:', err);
      setError('Failed to load games. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [filters]);

  // Load data on mount and when filters change
  useEffect(() => {
    loadData();
  }, [loadData]);

  // Handle filter changes
  const handleFilterChange = useCallback((newFilters: Partial<GameFilters>) => {
    setFilters(prev => ({
      ...prev,
      ...newFilters,
      page: 1 // Reset to first page when changing filters
    }));
  }, []);

  // Handle pagination
  const handlePageChange = useCallback((page: number) => {
    setFilters(prev => ({ ...prev, page }));
  }, []);

  // Handle game updates
  const handleUpdateGame = useCallback(async (gameId: number, updates: Partial<Game>) => {
    try {
      await updateGame(gameId, updates);
      // Refresh the list
      await loadData();
    } catch (err) {
      console.error('Failed to update game:', err);
      setError('Failed to update game. Please try again.');
    }
  }, [loadData]);

  // Handle game deletion
  const handleDeleteGame = useCallback(async (gameId: number) => {
    if (!confirm('Are you sure you want to delete this game? This action cannot be undone.')) {
      return;
    }

    try {
      await deleteGame(gameId);
      // Refresh the list
      await loadData();
    } catch (err) {
      console.error('Failed to delete game:', err);
      setError('Failed to delete game. Please try again.');
    }
  }, [loadData]);

  // Handle bulk operations
  const handleBulkOperation = useCallback(async (type: BulkOperation['type'], csvData: string) => {
    if (!csvData.trim()) {
      setError('Please provide CSV data');
      return;
    }

    try {
      setBulkOperation(prev => ({ ...prev, isLoading: true }));
      setError(null);

      switch (type) {
        case 'import':
          await bulkImportCsv(csvData);
          break;
        case 'categorize':
          await bulkCategorizeCsv(csvData);
          break;
        case 'nz_designers':
          await bulkUpdateNZDesigners(csvData);
          break;
      }

      setCsvInput('');
      setBulkOperation(prev => ({ ...prev, isVisible: false }));
      await loadData();

    } catch (err) {
      console.error(`Failed to perform ${type} operation:`, err);
      setError(`Failed to perform ${type} operation. Please try again.`);
    } finally {
      setBulkOperation(prev => ({ ...prev, isLoading: false }));
    }
  }, [loadData]);

  // Enhanced category colors
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

  const formatRating = (rating?: number | null): string => {
    if (!rating || rating === 0) return 'Unrated';
    return parseFloat(String(rating)).toFixed(1);
  };

  const totalPages = Math.ceil(totalGames / pageSize);

  if (loading && games.length === 0) {
    return (
      <div className={`space-y-6 ${className}`}>
        <div className="animate-pulse space-y-4">
          {Array.from({ length: 5 }).map((_, index) => (
            <div key={index} className="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
              <div className="flex gap-4">
                <div className="w-24 h-24 bg-slate-200 rounded-md flex-shrink-0"></div>
                <div className="flex-1 space-y-3">
                  <div className="h-6 bg-slate-200 rounded w-3/4"></div>
                  <div className="h-4 bg-slate-200 rounded w-1/2"></div>
                  <div className="flex gap-4">
                    <div className="h-4 bg-slate-200 rounded w-20"></div>
                    <div className="h-4 bg-slate-200 rounded w-20"></div>
                    <div className="h-4 bg-slate-200 rounded w-20"></div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header with controls */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Game Cards Management</h1>
          <p className="text-slate-600">Manage your board game collection</p>
          {categoryCounts && (
            <div className="text-sm text-slate-500 mt-1">
              Total: {categoryCounts.all} games | Uncategorized: {categoryCounts.uncategorized}
            </div>
          )}
        </div>

        <div className="flex flex-col sm:flex-row gap-3">
          {/* Bulk Operations Dropdown */}
          <div className="relative">
            <button
              onClick={() => setBulkOperation(prev => ({ ...prev, isVisible: !prev.isVisible }))}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
              type="button"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
              Bulk Operations
            </button>
          </div>

          {/* Filters */}
          <div className="flex gap-2">
            <select
              value={filters.sort}
              onChange={(e) => handleFilterChange({ sort: e.target.value as GameFilters['sort'] })}
              className="px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
            >
              <option value="title_asc">Title A-Z</option>
              <option value="title_desc">Title Z-A</option>
              <option value="year_asc">Year (Old-New)</option>
              <option value="year_desc">Year (New-Old)</option>
              <option value="rating_desc">Highest Rated</option>
              <option value="rating_asc">Lowest Rated</option>
            </select>

            <select
              value={filters.category || ''}
              onChange={(e) => handleFilterChange({ category: e.target.value || undefined })}
              className="px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
            >
              <option value="">All Categories</option>
              <option value="uncategorized">Uncategorized</option>
              {CATEGORY_KEYS.map(key => (
                <option key={key} value={key}>{CATEGORY_LABELS[key]}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Bulk Operations Panel */}
      {bulkOperation.isVisible && (
        <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-slate-900">Bulk Operations</h2>
            <button
              onClick={() => setBulkOperation(prev => ({ ...prev, isVisible: false }))}
              className="text-slate-400 hover:text-slate-600"
              type="button"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="space-y-4">
            <div className="flex gap-2">
              {(['import', 'categorize', 'nz_designers'] as const).map((type) => (
                <button
                  key={type}
                  onClick={() => setBulkOperation(prev => ({ ...prev, type }))}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    bulkOperation.type === type
                      ? 'bg-blue-100 text-blue-800 border border-blue-300'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                  type="button"
                >
                  {type === 'import' ? 'Import Games' : type === 'categorize' ? 'Categorize' : 'NZ Designers'}
                </button>
              ))}
            </div>

            <textarea
              value={csvInput}
              onChange={(e) => setCsvInput(e.target.value)}
              placeholder={
                bulkOperation.type === 'import'
                  ? 'Enter BGG IDs (one per line or comma-separated)'
                  : bulkOperation.type === 'categorize'
                  ? 'Enter CSV: game_id,category'
                  : 'Enter CSV: game_id,is_nz_designer'
              }
              rows={6}
              className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm font-mono"
            />

            <button
              onClick={() => handleBulkOperation(bulkOperation.type, csvInput)}
              disabled={bulkOperation.isLoading || !csvInput.trim()}
              className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              type="button"
            >
              {bulkOperation.isLoading ? (
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth={4}></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              )}
              Execute {bulkOperation.type}
            </button>
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
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

      {/* Games List */}
      <div className="space-y-4">
        {games.map((game) => (
          <GameAdminCard
            key={game.id}
            game={game}
            onUpdate={handleUpdateGame}
            onDelete={handleDeleteGame}
            getCategoryStyle={getCategoryStyle}
            formatRating={formatRating}
          />
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-8">
          <button
            onClick={() => handlePageChange(currentPage - 1)}
            disabled={currentPage <= 1}
            className="px-3 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-md hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
            type="button"
          >
            Previous
          </button>

          <div className="flex gap-1">
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              const page = Math.max(1, Math.min(totalPages - 4, currentPage - 2)) + i;
              return (
                <button
                  key={page}
                  onClick={() => handlePageChange(page)}
                  className={`px-3 py-2 text-sm font-medium rounded-md ${
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
            className="px-3 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-md hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
            type="button"
          >
            Next
          </button>
        </div>
      )}

      {games.length === 0 && !loading && (
        <div className="text-center py-12">
          <div className="w-24 h-24 mx-auto bg-slate-100 rounded-full flex items-center justify-center mb-6">
            <svg className="w-12 h-12 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
          </div>
          <h3 className="text-xl font-medium text-slate-900 mb-2">No games found</h3>
          <p className="text-slate-600 mb-4">Try adjusting your filters or import some games to get started.</p>
        </div>
      )}
    </div>
  );
};

// Individual game admin card component
interface GameAdminCardProps {
  game: Game;
  onUpdate: (gameId: number, updates: Partial<Game>) => Promise<void>;
  onDelete: (gameId: number) => Promise<void>;
  getCategoryStyle: (category: string | undefined) => string;
  formatRating: (rating?: number | null) => string;
}

const GameAdminCard: React.FC<GameAdminCardProps> = ({
  game,
  onUpdate,
  onDelete,
  getCategoryStyle,
  formatRating
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editingCategory, setEditingCategory] = useState(game.mana_meeple_category || '');
  const [editingNZDesigner, setEditingNZDesigner] = useState(game.nz_designer || false);

  const imgSrc = game.image_url ? imageProxyUrl(game.image_url) : null;
  const categoryLabel = labelFor(game.mana_meeple_category);

  const handleSaveChanges = async () => {
    try {
      await onUpdate(game.id, {
        mana_meeple_category: editingCategory || null,
        nz_designer: editingNZDesigner
      });
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to save changes:', error);
    }
  };

  return (
    <article className="bg-white rounded-lg shadow-sm border border-slate-200 p-6 hover:shadow-md transition-shadow">
      <div className="flex gap-6">
        {/* Game Image */}
        <div className="relative overflow-hidden bg-gradient-to-br from-slate-100 to-slate-200 w-24 h-24 rounded-md flex-shrink-0">
          {imgSrc ? (
            <img
              src={imgSrc}
              alt={`Cover art for ${game.title}`}
              className="w-full h-full object-cover"
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

          <div className={`w-full h-full flex items-center justify-center text-slate-400 ${imgSrc ? 'hidden' : 'flex'}`}>
            <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
              <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
            </svg>
          </div>
        </div>

        {/* Game Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between mb-3">
            <h3 className="text-xl font-bold text-slate-900 truncate pr-4">{game.title}</h3>
            <div className="flex gap-2 flex-shrink-0">
              <button
                onClick={() => setIsEditing(!isEditing)}
                className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-md transition-colors"
                type="button"
                aria-label="Edit game"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </button>
              <button
                onClick={() => onDelete(game.id)}
                className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
                type="button"
                aria-label="Delete game"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-4">
            <div>
              <span className="text-slate-500 block">Players</span>
              <span className="font-medium text-slate-900">
                {game.min_players && game.max_players ? `${game.min_players}-${game.max_players}` : 'Unknown'}
              </span>
            </div>
            <div>
              <span className="text-slate-500 block">Time</span>
              <span className="font-medium text-slate-900">
                {game.playtime_min ? `${game.playtime_min} min` : 'Unknown'}
              </span>
            </div>
            <div>
              <span className="text-slate-500 block">Year</span>
              <span className="font-medium text-slate-900">{game.year || 'Unknown'}</span>
            </div>
            <div>
              <span className="text-slate-500 block">Rating</span>
              <span className="font-medium text-slate-900">{formatRating(game.average_rating)}</span>
            </div>
          </div>

          {/* Editing Mode */}
          {isEditing ? (
            <div className="space-y-4 p-4 bg-slate-50 rounded-lg">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">Category</label>
                  <select
                    value={editingCategory}
                    onChange={(e) => setEditingCategory(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="">Uncategorized</option>
                    {CATEGORY_KEYS.map(key => (
                      <option key={key} value={key}>{CATEGORY_LABELS[key]}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">NZ Designer</label>
                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      checked={editingNZDesigner}
                      onChange={(e) => setEditingNZDesigner(e.target.checked)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-slate-300 rounded"
                    />
                    <span className="ml-2 text-sm text-slate-700">New Zealand Designer</span>
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleSaveChanges}
                  className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
                  type="button"
                >
                  Save Changes
                </button>
                <button
                  onClick={() => {
                    setIsEditing(false);
                    setEditingCategory(game.mana_meeple_category || '');
                    setEditingNZDesigner(game.nz_designer || false);
                  }}
                  className="px-4 py-2 bg-slate-300 text-slate-700 rounded-md hover:bg-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-500 focus:ring-offset-2"
                  type="button"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-3">
              {categoryLabel && (
                <span className={`px-2 py-1 rounded text-xs font-bold ${getCategoryStyle(game.mana_meeple_category)}`}>
                  {categoryLabel}
                </span>
              )}
              {game.nz_designer && (
                <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-bold">
                  NZ Designer
                </span>
              )}
              {game.bgg_id && (
                <span className="text-xs text-slate-500">BGG ID: {game.bgg_id}</span>
              )}
            </div>
          )}
        </div>
      </div>
    </article>
  );
};

export default CardsTab;