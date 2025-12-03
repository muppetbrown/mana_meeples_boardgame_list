// src/pages/PublicCatalogue.jsx - Enhanced Mobile-First Version
import React, { useEffect, useState, useMemo, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { getPublicGames, getPublicCategoryCounts } from "../api/client";
import { CATEGORY_KEYS, CATEGORY_LABELS } from "../constants/categories";
import GameCardPublic from "../components/public/GameCardPublic";
import SortSelect from "../components/public/SortSelect";
import SearchBox from "../components/public/SearchBox";

export default function PublicCatalogue() {
  // Use URL parameters to preserve state
  const [searchParams, setSearchParams] = useSearchParams();
  
  // Get initial values from URL or defaults - CHANGED: default sort to recent
  const [q, setQ] = useState(searchParams.get("q") || "");
  const [qDebounced, setQDebounced] = useState(q);
  const [category, setCategory] = useState(searchParams.get("category") || "all");
  const [designer, setDesigner] = useState(searchParams.get("designer") || "");
  const [nzDesigner, setNzDesigner] = useState(searchParams.get("nz_designer") === "true");
  const [players, setPlayers] = useState(searchParams.get("players") || "");
  const [recentlyAdded, setRecentlyAdded] = useState(searchParams.get("recently_added") === "30");
  const [sort, setSort] = useState(searchParams.get("sort") || "year_desc"); // NEW: Default to recent
  const [page, setPage] = useState(1); // NEW: Always start at page 1
  const [pageSize] = useState(12); // NEW: Smaller initial load

  // Loading states
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);
  const [items, setItems] = useState([]);
  const [allLoadedItems, setAllLoadedItems] = useState([]); // NEW: Track all loaded items
  const [total, setTotal] = useState(0);
  const [counts, setCounts] = useState(null);

  // UI state
  const [showScrollTop, setShowScrollTop] = useState(false);
  const [isHeaderVisible, setIsHeaderVisible] = useState(true); // NEW: Header visibility
  const [isFilterExpanded, setIsFilterExpanded] = useState(false); // NEW: Filter panel state
  const [isSticky, setIsSticky] = useState(false); // NEW: Sticky toolbar state
  const [expandedCards, setExpandedCards] = useState(new Set()); // NEW: Track expanded cards

  // Refs for scroll detection
  const lastScrollY = useRef(0);
  const headerRef = useRef(null);

  // Debounce search input
  useEffect(() => {
    const id = setTimeout(() => setQDebounced(q), 150);
    return () => clearTimeout(id);
  }, [q]);

  // Handle scroll for header hide/show and sticky toolbar
  useEffect(() => {
    const handleScroll = () => {
      const currentScrollY = window.scrollY;
      
      // Show/hide scroll to top button
      setShowScrollTop(currentScrollY > 400);
      
      // Header hide/show on scroll direction
      if (currentScrollY > 100) {
        if (currentScrollY > lastScrollY.current) {
          // Scrolling down
          setIsHeaderVisible(false);
          setIsSticky(true);
        } else {
          // Scrolling up
          setIsHeaderVisible(true);
        }
      } else {
        setIsHeaderVisible(true);
        setIsSticky(false);
      }
      
      lastScrollY.current = currentScrollY;
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Update URL when filters change
  useEffect(() => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (category !== "all") params.set("category", category);
    if (designer) params.set("designer", designer);
    if (nzDesigner) params.set("nz_designer", "true");
    if (players) params.set("players", players);
    if (recentlyAdded) params.set("recently_added", "30");
    if (sort !== "year_desc") params.set("sort", sort); // Changed default

    setSearchParams(params, { replace: true });
  }, [q, category, designer, nzDesigner, players, recentlyAdded, sort, setSearchParams]);

  // Fetch category counts
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const c = await getPublicCategoryCounts();
        if (!cancelled) setCounts(c);
      } catch (err) {
        console.warn("Failed to load category counts:", err);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Fetch games - NEW: Reset allLoadedItems when filters change
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setPage(1); // Reset to page 1 on filter change

    (async () => {
      try {
        const params = { q: qDebounced, page: 1, page_size: pageSize, sort };
        if (category !== "all") params.category = category;
        if (designer) params.designer = designer;
        if (nzDesigner) params.nz_designer = true;
        if (players) params.players = parseInt(players);
        if (recentlyAdded) params.recently_added = 30;

        const data = await getPublicGames(params);
        if (cancelled) return;

        setItems(data.items || []);
        setAllLoadedItems(data.items || []); // NEW: Initialize loaded items
        setTotal(data.total || 0);
        setError(null);
      } catch (e) {
        if (!cancelled) {
          setError("Failed to load games. Please try again.");
          setItems([]);
          setAllLoadedItems([]);
          setTotal(0);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [qDebounced, pageSize, category, designer, nzDesigner, players, recentlyAdded, sort]);

  // Load more function - NEW
  const loadMore = async () => {
    if (loadingMore || allLoadedItems.length >= total) return;
    
    setLoadingMore(true);
    const nextPage = page + 1;

    try {
      const params = { q: qDebounced, page: nextPage, page_size: pageSize, sort };
      if (category !== "all") params.category = category;
      if (designer) params.designer = designer;
      if (nzDesigner) params.nz_designer = true;
      if (players) params.players = parseInt(players);
      if (recentlyAdded) params.recently_added = 30;

      const data = await getPublicGames(params);
      
      setAllLoadedItems(prev => [...prev, ...(data.items || [])]);
      setPage(nextPage);
    } catch (e) {
      console.error("Failed to load more games:", e);
    } finally {
      setLoadingMore(false);
    }
  };

  // Helper functions
  const updateCategory = (newCategory) => {
    setCategory(newCategory);
    setExpandedCards(new Set()); // Collapse all cards on filter change
  };

  const updateSort = (newSort) => {
    setSort(newSort);
  };

  const updateSearch = (newSearch) => {
    setQ(newSearch);
  };

  const clearAllFilters = () => {
    setQ("");
    setCategory("all");
    setDesigner("");
    setNzDesigner(false);
    setPlayers("");
    setRecentlyAdded(false);
    setSort("year_desc");
    setExpandedCards(new Set());
  };

  const toggleNzDesigner = () => {
    setNzDesigner(!nzDesigner);
  };

  const toggleRecentlyAdded = () => {
    setRecentlyAdded(!recentlyAdded);
  };

  const updatePlayers = (newPlayers) => {
    setPlayers(newPlayers);
  };

  // NEW: Toggle card expansion
  const toggleCardExpansion = (gameId) => {
    setExpandedCards(prev => {
      const next = new Set(prev);
      if (next.has(gameId)) {
        next.delete(gameId);
      } else {
        next.clear(); // Accordion: only one open at a time
        next.add(gameId);
      }
      return next;
    });
  };

  // Scroll to top
  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Active filters count
  const activeFiltersCount = useMemo(() => {
    let count = 0;
    if (q) count++;
    if (category !== "all") count++;
    if (designer) count++;
    if (nzDesigner) count++;
    if (players) count++;
    if (recentlyAdded) count++;
    return count;
  }, [q, category, designer, nzDesigner, players, recentlyAdded]);

  // Reduce motion preference
  const prefersReducedMotion = useMemo(() => {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }, []);

  const transitionClass = prefersReducedMotion ? '' : 'transition-all duration-300';

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-emerald-50 to-amber-50">
      <div className="container mx-auto px-4 py-4 sm:py-8">
        
        {/* Header - with scroll-away behavior */}
        <header 
          ref={headerRef}
          className={`mb-4 text-center ${transitionClass} ${
            isHeaderVisible ? 'opacity-100 translate-y-0' : 'opacity-0 -translate-y-4 pointer-events-none'
          }`}
          style={{ height: isHeaderVisible ? 'auto' : '0', overflow: 'hidden' }}
        >
          <h1 className="text-2xl sm:text-4xl font-bold bg-gradient-to-r from-emerald-700 via-teal-600 to-amber-600 bg-clip-text text-transparent mb-2">
            Mana & Meeples
          </h1>
          <p className="text-sm sm:text-lg text-slate-600 mb-1">
            Timaru's Board Game Community
          </p>
          <p className="text-xs sm:text-sm text-slate-500 mb-3">
            Explore our game collection -{" "}
            <a 
              href="https://manaandmeeples.co.nz" 
              className="text-emerald-600 hover:underline focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 rounded"
            >
              manaandmeeples.co.nz
            </a>
          </p>
          <div className="w-12 sm:w-20 h-1 bg-gradient-to-r from-emerald-500 to-amber-500 mx-auto rounded-full" aria-hidden="true"></div>
        </header>

        <main id="main-content">
          
          {/* Sticky Search/Filter Toolbar - Mobile */}
          <div className={`md:hidden ${transitionClass} ${
            isSticky ? 'fixed top-0 left-0 right-0 z-40 shadow-lg' : 'relative'
          }`}>
            <div className="bg-white/95 backdrop-blur-sm border-b border-slate-200">
              
              {/* Collapsed Search Bar */}
              <div className="flex items-center gap-2 p-3">
                <button
                  onClick={() => setIsFilterExpanded(!isFilterExpanded)}
                  className="flex-1 flex items-center gap-2 min-h-[44px] px-3 py-2 bg-white border-2 border-slate-300 rounded-xl hover:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-colors"
                  aria-expanded={isFilterExpanded}
                  aria-label={`${isFilterExpanded ? 'Collapse' : 'Expand'} search and filters`}
                >
                  <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  <span className="flex-1 text-left text-slate-600">
                    {q || "Search games..."}
                  </span>
                  {activeFiltersCount > 0 && (
                    <span className="bg-emerald-500 text-white text-xs font-bold px-2 py-1 rounded-full">
                      {activeFiltersCount}
                    </span>
                  )}
                  <svg 
                    className={`w-4 h-4 text-slate-400 ${transitionClass} ${isFilterExpanded ? 'rotate-180' : ''}`} 
                    fill="none" 
                    stroke="currentColor" 
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                <SortSelect
                  sort={sort}
                  onChange={updateSort}
                  className="w-32"
                />
              </div>

              {/* Expanded Filter Panel */}
              {isFilterExpanded && (
                <div className="p-3 space-y-3 border-t border-slate-200 bg-slate-50">
                  
                  {/* Search */}
                  <div>
                    <label htmlFor="search-mobile" className="block text-sm font-semibold text-slate-700 mb-1.5">
                      Search Games
                    </label>
                    <SearchBox
                      id="search-mobile"
                      value={q}
                      onChange={updateSearch}
                      placeholder="Search by title..."
                      className="w-full"
                    />
                  </div>

                  {/* Player Count */}
                  <div>
                    <label htmlFor="players-mobile" className="block text-sm font-semibold text-slate-700 mb-1.5">
                      Player Count
                    </label>
                    <select
                      id="players-mobile"
                      value={players}
                      onChange={(e) => updatePlayers(e.target.value)}
                      className="w-full min-h-[44px] px-3 py-2 text-sm border-2 border-slate-300 rounded-xl focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200 focus:outline-none bg-white"
                    >
                      <option value="">Any</option>
                      <option value="1">1 player</option>
                      <option value="2">2 players</option>
                      <option value="3">3 players</option>
                      <option value="4">4 players</option>
                      <option value="5">5 players</option>
                      <option value="6">6 players</option>
                      <option value="7">7+ players</option>
                      <option value="8">8+ players</option>
                      <option value="10">10+ players</option>
                    </select>
                  </div>

                  {/* Quick Filters */}
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={toggleNzDesigner}
                      className={`min-h-[44px] px-3 py-2 text-sm font-medium rounded-xl ${transitionClass} focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                        nzDesigner
                          ? "bg-blue-600 text-white shadow-md focus:ring-blue-300"
                          : "bg-white text-blue-800 border-2 border-blue-200 hover:bg-blue-50 focus:ring-blue-300"
                      }`}
                      aria-pressed={nzDesigner}
                    >
                      <span className="flex items-center justify-center gap-1.5">
                        <span aria-hidden="true">🇳🇿</span>
                        <span>NZ Designer</span>
                      </span>
                    </button>

                    <button
                      onClick={toggleRecentlyAdded}
                      className={`min-h-[44px] px-3 py-2 text-sm font-medium rounded-xl ${transitionClass} focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                        recentlyAdded
                          ? "bg-purple-600 text-white shadow-md focus:ring-purple-300"
                          : "bg-white text-purple-800 border-2 border-purple-200 hover:bg-purple-50 focus:ring-purple-300"
                      }`}
                      aria-pressed={recentlyAdded}
                    >
                      <span className="flex items-center justify-center gap-1.5">
                        <span aria-hidden="true">✨</span>
                        <span>Recent (30d)</span>
                      </span>
                    </button>
                  </div>

                  {/* Clear Filters */}
                  {activeFiltersCount > 0 && (
                    <button
                      onClick={clearAllFilters}
                      className="w-full min-h-[44px] px-4 py-2 text-sm font-medium rounded-xl bg-slate-100 text-slate-800 hover:bg-slate-200 border-2 border-slate-300 focus:outline-none focus:ring-2 focus:ring-slate-300"
                    >
                      <span className="flex items-center justify-center gap-2">
                        <span>Clear All Filters</span>
                        <span className="bg-slate-200 px-2 py-0.5 rounded-full text-xs font-bold">
                          {activeFiltersCount}
                        </span>
                      </span>
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Desktop Filter Section - Unchanged for now */}
          <section 
            className="hidden md:block bg-white/90 backdrop-blur-sm rounded-2xl p-5 shadow-lg border border-slate-200/50 mb-6"
            aria-labelledby="search-filters-heading"
          >
            <h2 id="search-filters-heading" className="sr-only">
              Search and Filter Games
            </h2>

            <div className="space-y-3">
              {/* Row 1: Search + Players */}
              <div className="flex gap-3 items-end">
                <div className="flex-1">
                  <label htmlFor="search-desktop" className="block text-sm font-semibold text-slate-700 mb-1.5">
                    Search Games
                  </label>
                  <SearchBox
                    id="search-desktop"
                    value={q}
                    onChange={updateSearch}
                    placeholder="Search by title..."
                  />
                </div>

                <div className="w-40">
                  <label htmlFor="players-desktop" className="block text-sm font-semibold text-slate-700 mb-1.5">
                    Players
                  </label>
                  <select
                    id="players-desktop"
                    value={players}
                    onChange={(e) => updatePlayers(e.target.value)}
                    className="w-full min-h-[48px] px-3 py-2 border-2 border-slate-300 rounded-xl focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200 focus:outline-none bg-white"
                  >
                    <option value="">Any</option>
                    <option value="1">1p</option>
                    <option value="2">2p</option>
                    <option value="3">3p</option>
                    <option value="4">4p</option>
                    <option value="5">5p</option>
                    <option value="6">6p</option>
                    <option value="7">7p+</option>
                    <option value="8">8p+</option>
                    <option value="10">10p+</option>
                  </select>
                </div>
              </div>

              {/* Row 2: NZ Designer + Recent + Sort */}
              <div className="flex gap-3 items-end">
                <button
                  onClick={toggleNzDesigner}
                  className={`min-h-[48px] px-4 py-2.5 text-sm font-medium rounded-xl ${transitionClass} focus:outline-none focus:ring-3 focus:ring-offset-2 ${
                    nzDesigner
                      ? "bg-blue-600 text-white shadow-md focus:ring-blue-300"
                      : "bg-blue-50 text-blue-800 hover:bg-blue-100 border-2 border-blue-200 focus:ring-blue-300"
                  }`}
                  aria-pressed={nzDesigner}
                >
                  <span className="flex items-center gap-1.5">
                    <span aria-hidden="true">🇳🇿</span>
                    <span>NZ Designed</span>
                  </span>
                </button>

                <button
                  onClick={toggleRecentlyAdded}
                  className={`min-h-[48px] px-4 py-2.5 text-sm font-medium rounded-xl ${transitionClass} focus:outline-none focus:ring-3 focus:ring-offset-2 ${
                    recentlyAdded
                      ? "bg-purple-600 text-white shadow-md focus:ring-purple-300"
                      : "bg-purple-50 text-purple-800 hover:bg-purple-100 border-2 border-purple-200 focus:ring-purple-300"
                  }`}
                  aria-pressed={recentlyAdded}
                >
                  <span className="flex items-center gap-1.5">
                    <span aria-hidden="true">✨</span>
                    <span>Recent</span>
                  </span>
                </button>

                <div className="w-40">
                  <label htmlFor="sort-desktop" className="block text-sm font-semibold text-slate-700 mb-1.5">
                    Sort By
                  </label>
                  <SortSelect
                    id="sort-desktop"
                    sort={sort}
                    onChange={updateSort}
                  />
                </div>

                {activeFiltersCount > 0 && (
                  <button
                    onClick={clearAllFilters}
                    className="min-h-[48px] px-4 py-2 text-sm font-medium rounded-xl bg-slate-100 text-slate-800 hover:bg-slate-200 border-2 border-slate-300 focus:outline-none focus:ring-2 focus:ring-slate-300"
                  >
                    <span className="flex items-center gap-2">
                      <span aria-hidden="true">🗑️</span>
                      <span>Clear Filters</span>
                      <span className="bg-slate-200 px-2 py-0.5 rounded-full text-xs font-bold">
                        {activeFiltersCount}
                      </span>
                    </span>
                  </button>
                )}
              </div>
            </div>
          </section>

          {/* Category Pills - Sticky with toolbar */}
          <section 
            className={`mb-6 ${transitionClass} ${
              isSticky ? 'md:sticky md:top-0 md:z-30 md:bg-white/95 md:backdrop-blur-sm md:py-4 md:shadow-md' : ''
            }`}
            aria-labelledby="categories-heading"
          >
            <h2 id="categories-heading" className="sr-only">
              Game Categories
            </h2>
            <div className="flex gap-2 overflow-x-auto pb-3 px-2 -mx-2 snap-x scrollbar-hide">
              <button
                onClick={() => updateCategory("all")}
                className={`flex-shrink-0 snap-start rounded-full px-4 py-2 text-sm font-medium whitespace-nowrap ${transitionClass} min-h-[44px] focus:outline-none focus:ring-3 focus:ring-offset-2 ${
                  category === "all"
                    ? "bg-emerald-500 text-white shadow-md focus:ring-emerald-300"
                    : "bg-white/90 text-slate-700 border border-slate-200 hover:border-emerald-300 focus:ring-emerald-300"
                }`}
                aria-pressed={category === "all"}
              >
                All ({counts?.all ?? "..."})
              </button>

              {CATEGORY_KEYS.map((key) => (
                <button
                  key={key}
                  onClick={() => updateCategory(key)}
                  className={`flex-shrink-0 snap-start rounded-full px-4 py-2 text-sm font-medium whitespace-nowrap ${transitionClass} min-h-[44px] focus:outline-none focus:ring-3 focus:ring-offset-2 ${
                    category === key
                      ? "bg-emerald-500 text-white shadow-md focus:ring-emerald-300"
                      : "bg-white/90 text-slate-700 border border-slate-200 hover:border-emerald-300 focus:ring-emerald-300"
                  }`}
                  aria-pressed={category === key}
                >
                  {CATEGORY_LABELS[key]} ({counts?.[key] ?? "..."})
                </button>
              ))}
            </div>
          </section>

          {/* Results Summary */}
          {q && (
            <div className="mb-4 text-center text-slate-600">
              <span className="text-sm font-medium">
                {total} game{total !== 1 ? 's' : ''} found for "{q}"
              </span>
            </div>
          )}

          {/* Games Grid */}
          {error && (
            <div className="text-center py-12">
              <p className="text-red-600 mb-4">{error}</p>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700"
              >
                Retry
              </button>
            </div>
          )}

          {loading && (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-emerald-500 border-t-transparent"></div>
              <p className="mt-4 text-slate-600">Loading games...</p>
            </div>
          )}

          {!loading && !error && allLoadedItems.length === 0 && (
            <div className="text-center py-12">
              <p className="text-slate-600 text-lg">No games found matching your criteria.</p>
              <button
                onClick={clearAllFilters}
                className="mt-4 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700"
              >
                Clear Filters
              </button>
            </div>
          )}

          {!loading && !error && allLoadedItems.length > 0 && (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-6">
                {allLoadedItems.map((game) => (
                  <GameCardPublic
                    key={game.id}
                    game={game}
                    isExpanded={expandedCards.has(game.id)}
                    onToggleExpand={() => toggleCardExpansion(game.id)}
                    prefersReducedMotion={prefersReducedMotion}
                  />
                ))}
              </div>

              {/* Load More Button */}
              {allLoadedItems.length < total && (
                <div className="mt-8 text-center">
                  <button
                    onClick={loadMore}
                    disabled={loadingMore}
                    className="min-h-[48px] px-8 py-3 bg-emerald-600 text-white font-medium rounded-xl hover:bg-emerald-700 focus:outline-none focus:ring-3 focus:ring-emerald-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {loadingMore ? (
                      <span className="flex items-center gap-2">
                        <span className="inline-block animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></span>
                        Loading more...
                      </span>
                    ) : (
                      <span>Load More ({allLoadedItems.length} of {total})</span>
                    )}
                  </button>
                </div>
              )}

              {/* End of results message */}
              {allLoadedItems.length >= total && total > pageSize && (
                <div className="mt-8 text-center">
                  <p className="text-slate-600">
                    You've viewed all {total} games!
                  </p>
                </div>
              )}
            </>
          )}
        </main>

        {/* Scroll to Top Button */}
        {showScrollTop && (
          <button
            onClick={scrollToTop}
            className="fixed bottom-6 right-6 z-50 p-3 bg-emerald-600 text-white rounded-full shadow-lg hover:bg-emerald-700 focus:outline-none focus:ring-3 focus:ring-emerald-500 focus:ring-offset-2 transition-colors"
            aria-label="Scroll to top"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}
