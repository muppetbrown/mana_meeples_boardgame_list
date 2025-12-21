// src/hooks/useGameFilters.js
import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';

/**
 * Custom hook for managing game filter state and URL synchronization
 * Handles all filter states, debouncing, and URL parameter persistence
 *
 * @param {Object} defaultValues - Default filter values
 * @returns {Object} Filter state and update functions
 */
export function useGameFilters(defaultValues = {}) {
  const [searchParams, setSearchParams] = useSearchParams();

  // Get initial values from URL or defaults
  const [q, setQ] = useState(searchParams.get("q") || defaultValues.q || "");
  const [qDebounced, setQDebounced] = useState(q);
  const [category, setCategory] = useState(searchParams.get("category") || defaultValues.category || "all");
  const [designer, setDesigner] = useState(searchParams.get("designer") || defaultValues.designer || "");
  const [nzDesigner, setNzDesigner] = useState(searchParams.get("nz_designer") === "true");
  const [players, setPlayers] = useState(searchParams.get("players") || defaultValues.players || "");
  const [recentlyAdded, setRecentlyAdded] = useState(searchParams.get("recently_added") === "30");
  const [sort, setSort] = useState(searchParams.get("sort") || defaultValues.sort || "year_desc");

  // Debounce search input (150ms delay)
  useEffect(() => {
    const id = setTimeout(() => setQDebounced(q), 150);
    return () => clearTimeout(id);
  }, [q]);

  // Update URL when filters change
  useEffect(() => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (category !== "all") params.set("category", category);
    if (designer) params.set("designer", designer);
    if (nzDesigner) params.set("nz_designer", "true");
    if (players) params.set("players", players);
    if (recentlyAdded) params.set("recently_added", "30");
    if (sort !== (defaultValues.sort || "year_desc")) params.set("sort", sort);

    setSearchParams(params, { replace: true });
  }, [q, category, designer, nzDesigner, players, recentlyAdded, sort, setSearchParams, defaultValues.sort]);

  // Helper functions for updating filters
  const updateSearch = (newSearch) => setQ(newSearch);
  const updateCategory = (newCategory) => setCategory(newCategory);
  const updateDesigner = (newDesigner) => setDesigner(newDesigner);
  const updateNzDesigner = (value) => setNzDesigner(value);
  const updatePlayers = (value) => setPlayers(value);
  const updateRecentlyAdded = (value) => setRecentlyAdded(value);
  const updateSort = (newSort) => setSort(newSort);

  // Clear all filters
  const clearFilters = () => {
    setQ("");
    setCategory("all");
    setDesigner("");
    setNzDesigner(false);
    setPlayers("");
    setRecentlyAdded(false);
    setSort(defaultValues.sort || "year_desc");
  };

  // Get filter params object for API calls
  const getFilterParams = (additionalParams = {}) => {
    const params = { q: qDebounced, sort, ...additionalParams };
    if (category !== "all") params.category = category;
    if (designer) params.designer = designer;
    if (nzDesigner) params.nz_designer = true;
    if (players) params.players = parseInt(players);
    if (recentlyAdded) params.recently_added = 30;
    return params;
  };

  // Check if any filters are active
  const hasActiveFilters = () => {
    return q !== "" ||
           category !== "all" ||
           designer !== "" ||
           nzDesigner ||
           players !== "" ||
           recentlyAdded;
  };

  return {
    // Filter states
    q,
    qDebounced,
    category,
    designer,
    nzDesigner,
    players,
    recentlyAdded,
    sort,

    // Update functions
    updateSearch,
    updateCategory,
    updateDesigner,
    updateNzDesigner,
    updatePlayers,
    updateRecentlyAdded,
    updateSort,
    clearFilters,

    // Helper functions
    getFilterParams,
    hasActiveFilters: hasActiveFilters(),

    // Direct setters (for advanced use cases)
    setQ,
    setCategory,
    setDesigner,
    setNzDesigner,
    setPlayers,
    setRecentlyAdded,
    setSort,
  };
}
