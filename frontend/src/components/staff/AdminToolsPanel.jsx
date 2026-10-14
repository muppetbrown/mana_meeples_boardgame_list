import React, { useState, useCallback } from "react";
import { bulkUpdateAfterGameIDs, reimportAllGames, fetchAllSleeveData, backfillCloudinaryUrls, fixDatabaseSequence, getDebugCategories, getDebugDatabaseInfo, getDebugPerformance, exportGamesCSV, getHealthCheck, getDbHealthCheck } from "../../api/client";
import SleeveFetchStatus from "./SleeveFetchStatus";
import BulkResultSummary, { downloadTextFile } from "./BulkResultSummary";
import { useConfirm } from "../../context/StaffContext";

export function AdminToolsPanel({ onToast, onLibraryReload }) {
  const [afterGameText, setAfterGameText] = useState("");
  const [afterGameResult, setAfterGameResult] = useState(null);
  // Name of the operation currently running (null = idle); only that button shows progress
  const [busy, setBusy] = useState(null);
  const isLoading = busy !== null;
  const confirm = useConfirm();
  const [debugData, setDebugData] = useState(null);
  const [debugType, setDebugType] = useState("");
  const [sleeveFetchPollToken, setSleeveFetchPollToken] = useState(0);

  const downloadText = downloadTextFile;

  const handleBulkAfterGameIDs = useCallback(async () => {
    if (!afterGameText.trim()) {
      onToast("Please enter CSV data", "error");
      return;
    }

    setBusy("aftergame");
    try {
      const result = await bulkUpdateAfterGameIDs(afterGameText);
      const problems = (result.not_found?.length || 0) + (result.errors?.length || 0);
      onToast(
        `Updated: ${result.updated?.length || 0}, Not found: ${result.not_found?.length || 0}, Errors: ${result.errors?.length || 0}`,
        problems ? "warning" : "success"
      );
      setAfterGameResult({
        updated: result.updated || [],
        not_found: result.not_found || [],
        errors: result.errors || [],
      });
      setAfterGameText("");
      if (onLibraryReload) await onLibraryReload();
    } catch (error) {
      onToast("Bulk AfterGame IDs update failed", "error");
    } finally {
      setBusy(null);
    }
  }, [afterGameText, onToast, onLibraryReload]);

  const handleReimportAll = useCallback(async () => {
    const ok = await confirm({
      title: "Re-import ALL games from BoardGameGeek?",
      message:
        "This overwrites BGG-sourced data (ratings, descriptions, images, etc.) for every game and may take several minutes. Per-game edits you've made to category/expansion/sleeve fields are not touched.\n\nTo refresh only some games, select them in Manage Library instead.",
      confirmLabel: "Re-import everything",
      tone: "danger",
      requireText: "reimport",
    });
    if (!ok) return;

    setBusy("reimport");
    onToast("Re-importing all games... This may take several minutes", "info", 5000);

    try {
      const result = await reimportAllGames();
      onToast(`Re-import complete! Updated: ${result.updated || 0}, Errors: ${result.errors || 0}`, "success");
      if (onLibraryReload) await onLibraryReload();
    } catch (error) {
      onToast("Re-import failed", "error");
    } finally {
      setBusy(null);
    }
  }, [onToast, onLibraryReload, confirm]);

  const handleFetchSleeveData = useCallback(async () => {
    const ok = await confirm({
      title: "Fetch sleeve data for ALL games?",
      message: "This scrapes sleeve data for every game and may take several minutes.",
      confirmLabel: "Fetch all",
    });
    if (!ok) return;

    setBusy("sleeves");
    onToast("Fetching sleeve data for all games... This may take several minutes", "info", 5000);

    try {
      const result = await fetchAllSleeveData();
      onToast(`Sleeve data fetch started! Processing ${result.total_games || 0} games in background`, "success");
      // Bump the poll token so SleeveFetchStatus starts actively polling for progress.
      setSleeveFetchPollToken((t) => t + 1);
      if (onLibraryReload) await onLibraryReload();
    } catch (error) {
      onToast("Failed to start sleeve data fetch", "error");
    } finally {
      setBusy(null);
    }
  }, [onToast, onLibraryReload, confirm]);

  const handleFixSequence = useCallback(async () => {
    const ok = await confirm({
      title: "Fix the database ID sequence?",
      message: "This is safe and fixes 'duplicate key' errors when adding games.",
      confirmLabel: "Fix sequence",
    });
    if (!ok) return;

    setBusy("sequence");
    try {
      const result = await fixDatabaseSequence();
      onToast(`Sequence fixed! Next ID will be: ${result.next_id}`, "success");
    } catch (error) {
      onToast("Failed to fix sequence", "error");
    } finally {
      setBusy(null);
    }
  }, [onToast, confirm]);

  const handleBackfillCloudinary = useCallback(async () => {
    const ok = await confirm({
      title: "Backfill Cloudinary URLs?",
      message: "Pre-generates optimized image URLs for all games with images (about 50-150ms faster per image).",
      confirmLabel: "Backfill",
    });
    if (!ok) return;

    setBusy("cloudinary");
    onToast("Backfilling Cloudinary URLs...", "info", 3000);

    try {
      const result = await backfillCloudinaryUrls();
      const cloudinaryStatus = result.cloudinary_enabled ? "enabled" : "disabled (using fallback URLs)";
      onToast(
        `Backfill complete! Updated: ${result.updated}, Skipped: ${result.skipped}, Failed: ${result.failed}. Cloudinary: ${cloudinaryStatus}`,
        "success",
        5000
      );
      if (result.errors && result.errors.length > 0) {
        console.warn("Cloudinary backfill errors:", result.errors);
      }
    } catch (error) {
      onToast("Cloudinary URL backfill failed", "error");
    } finally {
      setBusy(null);
    }
  }, [onToast, confirm]);

  const handleDebugInfo = useCallback(async (type) => {
    setBusy("debug");
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
      setBusy(null);
    }
  }, [onToast]);

  const handleExportCSV = useCallback(async () => {
    setBusy("export");
    try {
      const csvData = await exportGamesCSV();
      const ts = new Date().toISOString().replace(/[:.]/g, "-");
      downloadText(`games-export-${ts}.csv`, csvData);
      onToast("CSV exported successfully", "success");
    } catch (error) {
      onToast("CSV export failed", "error");
    } finally {
      setBusy(null);
    }
  }, [onToast, downloadText]);

  return (
    <div className="space-y-6">
      {/* AfterGame IDs Bulk Update */}
      <div className="bg-white rounded-2xl p-6 shadow">
        <h3 className="text-lg font-semibold mb-2 flex items-center gap-2">
          🎲 Bulk Update AfterGame IDs
        </h3>
        <p className="text-sm text-gray-600 mb-2">
          CSV format: <code>bgg_id,aftergame_game_id[,title]</code>
        </p>
        <div className="mb-3 p-3 bg-emerald-50 rounded-lg border border-emerald-200">
          <p className="text-xs text-gray-700">
            <strong>Example:</strong><br />
            <code className="text-xs">
              174430,ac3a5f77-3e19-47af-a61a-d648d04b02e2,Gloomhaven<br />
              167791,bd4b6e88-4c2a-48bf-b71b-e759e15c13f3,Terraforming Mars
            </code>
          </p>
        </div>
        <textarea
          className="w-full h-32 border rounded-lg p-2 font-mono text-sm mb-2"
          placeholder="174430,ac3a5f77-3e19-47af-a61a-d648d04b02e2,Gloomhaven"
          value={afterGameText}
          onChange={(e) => setAfterGameText(e.target.value)}
          disabled={isLoading}
        />
        <button
          className={`px-4 py-2 rounded-lg text-white ${
            isLoading ? "bg-gray-400" : "bg-emerald-600 hover:bg-emerald-700"
          }`}
          onClick={handleBulkAfterGameIDs}
          disabled={isLoading || !afterGameText.trim()}
        >
          {busy === "aftergame" ? "Updating..." : "Update AfterGame IDs"}
        </button>
        <BulkResultSummary result={afterGameResult} logName="aftergame-ids" onDismiss={() => setAfterGameResult(null)} />
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
            {busy === "reimport" ? "Re-importing..." : "Re-import All Games"}
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

          <button
            className={`px-4 py-2 rounded-lg text-white ${
              isLoading ? "bg-gray-400" : "bg-indigo-600 hover:bg-indigo-700"
            }`}
            onClick={handleBackfillCloudinary}
            disabled={isLoading}
          >
            Backfill Cloudinary URLs
          </button>
        </div>
        <SleeveFetchStatus pollToken={sleeveFetchPollToken} />
        <p className="text-sm text-gray-600 mt-2">
          Re-import will fetch latest BGG data for all games. Fetch Sleeve Data will scrape sleeve information only. Fix Sequence resolves "duplicate key" errors when adding games. Export creates a CSV backup. Backfill Cloudinary URLs pre-generates optimized image URLs for faster loading.
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