// src/components/staff/tabs/BuyListTab.jsx
import React, { useState, useEffect, useRef } from "react";
import { useConfirm, useStaff } from "../../../context/StaffContext";
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
  reorderBuyList,
  suggestBuyListGames,
  getHLStockSignals,
  linkHLStockSignal,
  dismissHLStockSignal,
  getTrendingGames,
  getAwardWinners,
} from "../../../api/client";
import { CATEGORY_LABELS } from "../../../constants/categories";
import { parseBggId } from "../../../utils/bgg";

const PLAYER_COUNT_LABELS = {
  "1": "1 player", "2": "2 players", "3": "3 players", "4": "4 players",
  "5": "5 players", "6": "6 players", "7": "7 players", "8": "8 players",
  "9+": "9+ players",
};

const COMPLEXITY_LABELS = {
  light: "Light (under 2.0)",
  medium: "Medium (2.0-3.0)",
  heavy: "Heavy (3.0+)",
};

const PLAYTIME_LABELS = {
  quick: "Quick (under 30 min)",
  standard: "Standard (30-60 min)",
  long: "Long (60-120 min)",
  epic: "Epic (120+ min)",
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
  const [reranking, setReranking] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [suggestLoading, setSuggestLoading] = useState(false);
  const [suggestError, setSuggestError] = useState(null);
  const [addingSuggestionId, setAddingSuggestionId] = useState(null);
  const [hlSignals, setHlSignals] = useState([]);
  const [hlLoading, setHlLoading] = useState(false);
  const [hlError, setHlError] = useState(null);
  const [hlActionId, setHlActionId] = useState(null);
  const [hlLinkInputs, setHlLinkInputs] = useState({});
  const [trending, setTrending] = useState([]);
  const [trendingLoading, setTrendingLoading] = useState(true);
  const [trendingError, setTrendingError] = useState(null);
  const [addingTrendingId, setAddingTrendingId] = useState(null);
  const [awardWinners, setAwardWinners] = useState([]);
  const [awardWinnersLoading, setAwardWinnersLoading] = useState(true);
  const [awardWinnersError, setAwardWinnersError] = useState(null);
  const [addingAwardWinnerKey, setAddingAwardWinnerKey] = useState(null);
  const fileInputRef = useRef(null);
  const confirm = useConfirm();
  const { library } = useStaff();

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
  useEffect(() => {
    loadTrending();
  }, []);
  useEffect(() => {
    loadAwardWinners();
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

  const loadTrending = async () => {
    setTrendingLoading(true);
    setTrendingError(null);
    try {
      const data = await getTrendingGames(20);
      setTrending(data.trending || []);
    } catch (err) {
      console.error("Failed to load trending games:", err);
      setTrendingError("Failed to load trending games from BoardGameGeek");
    } finally {
      setTrendingLoading(false);
    }
  };

  const handleAddTrending = async (game) => {
    setAddingTrendingId(game.bgg_id);
    try {
      setError(null);
      await addToBuyList({ bgg_id: game.bgg_id, notes: `Trending on BoardGameGeek (#${game.rank})` });
      setSuccess(`Added "${game.title}" to the list`);
      setTrending((prev) =>
        prev.map((g) => (g.bgg_id === game.bgg_id ? { ...g, status: "on_buy_list" } : g))
      );
      await loadBuyList();
    } catch (err) {
      console.error("Failed to add trending game:", err);
      setError(err.response?.data?.detail || "Failed to add trending game");
    } finally {
      setAddingTrendingId(null);
    }
  };

  const loadAwardWinners = async () => {
    setAwardWinnersLoading(true);
    setAwardWinnersError(null);
    try {
      const data = await getAwardWinners(6);
      setAwardWinners(data.award_winners || []);
    } catch (err) {
      console.error("Failed to load award winners:", err);
      setAwardWinnersError("Failed to load award winners");
    } finally {
      setAwardWinnersLoading(false);
    }
  };

  const handleAddAwardWinner = async (entry) => {
    const key = `${entry.award}-${entry.year}`;
    setAddingAwardWinnerKey(key);
    try {
      setError(null);
      await addToBuyList({
        bgg_id: entry.bgg_id,
        notes: `${entry.award_label} ${entry.year}`,
      });
      setSuccess(`Added "${entry.title}" to the list`);
      setAwardWinners((prev) =>
        prev.map((w) => (w.award === entry.award && w.year === entry.year ? { ...w, status: "on_buy_list" } : w))
      );
      await loadBuyList();
    } catch (err) {
      console.error("Failed to add award winner:", err);
      setError(err.response?.data?.detail || "Failed to add award winner");
    } finally {
      setAddingAwardWinnerKey(null);
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

  const handleReRank = async () => {
    if (buyList.length === 0) return;
    const ok = await confirm({
      title: `Re-rank ${buyList.length} game(s) from the current sort order?`,
      message:
        "Sets each game's priority rank (1, 2, 3, …) to match the order shown right now, overwriting existing ranks.",
      confirmLabel: "Re-rank",
    });
    if (!ok) return;

    setReranking(true);
    try {
      setError(null);
      const orderedIds = buyList.map((item) => item.id);
      const result = await reorderBuyList(orderedIds);
      setBuyList(result.items || []);
      setSortBy("rank");
      setSortDesc(false);
      setSuccess(`Re-ranked ${orderedIds.length} game(s)`);
    } catch (err) {
      console.error("Failed to re-rank:", err);
      setError(err.response?.data?.detail || "Failed to re-rank");
    } finally {
      setReranking(false);
    }
  };

  const handleSuggestGames = async () => {
    setSuggestLoading(true);
    setSuggestError(null);
    try {
      const data = await suggestBuyListGames(6);
      const results = data.suggestions || [];
      setSuggestions(results);
      if (results.length === 0) {
        setSuggestError("Claude didn't return any suggestions. Try again in a moment.");
      }
    } catch (err) {
      console.error("Failed to get suggestions:", err);
      setSuggestError(err.response?.data?.detail || "Failed to get suggestions");
    } finally {
      setSuggestLoading(false);
    }
  };

  const dismissSuggestion = (suggestion) => {
    setSuggestions((prev) => prev.filter((s) => s !== suggestion));
  };

  const handleAddSuggestion = async (suggestion) => {
    if (!suggestion.suggested_bgg_id) return;
    setAddingSuggestionId(suggestion.suggested_bgg_id);
    try {
      setError(null);
      await addToBuyList({ bgg_id: suggestion.suggested_bgg_id, notes: suggestion.reason });
      setSuccess(`Added "${suggestion.title}" to the list`);
      dismissSuggestion(suggestion);
      await loadBuyList();
    } catch (err) {
      console.error("Failed to add suggested game:", err);
      setError(err.response?.data?.detail || "Failed to add suggested game");
    } finally {
      setAddingSuggestionId(null);
    }
  };

  // No confident BGG match was resolved server-side - open the manual Add
  // Game modal pre-filled with Claude's reasoning so staff can paste in the
  // ID they find via "Search on BGG".
  const handleAddSuggestionManually = (suggestion) => {
    setAddBggId("");
    setAddFormData({ rank: "", notes: suggestion.reason });
    setShowAddModal(true);
  };

  const loadHLStockSignals = async () => {
    setHlLoading(true);
    setHlError(null);
    try {
      const data = await getHLStockSignals();
      setHlSignals(data.items || []);
    } catch (err) {
      console.error("Failed to load HL stock signals:", err);
      setHlError(err.response?.data?.detail || "Failed to check HL Timaru stock");
    } finally {
      setHlLoading(false);
    }
  };

  const handleAddHLSignal = async (item) => {
    const note = `Selling well at HL Timaru (${item.units_sold ?? 0} sold, ${item.current_stock ?? 0} in stock)`;

    // Already fuzzy-matched to a game with a known BGG ID - add directly
    if (item.linked_game?.bgg_id) {
      setHlActionId(item.hl_internal_id);
      try {
        setError(null);
        await addToBuyList({ bgg_id: item.linked_game.bgg_id, notes: note });
        setSuccess(`Added "${item.linked_game.title}" to the list`);
        setHlSignals((prev) => prev.filter((s) => s.hl_internal_id !== item.hl_internal_id));
        await loadBuyList();
      } catch (err) {
        console.error("Failed to add HL stock signal to buy list:", err);
        setError(err.response?.data?.detail || "Failed to add game");
      } finally {
        setHlActionId(null);
      }
      return;
    }

    // No confident match - open the manual Add Game modal pre-filled, same
    // pattern as an unresolved AI suggestion.
    setAddBggId("");
    setAddFormData({ rank: "", notes: note });
    setShowAddModal(true);
  };

  const handleConfirmHLSignalMatch = async (item) => {
    if (!item.linked_game) return;
    setHlActionId(item.hl_internal_id);
    try {
      setHlError(null);
      await linkHLStockSignal(item.hl_internal_id, item.linked_game.id);
      setHlSignals((prev) =>
        prev.map((s) =>
          s.hl_internal_id === item.hl_internal_id ? { ...s, match_confidence: null } : s
        )
      );
    } catch (err) {
      console.error("Failed to confirm HL stock signal match:", err);
      setHlError(err.response?.data?.detail || "Failed to confirm match");
    } finally {
      setHlActionId(null);
    }
  };

  // Client-side title search over the already-loaded library (any status -
  // the fuzzy matcher itself isn't limited to owned games either), same
  // pattern GameEditModal uses for its base-game picker.
  const getLibraryMatchesForQuery = (query) => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return library.filter((g) => g.title?.toLowerCase().includes(q)).slice(0, 6);
  };

  const handleManualLinkHLSignal = async (item, game) => {
    setHlActionId(item.hl_internal_id);
    try {
      setHlError(null);
      await linkHLStockSignal(item.hl_internal_id, game.id);
      setHlSignals((prev) => prev.filter((s) => s.hl_internal_id !== item.hl_internal_id));
      setHlLinkInputs((prev) => {
        const next = { ...prev };
        delete next[item.hl_internal_id];
        return next;
      });
      setSuccess(`Linked "${item.hl_product_name}" to "${game.title}"`);
    } catch (err) {
      console.error("Failed to link HL stock signal:", err);
      setHlError(err.response?.data?.detail || "Failed to link");
    } finally {
      setHlActionId(null);
    }
  };

  const handleDismissHLSignal = async (item) => {
    setHlActionId(item.hl_internal_id);
    try {
      setHlError(null);
      await dismissHLStockSignal(item.hl_internal_id);
      setHlSignals((prev) => prev.filter((s) => s.hl_internal_id !== item.hl_internal_id));
    } catch (err) {
      console.error("Failed to dismiss HL stock signal:", err);
      setHlError(err.response?.data?.detail || "Failed to dismiss");
    } finally {
      setHlActionId(null);
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
  const gapComplexityBands = (gaps?.complexity_gaps || []).filter((g) => g.is_gap);
  const gapPlaytimeBands = (gaps?.playtime_gaps || []).filter((g) => g.is_gap);
  const hasAnyGaps =
    gapCategories.length > 0 || gapPlayerCounts.length > 0 || gapComplexityBands.length > 0 || gapPlaytimeBands.length > 0;

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
    if (gapMatch.complexity_is_gap) {
      badges.push(
        <span key="complexity" className="px-2 py-0.5 text-xs font-medium rounded-full bg-purple-100 text-purple-700">
          Fills complexity gap
        </span>
      );
    }
    if (gapMatch.playtime_is_gap) {
      badges.push(
        <span key="playtime" className="px-2 py-0.5 text-xs font-medium rounded-full bg-orange-100 text-orange-700">
          Fills playtime gap
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
        ) : !hasAnyGaps ? (
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
            {gapComplexityBands.length > 0 && (
              <div>
                <div className="text-sm font-medium text-gray-700 mb-2">Thin complexity coverage</div>
                <div className="flex flex-wrap gap-2">
                  {gapComplexityBands.map((g) => (
                    <span key={g.complexity_band} className="px-3 py-1 text-xs font-medium rounded-full bg-amber-100 text-amber-800">
                      {COMPLEXITY_LABELS[g.complexity_band] || g.complexity_band} ({g.pct_of_collection}%)
                    </span>
                  ))}
                </div>
              </div>
            )}
            {gapPlaytimeBands.length > 0 && (
              <div>
                <div className="text-sm font-medium text-gray-700 mb-2">Thin playtime coverage</div>
                <div className="flex flex-wrap gap-2">
                  {gapPlaytimeBands.map((g) => (
                    <span key={g.playtime_band} className="px-3 py-1 text-xs font-medium rounded-full bg-amber-100 text-amber-800">
                      {PLAYTIME_LABELS[g.playtime_band] || g.playtime_band} ({g.pct_of_collection}%)
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* AI-suggested additions */}
      <div className="bg-white rounded-2xl p-6 shadow">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
          <div>
            <h3 className="text-lg font-semibold">Suggest Additional Games</h3>
            <p className="text-sm text-gray-600 mt-1">
              Asks Claude for games worth adding, grounded in what's owned and where the collection is thin.
            </p>
          </div>
          <button
            onClick={handleSuggestGames}
            disabled={suggestLoading}
            className="px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
          >
            {suggestLoading ? "Thinking…" : suggestions.length > 0 ? "💡 Suggest More" : "💡 Suggest Additional Games"}
          </button>
        </div>

        {suggestError && (
          <div role="alert" className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {suggestError}
          </div>
        )}

        {suggestions.length > 0 && (
          <div className="grid md:grid-cols-2 gap-3">
            {suggestions.map((s) => {
              const resolved = Boolean(s.suggested_bgg_id);
              const bggUrl = resolved
                ? `https://boardgamegeek.com/boardgame/${s.suggested_bgg_id}`
                : s.bgg_search_url;
              const adding = addingSuggestionId === s.suggested_bgg_id && resolved;
              return (
                <div key={`${s.title}-${s.year ?? ""}`} className="border rounded-lg p-4 relative">
                  <button
                    onClick={() => dismissSuggestion(s)}
                    aria-label={`Dismiss suggestion: ${s.title}`}
                    className="absolute top-2 right-2 text-gray-400 hover:text-gray-600 text-sm"
                  >
                    ✕
                  </button>
                  <div className="pr-5">
                    <div className="font-semibold">
                      {s.title}
                      {s.year ? ` (${s.year})` : ""}
                    </div>
                    {s.category_key && (
                      <span className="inline-block mt-1 px-2 py-0.5 text-xs font-medium rounded-full bg-purple-100 text-purple-700">
                        {CATEGORY_LABELS[s.category_key] || s.category_key}
                      </span>
                    )}
                    <p className="text-sm text-gray-600 mt-2">{s.reason}</p>
                    <p className="text-xs mt-2">
                      {resolved ? (
                        <span className="text-green-700">
                          Matched: {s.suggested_bgg_title} {s.suggested_bgg_year ? `(${s.suggested_bgg_year})` : ""} · BGG #{s.suggested_bgg_id}
                        </span>
                      ) : (
                        <span className="text-amber-700">No confident BGG match — search below, then add manually</span>
                      )}
                    </p>
                  </div>
                  <div className="flex gap-2 mt-3">
                    <a
                      href={bggUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-300 hover:bg-gray-50"
                    >
                      🔍 Search on BGG
                    </a>
                    {resolved ? (
                      <button
                        onClick={() => handleAddSuggestion(s)}
                        disabled={adding}
                        className="px-3 py-1.5 text-xs font-medium rounded-lg bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {adding ? "Adding…" : "+ Add to List"}
                      </button>
                    ) : (
                      <button
                        onClick={() => handleAddSuggestionManually(s)}
                        className="px-3 py-1.5 text-xs font-medium rounded-lg bg-purple-100 text-purple-700 hover:bg-purple-200"
                      >
                        + Add Manually
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* HL Timaru stock signals */}
      <div className="bg-white rounded-2xl p-6 shadow">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
          <div>
            <h3 className="text-lg font-semibold">Selling Well at HL Timaru</h3>
            <p className="text-sm text-gray-600 mt-1">
              Board games selling or in stock at the HL Timaru store that aren't yet owned or on this list.
            </p>
          </div>
          <button
            onClick={loadHLStockSignals}
            disabled={hlLoading}
            className="px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
          >
            {hlLoading ? "Checking…" : hlSignals.length > 0 ? "🔄 Refresh" : "🔄 Check HL Stock"}
          </button>
        </div>

        {hlError && (
          <div role="alert" className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {hlError}
          </div>
        )}

        {!hlLoading && hlSignals.length === 0 && !hlError && (
          <p className="text-sm text-gray-500">
            Click "Check HL Stock" to pull current sales/stock data from the HL Timaru retail database.
          </p>
        )}

        {hlSignals.length > 0 && (
          <div className="grid md:grid-cols-2 gap-3">
            {hlSignals.map((item) => {
              const acting = hlActionId === item.hl_internal_id;
              const matched = item.match_status === "linked" && item.linked_game;
              const bggSearchUrl = `https://boardgamegeek.com/geeksearch.php?action=search&objecttype=boardgame&q=${encodeURIComponent(item.hl_product_name)}`;
              const libraryMatches = getLibraryMatchesForQuery(hlLinkInputs[item.hl_internal_id] || "");
              return (
                <div key={item.hl_internal_id} className="border rounded-lg p-4">
                  <div>
                    <div className="font-semibold">{item.hl_product_name}</div>
                    <p className="text-sm text-gray-600 mt-1">
                      {item.units_sold ?? 0} sold · {item.current_stock ?? 0} in stock
                      {item.last_sale_date ? ` · last sale ${item.last_sale_date}` : ""}
                    </p>
                    <p className="text-xs mt-2">
                      {matched ? (
                        <span className="text-green-700">
                          Matches: {item.linked_game.title}
                          {item.match_confidence != null ? ` (${Math.round(item.match_confidence)}% match - unconfirmed)` : " (confirmed)"}
                        </span>
                      ) : (
                        <span className="text-amber-700">No match found in this library</span>
                      )}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2 mt-3">
                    {matched && item.match_confidence != null && (
                      <button
                        onClick={() => handleConfirmHLSignalMatch(item)}
                        disabled={acting}
                        className="px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 disabled:opacity-50"
                      >
                        ✓ Confirm match
                      </button>
                    )}
                    <button
                      onClick={() => handleAddHLSignal(item)}
                      disabled={acting}
                      className="px-3 py-1.5 text-xs font-medium rounded-lg bg-cyan-600 text-white hover:bg-cyan-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {acting ? "Working…" : "+ Add to List"}
                    </button>
                    {!matched && (
                      <a
                        href={bggSearchUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-300 hover:bg-gray-50"
                      >
                        🔍 Search on BGG
                      </a>
                    )}
                    <button
                      onClick={() => handleDismissHLSignal(item)}
                      disabled={acting}
                      className="px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-50 disabled:opacity-50"
                    >
                      Not suitable for library
                    </button>
                  </div>
                  {!matched && (
                    <div className="mt-2">
                      <input
                        type="text"
                        value={hlLinkInputs[item.hl_internal_id] || ""}
                        onChange={(e) =>
                          setHlLinkInputs((prev) => ({ ...prev, [item.hl_internal_id]: e.target.value }))
                        }
                        placeholder="Search library by title (if the matcher missed it)"
                        className="w-full px-2 py-1 text-xs border border-gray-300 rounded"
                      />
                      {(hlLinkInputs[item.hl_internal_id] || "").trim() && (
                        <div className="mt-1 border border-gray-200 rounded-lg bg-white shadow-sm max-h-40 overflow-y-auto">
                          {libraryMatches.length === 0 ? (
                            <p className="px-2 py-1.5 text-xs text-gray-500">No matching games</p>
                          ) : (
                            libraryMatches.map((g) => (
                              <button
                                key={g.id}
                                type="button"
                                onClick={() => handleManualLinkHLSignal(item, g)}
                                disabled={acting}
                                className="block w-full text-left px-2 py-1.5 text-xs hover:bg-gray-50 disabled:opacity-50 border-b last:border-b-0 border-gray-100"
                              >
                                {g.title}
                                {g.year ? ` (${g.year})` : ""}
                              </button>
                            ))
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Trending on BoardGameGeek */}
      <div className="bg-white rounded-2xl p-6 shadow">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
          <div>
            <h3 className="text-lg font-semibold">🔥 Trending on BoardGameGeek</h3>
            <p className="text-sm text-gray-600 mt-1">
              BGG's current Hotness list — recent community activity, not a recommendation specific to this library
            </p>
          </div>
          <button
            onClick={loadTrending}
            disabled={trendingLoading}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {trendingLoading ? "Loading…" : "↻ Refresh"}
          </button>
        </div>

        {trendingError && (
          <div role="alert" className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {trendingError}
          </div>
        )}

        {trendingLoading && trending.length === 0 ? (
          <p className="text-sm text-gray-500">Loading trending games…</p>
        ) : trending.length === 0 && !trendingError ? (
          <p className="text-sm text-gray-500">No trending data available right now.</p>
        ) : (
          <div className="overflow-x-auto">
            <div className="flex gap-3 pb-1" style={{ width: "max-content" }}>
              {trending.map((game) => {
                const adding = addingTrendingId === game.bgg_id;
                return (
                  <div key={game.bgg_id} className="w-40 shrink-0 border rounded-lg p-3">
                    <div className="flex items-start justify-between gap-1 mb-1">
                      <span className="text-xs font-semibold text-gray-400">#{game.rank}</span>
                      {game.status === "owned" && (
                        <span className="px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-green-100 text-green-700">
                          Owned
                        </span>
                      )}
                      {game.status === "on_buy_list" && (
                        <span className="px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-blue-100 text-blue-700">
                          On list
                        </span>
                      )}
                    </div>
                    <Thumbnail src={game.thumbnail_url} alt={game.title} />
                    <div className="text-sm font-medium mt-2 line-clamp-2" title={game.title}>
                      {game.title}
                    </div>
                    {game.year && <div className="text-xs text-gray-500">{game.year}</div>}
                    <div className="mt-2 flex gap-1">
                      <a
                        href={`https://boardgamegeek.com/boardgame/${game.bgg_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex-1 px-2 py-1 text-xs text-center rounded border border-gray-300 hover:bg-gray-50"
                      >
                        View
                      </a>
                      {game.status === "new" && (
                        <button
                          onClick={() => handleAddTrending(game)}
                          disabled={adding}
                          className="flex-1 px-2 py-1 text-xs rounded bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {adding ? "…" : "+ Add"}
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Award Winners */}
      <div className="bg-white rounded-2xl p-6 shadow">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
          <div>
            <h3 className="text-lg font-semibold">🏆 Award Winners</h3>
            <p className="text-sm text-gray-600 mt-1">
              Recent Spiel des Jahres, Kennerspiel des Jahres, and Kinderspiel des Jahres winners
            </p>
          </div>
          <button
            onClick={loadAwardWinners}
            disabled={awardWinnersLoading}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {awardWinnersLoading ? "Loading…" : "↻ Refresh"}
          </button>
        </div>

        {awardWinnersError && (
          <div role="alert" className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {awardWinnersError}
          </div>
        )}

        {awardWinnersLoading && awardWinners.length === 0 ? (
          <p className="text-sm text-gray-500">Loading award winners…</p>
        ) : awardWinners.length === 0 && !awardWinnersError ? (
          <p className="text-sm text-gray-500">No award winner data available right now.</p>
        ) : (
          <div className="overflow-x-auto">
            <div className="flex gap-3 pb-1" style={{ width: "max-content" }}>
              {awardWinners.map((entry) => {
                const key = `${entry.award}-${entry.year}`;
                const adding = addingAwardWinnerKey === key;
                return (
                  <div key={key} className="w-40 shrink-0 border rounded-lg p-3">
                    <div className="flex items-start justify-between gap-1 mb-1">
                      <span className="text-xs font-semibold text-gray-400">
                        {entry.award_label} {entry.year}
                      </span>
                      {entry.status === "owned" && (
                        <span className="px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-green-100 text-green-700">
                          Owned
                        </span>
                      )}
                      {entry.status === "on_buy_list" && (
                        <span className="px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-blue-100 text-blue-700">
                          On list
                        </span>
                      )}
                    </div>
                    <Thumbnail src={entry.thumbnail_url} alt={entry.title} />
                    <div className="text-sm font-medium mt-2 line-clamp-2" title={entry.title}>
                      {entry.title}
                    </div>
                    <div className="mt-2 flex gap-1">
                      <a
                        href={
                          entry.bgg_id
                            ? `https://boardgamegeek.com/boardgame/${entry.bgg_id}`
                            : entry.bgg_search_url
                        }
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex-1 px-2 py-1 text-xs text-center rounded border border-gray-300 hover:bg-gray-50"
                      >
                        {entry.bgg_id ? "View" : "Search BGG"}
                      </a>
                      {entry.status === "new" && entry.bgg_id && (
                        <button
                          onClick={() => handleAddAwardWinner(entry)}
                          disabled={adding}
                          className="flex-1 px-2 py-1 text-xs rounded bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {adding ? "…" : "+ Add"}
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
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
              onChange={(e) => {
                const next = e.target.value;
                setSortBy(next);
                // Most-gaps-filled first is almost always what you want here
                if (next === "gaps_filled") setSortDesc(true);
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            >
              <option value="rank">Rank</option>
              <option value="title">Title</option>
              <option value="updated_at">Last Updated</option>
              <option value="gaps_filled">Gaps Filled</option>
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
          <div className="flex items-end">
            <button
              onClick={handleReRank}
              disabled={reranking || buyList.length === 0}
              title="Set each game's priority rank to match the order shown right now"
              className="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
            >
              {reranking ? "Re-ranking…" : "🔢 Re-rank from this order"}
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
