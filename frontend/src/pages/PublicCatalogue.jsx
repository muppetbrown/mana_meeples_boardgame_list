// src/pages/PublicCatalogue.jsx
import React, { useEffect, useState, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { getPublicGames, getPublicCategoryCounts } from "../api/client";
import { CATEGORY_KEYS, CATEGORY_LABELS } from "../constants/categories";
import GameCardPublic from "../components/public/GameCardPublic";
import SortSelect from "../components/public/SortSelect";
import SearchBox from "../components/public/SearchBox";
import Pagination from "../components/public/Pagination";

export default function PublicCatalogue() {
  // Use URL parameters to preserve state
  const [searchParams, setSearchParams] = useSearchParams();
  
  // Get initial values from URL or defaults
  const [q, setQ] = useState(searchParams.get("q") || "");
  const [qDebounced, setQDebounced] = useState(q);
  const [category, setCategory] = useState(searchParams.get("category") || "all");
  const [designer, setDesigner] = useState(searchParams.get("designer") || "");
  const [nzDesigner, setNzDesigner] = useState(searchParams.get("nz_designer") === "true");
  const [players, setPlayers] = useState(searchParams.get("players") || "");
  const [recentlyAdded, setRecentlyAdded] = useState(searchParams.get("recently_added") === "30");
  const [sort, setSort] = useState(searchParams.get("sort") || "title_asc");
  const [page, setPage] = useState(parseInt(searchParams.get("page")) || 1);
  const [pageSize] = useState(24);

  // Simplified loading state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [counts, setCounts] = useState(null);

  // Quick search shortcuts
  const [quickSort, setQuickSort] = useState(null);

  // Scroll to top button visibility
  const [showScrollTop, setShowScrollTop] = useState(false);

  // Debounce search input - faster response
  useEffect(() => {
    const id = setTimeout(() => setQDebounced(q), 150);
    return () => clearTimeout(id);
  }, [q]);

  // Handle scroll for "back to top" button
  useEffect(() => {
    const handleScroll = () => {
      setShowScrollTop(window.scrollY > 400);
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
  if (sort !== "title_asc") params.set("sort", sort);
  if (page !== 1) params.set("page", page.toString());

  setSearchParams(params, { replace: true });
}, [q, category, designer, nzDesigner, players, recentlyAdded, sort, page, setSearchParams]);

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

  // Simplified fetch with better error handling
  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    (async () => {
      try {
        const params = { q: qDebounced, page, page_size: pageSize, sort };
        if (category !== "all") {
          params.category = category;
        }
        if (designer) {
          params.designer = designer;
        }
        if (nzDesigner) {
           params.nz_designer = true;
        }
        if (players) {
          params.players = parseInt(players);
        }
        if (recentlyAdded) {
          params.recently_added = 30;
        }

        const data = await getPublicGames(params);
        if (cancelled) return;

        setItems(data.items || []);
        setTotal(data.total || 0);
        setError(null);
      } catch (e) {
        if (!cancelled) {
          setError("Failed to load games. Please try again.");
          setItems([]);
          setTotal(0);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [qDebounced, page, pageSize, category, designer, nzDesigner, players, recentlyAdded, sort]);

  // Helper functions
  const updateCategory = (newCategory) => {
    setCategory(newCategory);
    setPage(1);
  };

  const updateSort = (newSort) => {
    setSort(newSort);
    setPage(1);
    setQuickSort(null);
  };

  const updateSearch = (newSearch) => {
    setQ(newSearch);
    setPage(1);
  };

  const clearAllFilters = () => {
    setQ("");
    setCategory("all");
    setDesigner("");
    setNzDesigner(false);
    setPlayers("");
    setRecentlyAdded(false);
    setSort("title_asc");
    setPage(1);
    setQuickSort(null);
  };

  // Quick sort actions
  const showNewestGames = () => {
    setSort("year_desc");
    setQuickSort("newest");
    setPage(1);
  };

  const showShortestGames = () => {
    setSort("time_asc");
    setQuickSort("shortest");
    setPage(1);
  };

  const toggleNzDesigner = () => {
    setNzDesigner(!nzDesigner);
    setPage(1);
  };

  const toggleRecentlyAdded = () => {
    setRecentlyAdded(!recentlyAdded);
    setPage(1);
  };

  const updatePlayers = (newPlayers) => {
    setPlayers(newPlayers);
    setPage(1);
  };

  // Share game function
  const shareGame = (game) => {
    const url = `${window.location.origin}/game/${game.id}`;
    const text = `Check out ${game.title} - ${game.min_players || '?'}-${game.max_players || '?'} players, ${game.playing_time || '?'} min`;

    if (navigator.share) {
      navigator.share({
        title: game.title,
        text: text,
        url: url
      });
    } else {
      navigator.clipboard.writeText(`${text} ${url}`);
      // Could show a toast notification here
    }
  };

  // Scroll to top function
  const scrollToTop = () => {
    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    });
  };

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

  // Skeleton loader component - smaller to prevent layout shift
  const SkeletonCard = () => (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="aspect-square bg-slate-200 animate-pulse"></div>
      <div className="p-3 space-y-2">
        <div className="h-4 bg-slate-200 rounded animate-pulse"></div>
        <div className="h-3 bg-slate-200 rounded w-3/4 animate-pulse"></div>
      </div>
    </div>
  );

  return (
    <>
      {/* Skip to main content link */}
      <a 
        href="#main-content" 
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-blue-600 focus:text-white focus:rounded focus:font-medium"
      >
        Skip to main content
      </a>

      <div className="min-h-screen bg-gradient-to-br from-amber-50 via-emerald-50 to-teal-50">
        <div className="mx-auto max-w-7xl px-4 py-4 sm:py-8">
          {/* Header */}
          <header className="mb-6 sm:mb-8 text-center">
            <h1 className="text-3xl sm:text-5xl font-bold bg-gradient-to-r from-emerald-700 via-teal-600 to-amber-600 bg-clip-text text-transparent mb-2 sm:mb-3">
              Mana & Meeples
            </h1>
            <p className="text-base sm:text-xl text-slate-600 mb-2">
              Timaru's Board Game Community
            </p>
            <p className="text-sm text-slate-500 mb-4">
              Explore our game collection - Find out about our events at{" "}
              <a href="https://manaandmeeples.co.nz" className="text-emerald-600 hover:underline focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 rounded">
                manaandmeeples.co.nz
              </a>
            </p>
            <div className="w-16 sm:w-24 h-1 bg-gradient-to-r from-emerald-500 to-amber-500 mx-auto rounded-full" aria-hidden="true"></div>
          </header>

          <main id="main-content">
            {/* Compact Search and Filter Controls */}
            <section
              className="bg-white/90 backdrop-blur-sm rounded-2xl p-4 lg:p-5 shadow-lg border border-slate-200/50 mb-6"
              aria-labelledby="search-filters-heading"
            >
              {/* Screen reader heading */}
              <h2 id="search-filters-heading" className="sr-only">
                Search and Filter Games
              </h2>

              {/* Desktop Layout - Two Rows */}
              <div className="hidden lg:block">
                {/* Row 1: Search + Players */}
                <div className="flex gap-3 items-end mb-3">
                  {/* Search - Takes most space */}
                  <div className="flex-1 min-w-0">
                    <label htmlFor="game-search-desktop" className="block text-sm font-semibold text-slate-700 mb-1.5">
                      Search Games
                    </label>
                    <div className="relative">
                      <SearchBox
                        id="game-search-desktop"
                        value={q}
                        onChange={updateSearch}
                        placeholder="Search by title..."
                        aria-describedby="search-help-desktop"
                        className="w-full min-h-[48px] px-4 py-3 pr-10 text-base border-2 border-slate-300 rounded-xl focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200 focus:outline-none transition-all bg-white"
                      />
                      <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
                        <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                      </div>
                    </div>
                  </div>

                  {/* Players Dropdown */}
                  <div className="w-40">
                    <label htmlFor="player-count-desktop" className="block text-sm font-semibold text-slate-700 mb-1.5">
                      Players
                    </label>
                    <select
                      id="player-count-desktop"
                      value={players}
                      onChange={(e) => updatePlayers(e.target.value)}
                      className="w-full min-h-[48px] px-3 py-3 text-sm border-2 border-slate-300 rounded-xl focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200 focus:outline-none transition-all bg-white"
                      aria-label="Filter by player count"
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
                </div>

                {/* Row 2: Quick Action Buttons + Sort + Clear */}
                <div className="flex gap-3 items-center">
                  {/* Quick Action Buttons */}
                  <div className="flex gap-2">
                    <button
                      onClick={showNewestGames}
                      className={`
                        min-h-[48px] px-3 py-2 text-sm font-medium rounded-xl
                        transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2
                        ${quickSort === "newest"
                          ? "bg-emerald-600 text-white shadow-md focus:ring-emerald-300"
                          : "bg-emerald-50 text-emerald-800 hover:bg-emerald-100 border-2 border-emerald-200 focus:ring-emerald-300"
                        }
                      `}
                      aria-pressed={quickSort === "newest"}
                      aria-label="Show newest games first"
                      title="Show newest games"
                    >
                      <span className="flex items-center gap-1.5">
                        <span aria-hidden="true">🆕</span>
                        <span>New</span>
                      </span>
                    </button>

                    <button
                      onClick={showShortestGames}
                      className={`
                        min-h-[48px] px-3 py-2 text-sm font-medium rounded-xl
                        transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2
                        ${quickSort === "shortest"
                          ? "bg-amber-600 text-white shadow-md focus:ring-amber-300"
                          : "bg-amber-50 text-amber-800 hover:bg-amber-100 border-2 border-amber-200 focus:ring-amber-300"
                        }
                      `}
                      aria-pressed={quickSort === "shortest"}
                      aria-label="Show shortest games first"
                      title="Show quick games"
                    >
                      <span className="flex items-center gap-1.5">
                        <span aria-hidden="true">⚡</span>
                        <span>Quick</span>
                      </span>
                    </button>

                    <button
                      onClick={toggleNzDesigner}
                      className={`
                        min-h-[48px] px-3 py-2 text-sm font-medium rounded-xl
                        transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2
                        ${nzDesigner
                          ? "bg-blue-600 text-white shadow-md focus:ring-blue-300"
                          : "bg-blue-50 text-blue-800 hover:bg-blue-100 border-2 border-blue-200 focus:ring-blue-300"
                        }
                      `}
                      aria-pressed={nzDesigner}
                      aria-label="Filter by New Zealand designers"
                      title="NZ designed games"
                    >
                      <span className="flex items-center gap-1.5">
                        <span aria-hidden="true">🇳🇿</span>
                        <span>Kiwi</span>
                      </span>
                    </button>

                    <button
                      onClick={toggleRecentlyAdded}
                      className={`
                        min-h-[48px] px-3 py-2 text-sm font-medium rounded-xl
                        transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2
                        ${recentlyAdded
                          ? "bg-purple-600 text-white shadow-md focus:ring-purple-300"
                          : "bg-purple-50 text-purple-800 hover:bg-purple-100 border-2 border-purple-200 focus:ring-purple-300"
                        }
                      `}
                      aria-pressed={recentlyAdded}
                      aria-label="Show games added in the last 30 days"
                      title="Recently added games"
                    >
                      <span className="flex items-center gap-1.5">
                        <span aria-hidden="true">✨</span>
                        <span>Recent</span>
                      </span>
                    </button>
                  </div>

                  {/* Sort - Takes remaining space */}
                  <div className="flex-1">
                    <SortSelect
                      sort={sort}
                      onChange={updateSort}
                    />
                  </div>

                  {/* Clear Filters */}
                  {activeFiltersCount > 0 && (
                    <button
                      onClick={clearAllFilters}
                      className="
                        min-h-[48px] px-4 py-2 text-sm font-medium rounded-xl
                        bg-slate-100 text-slate-800 hover:bg-slate-200
                        border-2 border-slate-300 hover:border-slate-400
                        transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-slate-300 focus:ring-offset-2
                      "
                      aria-label={`Clear all ${activeFiltersCount} active filters`}
                      title={`Clear ${activeFiltersCount} filters`}
                    >
                      <span className="flex items-center gap-2">
                        <span aria-hidden="true">🗑️</span>
                        <span className="bg-slate-200 text-slate-700 px-2 py-0.5 rounded-full text-xs font-bold">
                          {activeFiltersCount}
                        </span>
                      </span>
                    </button>
                  )}
                </div>

                {/* Search results count - below search bar */}
                {q && (
                  <div id="search-help-desktop" className="mt-2 text-sm text-slate-600">
                    <span className="font-medium">
                      {total} game{total !== 1 ? 's' : ''} found
                    </span>
                  </div>
                )}
              </div>

              {/* Tablet Layout - 2 Rows */}
              <div className="hidden md:block lg:hidden">
                {/* Row 1: Search + Players */}
                <div className="flex gap-3 items-end mb-3">
                  <div className="flex-1">
                    <label htmlFor="game-search-tablet" className="block text-sm font-semibold text-slate-700 mb-1.5">
                      Search Games
                    </label>
                    <div className="relative">
                      <SearchBox
                        id="game-search-tablet"
                        value={q}
                        onChange={updateSearch}
                        placeholder="Search by title..."
                        className="w-full min-h-[48px] px-4 py-3 pr-10 text-base border-2 border-slate-300 rounded-xl focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200 focus:outline-none transition-all bg-white"
                      />
                      <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
                        <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                      </div>
                    </div>
                  </div>

                  <div className="w-40">
                    <label htmlFor="player-count-tablet" className="block text-sm font-semibold text-slate-700 mb-1.5">
                      Players
                    </label>
                    <select
                      id="player-count-tablet"
                      value={players}
                      onChange={(e) => updatePlayers(e.target.value)}
                      className="w-full min-h-[48px] px-3 py-3 text-sm border-2 border-slate-300 rounded-xl focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200 focus:outline-none transition-all bg-white"
                      aria-label="Filter by player count"
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
                </div>

                {/* Row 2: Quick Actions + Sort + Clear */}
                <div className="flex gap-3 items-center">
                  <div className="flex gap-2">
                    <button
                      onClick={showNewestGames}
                      className={`
                        min-h-[48px] px-3 py-2 text-sm font-medium rounded-xl
                        transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2
                        ${quickSort === "newest"
                          ? "bg-emerald-600 text-white shadow-md focus:ring-emerald-300"
                          : "bg-emerald-50 text-emerald-800 hover:bg-emerald-100 border-2 border-emerald-200 focus:ring-emerald-300"
                        }
                      `}
                      aria-pressed={quickSort === "newest"}
                      aria-label="Show newest games first"
                    >
                      <span className="flex items-center gap-1.5">
                        <span aria-hidden="true">🆕</span>
                        <span>New</span>
                      </span>
                    </button>

                    <button
                      onClick={showShortestGames}
                      className={`
                        min-h-[48px] px-3 py-2 text-sm font-medium rounded-xl
                        transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2
                        ${quickSort === "shortest"
                          ? "bg-amber-600 text-white shadow-md focus:ring-amber-300"
                          : "bg-amber-50 text-amber-800 hover:bg-amber-100 border-2 border-amber-200 focus:ring-amber-300"
                        }
                      `}
                      aria-pressed={quickSort === "shortest"}
                      aria-label="Show shortest games first"
                    >
                      <span className="flex items-center gap-1.5">
                        <span aria-hidden="true">⚡</span>
                        <span>Quick</span>
                      </span>
                    </button>

                    <button
                      onClick={toggleNzDesigner}
                      className={`
                        min-h-[48px] px-3 py-2 text-sm font-medium rounded-xl
                        transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2
                        ${nzDesigner
                          ? "bg-blue-600 text-white shadow-md focus:ring-blue-300"
                          : "bg-blue-50 text-blue-800 hover:bg-blue-100 border-2 border-blue-200 focus:ring-blue-300"
                        }
                      `}
                      aria-pressed={nzDesigner}
                      aria-label="Filter by New Zealand designers"
                    >
                      <span className="flex items-center gap-1.5">
                        <span aria-hidden="true">🇳🇿</span>
                        <span>Kiwi</span>
                      </span>
                    </button>

                    <button
                      onClick={toggleRecentlyAdded}
                      className={`
                        min-h-[48px] px-3 py-2 text-sm font-medium rounded-xl
                        transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2
                        ${recentlyAdded
                          ? "bg-purple-600 text-white shadow-md focus:ring-purple-300"
                          : "bg-purple-50 text-purple-800 hover:bg-purple-100 border-2 border-purple-200 focus:ring-purple-300"
                        }
                      `}
                      aria-pressed={recentlyAdded}
                      aria-label="Show games added in the last 30 days"
                    >
                      <span className="flex items-center gap-1.5">
                        <span aria-hidden="true">✨</span>
                        <span>Recent</span>
                      </span>
                    </button>
                  </div>

                  <div className="flex-1">
                    <SortSelect
                      sort={sort}
                      onChange={updateSort}
                    />
                  </div>

                  {activeFiltersCount > 0 && (
                    <button
                      onClick={clearAllFilters}
                      className="
                        min-h-[48px] px-4 py-2 text-sm font-medium rounded-xl
                        bg-slate-100 text-slate-800 hover:bg-slate-200
                        border-2 border-slate-300 hover:border-slate-400
                        transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-slate-300 focus:ring-offset-2
                      "
                      aria-label={`Clear all ${activeFiltersCount} active filters`}
                    >
                      <span className="flex items-center gap-2">
                        <span aria-hidden="true">🗑️</span>
                        <span className="bg-slate-200 text-slate-700 px-2 py-0.5 rounded-full text-xs font-bold">
                          {activeFiltersCount}
                        </span>
                      </span>
                    </button>
                  )}
                </div>

                {q && (
                  <div className="mt-2 text-sm text-slate-600">
                    <span className="font-medium">
                      {total} game{total !== 1 ? 's' : ''} found
                    </span>
                  </div>
                )}
              </div>

              {/* Mobile Layout - Compact */}
              <div className="md:hidden space-y-3">
                {/* Search */}
                <div>
                  <label htmlFor="game-search-mobile" className="block text-sm font-semibold text-slate-700 mb-1.5">
                    Search Games
                  </label>
                  <div className="relative">
                    <SearchBox
                      id="game-search-mobile"
                      value={q}
                      onChange={updateSearch}
                      placeholder="Search by title..."
                      aria-describedby="search-help-mobile"
                      className="w-full min-h-[48px] px-3 py-2.5 pr-10 text-sm border-2 border-slate-300 rounded-xl focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200 focus:outline-none transition-all bg-white"
                    />
                    <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
                      <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                    </div>
                  </div>
                  {q && (
                    <div id="search-help-mobile" className="mt-1.5 text-xs text-slate-600 text-center">
                      <span className="font-medium">
                        {total} game{total !== 1 ? 's' : ''} found
                      </span>
                    </div>
                  )}
                </div>

                {/* Players & Sort - Two column layout */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label htmlFor="player-count-mobile" className="block text-sm font-semibold text-slate-700 mb-1.5">
                      Players
                    </label>
                    <select
                      id="player-count-mobile"
                      value={players}
                      onChange={(e) => updatePlayers(e.target.value)}
                      className="w-full min-h-[48px] px-2.5 py-2.5 text-sm border-2 border-slate-300 rounded-xl focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200 focus:outline-none transition-all bg-white"
                      aria-label="Filter by player count"
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

                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                      Sort
                    </label>
                    <SortSelect
                      sort={sort}
                      onChange={updateSort}
                    />
                  </div>
                </div>

                {/* Quick Action Buttons - 2x2 grid */}
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={showNewestGames}
                    className={`
                      min-h-[48px] px-2 py-2 text-xs font-medium rounded-xl
                      transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2
                      ${quickSort === "newest"
                        ? "bg-emerald-600 text-white shadow-md focus:ring-emerald-300"
                        : "bg-emerald-50 text-emerald-800 hover:bg-emerald-100 border-2 border-emerald-200 focus:ring-emerald-300"
                      }
                    `}
                    aria-pressed={quickSort === "newest"}
                    aria-label="Show newest games first"
                  >
                    <span className="flex flex-col items-center gap-1">
                      <span aria-hidden="true" className="text-base">🆕</span>
                      <span>New</span>
                    </span>
                  </button>

                  <button
                    onClick={showShortestGames}
                    className={`
                      min-h-[48px] px-2 py-2 text-xs font-medium rounded-xl
                      transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2
                      ${quickSort === "shortest"
                        ? "bg-amber-600 text-white shadow-md focus:ring-amber-300"
                        : "bg-amber-50 text-amber-800 hover:bg-amber-100 border-2 border-amber-200 focus:ring-amber-300"
                      }
                    `}
                    aria-pressed={quickSort === "shortest"}
                    aria-label="Show shortest games first"
                  >
                    <span className="flex flex-col items-center gap-1">
                      <span aria-hidden="true" className="text-base">⚡</span>
                      <span>Quick</span>
                    </span>
                  </button>

                  <button
                    onClick={toggleNzDesigner}
                    className={`
                      min-h-[48px] px-2 py-2 text-xs font-medium rounded-xl
                      transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2
                      ${nzDesigner
                        ? "bg-blue-600 text-white shadow-md focus:ring-blue-300"
                        : "bg-blue-50 text-blue-800 hover:bg-blue-100 border-2 border-blue-200 focus:ring-blue-300"
                      }
                    `}
                    aria-pressed={nzDesigner}
                    aria-label="Filter by New Zealand designers"
                  >
                    <span className="flex flex-col items-center gap-1">
                      <span aria-hidden="true" className="text-base">🇳🇿</span>
                      <span>Kiwi</span>
                    </span>
                  </button>

                  <button
                    onClick={toggleRecentlyAdded}
                    className={`
                      min-h-[48px] px-2 py-2 text-xs font-medium rounded-xl
                      transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2
                      ${recentlyAdded
                        ? "bg-purple-600 text-white shadow-md focus:ring-purple-300"
                        : "bg-purple-50 text-purple-800 hover:bg-purple-100 border-2 border-purple-200 focus:ring-purple-300"
                      }
                    `}
                    aria-pressed={recentlyAdded}
                    aria-label="Show games added in the last 30 days"
                  >
                    <span className="flex flex-col items-center gap-1">
                      <span aria-hidden="true" className="text-base">✨</span>
                      <span>Recent</span>
                    </span>
                  </button>
                </div>

                {/* Clear Filters - Mobile */}
                {activeFiltersCount > 0 && (
                  <button
                    onClick={clearAllFilters}
                    className="
                      w-full min-h-[48px] px-4 py-2.5 text-sm font-medium rounded-xl
                      bg-slate-100 text-slate-800 hover:bg-slate-200
                      border-2 border-slate-300 hover:border-slate-400
                      transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-slate-300 focus:ring-offset-2
                    "
                    aria-label={`Clear all ${activeFiltersCount} active filters`}
                  >
                    <span className="flex items-center justify-center gap-2">
                      <span aria-hidden="true">🗑️</span>
                      <span>Clear Filters</span>
                      <span className="bg-slate-200 text-slate-700 px-2 py-0.5 rounded-full text-xs font-bold">
                        {activeFiltersCount}
                      </span>
                    </span>
                  </button>
                )}
              </div>
              
              {/* Active Search Status - Shared for both layouts */}
              {(q || category !== "all" || designer || nzDesigner || players) && (
                <div
                  className="bg-blue-50 border-2 border-blue-200 rounded-xl p-3 mt-4"
                  role="status"
                  aria-live="polite"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold text-blue-800 flex items-center gap-2">
                      <span aria-hidden="true">🔍</span>
                      <span>Active:</span>
                    </span>

                    {q && (
                      <span className="inline-flex items-center gap-1 bg-blue-100 text-blue-900 px-3 py-1.5 rounded-lg text-sm font-medium border border-blue-200">
                        <span>"{q}"</span>
                        <button
                          onClick={() => updateSearch("")}
                          className="ml-1 p-1 hover:bg-blue-200 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400"
                          aria-label={`Remove search: ${q}`}
                        >
                          <span aria-hidden="true" className="text-sm leading-none">×</span>
                        </button>
                      </span>
                    )}

                    {category !== "all" && (
                      <span className="inline-flex items-center gap-1 bg-blue-100 text-blue-900 px-3 py-1.5 rounded-lg text-sm font-medium border border-blue-200">
                        <span>{CATEGORY_LABELS[category]}</span>
                        <button
                          onClick={() => updateCategory("all")}
                          className="ml-1 p-1 hover:bg-blue-200 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400"
                          aria-label={`Remove category: ${CATEGORY_LABELS[category]}`}
                        >
                          <span aria-hidden="true" className="text-sm leading-none">×</span>
                        </button>
                      </span>
                    )}

                    {designer && (
                      <span className="inline-flex items-center gap-1 bg-blue-100 text-blue-900 px-3 py-1.5 rounded-lg text-sm font-medium border border-blue-200">
                        <span>{designer}</span>
                        <button
                          onClick={() => setDesigner("")}
                          className="ml-1 p-1 hover:bg-blue-200 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400"
                          aria-label={`Remove designer: ${designer}`}
                        >
                          <span aria-hidden="true" className="text-sm leading-none">×</span>
                        </button>
                      </span>
                    )}

                    {nzDesigner && (
                      <span className="inline-flex items-center gap-1 bg-blue-100 text-blue-900 px-3 py-1.5 rounded-lg text-sm font-medium border border-blue-200">
                        <span>NZ Designed</span>
                        <button
                          onClick={() => setNzDesigner(false)}
                          className="ml-1 p-1 hover:bg-blue-200 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400"
                          aria-label="Remove NZ designer filter"
                        >
                          <span aria-hidden="true" className="text-sm leading-none">×</span>
                        </button>
                      </span>
                    )}

                    {players && (
                      <span className="inline-flex items-center gap-1 bg-blue-100 text-blue-900 px-3 py-1.5 rounded-lg text-sm font-medium border border-blue-200">
                        <span>{players} player{players === "1" ? "" : "s"}</span>
                        <button
                          onClick={() => updatePlayers("")}
                          className="ml-1 p-1 hover:bg-blue-200 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400"
                          aria-label="Remove player count filter"
                        >
                          <span aria-hidden="true" className="text-sm leading-none">×</span>
                        </button>
                      </span>
                    )}
                  </div>
                </div>
              )}
            </section>

            {/* Categories - Mobile Optimized */}
            <section className="mb-4" aria-labelledby="categories-heading">
              <h2 id="categories-heading" className="text-lg font-semibold text-slate-700 mb-3 px-2">Categories</h2>
              <div className="relative">
                <div className="flex gap-3 overflow-x-auto pb-4 px-2 -mx-2 snap-x scrollbar-hide">
                  <button
                    onClick={() => updateCategory("all")}
                    className={`flex-shrink-0 snap-start rounded-full px-4 py-2 text-sm font-medium whitespace-nowrap transition-all min-h-[44px] focus:outline-none focus:ring-3 focus:ring-offset-2 ${
                      category === "all"
                        ? "bg-emerald-500 text-white shadow-md focus:ring-emerald-300"
                        : "bg-white/90 text-slate-700 border border-slate-200 hover:border-emerald-300 focus:ring-emerald-300"
                    }`}
                    aria-pressed={category === "all"}
                  >
                    All ({counts?.all ?? 0})
                  </button>

                  {CATEGORY_KEYS.map((k) => (
                    <button
                      key={k}
                      onClick={() => updateCategory(k)}
                      className={`flex-shrink-0 snap-start rounded-full px-4 py-2 text-sm font-medium whitespace-nowrap transition-all min-h-[44px] focus:outline-none focus:ring-3 focus:ring-offset-2 ${
                        category === k
                          ? "bg-amber-500 text-white shadow-md focus:ring-amber-300"
                          : "bg-white/90 text-slate-700 border border-slate-200 hover:border-amber-300 focus:ring-amber-300"
                      }`}
                      aria-pressed={category === k}
                    >
                      {CATEGORY_LABELS[k]} ({counts?.[k] ?? 0})
                    </button>
                  ))}
                </div>
                
                {/* Clearer scroll indicators */}
                <div className="absolute right-0 top-0 bottom-4 w-8 bg-gradient-to-l from-amber-50 to-transparent pointer-events-none flex items-center justify-center">
                  <div className="w-1 h-8 bg-slate-300 rounded-full opacity-50"></div>
                </div>
              </div>
            </section>

            {/* Game Results */}
            <section aria-live="polite" id="game-results">
              {loading ? (
                <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4 mb-6">
                  {Array.from({ length: 8 }, (_, i) => (
                    <SkeletonCard key={i} />
                  ))}
                </div>
              ) : error ? (
                <div className="text-center py-12">
                  <div className="bg-red-50 border border-red-200 rounded-xl p-6 max-w-md mx-auto">
                    <h3 className="text-red-700 font-medium text-lg mb-3">Something went wrong</h3>
                    <p className="text-red-600 mb-4">{error}</p>
                    <button 
                      onClick={() => window.location.reload()} 
                      className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 focus:outline-none focus:ring-3 focus:ring-red-300 focus:ring-offset-2 transition-colors"
                    >
                      Retry
                    </button>
                  </div>
                </div>
              ) : items.length === 0 ? (
                <div className="text-center py-16">
                  <div className="bg-amber-50 border border-amber-200 rounded-xl p-8 max-w-md mx-auto">
                    <h3 className="text-amber-700 font-medium text-lg mb-3">No games found</h3>
                    <p className="text-amber-600 mb-4">Try adjusting your search or browse our categories</p>
                    <button
                      onClick={clearAllFilters}
                      className="px-4 py-2 bg-amber-500 text-white rounded-lg hover:bg-amber-600 focus:outline-none focus:ring-3 focus:ring-amber-300 focus:ring-offset-2 transition-colors"
                    >
                      Show All Games
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  {/* Top Pagination */}
                  <Pagination
                    page={page}
                    pageSize={pageSize}
                    total={total}
                    onPage={setPage}
                    showResultsCount={true}
                  />

                  {/* Game Cards Grid with lazy loading */}
                  <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4 my-6">
                    {items.map((game) => (
                      <div key={game.id} className="transform transition-all duration-300 hover:scale-105 hover:z-50 relative">
                        <GameCardPublic
                          game={game}
                          onShare={() => shareGame(game)}
                          lazy={true}
                        />
                      </div>
                    ))}
                  </div>

                  {/* Bottom Pagination */}
                  <Pagination
                    page={page}
                    pageSize={pageSize}
                    total={total}
                    onPage={setPage}
                    showResultsCount={false}
                  />
                </>
              )}
            </section>
          </main>
        </div>
      </div>

      {/* Floating Back to Top Button */}
      {showScrollTop && (
        <button
          onClick={scrollToTop}
          className="fixed bottom-6 right-6 z-50 p-4 bg-gradient-to-r from-emerald-500 to-teal-500 text-white rounded-full shadow-2xl hover:shadow-emerald-500/50 hover:scale-110 transition-all duration-300 focus:outline-none focus:ring-4 focus:ring-emerald-300 focus:ring-offset-2 group"
          aria-label="Scroll back to top"
          title="Back to top"
        >
          <svg
            className="w-6 h-6 transition-transform group-hover:-translate-y-1"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 10l7-7m0 0l7 7m-7-7v18" />
          </svg>
        </button>
      )}

      <style jsx>{`
        .scrollbar-hide {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
        .scrollbar-hide::-webkit-scrollbar {
          display: none;
        }
      `}</style>
    </>
  );
}