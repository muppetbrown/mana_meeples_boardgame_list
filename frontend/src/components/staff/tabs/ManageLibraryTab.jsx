// src/components/staff/tabs/ManageLibraryTab.jsx
import React, { useState, useMemo } from "react";
import { useStaff } from "../../../context/StaffContext";
import CategoryFilter from "../../CategoryFilter";
import LibraryCard from "../LibraryCard";

/**
 * Manage Library tab - Browse, edit, and delete games with pagination
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

  const [currentPage, setCurrentPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState("");
  const itemsPerPage = 24; // 8 rows x 3 columns on desktop

  // Filter by search query
  const searchFilteredLibrary = useMemo(() => {
    if (!searchQuery.trim()) return filteredLibrary;
    const query = searchQuery.toLowerCase();
    return filteredLibrary.filter(
      (game) =>
        game.title?.toLowerCase().includes(query) ||
        game.designers?.some((d) => d.toLowerCase().includes(query))
    );
  }, [filteredLibrary, searchQuery]);

  // Pagination
  const totalPages = Math.ceil(searchFilteredLibrary.length / itemsPerPage);
  const paginatedLibrary = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    const end = start + itemsPerPage;
    return searchFilteredLibrary.slice(start, end);
  }, [searchFilteredLibrary, currentPage, itemsPerPage]);

  // Reset to page 1 when filters change
  React.useEffect(() => {
    setCurrentPage(1);
  }, [selectedCategory, searchQuery]);

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
            placeholder="Search by title or designer..."
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

      {/* Library Grid */}
      <div className="bg-white rounded-2xl p-6 shadow">
        {paginatedLibrary.length === 0 ? (
          <div className="text-center py-12">
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
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {paginatedLibrary.map((game) => (
                <LibraryCard
                  key={game.id}
                  game={game}
                  onEditCategory={(g) => openEditCategory(g)}
                  onDelete={handleDelete}
                />
              ))}
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="mt-6 pt-6 border-t border-gray-200">
                <div className="flex items-center justify-between">
                  <div className="text-sm text-gray-600">
                    Page {currentPage} of {totalPages}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setCurrentPage(1)}
                      disabled={currentPage === 1}
                      className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      First
                    </button>
                    <button
                      onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                      disabled={currentPage === 1}
                      className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      Previous
                    </button>
                    <button
                      onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                      disabled={currentPage === totalPages}
                      className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      Next
                    </button>
                    <button
                      onClick={() => setCurrentPage(totalPages)}
                      disabled={currentPage === totalPages}
                      className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      Last
                    </button>
                  </div>
                  <div className="text-sm text-gray-600">
                    {(currentPage - 1) * itemsPerPage + 1}-
                    {Math.min(currentPage * itemsPerPage, searchFilteredLibrary.length)} of{" "}
                    {searchFilteredLibrary.length}
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
