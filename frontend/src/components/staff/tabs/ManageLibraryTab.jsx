// src/components/staff/tabs/ManageLibraryTab.jsx
import React, { useState, useMemo, useEffect, useRef, useCallback } from "react";
import { useStaff } from "../../../context/StaffContext";
import CategoryFilter from "../../CategoryFilter";
import Icon from "../../common/Icon";
import { LibraryTableRow } from "../LibraryTableRow";
import { generateSleeveShoppingList, triggerSleeveFetch, generateGameLabels, reimportSelectedGames } from "../../../api/client";
import GameEditModal from "../GameEditModal";
import SleeveShoppingListModal from "../SleeveShoppingListModal";
import SleeveFetchStatus from "../SleeveFetchStatus";
import { ATTENTION_FILTERS } from "../../../utils/libraryQuality";
import AttentionHelp from "../AttentionHelp";

/**
 * Manage Library tab - Browse, edit, and delete games in compact table view
 */
export function ManageLibraryTab() {
  const {
    selectedCategory,
    setSelectedCategory,
    counts,
    filteredLibrary,
    library,
    deleteGameData,
    updateGameData,
    showToast,
    loadLibrary,
    confirm,
    attentionFilter,
    setAttentionFilter,
    addRecentOperation,
    isLoading,
  } = useStaff();

  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("date_added"); // default: date added
  const [sortReverse, setSortReverse] = useState(false); // flips the natural direction of sortBy
  const [compact, setCompact] = useState(() => {
    try {
      return localStorage.getItem("staff.library.density") !== "comfortable";
    } catch {
      return true;
    }
  });
  const [pageSize, setPageSize] = useState(50);
  const searchRef = useRef(null);
  const lastToggledIndex = useRef(null);
  const pageItemsRef = useRef([]);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingGame, setEditingGame] = useState(null);

  // Game selection state
  const [selectedGames, setSelectedGames] = useState(new Set());
  const [page, setPage] = useState(1);
  const [busyAction, setBusyAction] = useState(null); // 'labels' | 'sleeve-list' | null
  const [categorySaving, setCategorySaving] = useState(() => new Set());
  const [showSleeveShoppingList, setShowSleeveShoppingList] = useState(false);
  const [sleeveShoppingList, setSleeveShoppingList] = useState(null);
  const [sleeveFetchPollToken, setSleeveFetchPollToken] = useState(0);

  // Filter by search query and apply sorting
  const searchFilteredLibrary = useMemo(() => {
    let filtered = filteredLibrary;

    const attention = ATTENTION_FILTERS.find((f) => f.key === attentionFilter);
    if (attention) filtered = filtered.filter(attention.test);

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (game) =>
          game.title?.toLowerCase().includes(query) ||
          game.bgg_id?.toString().includes(query) ||
          game.designers?.some((d) => d.toLowerCase().includes(query))
      );
    }

    // Apply sorting
    const sorted = [...filtered].sort((a, b) => {
      if (sortBy === "title") {
        return (a.title || "").localeCompare(b.title || "");
      } else if (sortBy === "year") {
        return (b.year || 0) - (a.year || 0);
      } else if (sortBy === "category") {
        // Uncategorized games sort last (localeCompare would put a "~" sentinel first)
        const ca = a.mana_meeple_category;
        const cb = b.mana_meeple_category;
        if (!ca !== !cb) return ca ? -1 : 1;
        return (ca || "").localeCompare(cb || "") || (a.title || "").localeCompare(b.title || "");
      } else if (sortBy === "date_added") {
        // Sort by date_added descending (newest first)
        const dateA = a.date_added ? new Date(a.date_added) : new Date(0);
        const dateB = b.date_added ? new Date(b.date_added) : new Date(0);
        return dateB - dateA;
      }
      return 0;
    });

    return sortReverse ? sorted.reverse() : sorted;
  }, [filteredLibrary, searchQuery, sortBy, sortReverse, attentionFilter]);

  // Reset to page 1 and drop selections that are no longer in the filtered view
  useEffect(() => {
    setPage(1);
  }, [searchQuery, sortBy, sortReverse, selectedCategory, attentionFilter, pageSize]);

  useEffect(() => {
    setSelectedGames((prev) => {
      if (prev.size === 0) return prev;
      const visible = new Set(searchFilteredLibrary.map((g) => g.id));
      const next = new Set([...prev].filter((id) => visible.has(id)));
      return next.size === prev.size ? prev : next;
    });
  }, [searchFilteredLibrary]);

  const PAGE_SIZE = pageSize;
  const totalPages = Math.max(1, Math.ceil(searchFilteredLibrary.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pageItems = useMemo(
    () => searchFilteredLibrary.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE),
    [searchFilteredLibrary, currentPage, PAGE_SIZE]
  );
  pageItemsRef.current = pageItems;

  const handleDelete = useCallback(
    async (game) => {
      const ok = await confirm({
        title: `Delete "${game.title}"?`,
        message:
          "This permanently removes the game and its sleeve data. It cannot be undone.\n(If it's just not on the shelf any more, consider moving it to the Buy List instead.)",
        confirmLabel: "Delete game",
        tone: "danger",
      });
      if (!ok) return;
      try {
        await deleteGameData(game.id);
        setSelectedGames((prev) => {
          const next = new Set(prev);
          next.delete(game.id);
          return next;
        });
      } catch {
        // deleteGameData already toasts the failure
      }
    },
    [confirm, deleteGameData]
  );

  const handleCategoryChange = useCallback(
    async (game, value) => {
      const next = value || null;
      if ((game.mana_meeple_category || null) === next) return;
      setCategorySaving((prev) => new Set(prev).add(game.id));
      try {
        await updateGameData(game.id, { mana_meeple_category: next });
      } catch {
        // updateGameData already toasts the failure
      } finally {
        setCategorySaving((prev) => {
          const n = new Set(prev);
          n.delete(game.id);
          return n;
        });
      }
    },
    [updateGameData]
  );

  const handleEditGame = useCallback((game) => {
    setEditingGame(game);
    setEditModalOpen(true);
  }, []);

  const handleSaveGame = async (gameData) => {
    if (!editingGame) return;

    try {
      await updateGameData(editingGame.id, gameData);
      setEditModalOpen(false);
      setEditingGame(null);
    } catch (error) {
      // updateGameData already toasts; keep the modal open so edits aren't lost
    }
  };

  const handleCloseEditModal = () => {
    setEditModalOpen(false);
    setEditingGame(null);
  };

  // ---- Selection ----
  // Row toggle; shift-click selects/deselects the range since the last toggled row.
  const toggleGameSelection = useCallback((gameId, index, shiftKey) => {
    setSelectedGames((prev) => {
      const next = new Set(prev);
      const items = pageItemsRef.current;
      const turnOn = !prev.has(gameId);
      if (shiftKey && lastToggledIndex.current != null && lastToggledIndex.current < items.length) {
        const [from, to] = [lastToggledIndex.current, index].sort((a, b) => a - b);
        for (let i = from; i <= to; i++) {
          if (turnOn) next.add(items[i].id);
          else next.delete(items[i].id);
        }
      } else if (turnOn) {
        next.add(gameId);
      } else {
        next.delete(gameId);
      }
      return next;
    });
    lastToggledIndex.current = index;
  }, []);

  const pageAllSelected = pageItems.length > 0 && pageItems.every((g) => selectedGames.has(g.id));
  const pageSomeSelected = pageItems.some((g) => selectedGames.has(g.id));
  const allMatchingSelected =
    searchFilteredLibrary.length > 0 && searchFilteredLibrary.every((g) => selectedGames.has(g.id));
  const hasMultiplePages = searchFilteredLibrary.length > pageItems.length;

  const toggleSelectPage = () => {
    setSelectedGames((prev) => {
      const next = new Set(prev);
      if (pageAllSelected) pageItems.forEach((g) => next.delete(g.id));
      else pageItems.forEach((g) => next.add(g.id));
      return next;
    });
  };

  const selectAllMatching = () => setSelectedGames(new Set(searchFilteredLibrary.map((g) => g.id)));

  // Header-click sorting: first click sorts by that column, second flips direction
  const handleHeaderSort = (key) => {
    if (sortBy === key) setSortReverse((r) => !r);
    else {
      setSortBy(key);
      setSortReverse(false);
    }
  };

  const toggleDensity = (value) => {
    setCompact(value);
    try {
      localStorage.setItem("staff.library.density", value ? "compact" : "comfortable");
    } catch {
      /* preference just won't persist */
    }
  };

  const filtersActive = Boolean(searchQuery.trim() || attentionFilter || selectedCategory !== "all");
  const clearAllFilters = () => {
    setSearchQuery("");
    setAttentionFilter("");
    setSelectedCategory("all");
  };

  // "/" focuses the search box (unless already typing somewhere)
  useEffect(() => {
    const onKey = (e) => {
      if (e.key !== "/" || e.ctrlKey || e.metaKey || e.altKey) return;
      const t = e.target;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable)) return;
      if (!searchRef.current || searchRef.current.offsetParent === null) return; // tab hidden
      e.preventDefault();
      searchRef.current.focus();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const handleGenerateSleeveList = async () => {
    if (selectedGames.size === 0) {
      showToast('Please select at least one game', 'error');
      return;
    }

    setBusyAction('sleeve-list');
    try {
      const data = await generateSleeveShoppingList(Array.from(selectedGames));
      setSleeveShoppingList(data);
      setShowSleeveShoppingList(true);
    } catch (err) {
      console.error('Failed to generate shopping list:', err);
      showToast('Failed to generate sleeve shopping list', 'error');
    } finally {
      setBusyAction(null);
    }
  };

  const handleTriggerSleeveFetch = async () => {
    if (selectedGames.size === 0) {
      showToast('Please select at least one game', 'error');
      return;
    }

    const ok = await confirm({
      title: `Fetch sleeve data for ${selectedGames.size} game(s)?`,
      message: "This triggers a GitHub Actions workflow that runs in the background and may take a few minutes.",
      confirmLabel: "Fetch sleeve data",
    });
    if (!ok) return;

    try {
      const count = selectedGames.size;
      await triggerSleeveFetch(Array.from(selectedGames));
      showToast(`Sleeve fetch workflow triggered for ${count} game(s)`, 'success');
      // Bump the poll token so SleeveFetchStatus starts actively polling for progress.
      setSleeveFetchPollToken((t) => t + 1);
      addRecentOperation?.({
        label: `Sleeve data fetch (${count} game${count === 1 ? '' : 's'})`,
        etaMs: 180000,
      });
      // Clear selection after triggering
      setSelectedGames(new Set());
    } catch (err) {
      console.error('Failed to trigger sleeve fetch:', err);
      const errorMsg = err.response?.data?.detail || 'Failed to trigger sleeve fetch workflow';
      showToast(errorMsg, 'error');
    }
  };

  const handleReimportSelected = async () => {
    if (selectedGames.size === 0) {
      showToast('Please select at least one game', 'error');
      return;
    }

    const ok = await confirm({
      title: `Re-import ${selectedGames.size} game(s) from BoardGameGeek?`,
      message: "This refreshes BGG data (ratings, descriptions, images, etc.) for the selected games. It runs in the background and may take a minute or two.",
      confirmLabel: "Re-import",
    });
    if (!ok) return;

    try {
      const count = selectedGames.size;
      const result = await reimportSelectedGames(Array.from(selectedGames));
      showToast(result.message, 'success');
      addRecentOperation?.({
        label: `Re-import from BGG (${count} game${count === 1 ? '' : 's'})`,
        etaMs: Math.max(30000, count * 5000),
      });
      setSelectedGames(new Set());
    } catch (err) {
      console.error('Failed to re-import selected games:', err);
      const errorMsg = err.response?.data?.detail || 'Failed to start re-import';
      showToast(errorMsg, 'error');
    }
  };

  const handlePrintLabels = async () => {
    if (selectedGames.size === 0) {
      showToast('Please select at least one game', 'error');
      return;
    }

    setBusyAction('labels');
    try {
      showToast(`Generating labels for ${selectedGames.size} game(s)...`, 'info');

      // Call API to generate PDF
      const pdfBlob = await generateGameLabels(Array.from(selectedGames));

      // Create download link
      const url = window.URL.createObjectURL(pdfBlob);
      const link = document.createElement('a');
      link.href = url;

      // Generate filename with timestamp
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
      link.download = `board-game-labels-${timestamp}.pdf`;

      // Trigger download
      document.body.appendChild(link);
      link.click();

      // Cleanup
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      showToast(`Labels generated successfully for ${selectedGames.size} game(s)`, 'success');

      // Optionally clear selection after successful generation
      // setSelectedGames(new Set());
    } catch (err) {
      console.error('Failed to generate labels:', err);
      const errorMsg = err.response?.data?.detail || 'Failed to generate labels';
      showToast(errorMsg, 'error');
    } finally {
      setBusyAction(null);
    }
  };

  const thCls = "px-3 py-2 text-left text-[11px] font-semibold text-gray-600 uppercase tracking-wider";
  const stickyTop = "calc(var(--staff-topbar-h, 6rem) + 3rem)";

  const SortHeader = ({ sortKey, label, align = "left", extra = "" }) => {
    const active = sortBy === sortKey;
    const natural = sortKey === "title" || sortKey === "category" ? "ascending" : "descending";
    const dir = active ? (sortReverse ? (natural === "ascending" ? "descending" : "ascending") : natural) : "none";
    return (
      <th
        scope="col"
        aria-sort={dir}
        className={`${thCls} ${align === "right" ? "text-right" : ""} ${extra} bg-gray-50 sticky z-10`}
        style={{ top: stickyTop }}
      >
        <button
          type="button"
          onClick={() => handleHeaderSort(sortKey)}
          className={`inline-flex items-center gap-1 uppercase tracking-wider font-semibold hover:text-purple-700 ${active ? "text-purple-700" : ""}`}
        >
          {label}
          <Icon
            name={active ? (dir === "ascending" ? "chevronUp" : "chevronDown") : "chevronsUpDown"}
            size={12}
            className={active ? "" : "opacity-40"}
          />
        </button>
      </th>
    );
  };
  const StaticHeader = ({ children, extra = "", align = "left" }) => (
    <th
      scope="col"
      className={`${thCls} ${align === "right" ? "text-right" : ""} ${extra} bg-gray-50 sticky z-10`}
      style={{ top: stickyTop }}
    >
      {children}
    </th>
  );

  const actionBtn =
    "inline-flex items-center gap-1.5 h-8 px-3 text-sm font-medium rounded-md border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 hover:border-gray-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors";
  const hasSelection = selectedGames.size > 0;

  return (
    <div className="space-y-4">
      {/* Header, search and filters */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold">Your Library</h2>
          <div className="flex items-center gap-4">
            <div className="text-sm text-gray-600 tabular">
              Showing <strong>{searchFilteredLibrary.length}</strong> of <strong>{filteredLibrary.length}</strong> games
              {searchQuery && " (filtered by search)"}
            </div>
            <div className="inline-flex rounded-md border border-gray-300 overflow-hidden" role="group" aria-label="Row density">
              {[
                [true, "Compact"],
                [false, "Comfortable"],
              ].map(([value, label]) => (
                <button
                  key={label}
                  type="button"
                  aria-pressed={compact === value}
                  onClick={() => toggleDensity(value)}
                  className={`h-7 px-2.5 text-xs font-medium ${
                    compact === value ? "bg-purple-600 text-white" : "bg-white text-gray-600 hover:bg-gray-50"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Search Bar and Sort Controls */}
        <div className="mb-3 flex gap-2">
          <div className="relative flex-1">
            <Icon name="search" size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
            <input
              ref={searchRef}
              type="text"
              className="w-full border border-gray-300 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 rounded-md pl-9 pr-10 h-9 text-sm outline-none transition-all"
              aria-label="Search library"
              placeholder="Search by title, BGG ID, or designer…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[11px] text-gray-400 border border-gray-200 rounded px-1.5 bg-gray-50" aria-hidden="true">
              /
            </kbd>
          </div>
          <select
            aria-label="Sort library"
            value={sortBy}
            onChange={(e) => {
              setSortBy(e.target.value);
              setSortReverse(false);
            }}
            className="border border-gray-300 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 rounded-md px-3 h-9 text-sm outline-none transition-all"
          >
            <option value="date_added">Sort: Date Added (Newest)</option>
            <option value="title">Sort: Title (A-Z)</option>
            <option value="year">Sort: Year (Newest)</option>
            <option value="category">Sort: Category</option>
          </select>
          <select
            aria-label="Data quality filter"
            value={attentionFilter}
            onChange={(e) => setAttentionFilter(e.target.value)}
            className="border border-gray-300 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 rounded-md px-3 h-9 text-sm outline-none transition-all"
          >
            <option value="">Quality: All games</option>
            {ATTENTION_FILTERS.map((f) => (
              <option key={f.key} value={f.key}>
                Needs attention: {f.label}
              </option>
            ))}
          </select>
        </div>

        {/* Category Filter */}
        <CategoryFilter selected={selectedCategory} counts={counts} onChange={setSelectedCategory} dense />

        {/* Guidance for the active needs-attention filter */}
        <AttentionHelp
          filterKey={attentionFilter}
          count={searchFilteredLibrary.length}
          onClear={() => setAttentionFilter("")}
        />
      </div>

      {/* Selection toolbar (sticky) */}
      {searchFilteredLibrary.length > 0 && (
        <div
          className={`rounded-lg px-4 min-h-12 py-1.5 sticky z-20 border flex items-center justify-between flex-wrap gap-x-4 gap-y-2 ${
            hasSelection ? "bg-purple-50 border-purple-200 shadow-sm" : "bg-white border-gray-200"
          }`}
          style={{ top: "var(--staff-topbar-h, 6rem)" }}
        >
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={pageAllSelected}
                ref={(el) => {
                  if (el) el.indeterminate = pageSomeSelected && !pageAllSelected;
                }}
                onChange={toggleSelectPage}
                className="w-4 h-4 text-purple-600 rounded focus:ring-purple-500"
              />
              <span className="font-medium text-sm">
                {pageAllSelected
                  ? "Deselect All"
                  : hasMultiplePages
                    ? `Select page (${pageItems.length})`
                    : `Select All ${pageItems.length}`}
              </span>
            </label>
            <span className="text-sm text-gray-600 tabular" aria-live="polite">
              {selectedGames.size} game(s) selected
            </span>
            {hasSelection && (
              <button
                onClick={() => setSelectedGames(new Set())}
                className="text-sm text-purple-700 underline hover:text-purple-900"
              >
                Clear
              </button>
            )}
          </div>

          {hasSelection ? (
            <div className="flex gap-2 flex-wrap items-center">
              <button
                onClick={handleReimportSelected}
                className={actionBtn}
                title="Re-import selected games from BoardGameGeek"
              >
                <Icon name="refresh" size={14} /> Re-import from BGG
              </button>
              <button
                onClick={handleTriggerSleeveFetch}
                className={actionBtn}
                title="Trigger GitHub Actions workflow to fetch sleeve data"
              >
                <Icon name="sleeve" size={14} /> Fetch Sleeve Data
              </button>
              <button
                onClick={handleGenerateSleeveList}
                disabled={busyAction === "sleeve-list"}
                className={actionBtn}
              >
                <Icon name="tasks" size={14} />
                {busyAction === "sleeve-list" ? "Building list…" : "Generate Sleeve Shopping List"}
              </button>
              <button
                onClick={handlePrintLabels}
                disabled={busyAction === "labels"}
                className={actionBtn}
                title="Generate PDF labels for printing"
              >
                <Icon name="print" size={14} />
                {busyAction === "labels" ? "Generating…" : "Print Labels"}
              </button>
            </div>
          ) : (
            <span className="text-xs text-gray-500">
              Select games to re-import, fetch sleeve data, build a shopping list or print labels.
            </span>
          )}
          <SleeveFetchStatus pollToken={sleeveFetchPollToken} />
        </div>
      )}

      {/* Cross-page selection banner */}
      {hasMultiplePages && pageAllSelected && (
        <div role="status" className="text-sm text-center bg-purple-50 border border-purple-200 rounded-lg px-4 py-2 text-purple-900">
          {allMatchingSelected ? (
            <>
              All <strong>{searchFilteredLibrary.length}</strong> matching games are selected.{" "}
              <button onClick={() => setSelectedGames(new Set())} className="underline font-medium">
                Clear selection
              </button>
            </>
          ) : (
            <>
              All {pageItems.length} games on this page are selected.{" "}
              <button onClick={selectAllMatching} className="underline font-medium">
                Select all {searchFilteredLibrary.length} matching games
              </button>
            </>
          )}
        </div>
      )}

      {/* Library Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 [overflow-x:clip]">
        {isLoading && library.length === 0 ? (
          <div className="p-4 space-y-2" role="status" aria-label="Loading library">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-9 rounded bg-gray-100 animate-pulse" />
            ))}
          </div>
        ) : searchFilteredLibrary.length === 0 ? (
          <div className="text-center py-12 px-6">
            <div className="text-gray-300 flex justify-center mb-3">
              <Icon name="library" size={40} />
            </div>
            <div className="text-gray-600">
              {searchQuery ? (
                <>
                  No games found matching "<strong>{searchQuery}</strong>"
                </>
              ) : (
                "No games in this category"
              )}
            </div>
            {filtersActive && (
              <button
                onClick={clearAllFilters}
                className="mt-4 inline-flex items-center h-8 px-3 text-sm font-medium rounded-md border border-gray-300 hover:bg-gray-50"
              >
                Clear filters
              </button>
            )}
          </div>
        ) : (
          <table className="w-full">
            <thead className="border-b border-gray-200">
              <tr>
                <StaticHeader extra="text-center w-10">
                  <span className="sr-only">Select</span>
                </StaticHeader>
                <StaticHeader>
                  <span className="sr-only">Thumbnail</span>
                </StaticHeader>
                <SortHeader sortKey="title" label="Name" />
                <StaticHeader>Type</StaticHeader>
                <StaticHeader extra="hidden xl:table-cell">Players</StaticHeader>
                <StaticHeader extra="hidden xl:table-cell">Time</StaticHeader>
                <StaticHeader extra="hidden xl:table-cell" align="right">Weight</StaticHeader>
                <StaticHeader extra="hidden xl:table-cell" align="right">Rating</StaticHeader>
                <SortHeader sortKey="category" label="Category" />
                <StaticHeader align="right">Actions</StaticHeader>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {pageItems.map((game, index) => (
                <LibraryTableRow
                  key={game.id}
                  game={game}
                  index={index}
                  compact={compact}
                  selected={selectedGames.has(game.id)}
                  saving={categorySaving.has(game.id)}
                  onToggle={toggleGameSelection}
                  onCategoryChange={handleCategoryChange}
                  onEdit={handleEditGame}
                  onDelete={handleDelete}
                />
              ))}
            </tbody>
          </table>
        )}
        {searchFilteredLibrary.length > 0 && (totalPages > 1 || searchFilteredLibrary.length > 25) && (
          <div className="flex items-center justify-between px-4 py-2 border-t border-gray-200 bg-gray-50 text-sm">
            <span className="text-gray-600 tabular">
              Showing {(currentPage - 1) * PAGE_SIZE + 1}–{Math.min(currentPage * PAGE_SIZE, searchFilteredLibrary.length)} of {searchFilteredLibrary.length}
            </span>
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-1.5 text-gray-600">
                Rows
                <select
                  aria-label="Rows per page"
                  value={pageSize}
                  onChange={(e) => setPageSize(Number(e.target.value))}
                  className="border border-gray-300 rounded-md h-8 px-2 text-sm bg-white"
                >
                  {[25, 50, 100, 200].map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </label>
              {totalPages > 1 && (
                <>
                  <button
                    onClick={() => setPage(currentPage - 1)}
                    disabled={currentPage === 1}
                    className="px-3 h-8 rounded-md border border-gray-300 bg-white hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    ← Previous
                  </button>
                  <span className="text-gray-700 tabular">
                    Page {currentPage} of {totalPages}
                  </span>
                  <button
                    onClick={() => setPage(currentPage + 1)}
                    disabled={currentPage === totalPages}
                    className="px-3 h-8 rounded-md border border-gray-300 bg-white hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    Next →
                  </button>
                </>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Game Edit Modal */}
      {editModalOpen && (
        <GameEditModal
          game={editingGame}
          library={library}
          onSave={handleSaveGame}
          onClose={handleCloseEditModal}
          onSleeveUpdate={loadLibrary}
        />
      )}

      {/* Sleeve Shopping List Modal */}
      {showSleeveShoppingList && sleeveShoppingList && (
        <SleeveShoppingListModal
          shoppingList={sleeveShoppingList}
          onClose={() => {
            setShowSleeveShoppingList(false);
            setSleeveShoppingList(null);
          }}
        />
      )}
    </div>
  );
}
