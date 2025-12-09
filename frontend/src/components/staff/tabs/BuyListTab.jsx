// src/components/staff/tabs/BuyListTab.jsx
import React, { useState, useEffect } from "react";
import {
  getBuyListGames,
  getLastPriceUpdate,
  addToBuyList,
  updateBuyListGame,
  removeFromBuyList,
  importPrices,
  getAllGames,
} from "../../../api/client";

/**
 * Buy List tab - Manage games to purchase with pricing data
 */
export function BuyListTab() {
  const [buyList, setBuyList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [filters, setFilters] = useState({
    lpg_status: "",
    buy_filter: "",
    sort_by: "rank",
    sort_desc: false,
  });
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [showAddModal, setShowAddModal] = useState(false);
  const [addGameSearch, setAddGameSearch] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Load buy list and last update on mount
  useEffect(() => {
    loadBuyList();
    loadLastUpdate();
  }, [filters]);

  const loadBuyList = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getBuyListGames(filters);
      setBuyList(data.items || []);
    } catch (err) {
      console.error("Failed to load buy list:", err);
      setError("Failed to load buy list");
    } finally {
      setLoading(false);
    }
  };

  const loadLastUpdate = async () => {
    try {
      const data = await getLastPriceUpdate();
      setLastUpdate(data);
    } catch (err) {
      console.error("Failed to load last update:", err);
    }
  };

  const handleImportPrices = async () => {
    try {
      setError(null);
      setSuccess(null);
      const result = await importPrices("latest_prices.json");
      setSuccess(
        `Imported ${result.imported} prices, skipped ${result.skipped}`
      );
      await loadBuyList();
      await loadLastUpdate();
    } catch (err) {
      console.error("Failed to import prices:", err);
      setError("Failed to import prices");
    }
  };

  const handleEdit = (item) => {
    setEditingId(item.id);
    setEditForm({
      rank: item.rank || "",
      bgo_link: item.bgo_link || "",
      lpg_rrp: item.lpg_rrp || "",
      lpg_status: item.lpg_status || "",
    });
  };

  const handleSaveEdit = async () => {
    try {
      setError(null);
      await updateBuyListGame(editingId, editForm);
      setEditingId(null);
      setSuccess("Updated successfully");
      await loadBuyList();
    } catch (err) {
      console.error("Failed to update:", err);
      setError("Failed to update");
    }
  };

  const handleRemove = async (id) => {
    if (!window.confirm("Remove this game from the buy list?")) return;

    try {
      setError(null);
      await removeFromBuyList(id);
      setSuccess("Removed from buy list");
      await loadBuyList();
    } catch (err) {
      console.error("Failed to remove:", err);
      setError("Failed to remove");
    }
  };

  const handleSearchGames = async () => {
    if (!addGameSearch.trim()) return;

    try {
      const data = await getAllGames({ q: addGameSearch, page_size: 10 });
      setSearchResults(data.items || []);
    } catch (err) {
      console.error("Failed to search games:", err);
      setError("Failed to search games");
    }
  };

  const handleAddGame = async (gameId) => {
    try {
      setError(null);
      await addToBuyList({ game_id: gameId });
      setSuccess("Added to buy list");
      setShowAddModal(false);
      setAddGameSearch("");
      setSearchResults([]);
      await loadBuyList();
    } catch (err) {
      console.error("Failed to add to buy list:", err);
      setError(err.response?.data?.detail || "Failed to add to buy list");
    }
  };

  const formatPrice = (price) => {
    return price ? `$${parseFloat(price).toFixed(2)}` : "-";
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "-";
    return new Date(dateStr).toLocaleDateString("en-NZ", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getBuyFilterBadge = (buyFilter) => {
    if (buyFilter === true) {
      return (
        <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-700">
          BUY NOW
        </span>
      );
    }
    return null;
  };

  const getStatusColor = (status) => {
    const colors = {
      AVAILABLE: "bg-green-100 text-green-700",
      BACK_ORDER: "bg-yellow-100 text-yellow-700",
      NOT_FOUND: "bg-gray-100 text-gray-700",
      BACK_ORDER_OOS: "bg-red-100 text-red-700",
    };
    return colors[status] || "bg-gray-100 text-gray-700";
  };

  return (
    <div className="space-y-6">
      {/* Header with Actions */}
      <div className="bg-white rounded-2xl p-6 shadow">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
          <div>
            <h2 className="text-xl font-semibold">Buy List Management</h2>
            <p className="text-sm text-gray-600 mt-1">
              Manage games to purchase and track prices
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setShowAddModal(true)}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
            >
              + Add Game
            </button>
            <button
              onClick={handleImportPrices}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              ↻ Import Prices
            </button>
          </div>
        </div>

        {/* Last Update */}
        {lastUpdate?.last_updated && (
          <div className="text-sm text-gray-600">
            Last price update:{" "}
            <span className="font-medium">
              {formatDate(lastUpdate.last_updated)}
            </span>
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg p-4 shadow">
        <div className="grid md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              LPG Status
            </label>
            <select
              value={filters.lpg_status}
              onChange={(e) =>
                setFilters({ ...filters, lpg_status: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            >
              <option value="">All</option>
              <option value="AVAILABLE">Available</option>
              <option value="BACK_ORDER">Back Order</option>
              <option value="NOT_FOUND">Not Found</option>
              <option value="BACK_ORDER_OOS">Back Order OOS</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Buy Filter
            </label>
            <select
              value={filters.buy_filter}
              onChange={(e) =>
                setFilters({ ...filters, buy_filter: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            >
              <option value="">All</option>
              <option value="true">Buy Now</option>
              <option value="false">Not Recommended</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Sort By
            </label>
            <select
              value={filters.sort_by}
              onChange={(e) =>
                setFilters({ ...filters, sort_by: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            >
              <option value="rank">Rank</option>
              <option value="title">Title</option>
              <option value="updated_at">Last Updated</option>
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={() =>
                setFilters({ ...filters, sort_desc: !filters.sort_desc })
              }
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              {filters.sort_desc ? "↓ Desc" : "↑ Asc"}
            </button>
          </div>
        </div>
      </div>

      {/* Error/Success Messages */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          {error}
        </div>
      )}
      {success && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-green-700">
          {success}
        </div>
      )}

      {/* Buy List Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-500">Loading...</div>
        ) : buyList.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            No games in buy list
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-4 py-3 text-left font-semibold">Rank</th>
                  <th className="px-4 py-3 text-left font-semibold">Game</th>
                  <th className="px-4 py-3 text-left font-semibold">
                    LPG Status
                  </th>
                  <th className="px-4 py-3 text-left font-semibold">
                    LPG RRP
                  </th>
                  <th className="px-4 py-3 text-left font-semibold">
                    Best Price
                  </th>
                  <th className="px-4 py-3 text-left font-semibold">
                    Store
                  </th>
                  <th className="px-4 py-3 text-left font-semibold">
                    Discount
                  </th>
                  <th className="px-4 py-3 text-left font-semibold">
                    Filter
                  </th>
                  <th className="px-4 py-3 text-right font-semibold">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {buyList.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50">
                    {editingId === item.id ? (
                      <>
                        <td className="px-4 py-3">
                          <input
                            type="number"
                            value={editForm.rank}
                            onChange={(e) =>
                              setEditForm({ ...editForm, rank: e.target.value })
                            }
                            className="w-20 px-2 py-1 border rounded"
                          />
                        </td>
                        <td className="px-4 py-3" colSpan="7">
                          <div className="space-y-2">
                            <div className="font-medium">{item.title}</div>
                            <div className="grid grid-cols-2 gap-2">
                              <div>
                                <label className="text-xs text-gray-600">
                                  LPG Status
                                </label>
                                <select
                                  value={editForm.lpg_status}
                                  onChange={(e) =>
                                    setEditForm({
                                      ...editForm,
                                      lpg_status: e.target.value,
                                    })
                                  }
                                  className="w-full px-2 py-1 border rounded text-sm"
                                >
                                  <option value="">-</option>
                                  <option value="AVAILABLE">Available</option>
                                  <option value="BACK_ORDER">Back Order</option>
                                  <option value="NOT_FOUND">Not Found</option>
                                  <option value="BACK_ORDER_OOS">
                                    Back Order OOS
                                  </option>
                                </select>
                              </div>
                              <div>
                                <label className="text-xs text-gray-600">
                                  LPG RRP
                                </label>
                                <input
                                  type="number"
                                  step="0.01"
                                  value={editForm.lpg_rrp}
                                  onChange={(e) =>
                                    setEditForm({
                                      ...editForm,
                                      lpg_rrp: e.target.value,
                                    })
                                  }
                                  className="w-full px-2 py-1 border rounded text-sm"
                                  placeholder="0.00"
                                />
                              </div>
                              <div className="col-span-2">
                                <label className="text-xs text-gray-600">
                                  BGO Link
                                </label>
                                <input
                                  type="url"
                                  value={editForm.bgo_link}
                                  onChange={(e) =>
                                    setEditForm({
                                      ...editForm,
                                      bgo_link: e.target.value,
                                    })
                                  }
                                  className="w-full px-2 py-1 border rounded text-sm"
                                  placeholder="https://boardgameoracle.com/..."
                                />
                              </div>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex gap-1">
                            <button
                              onClick={handleSaveEdit}
                              className="px-2 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700"
                            >
                              Save
                            </button>
                            <button
                              onClick={() => setEditingId(null)}
                              className="px-2 py-1 bg-gray-600 text-white rounded text-xs hover:bg-gray-700"
                            >
                              Cancel
                            </button>
                          </div>
                        </td>
                      </>
                    ) : (
                      <>
                        <td className="px-4 py-3 text-gray-700">
                          {item.rank || "-"}
                        </td>
                        <td className="px-4 py-3">
                          <div className="font-medium">{item.title}</div>
                          {item.bgo_link && (
                            <a
                              href={item.bgo_link}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-blue-600 hover:underline"
                            >
                              BGO ↗
                            </a>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          {item.lpg_status ? (
                            <span
                              className={`px-2 py-1 text-xs rounded-full ${getStatusColor(
                                item.lpg_status
                              )}`}
                            >
                              {item.lpg_status.replace(/_/g, " ")}
                            </span>
                          ) : (
                            "-"
                          )}
                        </td>
                        <td className="px-4 py-3 text-gray-700">
                          {formatPrice(item.lpg_rrp)}
                        </td>
                        <td className="px-4 py-3 text-gray-700 font-medium">
                          {item.latest_price?.best_price
                            ? formatPrice(item.latest_price.best_price)
                            : "-"}
                        </td>
                        <td className="px-4 py-3 text-gray-600 text-xs">
                          {item.latest_price?.best_store || "-"}
                        </td>
                        <td className="px-4 py-3">
                          {item.latest_price?.discount_pct ? (
                            <span className="text-green-700 font-medium">
                              {item.latest_price.discount_pct.toFixed(0)}%
                            </span>
                          ) : (
                            "-"
                          )}
                        </td>
                        <td className="px-4 py-3">
                          {getBuyFilterBadge(item.buy_filter)}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex gap-1 justify-end">
                            <button
                              onClick={() => handleEdit(item)}
                              className="px-2 py-1 text-blue-600 hover:bg-blue-50 rounded text-xs"
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => handleRemove(item.id)}
                              className="px-2 py-1 text-red-600 hover:bg-red-50 rounded text-xs"
                            >
                              Remove
                            </button>
                          </div>
                        </td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add Game Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-auto">
            <div className="p-6">
              <h3 className="text-lg font-semibold mb-4">Add Game to Buy List</h3>

              <div className="flex gap-2 mb-4">
                <input
                  type="text"
                  value={addGameSearch}
                  onChange={(e) => setAddGameSearch(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && handleSearchGames()}
                  placeholder="Search games..."
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg"
                />
                <button
                  onClick={handleSearchGames}
                  className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
                >
                  Search
                </button>
              </div>

              {searchResults.length > 0 && (
                <div className="space-y-2 mb-4">
                  {searchResults.map((game) => (
                    <div
                      key={game.id}
                      className="flex items-center justify-between p-3 border border-gray-200 rounded-lg hover:bg-gray-50"
                    >
                      <div>
                        <div className="font-medium">{game.title}</div>
                        <div className="text-sm text-gray-600">
                          {game.year} • BGG ID: {game.bgg_id}
                        </div>
                      </div>
                      <button
                        onClick={() => handleAddGame(game.id)}
                        className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700"
                      >
                        Add
                      </button>
                    </div>
                  ))}
                </div>
              )}

              <div className="flex justify-end gap-2">
                <button
                  onClick={() => {
                    setShowAddModal(false);
                    setAddGameSearch("");
                    setSearchResults([]);
                  }}
                  className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
