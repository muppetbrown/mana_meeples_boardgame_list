// src/components/staff/tabs/ManageLibraryTab.jsx
import React, { useState, useMemo } from "react";
import { useStaff } from "../../../context/StaffContext";
import CategoryFilter from "../../CategoryFilter";
import { CATEGORY_LABELS } from "../../../constants/categories";
import { imageProxyUrl } from "../../../api/client";

/**
 * Manage Library tab - Browse, edit, and delete games in compact table view
 */
export function ManageLibraryTab() {
  const {
    selectedCategory,
    setSelectedCategory,
    counts,
    filteredLibrary,
    openEditCategory,
    deleteGameData,
    showToast,
  } = useStaff();

  const [searchQuery, setSearchQuery] = useState("");

  // Filter by search query
  const searchFilteredLibrary = useMemo(() => {
    if (!searchQuery.trim()) return filteredLibrary;
    const query = searchQuery.toLowerCase();
    return filteredLibrary.filter(
      (game) =>
        game.title?.toLowerCase().includes(query) ||
        game.bgg_id?.toString().includes(query) ||
        game.designers?.some((d) => d.toLowerCase().includes(query))
    );
  }, [filteredLibrary, searchQuery]);

  const handleDelete = async (game) => {
    if (!window.confirm(`Delete "${game.title}"?`)) return;
    try {
      await deleteGameData(game.id);
    } catch {
      showToast("Delete failed", "error");
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

        {/* Search Bar */}
        <div className="mb-4">
          <input
            type="text"
            className="w-full border-2 border-gray-300 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 rounded-lg px-4 py-2 outline-none transition-all"
            placeholder="Search by title, BGG ID, or designer..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        {/* Category Filter */}
        <CategoryFilter
          selected={selectedCategory}
          counts={counts}
          onChange={setSelectedCategory}
        />
      </div>

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
                    {/* Thumbnail */}
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="w-12 h-12 rounded overflow-hidden bg-gray-100 flex items-center justify-center">
                        {game.thumbnail_url || game.image ? (
                          <img
                            src={imageProxyUrl(game.image || game.thumbnail_url)}
                            alt={game.title}
                            className="w-full h-full object-cover"
                            onError={(e) => {
                              e.target.style.display = 'none';
                              e.target.parentElement.innerHTML = '<span class="text-xs text-gray-400">No img</span>';
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
                              +{game.modifies_players_min ?? game.min_players}-{game.modifies_players_max}p
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
                          onClick={() => openEditCategory(game)}
                          className="px-3 py-1.5 text-xs font-medium rounded-lg bg-purple-100 text-purple-700 hover:bg-purple-200 transition-colors"
                        >
                          Edit Category
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
    </div>
  );
}
