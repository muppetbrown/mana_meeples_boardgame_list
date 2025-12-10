// src/components/staff/tabs/AddGamesTab.jsx
import React from "react";
import { useStaff } from "../../../context/StaffContext";
import { ManualGameEntryPanel } from "../ManualGameEntryPanel";
import { BulkImportPanel } from "../BulkPanels";

/**
 * Add Games tab - All methods for adding new games to the library
 */
export function AddGamesTab() {
  const {
    bggIdInput,
    setBggIdInput,
    handleAddGame,
    csvImportText,
    setCsvImportText,
    doBulkImport,
    showToast,
  } = useStaff();

  return (
    <div className="space-y-6">
      {/* Add by BGG ID - Primary Method */}
      <div className="bg-white rounded-2xl p-6 shadow">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-xl font-semibold mb-2">Add Game by BGG ID</h2>
            <p className="text-sm text-gray-600">
              <strong>Recommended method:</strong> Automatically imports complete game data from BoardGameGeek
            </p>
          </div>
          <span className="px-3 py-1 bg-purple-100 text-purple-700 text-xs font-semibold rounded-full">
            Primary Method
          </span>
        </div>

        <div className="bg-purple-50 rounded-lg p-4 mb-4 border border-purple-100">
          <div className="flex items-start gap-3">
            <span className="text-2xl">💡</span>
            <div className="text-sm text-purple-900">
              <strong className="block mb-1">How to find BGG IDs:</strong>
              <ol className="list-decimal list-inside space-y-1">
                <li>Visit <a href="https://boardgamegeek.com" target="_blank" rel="noopener noreferrer" className="underline">boardgamegeek.com</a></li>
                <li>Search for your game</li>
                <li>Look at the URL: <code className="bg-white px-2 py-0.5 rounded">/boardgame/<strong>30549</strong>/pandemic</code></li>
                <li>The number (30549) is the BGG ID</li>
              </ol>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 items-center">
          <input
            className="flex-1 min-w-[280px] border-2 border-gray-300 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 rounded-lg px-4 py-3 text-base outline-none transition-all"
            placeholder="Enter BoardGameGeek ID (e.g., 30549 for Pandemic)"
            value={bggIdInput}
            onChange={(e) => setBggIdInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAddGame()}
          />
          <button
            className="px-6 py-3 rounded-lg bg-purple-600 text-white font-medium hover:bg-purple-700 transition-colors shadow-sm"
            onClick={handleAddGame}
          >
            Add Game
          </button>
        </div>

        <div className="mt-4 p-3 bg-gray-50 rounded-lg border border-gray-200">
          <div className="text-xs text-gray-600 font-medium mb-1">⚡ Features:</div>
          <ul className="text-xs text-gray-600 space-y-1">
            <li>✓ Automatic retry with exponential backoff (up to 4 retries)</li>
            <li>✓ Fetches all game data: title, designers, mechanics, ratings, complexity, images</li>
            <li>✓ Handles BGG API rate limiting gracefully</li>
          </ul>
        </div>
      </div>

      {/* Bulk Import */}
      <div className="bg-white rounded-2xl p-6 shadow">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-xl font-semibold mb-2">Bulk Import from CSV</h2>
            <p className="text-sm text-gray-600">
              Import multiple games at once using BoardGameGeek IDs
            </p>
          </div>
        </div>

        <BulkImportPanel
          value={csvImportText}
          onChange={setCsvImportText}
          onSubmit={doBulkImport}
        />

        <div className="mt-4 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
          <div className="flex items-start gap-2">
            <span className="text-lg">⚠️</span>
            <div className="text-xs text-yellow-800">
              <strong>Note:</strong> Bulk imports can take several minutes depending on the number of games and BGG API response times. Each game is imported individually with full data.
            </div>
          </div>
        </div>
      </div>

      {/* Manual Entry - Fallback Method */}
      <div className="bg-white rounded-2xl p-6 shadow border-2 border-dashed border-gray-300">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-xl font-semibold mb-2">Manual Game Entry</h2>
            <p className="text-sm text-gray-600">
              <strong>Use only when BGG import is unavailable:</strong> Manually enter game data
            </p>
          </div>
          <span className="px-3 py-1 bg-gray-100 text-gray-600 text-xs font-semibold rounded-full">
            Fallback Method
          </span>
        </div>

        <ManualGameEntryPanel
          onSuccess={() => window.location.reload()}
          onToast={showToast}
        />
      </div>
    </div>
  );
}
