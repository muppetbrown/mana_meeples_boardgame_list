// src/pages/PublicCatalogue.jsx - Enhanced Mobile-First Version with Accessibility
// Phase 2 Performance: Refactored to use React Query for API caching and infinite scroll
import React, { useEffect, useState, useMemo, useRef, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { getPublicGames, getPublicCategoryCounts } from "../api/client";
import { CATEGORY_KEYS, CATEGORY_LABELS } from "../constants/categories";
import GameCardPublic from "../components/public/GameCardPublic";
import GameCardSkeleton from "../components/public/GameCardSkeleton";
import SortSelect from "../components/public/SortSelect";
import SearchBox from "../components/public/SearchBox";
import SkipNav from "../components/common/SkipNav";
import LiveRegion from "../components/common/LiveRegion";
import { HelpModal } from "../components/onboarding/HelpModal";
import { HelpButton } from "../components/onboarding/HelpButton";
import { useOnboarding } from "../hooks/useOnboarding";

export default function PublicCatalogue() {
  // Use URL parameters to preserve state
  const [searchParams, setSearchParams] = useSearchParams();

  // Get initial values from URL or defaults
  const [q, setQ] = useState(searchParams.get("q") || "");
  const [category, setCategory] = useState(searchParams.get("category") || "all");
  const [designer, setDesigner] = useState(searchParams.get("designer") || "");
  const [nzDesigner, setNzDesigner] = useState(searchParams.get("nz_designer") === "true");
  const [players, setPlayers] = useState(searchParams.get("players") || "");
  const [complexityRange, setComplexityRange] = useState(searchParams.get("complexity") || "");
  const [recentlyAdded, setRecentlyAdded] = useState(searchParams.get("recently_added") === "30");
  const [sort, setSort] = useState(searchParams.get("sort") || "year_desc");
  const pageSize = 12; // Items per page

  // UI state
  const [showScrollTop, setShowScrollTop] = useState(false);
  const [isHeaderVisible, setIsHeaderVisible] = useState(true);
  const [isFilterExpanded, setIsFilterExpanded] = useState(false);
  const [isSticky, setIsSticky] = useState(false);
  const [expandedCards, setExpandedCards] = useState(new Set());
  const [announcement, setAnnouncement] = useState("");

  // Onboarding state
  const [isHelpModalOpen, setIsHelpModalOpen] = useState(false);
  const { isFirstVisit, markHelpOpened } = useOnboarding();

  // Refs for scroll detection
  const lastScrollY = useRef(0);
  const lastToggleY = useRef(0);
  const headerRef = useRef(null);
  const toolbarRef = useRef(null);
  const ticking = useRef(false);
  const loadMoreTriggerRef = useRef(null);

  // Build query parameters
  const queryParams = useMemo(() => {
    const params = { q, page_size: pageSize, sort };
    if (category !== "all") params.category = category;
    if (designer) params.designer = designer;
    if (nzDesigner) params.nz_designer = true;
    if (players) params.players = parseInt(players);
    if (complexityRange) {
      const [min, max] = complexityRange.split('-').map(parseFloat);
      params.complexity_min = min;
      params.complexity_max = max;
    }
    if (recentlyAdded) params.recently_added = 30;
    return params;
  }, [q, category, designer, nzDesigner, players, complexityRange, recentlyAdded, sort, pageSize]);

  // Phase 2 Performance: React Query for infinite scroll games data
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isError,
    error,
    refetch,
  } = useInfiniteQuery({
    queryKey: ['games', queryParams],
    queryFn: async ({ pageParam = 1 }) => {
      const response = await getPublicGames({ ...queryParams, page: pageParam });
      return response;
    },
    getNextPageParam: (lastPage, allPages) => {
      const currentItems = allPages.reduce((sum, page) => sum + (page.items?.length || 0), 0);
      const totalPages = Math.ceil((lastPage.total || 0) / pageSize);
      const currentPage = allPages.length;
      return currentPage < totalPages ? currentPage + 1 : undefined;
    },
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false,
  });

  // Phase 2 Performance: React Query for category counts
  const { data: counts } = useQuery({
    queryKey: ['category-counts'],
    queryFn: getPublicCategoryCounts,
    staleTime: 60 * 1000, // 1 minute (counts change infrequently)
    gcTime: 10 * 60 * 1000, // 10 minutes
  });

  // Flatten all loaded items from pages
  const allLoadedItems = useMemo(() => {
    return data?.pages?.flatMap(page => page.items || []) || [];
  }, [data]);

  // Get total count
  const total = data?.pages?.[0]?.total || 0;

  // Scroll to top on initial page load/refresh
  useEffect(() => {
    window.scrollTo(0, 0);
    setIsHeaderVisible(true);
    setIsSticky(false);
  }, []);

  // Handle scroll for header hide/show and sticky toolbar
  useEffect(() => {
    const handleScroll = () => {
      // Skip scroll handling during loading
      if (isFetchingNextPage) {
        return;
      }

      if (!ticking.current) {
        window.requestAnimationFrame(() => {
          const currentScrollY = window.scrollY;
          const scrollDelta = currentScrollY - lastScrollY.current;
          const headerHeight = headerRef.current?.offsetHeight || 0;
          const SCROLL_THRESHOLD = 15;
          const TOGGLE_BUFFER = 50;

          // Show/hide scroll to top button with hysteresis
          if (currentScrollY > 450) {
            setShowScrollTop(true);
          } else if (currentScrollY < 350) {
            setShowScrollTop(false);
          }

          // Always show header when at the very top
          if (currentScrollY < 50) {
            setIsHeaderVisible(true);
            setIsSticky(false);
            lastToggleY.current = currentScrollY;
          }
          // Header hide/show on scroll direction
          else if (currentScrollY > headerHeight + 20) {
            const distanceFromLastToggle = Math.abs(currentScrollY - lastToggleY.current);

            if (distanceFromLastToggle > TOGGLE_BUFFER) {
              if (scrollDelta > SCROLL_THRESHOLD) {
                setIsHeaderVisible(false);
                setIsSticky(true);
                lastToggleY.current = currentScrollY;
              } else if (scrollDelta < -SCROLL_THRESHOLD) {
                setIsHeaderVisible(true);
                lastToggleY.current = currentScrollY;
              }
            }
          } else {
            setIsHeaderVisible(true);
            setIsSticky(false);
            lastToggleY.current = currentScrollY;
          }

          lastScrollY.current = currentScrollY;
          ticking.current = false;
        });

        ticking.current = true;
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [isFetchingNextPage]);

  // Update URL when filters change
  useEffect(() => {
    const updateURL = () => {
      const params = new URLSearchParams();
      if (q) params.set("q", q);
      if (category !== "all") params.set("category", category);
      if (designer) params.set("designer", designer);
      if (nzDesigner) params.set("nz_designer", "true");
      if (players) params.set("players", players);
      if (complexityRange) params.set("complexity", complexityRange);
      if (recentlyAdded) params.set("recently_added", "30");
      if (sort !== "year_desc") params.set("sort", sort);

      setSearchParams(params, { replace: true });
    };

    const timer = setTimeout(updateURL, 100);
    return () => clearTimeout(timer);
  }, [q, category, designer, nzDesigner, players, complexityRange, recentlyAdded, sort, setSearchParams]);

  // Infinite scroll: Intersection Observer
  useEffect(() => {
    const sentinel = loadMoreTriggerRef.current;
    if (!sentinel) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (entry.isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPage();
        }
      },
      {
        root: null,
        rootMargin: '100px',
        threshold: 0.1,
      }
    );

    observer.observe(sentinel);

    return () => {
      observer.disconnect();
    };
  }, [fetchNextPage, hasNextPage, isFetchingNextPage]);

  // Helper functions with accessibility announcements (wrapped in useCallback)
  const updateCategory = useCallback((newCategory) => {
    setCategory(newCategory);
    setExpandedCards(new Set());

    const categoryName = newCategory === "all"
      ? "All Games"
      : newCategory === "uncategorized"
      ? "Uncategorized"
      : CATEGORY_LABELS[newCategory];
    setAnnouncement(`Filtering by ${categoryName}`);
  }, []);

  const updateSort = useCallback((newSort) => {
    setSort(newSort);
    const sortLabels = {
      "title_asc": "Title A to Z",
      "title_desc": "Title Z to A",
      "year_desc": "Newest first",
      "year_asc": "Oldest first",
      "rating_desc": "Highest rated first",
      "rating_asc": "Lowest rated first",
      "time_asc": "Shortest play time first",
      "time_desc": "Longest play time first"
    };
    setAnnouncement(`Sorting by ${sortLabels[newSort] || newSort}`);
  }, []);

  const updateSearch = useCallback((newSearch) => {
    setQ(newSearch);
    if (newSearch) {
      setAnnouncement(`Searching for ${newSearch}`);
    }
  }, []);

  const clearAllFilters = useCallback(() => {
    setQ("");
    setCategory("all");
    setDesigner("");
    setNzDesigner(false);
    setPlayers("");
    setComplexityRange("");
    setRecentlyAdded(false);
    setSort("year_desc");
    setExpandedCards(new Set());
    setAnnouncement("All filters cleared. Showing all games.");
  }, []);

  const toggleNzDesigner = useCallback(() => {
    setNzDesigner(prev => {
      const newValue = !prev;
      setAnnouncement(newValue ? "Filtering by New Zealand designers" : "New Zealand designer filter removed");
      return newValue;
    });
  }, []);

  const toggleRecentlyAdded = useCallback(() => {
    setRecentlyAdded(prev => {
      const newValue = !prev;
      setAnnouncement(newValue ? "Showing recently added games" : "Recently added filter removed");
      return newValue;
    });
  }, []);

  const updatePlayers = useCallback((newPlayers) => {
    setPlayers(newPlayers);
    if (newPlayers) {
      setAnnouncement(`Filtering by ${newPlayers} players`);
    }
  }, []);

  const updateComplexity = useCallback((newComplexity) => {
    setComplexityRange(newComplexity);
    if (newComplexity) {
      const labels = {
        "1-1.5": "Light",
        "1.5-2.5": "Light-Medium",
        "2.5-3.5": "Medium",
        "3.5-4.5": "Medium-Heavy",
        "4.5-5": "Heavy"
      };
      setAnnouncement(`Filtering by ${labels[newComplexity] || newComplexity} complexity`);
    }
  }, []);

  const toggleCardExpansion = useCallback((gameId) => {
    setExpandedCards(prev => {
      const next = new Set(prev);
      if (next.has(gameId)) {
        next.delete(gameId);
      } else {
        next.clear();
        next.add(gameId);
      }
      return next;
    });
  }, []);

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
    if (complexityRange) count++;
    if (recentlyAdded) count++;
    return count;
  }, [q, category, designer, nzDesigner, players, complexityRange, recentlyAdded]);

  // Reduce motion preference
  const prefersReducedMotion = useMemo(() => {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }, []);

  const transitionClass = prefersReducedMotion ? '' : 'transition-all duration-300';

  return (
    <div className="min-h-screen bg-linear-to-br from-slate-50 via-emerald-50 to-amber-50">
      <SkipNav />
      <LiveRegion message={announcement} />

      <main role="main" id="main-content" className="container mx-auto px-4 py-4 sm:py-8">
        {/* Screen-reader-only h1 - always present for accessibility */}
        <h1 className="sr-only">Mana & Meeples Board Game Library</h1>

        {/* Header */}
        <div className="mb-4">
          <header
            ref={headerRef}
            className={`${transitionClass} ${
              isHeaderVisible
                ? 'opacity-100 translate-y-0'
                : 'opacity-0 -translate-y-full pointer-events-none h-0 overflow-hidden'
            }`}
          >
          {/* Logo and Text */}
          <div className="flex items-center gap-3 sm:gap-4 mb-4">
            <a
              href="https://www.manaandmeeples.co.nz"
              target="_blank"
              rel="noopener noreferrer"
              className="shrink-0 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 rounded-lg transition-transform hover:scale-105"
              aria-label="Visit Mana & Meeples homepage"
            >
              <img
                src="/logo192.png"
                alt="Mana & Meeples logo"
                className="w-12 h-12 sm:w-16 sm:h-16"
              />
            </a>
            <div className="flex-1">
              <p className="text-2xl sm:text-4xl font-bold bg-linear-to-r from-emerald-700 via-teal-600 to-amber-600 bg-clip-text text-transparent mb-1" aria-hidden="true">
                Mana & Meeples
              </p>
              <p className="text-sm sm:text-lg text-slate-600 mb-0.5">
                Timaru's Board Game Community
              </p>
              <p className="text-xs sm:text-sm text-slate-500">
                Explore our game collection
              </p>
            </div>
            {/* Partner Logos - Desktop only */}
            <div className="hidden lg:flex flex-col items-end gap-2 shrink-0">
              <p className="text-xs text-slate-500 font-medium">With help from:</p>
              <div className="flex gap-3 items-center">
                <a
                  href="https://boardgamegeek.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 rounded transition-opacity hover:opacity-80"
                  aria-label="Visit BoardGameGeek"
                >
                  <img
                    src="/boardgamegeek_logo.webp"
                    alt="BoardGameGeek"
                    className="h-8 w-auto"
                  />
                </a>
                <a
                  href="https://aftergame.app"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 rounded transition-opacity hover:opacity-80"
                  aria-label="Visit Aftergame"
                >
                  <img
                    src="/Aftergame Logo V3-Light.png"
                    alt="Aftergame"
                    className="h-8 w-auto"
                  />
                </a>
              </div>
            </div>
          </div>
          <div className="w-12 sm:w-20 h-1 bg-linear-to-r from-emerald-500 to-amber-500 rounded-full mb-4" aria-hidden="true"></div>

          {/* Category Pills */}
          <section id="category-filters" aria-labelledby="categories-heading" className="mt-4">
            <h2 id="categories-heading" className="sr-only">
              Game Categories
            </h2>
            <div className="flex gap-2 overflow-x-auto pb-3 snap-x scrollbar-hide" role="group" aria-label="Filter games by category">
              <button
                onClick={() => updateCategory("all")}
                className={`shrink-0 snap-start rounded-full px-4 py-2 text-sm font-medium whitespace-nowrap ${transitionClass} min-h-11 focus:outline-none focus:ring-3 focus:ring-offset-2 ${
                  category === "all"
                    ? "bg-emerald-500 text-white shadow-md focus:ring-emerald-300"
                    : "bg-white/90 text-slate-700 border border-slate-200 hover:border-emerald-300 focus:ring-emerald-300"
                }`}
                aria-pressed={category === "all"}
                aria-label={`Show all games. ${counts?.all ?? 0} total games.`}
              >
                All ({counts?.all ?? "..."})
              </button>

              {CATEGORY_KEYS.map((key) => (
                <button
                  key={key}
                  onClick={() => updateCategory(key)}
                  className={`shrink-0 snap-start rounded-full px-4 py-2 text-sm font-medium whitespace-nowrap ${transitionClass} min-h-11 focus:outline-none focus:ring-3 focus:ring-offset-2 ${
                    category === key
                      ? "bg-emerald-500 text-white shadow-md focus:ring-emerald-300"
                      : "bg-white/90 text-slate-700 border border-slate-200 hover:border-emerald-300 focus:ring-emerald-300"
                  }`}
                  aria-pressed={category === key}
                  aria-label={`Filter by ${CATEGORY_LABELS[key]}. ${counts?.[key] ?? 0} games in this category.`}
                >
                  {CATEGORY_LABELS[key]} ({counts?.[key] ?? "..."})
                </button>
              ))}
            </div>
          </section>
        </header>
        </div>

          {/* Mobile Sticky Toolbar */}
          <div ref={toolbarRef} className="md:hidden sticky top-0 z-40 mb-4">
            <div className="bg-white/95 backdrop-blur-sm border-b border-slate-200 shadow-md">

              <div className="flex items-center gap-2 p-3">
                <SortSelect
                  sort={sort}
                  onChange={updateSort}
                  className="flex-1"
                />

                <button
                  onClick={() => setIsFilterExpanded(!isFilterExpanded)}
                  className="flex items-center gap-2 min-h-11 px-4 py-2 bg-linear-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 rounded-xl shadow-sm hover:shadow-md focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:ring-offset-2 transition-all"
                  aria-expanded={isFilterExpanded}
                  aria-label={`${isFilterExpanded ? 'Collapse' : 'Expand'} search and filters`}
                >
                  <span className="text-sm font-semibold text-white whitespace-nowrap">
                    Filters
                  </span>
                  {activeFiltersCount > 0 && (
                    <span className="bg-white text-emerald-700 text-xs font-bold px-1.5 py-0.5 rounded-full min-w-5 text-center">
                      {activeFiltersCount}
                    </span>
                  )}
                  <svg
                    className={`w-4 h-4 text-white ${transitionClass} ${isFilterExpanded ? 'rotate-180' : ''}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
              </div>

              {/* Expanded Filter Panel - Mobile */}
              {isFilterExpanded && (
                <div className="p-3 space-y-3 border-t border-slate-200 bg-slate-50">

                  {/* Search */}
                  <div>
                    <label htmlFor="search-box" className="block text-sm font-semibold text-slate-700 mb-1.5">
                      Search Games
                    </label>
                    <SearchBox
                      id="search-box"
                      value={q}
                      onChange={updateSearch}
                      placeholder="Search by title, designer, or description..."
                      className="w-full"
                      aria-describedby="search-help"
                    />
                    <p id="search-help" className="sr-only">
                      Search across game titles, designer names, and descriptions. Results update as you type.
                    </p>
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
                      className="w-full min-h-11 px-3 py-2 text-sm border-2 border-slate-300 rounded-xl focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200 focus:outline-none bg-white"
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

                  {/* Complexity */}
                  <div>
                    <label htmlFor="complexity-mobile" className="block text-sm font-semibold text-slate-700 mb-1.5">
                      Complexity
                    </label>
                    <select
                      id="complexity-mobile"
                      value={complexityRange}
                      onChange={(e) => updateComplexity(e.target.value)}
                      className="w-full min-h-11 px-3 py-2 text-sm border-2 border-slate-300 rounded-xl focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200 focus:outline-none bg-white"
                    >
                      <option value="">Any</option>
                      <option value="1-1.5">Light (1-1.5)</option>
                      <option value="1.5-2.5">Light-Medium (1.5-2.5)</option>
                      <option value="2.5-3.5">Medium (2.5-3.5)</option>
                      <option value="3.5-4.5">Medium-Heavy (3.5-4.5)</option>
                      <option value="4.5-5">Heavy (4.5-5)</option>
                    </select>
                  </div>

                  {/* Quick Filters */}
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={toggleNzDesigner}
                      className={`min-h-11 px-3 py-2 text-sm font-medium rounded-xl ${transitionClass} focus:outline-none focus:ring-2 focus:ring-offset-2 ${
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
                      className={`min-h-11 px-3 py-2 text-sm font-medium rounded-xl ${transitionClass} focus:outline-none focus:ring-2 focus:ring-offset-2 ${
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
                      className="w-full min-h-11 px-4 py-2 text-sm font-medium rounded-xl bg-slate-100 text-slate-800 hover:bg-slate-200 border-2 border-slate-300 focus:outline-none focus:ring-2 focus:ring-slate-300"
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

          {/* Desktop Filter Section */}
          <section
            className="hidden md:block bg-white/90 backdrop-blur-sm rounded-2xl p-5 shadow-lg border border-slate-200/50 mb-6"
            aria-labelledby="search-filters-heading"
          >
            <h2 id="search-filters-heading" className="sr-only">
              Search and Filter Games
            </h2>

            <div className="space-y-3">
              {/* Row 1: Search + Players + Complexity */}
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
                    className="w-full min-h-12 px-3 py-2 border-2 border-slate-300 rounded-xl focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200 focus:outline-none bg-white"
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

                <div className="w-48">
                  <label htmlFor="complexity-desktop" className="block text-sm font-semibold text-slate-700 mb-1.5">
                    Complexity
                  </label>
                  <select
                    id="complexity-desktop"
                    value={complexityRange}
                    onChange={(e) => updateComplexity(e.target.value)}
                    className="w-full min-h-12 px-3 py-2 border-2 border-slate-300 rounded-xl focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200 focus:outline-none bg-white"
                  >
                    <option value="">Any</option>
                    <option value="1-1.5">Light</option>
                    <option value="1.5-2.5">Light-Medium</option>
                    <option value="2.5-3.5">Medium</option>
                    <option value="3.5-4.5">Medium-Heavy</option>
                    <option value="4.5-5">Heavy</option>
                  </select>
                </div>
              </div>

              {/* Row 2: NZ Designer + Recent + Sort */}
              <div className="flex gap-3 items-end">
                <button
                  onClick={toggleNzDesigner}
                  className={`min-h-12 px-4 py-2.5 text-sm font-medium rounded-xl ${transitionClass} focus:outline-none focus:ring-3 focus:ring-offset-2 ${
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
                  className={`min-h-12 px-4 py-2.5 text-sm font-medium rounded-xl ${transitionClass} focus:outline-none focus:ring-3 focus:ring-offset-2 ${
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
                    className="min-h-12 px-4 py-2 text-sm font-medium rounded-xl bg-slate-100 text-slate-800 hover:bg-slate-200 border-2 border-slate-300 focus:outline-none focus:ring-2 focus:ring-slate-300"
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

          {/* Results Summary */}
          {q && (
            <div className="mb-4 text-center text-slate-600">
              <span className="text-sm font-medium">
                {total} game{total !== 1 ? 's' : ''} found for "{q}"
              </span>
            </div>
          )}

          {/* Games Grid */}
          {isError && (
            <div className="text-center py-12">
              <p className="text-red-600 mb-4">{error?.message || 'Failed to load games'}</p>
              <button
                onClick={() => refetch()}
                className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700"
              >
                Retry
              </button>
            </div>
          )}

          {/* Show skeletons ONLY on initial page load */}
          {isLoading && (
            <div className="game-grid grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4 items-start">
              {Array.from({ length: pageSize }).map((_, index) => (
                <GameCardSkeleton key={`skeleton-${index}`} />
              ))}
            </div>
          )}

          {/* No results message */}
          {!isLoading && !isError && allLoadedItems.length === 0 && (
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

          {/* Show games */}
          {!isLoading && !isError && allLoadedItems.length > 0 && (
            <>
              <div className="game-grid grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4 items-start">
                {allLoadedItems.map((game, index) => (
                  <GameCardPublic
                    key={game.id}
                    game={game}
                    isExpanded={expandedCards.has(game.id)}
                    onToggleExpand={() => toggleCardExpansion(game.id)}
                    prefersReducedMotion={prefersReducedMotion}
                    priority={index < 8}
                    lazy={index >= 8}
                  />
                ))}
              </div>

              {/* Infinite Scroll Trigger & Loading Indicator */}
              {hasNextPage && (
                <>
                  {/* Show skeleton loaders while loading more */}
                  {isFetchingNextPage && (
                    <div className="game-grid grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4 items-start mt-6">
                      {Array.from({ length: Math.min(pageSize, total - allLoadedItems.length) }).map((_, index) => (
                        <GameCardSkeleton key={`loading-skeleton-${index}`} />
                      ))}
                    </div>
                  )}

                  <div
                    ref={loadMoreTriggerRef}
                    className="mt-8 py-8 text-center"
                  >
                    {!isFetchingNextPage && (
                      <p className="text-xs text-slate-400">
                        Scroll for more • {allLoadedItems.length} of {total}
                      </p>
                    )}
                  </div>
                </>
              )}

              {/* End of results message */}
              {!hasNextPage && total > pageSize && (
                <div className="mt-8 py-4 text-center">
                  <div className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-50 text-emerald-700 rounded-full">
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    <span className="text-sm font-medium">
                      All {total} games loaded
                    </span>
                  </div>
                </div>
              )}
            </>
          )}

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

        {/* Help Button */}
        <HelpButton
          onClick={() => {
            setIsHelpModalOpen(true);
            markHelpOpened();
          }}
          showPulse={isFirstVisit}
        />

        {/* Help Modal */}
        <HelpModal
          isOpen={isHelpModalOpen}
          onClose={() => setIsHelpModalOpen(false)}
        />
      </main>
    </div>
  );
}
