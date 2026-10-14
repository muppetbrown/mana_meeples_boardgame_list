// src/components/staff/tabs/ManageLibraryTab.jsx
import React, { useState, useMemo, useEffect } from "react";
import { useStaff } from "../../../context/StaffContext";
import CategoryFilter from "../../CategoryFilter";
import { CATEGORY_KEYS, CATEGORY_LABELS } from "../../../constants/categories";
import Thumbnail from "../../common/Thumbnail";
import { generateSleeveShoppingList, triggerSleeveFetch, generateGameLabels, reimportSelectedGames } from "../../../api/client";
import GameEditModal from "../GameEditModal";
import SleeveShoppingListModal from "../SleeveShoppingListModal";
import SleeveFetchStatus from "../SleeveFetchStatus";
import { ATTENTION_FILTERS } from "../../../utils/libraryQuality";

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
  } = useStaff();

  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("date_added"); // default: date added
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

    return sorted;
  }, [filteredLibrary, searchQuery, sortBy, attentionFilter]);

  // Reset to page 1 and drop selections that are no longer in the filtered view
  useEffect(() => {
    setPage(1);
  }, [searchQuery, sortBy, selectedCategory, attentionFilter]);

  useEffect(() => {
    setSelectedGames((prev) => {
      if (prev.size === 0) return prev;
      const visible = new Set(searchFilteredLibrary.map((g) => g.id));
      const next = new Set([...prev].filter((id) => visible.has(id)));
      return next.size === prev.size ? prev : next;
    });
  }, [searchFilteredLibrary]);

  const PAGE_SIZE = 50;
  const totalPages = Math.max(1, Math.ceil(searchFilteredLibrary.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pageItems = useMemo(
    () => searchFilteredLibrary.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE),
    [searchFilteredLibrary, currentPage]
  );

  const handleDelete = async (game) => {
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
  };

  const handleCategoryChange = async (game, value) => {
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
  };

  const handleEditGame = (game) => {
    setEditingGame(game);
    setEditModalOpen(true);
  };

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

  // Game selection handlers
  const toggleGameSelection = (gameId) => {
    const newSelected = new Set(selectedGames);
    if (newSelected.has(gameId)) {
      newSelected.delete(gameId);
    } else {
      newSelected.add(gameId);
    }
    setSelectedGames(newSelected);
  };

  const toggleSelectAll = () => {
    if (selectedGames.size === searchFilteredLibrary.length) {
      setSelectedGames(new Set());
    } else {
      setSelectedGames(new Set(searchFilteredLibrary.map(g => g.id)));
    }
  };

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
      await triggerSleeveFetch(Array.from(selectedGames));
      showToast(`Sleeve fetch workflow triggered for ${selectedGames.size} game(s)`, 'success');
      // Bump the poll token so SleeveFetchStatus starts actively polling for progress.
      setSleeveFetchPollToken((t) => t + 1);
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
      const result = await reimportSelectedGames(Array.from(selectedGames));
      showToast(result.message, 'success');
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

  return (
    <div className="space-y-6">
      {/* Header with Stats */}
      <div className="bg-white rounded-2xl p-6 shadow">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">Your Library</h2>
          <div className="text-sm text-gray-600">
            Showing <strong>{searchFilteredLibrary.length}</strong> of <strong>{filteredLibrary.length}</strong> games
            {searchQuery && " (filtered by search)"}
          </div>
        </div>

        {/* Search Bar and Sort Controls */}
        <div className="mb-4 flex gap-3">
          <input
            type="text"
            className="flex-1 border-2 border-gray-300 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 rounded-lg px-4 py-2 outline-none transition-all"
            aria-label="Search library"
            placeholder="Search by title, BGG ID, or designer..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <select
            aria-label="Sort library"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="border-2 border-gray-300 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 rounded-lg px-4 py-2 outline-none transition-all"
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
            className="border-2 border-gray-300 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 rounded-lg px-4 py-2 outline-none transition-all"
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
        <CategoryFilter
          selected={selectedCategory}
          counts={counts}
          onChange={setSelectedCategory}
        />
      </div>

      {/* Selection Actions Bar */}
      {searchFilteredLibrary.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 sticky top-32 z-20 shadow-sm">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectedGames.size === searchFilteredLibrary.length && searchFilteredLibrary.length > 0}
                  ref={(el) => {
                    if (el) el.indeterminate = selectedGames.size > 0 && selectedGames.size < searchFilteredLibrary.length;
                  }}
                  onChange={toggleSelectAll}
                  className="w-4 h-4 text-purple-600 rounded focus:ring-purple-500"
                />
                <span className="font-medium text-sm">
                  {selectedGames.size === searchFilteredLibrary.length ? 'Deselect All' : `Select All ${searchFilteredLibrary.length}`}
                </span>
              </label>
              <span className="text-sm text-gray-600" aria-live="polite">
                {selectedGames.size} game(s) selected
              </span>
              {selectedGames.size > 0 && (
                <button
                  onClick={() => setSelectedGames(new Set())}
                  className="text-sm text-blue-700 underline hover:text-blue-900"
                >
                  Clear
                </button>
              )}
            </div>

            <div className="flex gap-2 flex-wrap">
              <button
                onClick={handleReimportSelected}
                disabled={selectedGames.size === 0}
                className="px-4 py-2 bg-orange-600 text-white text-sm font-medium rounded-lg hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                title="Re-import selected games from BoardGameGeek"
              >
                ♻️ Re-import from BGG
              </button>
              <button
                onClick={handleTriggerSleeveFetch}
                disabled={selectedGames.size === 0}
                className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                title="Trigger GitHub Actions workflow to fetch sleeve data"
              >
                🔄 Fetch Sleeve Data
              </button>
              <button
                onClick={handleGenerateSleeveList}
                disabled={selectedGames.size === 0 || busyAction === 'sleeve-list'}
                className="px-4 py-2 bg-purple-600 text-white text-sm font-medium rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {busyAction === 'sleeve-list' ? 'Building list…' : '📋 Generate Sleeve Shopping List'}
              </button>
              <button
                onClick={handlePrintLabels}
                disabled={selectedGames.size === 0 || busyAction === 'labels'}
                className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                title="Generate PDF labels for printing"
              >
                {busyAction === 'labels' ? 'Generating…' : '🏷️ Print Labels'}
              </button>
            </div>
            <SleeveFetchStatus pollToken={sleeveFetchPollToken} />
          </div>
        </div>
      )}

      {/* Library Table */}
      <div className="bg-white rounded-2xl shadow overflow-hidden">
        {searchFilteredLibrary.length === 0 ? (
          <div className="text-center py-12 px-6">
            <div className="text-4xl mb-3">📚</div>
            <div className="text-gray-600">
              {searchQuery ? (
                <>
                  No games found matching "<strong>{searchQuery}</strong>"
                </>
              ) : (
                "No games in this category"
              )}
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Select
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Thumbnail
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Name
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    BGG ID
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Category
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {pageItems.map((game) => (
                  <tr key={game.id} className="hover:bg-gray-50 transition-colors">
                    {/* Select Checkbox */}
                    <td className="px-4 py-3 whitespace-nowrap text-center">
                      <input
                        type="checkbox"
                        aria-label={`Select ${game.title}`}
                        checked={selectedGames.has(game.id)}
                        onChange={() => toggleGameSelection(game.id)}
                        className="w-4 h-4 text-purple-600 rounded focus:ring-purple-500 cursor-pointer"
                      />
                    </td>

                    {/* Thumbnail */}
                    <td className="px-4 py-3 whitespace-nowrap">
                      <Thumbnail src={game.cloudinary_url || game.image_url} alt={game.title} />
                    </td>

                    {/* Name */}
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="text-sm font-medium text-gray-900">{game.title}</div>
                        {game.fully_sleeved && (
                          <span
                            className="text-lg"
                            title="All sleeve requirements marked as sleeved"
                          >
                            🃏
                          </span>
                        )}
                        {game.has_sleeves === 'none' && (
                          <span
                            className="text-sm"
                            title="No sleeve requirements for this game"
                          >
                            🚫🃏
                          </span>
                        )}
                        {(game.has_sleeves === 'not_found' || game.has_sleeves === 'check' || !game.has_sleeves) && (
                          <span
                            className="text-sm"
                            title="Sleeve status needs investigation"
                          >
                            ❓🃏
                          </span>
                        )}
                      </div>
                      {game.year && (
                        <div className="text-xs text-gray-500">{game.year}</div>
                      )}
                    </td>

                    {/* Type - Expansion Badge */}
                    <td className="px-4 py-3 whitespace-nowrap">
                      {game.is_expansion ? (
                        <div className="flex flex-col gap-1">
                          <span className={`inline-flex px-2 py-0.5 text-xs font-semibold rounded-full ${
                            game.expansion_type === 'both' || game.expansion_type === 'standalone'
                              ? 'bg-indigo-100 text-indigo-800'
                              : 'bg-purple-100 text-purple-800'
                          }`}>
                            {game.expansion_type === 'both' || game.expansion_type === 'standalone'
                              ? 'STANDALONE'
                              : 'EXPANSION'}
                          </span>
                          {game.modifies_players_max && (
                            <span className="text-xs text-purple-600">
                              +{game.modifies_players_min ?? game.players_min}-{game.modifies_players_max}p
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="inline-flex px-2 py-0.5 text-xs font-medium rounded-full bg-gray-100 text-gray-600">
                          Base Game
                        </span>
                      )}
                    </td>

                    {/* BGG ID */}
                    <td className="px-4 py-3 whitespace-nowrap">
                      {game.bgg_id ? (
                        <a
                          href={`https://boardgamegeek.com/boardgame/${game.bgg_id}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-purple-600 hover:text-purple-800 underline"
                        >
                          {game.bgg_id}
                        </a>
                      ) : (
                        <span className="text-sm text-gray-400">—</span>
                      )}
                    </td>

                    {/* Category (inline editable) */}
                    <td className="px-4 py-3">
                      <select
                        aria-label={`Category for ${game.title}`}
                        value={game.mana_meeple_category || ""}
                        disabled={categorySaving.has(game.id)}
                        onChange={(e) => handleCategoryChange(game, e.target.value)}
                        className={`text-xs font-medium rounded-full border px-2 py-1 outline-none focus:ring-2 focus:ring-purple-300 disabled:opacity-50 ${
                          game.mana_meeple_category
                            ? "bg-purple-50 text-purple-800 border-purple-200"
                            : "bg-gray-100 text-gray-600 border-gray-300"
                        }`}
                      >
                        <option value="">Uncategorized</option>
                        {CATEGORY_KEYS.map((key) => (
                          <option key={key} value={key}>
                            {CATEGORY_LABELS[key]}
                          </option>
                        ))}
                      </select>
                    </td>

                    {/* Actions */}
                    <td className="px-4 py-3 whitespace-nowrap text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleEditGame(game)}
                          className="px-3 py-1.5 text-xs font-medium rounded-lg bg-purple-100 text-purple-700 hover:bg-purple-200 transition-colors"
                          title="Edit game details"
                          aria-label={`Edit Game: ${game.title}`}
                        >
                          Edit Game
                        </button>
                        <button
                          onClick={() => handleDelete(game)}
                          aria-label={`Delete ${game.title}`}
                          className="px-3 py-1.5 text-xs font-medium rounded-lg bg-red-100 text-red-700 hover:bg-red-200 transition-colors"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gray-50 text-sm">
            <span className="text-gray-600">
              Showing {(currentPage - 1) * PAGE_SIZE + 1}–{Math.min(currentPage * PAGE_SIZE, searchFilteredLibrary.length)} of {searchFilteredLibrary.length}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(currentPage - 1)}
                disabled={currentPage === 1}
                className="px-3 py-1.5 rounded-lg border border-gray-300 bg-white hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                ← Previous
              </button>
              <span className="text-gray-700">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => setPage(currentPage + 1)}
                disabled={currentPage === totalPages}
                className="px-3 py-1.5 rounded-lg border border-gray-300 bg-white hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Next →
              </button>
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
