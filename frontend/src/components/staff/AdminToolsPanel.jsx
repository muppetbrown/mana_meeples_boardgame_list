import React, { useState, useCallback } from "react";
import { bulkUpdateNZDesigners, reimportAllGames, fetchAllSleeveData, fixDatabaseSequence, getDebugCategories, getDebugDatabaseInfo, getDebugPerformance, exportGamesCSV, getHealthCheck, getDbHealthCheck } from "../../api/client";

export function AdminToolsPanel({ onToast, onLibraryReload }) {
  const [nzDesignersText, setNzDesignersText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [debugData, setDebugData] = useState(null);
  const [debugType, setDebugType] = useState("");

  const downloadText = useCallback((name, text) => {
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.click();
    URL.revokeObjectURL(url);
  }, []);

  const handleBulkNZDesigners = useCallback(async () => {
    if (!nzDesignersText.trim()) {
      onToast("Please enter CSV data", "error");
      return;
    }

    setIsLoading(true);
    try {
      const result = await bulkUpdateNZDesigners(nzDesignersText);
      const msg = `Updated: ${result.updated?.length || 0}, Not found: ${result.not_found?.length || 0}, Errors: ${result.errors?.length || 0}`;
      onToast(msg, "success");

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
      downloadText(`nz-designers-${ts}.log.txt`, log);

      setNzDesignersText("");
      if (onLibraryReload) await onLibraryReload();
    } catch (error) {
      onToast("Bulk NZ designers update failed", "error");
    } finally {
      setIsLoading(false);
    }
  }, [nzDesignersText, onToast, onLibraryReload, downloadText]);

  const handleReimportAll = useCallback(async () => {
    if (!window.confirm("This will re-import ALL games from BGG and may take several minutes. Continue?")) {
      return;
    }

    setIsLoading(true);
    onToast("Re-importing all games... This may take several minutes", "info", 5000);

    try {
      const result = await reimportAllGames();
      onToast(`Re-import complete! Updated: ${result.updated || 0}, Errors: ${result.errors || 0}`, "success");
      if (onLibraryReload) await onLibraryReload();
    } catch (error) {
      onToast("Re-import failed", "error");
    } finally {
      setIsLoading(false);
    }
  }, [onToast, onLibraryReload]);

  const handleFetchSleeveData = useCallback(async () => {
    if (!window.confirm("This will fetch sleeve data for ALL games using web scraping and may take several minutes. Continue?")) {
      return;
    }

    setIsLoading(true);
    onToast("Fetching sleeve data for all games... This may take several minutes", "info", 5000);

    try {
      const result = await fetchAllSleeveData();
      onToast(`Sleeve data fetch started! Processing ${result.total_games || 0} games in background`, "success");
      if (onLibraryReload) await onLibraryReload();
    } catch (error) {
      onToast("Failed to start sleeve data fetch", "error");
    } finally {
      setIsLoading(false);
    }
  }, [onToast, onLibraryReload]);

  const handleFixSequence = useCallback(async () => {
    if (!window.confirm("This will reset the database ID sequence. This is safe and fixes 'duplicate key' errors. Continue?")) {
      return;
    }

    setIsLoading(true);
    try {
      const result = await fixDatabaseSequence();
      onToast(`Sequence fixed! Next ID will be: ${result.next_id}`, "success");
    } catch (error) {
      onToast("Failed to fix sequence", "error");
    } finally {
      setIsLoading(false);
    }
  }, [onToast]);

  const handleDebugInfo = useCallback(async (type) => {
    setIsLoading(true);
    setDebugType(type);

    try {
      let data;
      switch (type) {
        case "categories":
          data = await getDebugCategories();
          break;
        case "database":
          data = await getDebugDatabaseInfo(100);
          break;
        case "performance":
          data = await getDebugPerformance();
          break;
        case "health":
          const health = await getHealthCheck();
          const dbHealth = await getDbHealthCheck();
          data = { basic_health: health, database_health: dbHealth };
          break;
        default:
          throw new Error("Unknown debug type");
      }
      setDebugData(data);
    } catch (error) {
      onToast(`Failed to get ${type} info`, "error");
      setDebugData(null);
    } finally {
      setIsLoading(false);
    }
  }, [onToast]);

  const handleExportCSV = useCallback(async () => {
    setIsLoading(true);
    try {
      const csvData = await exportGamesCSV();
      const ts = new Date().toISOString().replace(/[:.]/g, "-");
      downloadText(`games-export-${ts}.csv`, csvData);
      onToast("CSV exported successfully", "success");
    } catch (error) {
      onToast("CSV export failed", "error");
    } finally {
      setIsLoading(false);
    }
  }, [onToast, downloadText]);

  return (
    <div className="space-y-6">
      {/* NZ Designers Bulk Update */}
      <div className="bg-white rounded-2xl p-6 shadow">
        <h3 className="text-lg font-semibold mb-2">Bulk Update NZ Designers</h3>
        <p className="text-sm text-gray-600 mb-2">
          CSV format: <code>bgg_id,nz_designer</code> (true/false or 1/0)
        </p>
        <textarea
          className="w-full h-32 border rounded-lg p-2 font-mono text-sm mb-2"
          placeholder="12345,true
67890,false"
          value={nzDesignersText}
          onChange={(e) => setNzDesignersText(e.target.value)}
          disabled={isLoading}
        />
        <button
          className={`px-4 py-2 rounded-lg text-white ${
            isLoading ? "bg-gray-400" : "bg-orange-600 hover:bg-orange-700"
          }`}
          onClick={handleBulkNZDesigners}
          disabled={isLoading || !nzDesignersText.trim()}
        >
          {isLoading ? "Updating..." : "Update NZ Designers"}
        </button>
      </div>

      {/* Advanced Operations */}
      <div className="bg-white rounded-2xl p-6 shadow">
        <h3 className="text-lg font-semibold mb-4">Advanced Operations</h3>
        <div className="flex flex-wrap gap-2">
          <button
            className={`px-4 py-2 rounded-lg text-white ${
              isLoading ? "bg-gray-400" : "bg-red-600 hover:bg-red-700"
            }`}
            onClick={handleReimportAll}
            disabled={isLoading}
          >
            {isLoading ? "Re-importing..." : "Re-import All Games"}
          </button>

          <button
            className={`px-4 py-2 rounded-lg text-white ${
              isLoading ? "bg-gray-400" : "bg-purple-600 hover:bg-purple-700"
            }`}
            onClick={handleFetchSleeveData}
            disabled={isLoading}
          >
            Fetch Sleeve Data
          </button>

          <button
            className={`px-4 py-2 rounded-lg text-white ${
              isLoading ? "bg-gray-400" : "bg-yellow-600 hover:bg-yellow-700"
            }`}
            onClick={handleFixSequence}
            disabled={isLoading}
          >
            Fix Database Sequence
          </button>

          <button
            className={`px-4 py-2 rounded-lg text-white ${
              isLoading ? "bg-gray-400" : "bg-teal-600 hover:bg-teal-700"
            }`}
            onClick={handleExportCSV}
            disabled={isLoading}
          >
            Export Games CSV
          </button>
        </div>
        <p className="text-sm text-gray-600 mt-2">
          Re-import will fetch latest BGG data for all games. Fetch Sleeve Data will scrape sleeve information only. Fix Sequence resolves "duplicate key" errors when adding games. Export creates a CSV backup.
        </p>
      </div>

      {/* Debug & Monitoring */}
      <div className="bg-white rounded-2xl p-6 shadow">
        <h3 className="text-lg font-semibold mb-4">Debug & Monitoring</h3>
        <div className="flex flex-wrap gap-2 mb-4">
          <button
            className={`px-3 py-2 rounded-lg text-sm ${
              isLoading ? "bg-gray-200 text-gray-400" : "bg-blue-100 hover:bg-blue-200 text-blue-700"
            }`}
            onClick={() => handleDebugInfo("health")}
            disabled={isLoading}
          >
            System Health
          </button>

          <button
            className={`px-3 py-2 rounded-lg text-sm ${
              isLoading ? "bg-gray-200 text-gray-400" : "bg-blue-100 hover:bg-blue-200 text-blue-700"
            }`}
            onClick={() => handleDebugInfo("performance")}
            disabled={isLoading}
          >
            Performance Stats
          </button>

          <button
            className={`px-3 py-2 rounded-lg text-sm ${
              isLoading ? "bg-gray-200 text-gray-400" : "bg-blue-100 hover:bg-blue-200 text-blue-700"
            }`}
            onClick={() => handleDebugInfo("database")}
            disabled={isLoading}
          >
            Database Info
          </button>

          <button
            className={`px-3 py-2 rounded-lg text-sm ${
              isLoading ? "bg-gray-200 text-gray-400" : "bg-blue-100 hover:bg-blue-200 text-blue-700"
            }`}
            onClick={() => handleDebugInfo("categories")}
            disabled={isLoading}
          >
            BGG Categories
          </button>
        </div>

        {/* Debug Data Display */}
        {debugData && (
          <div className="mt-4">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-medium text-gray-700">
                {debugType.charAt(0).toUpperCase() + debugType.slice(1)} Data
              </h4>
              <button
                className="text-sm px-2 py-1 rounded bg-gray-100 hover:bg-gray-200"
                onClick={() => {
                  const ts = new Date().toISOString().replace(/[:.]/g, "-");
                  downloadText(`${debugType}-${ts}.json`, JSON.stringify(debugData, null, 2));
                }}
              >
                Download JSON
              </button>
            </div>
            <pre className="bg-gray-50 p-3 rounded-lg text-xs overflow-x-auto max-h-96 overflow-y-auto border">
              {JSON.stringify(debugData, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}