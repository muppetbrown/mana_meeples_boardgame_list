// src/components/staff/tabs/BuyListTab.jsx
import React, { useState, useEffect, useRef } from "react";
import { useConfirm } from "../../../context/StaffContext";
import Thumbnail from "../../common/Thumbnail";
import {
  getBuyListGames,
  getLibraryGaps,
  addToBuyList,
  updateBuyListGame,
  removeFromBuyList,
  bulkImportBuyListCSV,
  updateGame,
  importFromBGG,
} from "../../../api/client";
import { CATEGORY_LABELS } from "../../../constants/categories";
import { parseBggId } from "../../../utils/bgg";

const PLAYER_COUNT_LABELS = {
  "1": "1 player", "2": "2 players", "3": "3 players", "4": "4 players",
  "5": "5 players", "6": "6 players", "7": "7 players", "8": "8 players",
  "9+": "9+ players",
};

/**
 * Games to Add tab - a gap-aware list of candidate games worth buying,
 * curated by rank and notes rather than tracked online prices.
 */
export function BuyListTab() {
  const [buyList, setBuyList] = useState([]);
  const [gaps, setGaps] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState("rank");
  const [sortDesc, setSortDesc] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [showAddModal, setShowAddModal] = useState(false);
  const [showBulkImportModal, setShowBulkImportModal] = useState(false);
  const [addBggId, setAddBggId] = useState("");
  const [addFormData, setAddFormData] = useState({ rank: "", notes: "" });
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const fileInputRef = useRef(null);
  const confirm = useConfirm();

  // Banners auto-dismiss (errors linger longer so they can be read)
  useEffect(() => {
    if (!success) return undefined;
    const t = setTimeout(() => setSuccess(null), 6000);
    return () => clearTimeout(t);
  }, [success]);
  useEffect(() => {
    if (!error) return undefined;
    const t = setTimeout(() => setError(null), 10000);
    return () => clearTimeout(t);
  }, [error]);

  useEffect(() => {
    loadBuyList();
  }, [sortBy, sortDesc]);
  useEffect(() => {
    loadGaps();
  }, []);

  const loadBuyList = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getBuyListGames({ sort_by: sortBy, sort_desc: sortDesc });
      setBuyList(data.items || []);
    } catch (err) {
      console.error("Failed to load games to add:", err);
      setError("Failed to load games to add");
    } finally {
      setLoading(false);
    }
  };

  const loadGaps = async () => {
    try {
      const data = await getLibraryGaps();
      setGaps(data);
    } catch (err) {
      console.error("Failed to load library gaps:", err);
    }
  };

  const handleEdit = (item) => {
    setEditingId(item.id);
    setEditForm({ rank: item.rank || "", notes: item.notes || "" });
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
    const ok = await confirm({ title: "Remove this game from the list?", confirmLabel: "Remove", tone: "danger" });
    if (!ok) return;

    try {
      setError(null);
      await removeFromBuyList(id);
      setSuccess("Removed from the list");
      await loadBuyList();
    } catch (err) {
      console.error("Failed to remove:", err);
      setError("Failed to remove");
    }
  };

  const handleMoveToOwned = async (item) => {
    const ok = await confirm({
      title: `Move "${item.title}" to your owned collection?`,
      message: "It will be added to the public library and refreshed from BoardGameGeek.",
      confirmLabel: "Move to owned",
    });
    if (!ok) return;

    try {
      setError(null);

      // Update the game status to OWNED and set date_added
      await updateGame(item.game_id, {
        status: "OWNED",
        date_added: new Date().toISOString(),
      });

      // Update the buy list entry to mark as not on the list
      await updateBuyListGame(item.id, {
        on_buy_list: false,
      });

      // Force a BGG reimport to ensure all derived fields (nz_designer, mana_meeple_category,
      // etc.) are fully populated — additions here may have used an older import path
      let reimportFailed = false;
      if (item.bgg_id) {
        try {
          await importFromBGG(item.bgg_id, true);
        } catch (reimportErr) {
          console.warn("BGG data refresh failed after move-to-owned:", reimportErr);
          reimportFailed = true;
        }
      }

      if (reimportFailed) {
        setSuccess(`"${item.title}" moved to owned collection. BGG data refresh failed — use Re-import in Manage Library to update it.`);
      } else {
        setSuccess(`"${item.title}" moved to owned collection!`);
      }
      await loadBuyList();
      await loadGaps();
    } catch (err) {
      console.error("Failed to move to owned:", err);
      setError("Failed to move game to owned collection");
    }
  };

  const handleAddGameByBggId = async () => {
    if (!addBggId.trim()) {
      setError("Please enter a BGG ID");
      return;
    }

    // Accept a pasted BGG URL as well as a bare ID
    const bggIdNum = parseBggId(addBggId);
    if (!bggIdNum) {
      setError("Please enter a valid BGG ID or BoardGameGeek URL");
      return;
    }

    try {
      setError(null);
      const payload = {
        bgg_id: bggIdNum,
        rank: addFormData.rank ? parseInt(addFormData.rank) : null,
        notes: addFormData.notes || null,
      };

      await addToBuyList(payload);
      setSuccess("Added to the list (imported from BGG if needed)");
      setShowAddModal(false);
      setAddBggId("");
      setAddFormData({ rank: "", notes: "" });
      await loadBuyList();
    } catch (err) {
      console.error("Failed to add game:", err);
      setError(err.response?.data?.detail || "Failed to add game");
    }
  };

  const handleBulkImportCSV = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      setError(null);
      setSuccess(null);
      const result = await bulkImportBuyListCSV(file);

      let message = `Bulk import completed: ${result.added} added, ${result.updated} updated`;
      if (result.skipped > 0) {
        message += `, ${result.skipped} skipped`;
      }
      if (result.errors > 0) {
        message += `, ${result.errors} errors`;
        if (result.error_details?.length > 0) {
          console.error("Import errors:", result.error_details);
          message += ` (see console for details)`;
        }
      }

      setSuccess(message);
      setShowBulkImportModal(false);
      await loadBuyList();

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (err) {
      console.error("Failed to import CSV:", err);
      setError(err.response?.data?.detail || "Failed to import CSV");
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const gapCategories = (gaps?.category_gaps || []).filter((g) => g.is_gap);
  const gapPlayerCounts = (gaps?.player_count_gaps || []).filter((g) => g.is_gap);

  const renderGapMatchBadges = (gapMatch) => {
    if (!gapMatch) return null;
    const badges = [];
    if (gapMatch.category_is_gap) {
      badges.push(
        <span key="category" className="px-2 py-0.5 text-xs font-medium rounded-full bg-emerald-100 text-emerald-700">
          Fills category gap
        </span>
      );
    }
    for (const count of gapMatch.matching_player_count_gaps || []) {
      badges.push(
        <span key={`players-${count}`} className="px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 text-blue-700">
          Fills {PLAYER_COUNT_LABELS[count] || `${count} players`} gap
        </span>
      );
    }
    if (badges.length === 0) return null;
    return <div className="flex flex-wrap gap-1 mt-1">{badges}</div>;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-2xl p-6 shadow">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold">Games to Add</h2>
            <p className="text-sm text-gray-600 mt-1">
              Candidate games worth buying, with notes on why — now bought directly through distributors
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
              onClick={() => setShowBulkImportModal(true)}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
            >
              📥 Bulk Import CSV
            </button>
          </div>
        </div>
      </div>

      {/* Library gaps */}
      <div className="bg-white rounded-2xl p-6 shadow">
        <h3 className="text-lg font-semibold mb-3">Where the collection is thin</h3>
        {!gaps ? (
          <p className="text-sm text-gray-500">Loading gap analysis…</p>
        ) : gaps.total_games === 0 ? (
          <p className="text-sm text-gray-500">Add games to the owned collection to see gap analysis.</p>
        ) : gapCategories.length === 0 && gapPlayerCounts.length === 0 ? (
          <p className="text-sm text-green-700">No significant gaps detected. 👍</p>
        ) : (
          <div className="grid md:grid-cols-2 gap-4">
            {gapCategories.length > 0 && (
              <div>
                <div className="text-sm font-medium text-gray-700 mb-2">Under-represented categories</div>
                <div className="flex flex-wrap gap-2">
                  {gapCategories.map((g) => (
                    <span key={g.category} className="px-3 py-1 text-xs font-medium rounded-full bg-amber-100 text-amber-800">
                      {CATEGORY_LABELS[g.category] || g.category} ({g.pct_of_collection}%)
                    </span>
                  ))}
                </div>
              </div>
            )}
            {gapPlayerCounts.length > 0 && (
              <div>
                <div className="text-sm font-medium text-gray-700 mb-2">Thin player-count coverage</div>
                <div className="flex flex-wrap gap-2">
                  {gapPlayerCounts.map((g) => (
                    <span key={g.player_count} className="px-3 py-1 text-xs font-medium rounded-full bg-amber-100 text-amber-800">
                      {PLAYER_COUNT_LABELS[g.player_count] || g.player_count} ({g.games_supporting} games)
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Sort controls */}
      <div className="bg-white rounded-lg p-4 shadow">
        <div className="grid md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Sort By
            </label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            >
              <option value="rank">Rank</option>
              <option value="title">Title</option>
              <option value="updated_at">Last Updated</option>
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={() => setSortDesc(!sortDesc)}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              {sortDesc ? "↓ Desc" : "↑ Asc"}
            </button>
          </div>
        </div>
      </div>

      {/* Error/Success Messages */}
      {error && (
        <div role="alert" className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 flex justify-between gap-4">
          <span>{error}</span>
          <button onClick={() => setError(null)} aria-label="Dismiss error" className="text-red-700 hover:text-red-900">✕</button>
        </div>
      )}
      {success && (
        <div role="status" className="bg-green-50 border border-green-200 rounded-lg p-4 text-green-700 flex justify-between gap-4">
          <span>{success}</span>
          <button onClick={() => setSuccess(null)} aria-label="Dismiss message" className="text-green-700 hover:text-green-900">✕</button>
        </div>
      )}

      {/* Games to Add Table */}
      <div className={`bg-white rounded-lg shadow overflow-hidden transition-opacity ${loading && buyList.length > 0 ? "opacity-60" : ""}`} aria-busy={loading}>
        {loading && buyList.length === 0 ? (
          <div className="p-8 text-center text-gray-500">Loading...</div>
        ) : buyList.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            No games on the list yet
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-4 py-3 text-left font-semibold">Image</th>
                  <th className="px-4 py-3 text-left font-semibold">Rank</th>
                  <th className="px-4 py-3 text-left font-semibold">Game</th>
                  <th className="px-4 py-3 text-left font-semibold">Notes</th>
                  <th className="px-4 py-3 text-right font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {buyList.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50">
                    {editingId === item.id ? (
                      <>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <Thumbnail src={item.cloudinary_url || item.image_url} alt={item.title} />
                        </td>
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
                        <td className="px-4 py-3" colSpan="2">
                          <div className="space-y-2">
                            <div className="font-medium">{item.title}</div>
                            <textarea
                              value={editForm.notes}
                              onChange={(e) =>
                                setEditForm({ ...editForm, notes: e.target.value })
                              }
                              placeholder="Why this fills a gap, or other curation notes"
                              className="w-full px-2 py-1 border rounded text-sm"
                              rows={2}
                            />
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex gap-1 justify-end">
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
                        <td className="px-4 py-3 whitespace-nowrap">
                          <Thumbnail src={item.cloudinary_url || item.image_url} alt={item.title} />
                        </td>
                        <td className="px-4 py-3 text-gray-700">
                          {item.rank || "-"}
                        </td>
                        <td className="px-4 py-3">
                          <div className="font-medium">{item.title}</div>
                          {renderGapMatchBadges(item.gap_match)}
                        </td>
                        <td className="px-4 py-3 text-gray-600">
                          {item.notes || "-"}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex gap-1 justify-end">
                            <button
                              onClick={() => handleMoveToOwned(item)}
                              className="px-2 py-1 text-green-600 hover:bg-green-50 rounded text-xs font-medium"
                              title="Move to owned collection"
                            >
                              → Owned
                            </button>
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
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-auto">
            <div className="p-6">
              <h3 className="text-lg font-semibold mb-4">Add a Candidate Game by BGG ID</h3>
              <p className="text-sm text-gray-600 mb-4">
                Enter a BoardGameGeek ID. If the game isn't in your library, it will be automatically imported.
              </p>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    BGG ID or URL <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    inputMode="numeric"
                    value={addBggId}
                    onChange={(e) => setAddBggId(e.target.value)}
                    placeholder="e.g., 174430 or a boardgamegeek.com/boardgame/... URL"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Find BGG ID at <a href="https://boardgamegeek.com" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">boardgamegeek.com</a> — paste the ID or the full game URL
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Priority Rank (optional)
                  </label>
                  <input
                    type="number"
                    value={addFormData.rank}
                    onChange={(e) => setAddFormData({ ...addFormData, rank: e.target.value })}
                    placeholder="1 = highest priority"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                    min="1"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Notes (optional)
                  </label>
                  <textarea
                    value={addFormData.notes}
                    onChange={(e) => setAddFormData({ ...addFormData, notes: e.target.value })}
                    placeholder="Why this game is worth adding"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                    rows={3}
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 mt-6">
                <button
                  onClick={() => {
                    setShowAddModal(false);
                    setAddBggId("");
                    setAddFormData({ rank: "", notes: "" });
                  }}
                  className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAddGameByBggId}
                  disabled={!addBggId.trim()}
                  className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Add to List
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Bulk Import CSV Modal */}
      {showBulkImportModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full">
            <div className="p-6">
              <h3 className="text-lg font-semibold mb-4">Bulk Import Games to Add from CSV</h3>
              <p className="text-sm text-gray-600 mb-4">
                Upload a CSV file with the following columns to add multiple candidate games:
              </p>

              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-4">
                <h4 className="font-semibold text-sm mb-2">CSV Format:</h4>
                <ul className="text-xs text-gray-700 space-y-1 list-disc list-inside">
                  <li><strong>bgg_id</strong> (required) - BoardGameGeek ID</li>
                  <li><strong>rank</strong> (optional) - Priority rank (numeric)</li>
                  <li><strong>notes</strong> (optional) - Curation notes</li>
                </ul>
                <div className="mt-3 text-xs text-gray-600">
                  <strong>Example CSV:</strong>
                  <pre className="bg-white p-2 rounded border mt-1 overflow-x-auto">
bgg_id,rank,notes
174430,1,Fills the Core Strategy gap
167791,2,Good for large groups</pre>
                </div>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select CSV File
                </label>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv"
                  onChange={handleBulkImportCSV}
                  className="block w-full text-sm text-gray-500
                    file:mr-4 file:py-2 file:px-4
                    file:rounded-lg file:border-0
                    file:text-sm file:font-semibold
                    file:bg-indigo-50 file:text-indigo-700
                    hover:file:bg-indigo-100
                    cursor-pointer"
                />
              </div>

              <p className="text-xs text-gray-500 mb-4">
                <strong>Note:</strong> Games not in your database will be automatically imported from BoardGameGeek.
                Existing entries will be updated with new values from the CSV.
              </p>

              <div className="flex justify-end">
                <button
                  onClick={() => setShowBulkImportModal(false)}
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
