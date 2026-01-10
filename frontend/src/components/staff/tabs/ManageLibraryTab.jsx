// src/components/staff/tabs/ManageLibraryTab.jsx
import React, { useState, useMemo } from "react";
import { useStaff } from "../../../context/StaffContext";
import CategoryFilter from "../../CategoryFilter";
import { CATEGORY_LABELS } from "../../../constants/categories";
import { imageProxyUrl, generateSleeveShoppingList, triggerSleeveFetch, generateGameLabels } from "../../../api/client";
import GameEditModal from "../GameEditModal";
import SleeveShoppingListModal from "../SleeveShoppingListModal";

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
    openEditCategory,
    deleteGameData,
    updateGameData,
    showToast,
  } = useStaff();

  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("date_added"); // default: date added
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingGame, setEditingGame] = useState(null);

  // Game selection state
  const [selectedGames, setSelectedGames] = useState(new Set());
  const [showSleeveShoppingList, setShowSleeveShoppingList] = useState(false);
  const [sleeveShoppingList, setSleeveShoppingList] = useState(null);

  // Filter by search query and apply sorting
  const searchFilteredLibrary = useMemo(() => {
    let filtered = filteredLibrary;

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
      } else if (sortBy === "date_added") {
        // Sort by date_added descending (newest first)
        const dateA = a.date_added ? new Date(a.date_added) : new Date(0);
        const dateB = b.date_added ? new Date(b.date_added) : new Date(0);
        return dateB - dateA;
      }
      return 0;
    });

    return sorted;
  }, [filteredLibrary, searchQuery, sortBy]);

  const handleDelete = async (game) => {
    if (!window.confirm(`Delete "${game.title}"?`)) return;
    try {
      await deleteGameData(game.id);
    } catch {
      showToast("Delete failed", "error");
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
      showToast("Game details updated successfully", "success");
      setEditModalOpen(false);
      setEditingGame(null);
    } catch (error) {
      showToast("Failed to update game details", "error");
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

    try {
      const data = await generateSleeveShoppingList(Array.from(selectedGames));
      setSleeveShoppingList(data);
      setShowSleeveShoppingList(true);
    } catch (err) {
      console.error('Failed to generate shopping list:', err);
      showToast('Failed to generate sleeve shopping list', 'error');
    }
  };

  const handleTriggerSleeveFetch = async () => {
    if (selectedGames.size === 0) {
      showToast('Please select at least one game', 'error');
      return;
    }

    if (!window.confirm(`Trigger GitHub Actions workflow to fetch sleeve data for ${selectedGames.size} game(s)?\n\nThis will run in the background and may take a few minutes.`)) {
      return;
    }

    try {
      const data = await triggerSleeveFetch(Array.from(selectedGames));
      showToast(`Sleeve fetch workflow triggered for ${selectedGames.size} game(s)`, 'success');
      // Clear selection after triggering
      setSelectedGames(new Set());
    } catch (err) {
      console.error('Failed to trigger sleeve fetch:', err);
      const errorMsg = err.response?.data?.detail || 'Failed to trigger sleeve fetch workflow';
      showToast(errorMsg, 'error');
    }
  };

  const handlePrintLabels = async () => {
    if (selectedGames.size === 0) {
      showToast('Please select at least one game', 'error');
      return;
    }

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
            placeholder="Search by title, BGG ID, or designer..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="border-2 border-gray-300 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 rounded-lg px-4 py-2 outline-none transition-all"
          >
            <option value="date_added">Sort: Date Added (Newest)</option>
            <option value="title">Sort: Title (A-Z)</option>
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
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectedGames.size === searchFilteredLibrary.length && searchFilteredLibrary.length > 0}
                  onChange={toggleSelectAll}
                  className="w-4 h-4 text-purple-600 rounded focus:ring-purple-500"
                />
                <span className="font-medium text-sm">
                  {selectedGames.size === searchFilteredLibrary.length ? 'Deselect All' : 'Select All'}
                </span>
              </label>
              <span className="text-sm text-gray-600">
                {selectedGames.size} game(s) selected
              </span>
            </div>

            <div className="flex gap-2">
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
                disabled={selectedGames.size === 0}
                className="px-4 py-2 bg-purple-600 text-white text-sm font-medium rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                📋 Generate Sleeve Shopping List
              </button>
              <button
                onClick={handlePrintLabels}
                disabled={selectedGames.size === 0}
                className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                title="Generate PDF labels for printing"
              >
                🏷️ Print Labels
              </button>
            </div>
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
                {searchFilteredLibrary.map((game) => (
                  <tr key={game.id} className="hover:bg-gray-50 transition-colors">
                    {/* Select Checkbox */}
                    <td className="px-4 py-3 whitespace-nowrap text-center">
                      <input
                        type="checkbox"
                        checked={selectedGames.has(game.id)}
                        onChange={() => toggleGameSelection(game.id)}
                        className="w-4 h-4 text-purple-600 rounded focus:ring-purple-500 cursor-pointer"
                      />
                    </td>

                    {/* Thumbnail */}
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="w-12 h-12 rounded overflow-hidden bg-gray-100 flex items-center justify-center">
                        {game.cloudinary_url || game.image_url ? (
                          <img
                            src={imageProxyUrl(game.cloudinary_url || game.image_url)}
                            alt={game.title}
                            className="w-full h-full object-cover"
                            onError={(e) => {
                              // SECURITY: Use createElement instead of innerHTML to prevent XSS
                              e.target.style.display = 'none';
                              const fallback = document.createElement('span');
                              fallback.className = 'text-xs text-gray-400';
                              fallback.textContent = 'No img';
                              e.target.parentElement.replaceChild(fallback, e.target);
                            }}
                          />
                        ) : (
                          <span className="text-xs text-gray-400">No img</span>
                        )}
                      </div>
                    </td>

                    {/* Name */}
                    <td className="px-4 py-3">
                      <div className="text-sm font-medium text-gray-900">{game.title}</div>
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

                    {/* Category */}
                    <td className="px-4 py-3">
                      {game.mana_meeple_category ? (
                        <span className="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-purple-100 text-purple-800">
                          {CATEGORY_LABELS[game.mana_meeple_category] || game.mana_meeple_category}
                        </span>
                      ) : (
                        <span className="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-600">
                          Uncategorized
                        </span>
                      )}
                    </td>

                    {/* Actions */}
                    <td className="px-4 py-3 whitespace-nowrap text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleEditGame(game)}
                          className="px-3 py-1.5 text-xs font-medium rounded-lg bg-purple-100 text-purple-700 hover:bg-purple-200 transition-colors"
                          title="Edit game details"
                        >
                          Edit Game
                        </button>
                        <button
                          onClick={() => handleDelete(game)}
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
      </div>

      {/* Game Edit Modal */}
      {editModalOpen && (
        <GameEditModal
          game={editingGame}
          library={library}
          onSave={handleSaveGame}
          onClose={handleCloseEditModal}
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
