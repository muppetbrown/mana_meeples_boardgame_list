// src/components/staff/tabs/CategoriesTab.jsx
import React, { useState, useMemo } from "react";
import { useStaff } from "../../../context/StaffContext";
import { BulkCategorizePanel } from "../BulkPanels";
import { CATEGORY_KEYS, CATEGORY_LABELS } from "../../../constants/categories";
import { bulkUpdateNZDesigners } from "../../../api/client";

/**
 * Categories tab - Manage game categorization and NZ designer flags
 */
export function CategoriesTab() {
  const {
    library,
    counts,
    csvCategorizeText,
    setCsvCategorizeText,
    doBulkCategorize,
    openEditCategory,
    showToast,
    loadLibrary,
  } = useStaff();

  const [nzDesignersText, setNzDesignersText] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // Get uncategorized games
  const uncategorizedGames = useMemo(() => {
    return library.filter((g) => !g.mana_meeple_category);
  }, [library]);

  // Get games by category
  const gamesByCategory = useMemo(() => {
    const result = {};
    CATEGORY_KEYS.forEach((key) => {
      result[key] = library.filter((g) => g.mana_meeple_category === key);
    });
    return result;
  }, [library]);

  // Handle NZ Designer bulk update
  const handleBulkNZDesigners = async () => {
    if (!nzDesignersText.trim()) {
      showToast("Please enter CSV data", "error");
      return;
    }

    setIsLoading(true);
    try {
      const result = await bulkUpdateNZDesigners(nzDesignersText);
      const msg = `Updated: ${result.updated?.length || 0}, Not found: ${result.not_found?.length || 0}, Errors: ${result.errors?.length || 0}`;
      showToast(msg, "success");

      // Download log file
      const ts = new Date().toISOString().replace(/[:.]/g, "-");
      const log = [
        "Updated:",
        ...(result.updated || []),
        "",
        "Not found:",
        ...(result.not_found || []),
        "",
        "Errors:",
        ...(result.errors || []),
        "",
      ].join("\n");

      const blob = new Blob([log], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `nz-designers-${ts}.log.txt`;
      a.click();
      URL.revokeObjectURL(url);

      setNzDesignersText("");
      await loadLibrary();
    } catch (error) {
      showToast("Bulk NZ designers update failed", "error");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Category Overview */}
      <div className="bg-white rounded-2xl p-6 shadow">
        <h2 className="text-xl font-semibold mb-4">Category Overview</h2>
        <div className="grid md:grid-cols-3 gap-4">
          {CATEGORY_KEYS.map((key) => (
            <div
              key={key}
              className="p-4 rounded-lg border-2 border-gray-200 hover:border-purple-300 transition-colors"
            >
              <div className="text-sm font-medium text-gray-700 mb-1">
                {CATEGORY_LABELS[key]}
              </div>
              <div className="text-3xl font-bold text-purple-700">
                {counts[key] || 0}
              </div>
              <div className="text-xs text-gray-500 mt-1">games</div>
            </div>
          ))}
        </div>

        {uncategorizedGames.length > 0 && (
          <div className="mt-4 p-4 bg-orange-50 rounded-lg border border-orange-200">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-semibold text-orange-800 mb-1">
                  ⚠️ {uncategorizedGames.length} Uncategorized Games
                </div>
                <div className="text-sm text-orange-700">
                  These games need to be assigned to a category
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Quick Categorize - Uncategorized Games */}
      {uncategorizedGames.length > 0 && (
        <div className="bg-white rounded-2xl p-6 shadow">
          <h2 className="text-xl font-semibold mb-4">Quick Categorize</h2>
          <p className="text-sm text-gray-600 mb-4">
            Click on any game below to assign it to a category
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 max-h-96 overflow-y-auto">
            {uncategorizedGames.map((game) => (
              <button
                key={game.id}
                onClick={() => openEditCategory(game)}
                className="p-3 text-left rounded-lg border border-gray-300 hover:border-purple-400 hover:bg-purple-50 transition-colors"
              >
                <div className="font-medium text-gray-900 truncate">{game.title}</div>
                <div className="text-xs text-gray-600 mt-1">
                  {game.year && `${game.year} · `}
                  {game.players_min && game.players_max && `${game.players_min}-${game.players_max} players`}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Bulk Categorize */}
      <div className="bg-white rounded-2xl p-6 shadow">
        <h2 className="text-xl font-semibold mb-4">Bulk Categorize from CSV</h2>
        <p className="text-sm text-gray-600 mb-4">
          Update multiple game categories at once using a CSV file
        </p>
        <BulkCategorizePanel
          value={csvCategorizeText}
          onChange={setCsvCategorizeText}
          onSubmit={doBulkCategorize}
        />
      </div>

      {/* NZ Designer Management */}
      <div className="bg-white rounded-2xl p-6 shadow border-2 border-green-200">
        <div className="flex items-start gap-3 mb-4">
          <span className="text-2xl">🇳🇿</span>
          <div>
            <h2 className="text-xl font-semibold">New Zealand Designer Management</h2>
            <p className="text-sm text-gray-600 mt-1">
              Flag games by New Zealand designers for special highlighting in the public catalogue
            </p>
          </div>
        </div>

        <div className="mb-4 p-3 bg-green-50 rounded-lg border border-green-200">
          <div className="text-sm text-green-800">
            <strong>CSV format:</strong> <code className="bg-white px-2 py-0.5 rounded">bgg_id,nz_designer</code>
          </div>
          <div className="text-xs text-green-700 mt-2">
            Example: <code className="bg-white px-2 py-0.5 rounded">12345,true</code> or <code className="bg-white px-2 py-0.5 rounded">67890,1</code>
          </div>
        </div>

        <textarea
          className="w-full h-32 border-2 border-gray-300 focus:border-green-500 focus:ring-2 focus:ring-green-200 rounded-lg p-3 font-mono text-sm mb-3 outline-none transition-all"
          placeholder="12345,true&#10;67890,false&#10;11111,1"
          value={nzDesignersText}
          onChange={(e) => setNzDesignersText(e.target.value)}
          disabled={isLoading}
        />

        <button
          className={`px-6 py-2.5 rounded-lg text-white font-medium transition-colors ${
            isLoading || !nzDesignersText.trim()
              ? "bg-gray-400 cursor-not-allowed"
              : "bg-green-600 hover:bg-green-700"
          }`}
          onClick={handleBulkNZDesigners}
          disabled={isLoading || !nzDesignersText.trim()}
        >
          {isLoading ? "Updating..." : "Update NZ Designer Flags"}
        </button>

        <div className="mt-3 text-xs text-gray-600">
          <strong>Note:</strong> A log file will be downloaded after the update completes showing which games were updated, not found, or had errors.
        </div>
      </div>

      {/* Category Distribution Visualization */}
      <div className="bg-linear-to-r from-purple-50 to-blue-50 rounded-2xl p-6 border border-purple-100">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">📊 Category Distribution</h3>
        <div className="space-y-2">
          {CATEGORY_KEYS.map((key) => {
            const count = counts[key] || 0;
            const percentage = counts.all > 0 ? (count / counts.all) * 100 : 0;
            return (
              <div key={key} className="flex items-center gap-3">
                <div className="w-40 text-sm text-gray-700 font-medium">
                  {CATEGORY_LABELS[key]}
                </div>
                <div className="flex-1 bg-gray-200 rounded-full h-6 overflow-hidden">
                  <div
                    className="bg-purple-600 h-full flex items-center justify-end pr-2"
                    style={{ width: `${percentage}%` }}
                  >
                    {percentage > 10 && (
                      <span className="text-xs text-white font-medium">
                        {count} ({percentage.toFixed(0)}%)
                      </span>
                    )}
                  </div>
                </div>
                {percentage <= 10 && (
                  <div className="w-20 text-sm text-gray-600">
                    {count} ({percentage.toFixed(0)}%)
                  </div>
                )}
              </div>
            );
          })}
          {uncategorizedGames.length > 0 && (
            <div className="flex items-center gap-3 pt-2 border-t border-gray-300">
              <div className="w-40 text-sm text-orange-700 font-medium">Uncategorized</div>
              <div className="flex-1 bg-gray-200 rounded-full h-6 overflow-hidden">
                <div
                  className="bg-orange-500 h-full flex items-center justify-end pr-2"
                  style={{
                    width: `${counts.all > 0 ? (uncategorizedGames.length / counts.all) * 100 : 0}%`,
                  }}
                >
                  {uncategorizedGames.length / counts.all > 0.1 && (
                    <span className="text-xs text-white font-medium">
                      {uncategorizedGames.length} (
                      {((uncategorizedGames.length / counts.all) * 100).toFixed(0)}%)
                    </span>
                  )}
                </div>
              </div>
              {uncategorizedGames.length / counts.all <= 0.1 && (
                <div className="w-20 text-sm text-orange-700">
                  {uncategorizedGames.length} (
                  {((uncategorizedGames.length / counts.all) * 100).toFixed(0)}%)
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
