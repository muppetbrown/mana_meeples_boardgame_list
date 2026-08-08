// src/pages/PublicCatalogue.jsx
// Mobile-first library redesign: quick-picks, shelf picker, sticky "Narrow it
// down" bar + bottom sheet, and a simplified vertical game card list.
import React, { useEffect, useState, useMemo, useRef, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { useInfiniteQuery, useQuery, keepPreviousData } from "@tanstack/react-query";
import { getPublicGames, getPublicCategoryCounts } from "../api/client";
import { CATEGORY_LABELS } from "../constants/categories";
import GameCardPublic from "../components/public/GameCardPublic";
import GameCardSkeleton from "../components/public/GameCardSkeleton";
import ShelfPicker from "../components/public/ShelfPicker";
import FilterSheet from "../components/public/FilterSheet";
import SkipNav from "../components/common/SkipNav";
import LiveRegion from "../components/common/LiveRegion";
import {
  QUICK_PICKS,
  playersToParam,
  timeToPlaytimeParams,
  weightToComplexityParams,
  timeLabel,
} from "../utils/libraryFilters";

const PAGE_SIZE = 12;

export default function PublicCatalogue() {
  const [searchParams, setSearchParams] = useSearchParams();

  const [quickPick, setQuickPick] = useState(searchParams.get("quickPick") || "");
  const [cats, setCats] = useState(() => {
    const raw = searchParams.get("cats");
    return raw ? raw.split(",").filter(Boolean) : [];
  });
  const [players, setPlayers] = useState(searchParams.get("players") || "");
  const [time, setTime] = useState(searchParams.get("time") || "");
  const [weight, setWeight] = useState(searchParams.get("weight") || "");

  const [sheetOpen, setSheetOpen] = useState(false);
  const [expandedId, setExpandedId] = useState(null);
  const [announcement, setAnnouncement] = useState("");

  const loadMoreTriggerRef = useRef(null);
  const isFilterChangeRef = useRef(false);
  const prevFilterKeyRef = useRef(null);

  // Build API query params from current filter state
  const queryParams = useMemo(() => {
    const params = { page_size: PAGE_SIZE, sort: "title_asc" };
    if (cats.length > 0) params.category = cats.join(",");
    if (quickPick) params.quick_pick = quickPick;
    const p = playersToParam(players);
    if (p) params.players = p;
    Object.assign(params, timeToPlaytimeParams(time));
    Object.assign(params, weightToComplexityParams(weight));
    return params;
  }, [cats, quickPick, players, time, weight]);

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
    queryKey: ["games", queryParams],
    queryFn: async ({ pageParam = 1 }) => getPublicGames({ ...queryParams, page: pageParam }),
    getNextPageParam: (lastPage, allPages) => {
      const totalLoaded = allPages.reduce((sum, page) => sum + (page.items?.length || 0), 0);
      return totalLoaded < (lastPage.total || 0) ? allPages.length + 1 : undefined;
    },
    placeholderData: keepPreviousData,
    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  });

  const { data: counts } = useQuery({
    queryKey: ["category-counts"],
    queryFn: getPublicCategoryCounts,
    staleTime: 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });

  const items = useMemo(() => data?.pages?.flatMap((page) => page.items || []) || [], [data]);
  const total = data?.pages?.[0]?.total ?? 0;
  const totalGames = counts?.all;

  // Scroll to top on initial page load
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  const scrollToTopOnFilterChange = useCallback(() => {
    const shouldAnimate = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.scrollTo({ top: 0, behavior: shouldAnimate ? "smooth" : "instant" });
    setExpandedId(null);
  }, []);

  // Scroll to top when filters change (not on initial mount)
  useEffect(() => {
    const filterKey = JSON.stringify(queryParams);
    if (prevFilterKeyRef.current === null) {
      prevFilterKeyRef.current = filterKey;
      return;
    }
    if (filterKey !== prevFilterKeyRef.current) {
      isFilterChangeRef.current = true;
      scrollToTopOnFilterChange();
    }
    prevFilterKeyRef.current = filterKey;
  }, [queryParams, scrollToTopOnFilterChange]);

  // Keep filter state in the URL
  useEffect(() => {
    const params = new URLSearchParams();
    if (quickPick) params.set("quickPick", quickPick);
    if (cats.length > 0) params.set("cats", cats.join(","));
    if (players) params.set("players", players);
    if (time) params.set("time", time);
    if (weight) params.set("weight", weight);
    setSearchParams(params, { replace: true });
  }, [quickPick, cats, players, time, weight, setSearchParams]);

  // Infinite scroll: Intersection Observer
  useEffect(() => {
    const sentinel = loadMoreTriggerRef.current;
    if (!sentinel) return undefined;

    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (isFilterChangeRef.current) {
          isFilterChangeRef.current = false;
          return;
        }
        if (entry.isIntersecting && hasNextPage && !isFetchingNextPage && !isLoading) {
          fetchNextPage();
        }
      },
      { root: null, rootMargin: "100px", threshold: 0.1 }
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [fetchNextPage, hasNextPage, isFetchingNextPage, isLoading]);

  const toggleQuickPick = useCallback((key) => {
    setQuickPick((prev) => {
      const next = prev === key ? "" : key;
      const qp = QUICK_PICKS.find((q) => q.key === key);
      setAnnouncement(next ? `Showing ${qp?.label}` : "Quick pick removed");
      return next;
    });
    setExpandedId(null);
  }, []);

  const toggleCategory = useCallback((key) => {
    setCats((prev) => {
      const active = prev.includes(key);
      const next = active ? prev.filter((c) => c !== key) : [...prev, key];
      setAnnouncement(active ? `${CATEGORY_LABELS[key]} removed` : `Added ${CATEGORY_LABELS[key]} to the shelf`);
      return next;
    });
    setExpandedId(null);
  }, []);

  const updatePlayers = useCallback((value) => {
    setPlayers(value);
    setAnnouncement(value ? `Filtering by ${value} players` : "Player filter removed");
  }, []);

  const updateTime = useCallback((value) => {
    setTime(value);
    setAnnouncement(value ? `Filtering by ${timeLabel(value)}` : "Duration filter removed");
  }, []);

  const updateWeight = useCallback((value) => {
    setWeight(value);
    setAnnouncement(value ? `Filtering by ${value} rules` : "Rules-crunch filter removed");
  }, []);

  const clearAll = useCallback(() => {
    setQuickPick("");
    setCats([]);
    setPlayers("");
    setTime("");
    setWeight("");
    setAnnouncement("All filters cleared. Showing all games.");
  }, []);

  const toggleCardExpansion = useCallback((gameId) => {
    setExpandedId((prev) => (prev === gameId ? null : gameId));
  }, []);

  const prefersReducedMotion = useMemo(
    () => window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    []
  );

  const activeChips = useMemo(() => {
    const chips = [];
    if (quickPick) {
      const qp = QUICK_PICKS.find((q) => q.key === quickPick);
      if (qp) chips.push({ id: `qp-${qp.key}`, label: qp.label, onClear: () => toggleQuickPick(qp.key) });
    }
    cats.forEach((key) => {
      chips.push({ id: `cat-${key}`, label: CATEGORY_LABELS[key] || key, onClear: () => toggleCategory(key) });
    });
    if (players) chips.push({ id: "players", label: `${players} players`, onClear: () => updatePlayers("") });
    if (time) chips.push({ id: "time", label: timeLabel(time), onClear: () => updateTime("") });
    if (weight) chips.push({ id: "weight", label: `${weight} rules`, onClear: () => updateWeight("") });
    return chips;
  }, [quickPick, cats, players, time, weight, toggleQuickPick, toggleCategory, updatePlayers, updateTime, updateWeight]);

  const hasActiveFilters = activeChips.length > 0;

  return (
    <div className="library-page" style={{ minHeight: "100vh" }}>
      <SkipNav />
      <LiveRegion message={announcement} />

      <main role="main" id="main-content" style={{ maxWidth: 480, margin: "0 auto" }}>
        <h1 className="sr-only">Mana &amp; Meeples Board Game Library</h1>

        {/* Header */}
        <header style={{ background: "linear-gradient(170deg, #3d5135 0%, #2d4a47 100%)", color: "white", padding: "16px 20px 24px 20px" }}>
          <a
            href="https://www.manaandmeeples.co.nz"
            target="_blank"
            rel="noopener noreferrer"
            style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none", marginBottom: 18 }}
          >
            <img src="/logo192.png" alt="Mana & Meeples logo" style={{ width: 38, height: 38, borderRadius: "50%", background: "white" }} />
            <span style={{ fontFamily: "'Bricolage Grotesque', sans-serif", fontSize: 22, fontWeight: 800, letterSpacing: "-0.01em", color: "white" }}>
              The Game Library
            </span>
            <span style={{ marginLeft: "auto", fontSize: 13, fontWeight: 600, color: "#cfe0c8" }}>← main site</span>
          </a>
          <p style={{ fontSize: 15, color: "#e8f0e4", margin: 0 }}>
            {totalGames != null ? `${totalGames} games` : "Games"} on our shelves — let&apos;s find yours.
          </p>
        </header>

        {/* Quick picks */}
        <section style={{ padding: "20px 20px 4px 20px" }}>
          <h2 style={{ fontFamily: "'Bricolage Grotesque', sans-serif", fontSize: 19, fontWeight: 700, color: "#3d5135", margin: "0 0 3px 0" }}>
            Who&apos;s playing today?
          </h2>
          <p style={{ fontSize: 14, color: "#5f726c", margin: "0 0 14px 0" }}>Tap one and we&apos;ll shortlist the shelf for you.</p>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }} role="group" aria-label="Who's playing today?">
            {QUICK_PICKS.map((qp) => {
              const active = quickPick === qp.key;
              return (
                <button
                  key={qp.key}
                  type="button"
                  onClick={() => toggleQuickPick(qp.key)}
                  aria-pressed={active}
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "flex-start",
                    gap: 3,
                    minHeight: 44,
                    padding: "11px 13px",
                    borderRadius: 14,
                    cursor: "pointer",
                    textAlign: "left",
                    fontFamily: "'Source Sans 3', sans-serif",
                    border: active ? "2px solid #a35040" : "2px solid transparent",
                    background: active ? "#fdf0ec" : "white",
                    color: "#3e473d",
                    boxShadow: "0 2px 8px rgba(61,81,53,0.08)",
                  }}
                >
                  <span style={{ display: "flex", alignItems: "center", gap: 7 }}>
                    <span style={{ fontSize: 17 }} aria-hidden="true">{qp.icon}</span>
                    <span style={{ fontFamily: "'Bricolage Grotesque', sans-serif", fontSize: 15, fontWeight: 700, lineHeight: 1.2 }}>{qp.label}</span>
                  </span>
                  <span style={{ fontSize: 12, fontWeight: 600, color: active ? "#a35040" : "#5f726c" }}>{qp.sub}</span>
                </button>
              );
            })}
          </div>
        </section>

        {/* Shelf picker */}
        <ShelfPicker counts={counts} selected={cats} onToggle={toggleCategory} />

        {/* Sticky "Narrow it down" bar */}
        <div style={{ position: "sticky", top: 0, zIndex: 40, background: "rgba(247,245,237,0.95)", backdropFilter: "blur(12px)", borderBottom: "1px solid #d4e0d1" }}>
          <div style={{ padding: "10px 20px" }}>
            <button
              type="button"
              onClick={() => setSheetOpen(true)}
              style={{
                width: "100%",
                display: "flex",
                alignItems: "center",
                gap: 10,
                minHeight: 50,
                padding: "10px 18px",
                background: "#3d5135",
                border: "none",
                borderRadius: 999,
                cursor: "pointer",
                boxShadow: "0 2px 8px rgba(61,81,53,0.25)",
              }}
              aria-haspopup="dialog"
              aria-expanded={sheetOpen}
            >
              <svg width="17" height="17" fill="none" stroke="white" strokeWidth="2.5" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" d="M4 6h16M7 12h10M10 18h4" />
              </svg>
              <span style={{ fontSize: 15, fontWeight: 700, color: "white" }}>Narrow it down</span>
              <span style={{ fontSize: 13, fontWeight: 600, color: "#cfe0c8" }}>players · time · rules</span>
              {hasActiveFilters && (
                <span
                  aria-hidden="true"
                  style={{
                    marginLeft: "auto",
                    background: "#a35040",
                    color: "white",
                    fontSize: 12,
                    fontWeight: 700,
                    minWidth: 20,
                    height: 20,
                    borderRadius: 999,
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  {activeChips.length}
                </span>
              )}
            </button>
          </div>

          {hasActiveFilters && (
            <div style={{ display: "flex", gap: 6, overflowX: "auto", padding: "0 20px 10px 20px", alignItems: "center" }}>
              {activeChips.map((chip) => (
                <button
                  key={chip.id}
                  type="button"
                  onClick={chip.onClear}
                  style={{
                    flexShrink: 0,
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    background: "#e8f0e4",
                    color: "#3d5135",
                    border: "none",
                    borderRadius: 999,
                    padding: "6px 12px",
                    fontSize: 13,
                    fontWeight: 600,
                    fontFamily: "'Source Sans 3', sans-serif",
                    cursor: "pointer",
                  }}
                >
                  {chip.label} ✕
                </button>
              ))}
              <button
                type="button"
                onClick={clearAll}
                style={{ flexShrink: 0, background: "none", border: "none", color: "#a35040", fontSize: 13, fontWeight: 700, fontFamily: "'Source Sans 3', sans-serif", cursor: "pointer", padding: "6px 8px" }}
              >
                Clear all
              </button>
            </div>
          )}
        </div>

        {/* Results list */}
        <div style={{ padding: "14px 20px 60px 20px", display: "flex", flexDirection: "column", gap: 12 }}>
          {/* Aftergame explainer strip */}
          <div style={{ display: "flex", alignItems: "center", gap: 12, background: "#eef1fd", border: "1px solid #d3daf7", borderRadius: 14, padding: "12px 14px" }}>
            <img src="/Aftergame_Icon_Logo_V3-Light.webp" alt="Aftergame" style={{ width: 30, height: 30, flexShrink: 0 }} />
            <p style={{ fontSize: 13, color: "#3e473d", lineHeight: 1.45, margin: 0 }}>
              <strong>Keen to play but short on players?</strong> Tap{" "}
              <img src="/Aftergame_Icon_Logo_V3-Light.webp" alt="Aftergame" style={{ width: 15, height: 15, verticalAlign: -2 }} /> on any game to
              organise a session for a day that suits you — and invite anyone in the Mana &amp; Meeples community to join.
            </p>
          </div>

          {isError && (
            <div style={{ textAlign: "center", padding: "40px 20px" }}>
              <p style={{ color: "#a35040", marginBottom: 16 }}>{error?.message || "Failed to load games"}</p>
              <button
                type="button"
                onClick={() => refetch()}
                style={{ minHeight: 48, padding: "12px 26px", background: "#3d5135", color: "white", border: "none", borderRadius: 999, fontSize: 15, fontWeight: 700, cursor: "pointer" }}
              >
                Retry
              </button>
            </div>
          )}

          {isLoading &&
            Array.from({ length: PAGE_SIZE }).map((_, index) => <GameCardSkeleton key={`skeleton-${index}`} />)}

          {!isLoading && !isError && items.length === 0 && (
            <div style={{ textAlign: "center", padding: "40px 20px" }}>
              <p style={{ fontSize: 17, color: "#5f726c", margin: "0 0 16px 0" }}>No games match — yet. Try loosening a filter.</p>
              <button
                type="button"
                onClick={clearAll}
                style={{ minHeight: 48, padding: "12px 26px", background: "#a35040", color: "white", border: "none", borderRadius: 999, fontSize: 15, fontWeight: 700, fontFamily: "'Source Sans 3', sans-serif", cursor: "pointer" }}
              >
                Clear all filters
              </button>
            </div>
          )}

          {!isLoading && !isError && items.length > 0 && (
            <>
              {items.map((game, index) => (
                <GameCardPublic
                  key={game.id}
                  game={game}
                  isExpanded={expandedId === game.id}
                  onToggleExpand={() => toggleCardExpansion(game.id)}
                  prefersReducedMotion={prefersReducedMotion}
                  priority={index < 8}
                  lazy={index >= 8}
                />
              ))}

              {isFetchingNextPage &&
                Array.from({ length: Math.min(PAGE_SIZE, Math.max(total - items.length, 0)) }).map((_, index) => (
                  <GameCardSkeleton key={`loading-skeleton-${index}`} />
                ))}

              <div ref={loadMoreTriggerRef} />
              <p style={{ textAlign: "center", fontSize: 13, color: "#5f726c", margin: "8px 0 0 0" }}>
                Keep scrolling — {items.length === total ? `${total} games` : `${items.length} of ${total} games`} on this shelf
              </p>
            </>
          )}
        </div>
      </main>

      <FilterSheet
        open={sheetOpen}
        onClose={() => setSheetOpen(false)}
        players={players}
        onPlayersChange={updatePlayers}
        time={time}
        onTimeChange={updateTime}
        weight={weight}
        onWeightChange={updateWeight}
        onClear={clearAll}
        resultCount={total}
      />
    </div>
  );
}
