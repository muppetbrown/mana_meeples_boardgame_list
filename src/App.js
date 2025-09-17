// src/App.js
import React, { useEffect, useMemo, useCallback, useState } from "react";
import { Routes, Route, Navigate, useNavigate } from "react-router-dom";

// ---- Public pages ----
import PublicCatalogue from "./pages/PublicCatalogue";
import GameDetails from "./pages/GameDetails";
import AdminLogin from "./pages/AdminLogin";

// ---- API ----
import {
  getGames,
  bulkImportCsv,
  bulkCategorizeCsv,
  addGame as apiAdd,
  updateGame,
  deleteGame,
} from "./api/client";

// ---- Categories ----
import { CATEGORY_KEYS, labelFor } from "./constants/categories";

// ---- UI components ----
import CategoryFilter from "./components/CategoryFilter";
import CategorySelectModal from "./components/CategorySelectModal";

// ---- Staff components ----
import LibraryCard from "./components/staff/LibraryCard";
import { BulkImportPanel, BulkCategorizePanel } from "./components/staff/BulkPanels";

/** Tiny toast */
function Toast({ message, type }) {
  if (!message) return null;
  const base =
    "fixed bottom-4 left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded-lg shadow-lg text-white";
  const byType = {
    info: "bg-gray-800",
    success: "bg-green-600",
    warning: "bg-amber-600",
    error: "bg-red-600",
  };
  return <div className={`${base} ${byType[type || "info"]}`}>{message}</div>;
}

// Count games by backend enum KEYS
function computeCounts(list) {
  const counts = { all: list.length, uncategorized: 0 };
  CATEGORY_KEYS.forEach((k) => (counts[k] = 0));
  for (const g of list) {
    const k = g.mana_meeple_category;
    if (!k) counts.uncategorized++;
    else if (Object.prototype.hasOwnProperty.call(counts, k)) counts[k]++;
  }
  return counts;
}

// Simple download helper for CSV logs
function downloadText(name, text) {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

/** -------------------------------
 * Staff view
 * -------------------------------- */
function StaffView() {
  const navigate = useNavigate();
  useEffect(() => {
    const t = localStorage.getItem("ADMIN_TOKEN");
    if (!t) navigate("/staff/login");
  }, [navigate]);

  // ----- State -----
  const [library, setLibrary] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState("all");

  const [csvImportText, setCsvImportText] = useState("");
  const [csvCategorizeText, setCsvCategorizeText] = useState("");

  // BGG ID input for manual adding
  const [bggIdInput, setBggIdInput] = useState("");

  const [toast, setToast] = useState({ message: "", type: "info" });
  const showToast = (message, type = "info", ms = 2000) => {
    setToast({ message, type });
    setTimeout(() => setToast({ message: "", type: "info" }), ms);
  };

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [pendingGame, setPendingGame] = useState(null);
  const [modalMode, setModalMode] = useState("add"); // 'add' | 'edit'

  // ----- Data loading -----
  const loadLibrary = useCallback(async () => {
    try {
      const data = await getGames();
      setLibrary(Array.isArray(data) ? data : []);
      if (typeof window !== "undefined") window.__LIB__ = Array.isArray(data) ? data : [];
    } catch (e) {
      showToast("Failed to load library", "error");
      setLibrary([]);
    }
  }, []);

  useEffect(() => {
    loadLibrary();
  }, [loadLibrary]);

  // ----- Derived state (memoized) -----
  const stats = useMemo(() => {
    const total = library.length;
    const available = library.filter((g) => g.available).length;
    const rated = library.filter((g) => typeof g.rating === "number");
    const avg =
      rated.length > 0
        ? (rated.reduce((s, g) => s + g.rating, 0) / rated.length).toFixed(1)
        : "N/A";
    return { total, available, avgRating: avg };
  }, [library]);

  const counts = useMemo(() => computeCounts(library), [library]);

  const filteredLibrary = useMemo(() => {
    if (selectedCategory === "all") return library;
    if (selectedCategory === "uncategorized")
      return library.filter((g) => !g.mana_meeple_category);
    return library.filter((g) => g.mana_meeple_category === selectedCategory);
  }, [library, selectedCategory]);

  // ----- Actions -----
  const addGameByBggId = useCallback(async (bggId) => {
    try {
      const API_BASE = window.__API_BASE__ || '/library/api-proxy.php?path=';
      const response = await fetch(`${API_BASE}/api/admin/import/bgg?bgg_id=${bggId}`, {
        method: 'POST',
        headers: {
          'X-Admin-Token': localStorage.getItem('ADMIN_TOKEN')
        }
      });
      if (response.ok) {
        const result = await response.json();
        showToast(`Added "${result.title}" successfully!`, "success");
        await loadLibrary();
      } else {
        showToast("Failed to add game", "error");
      }
    } catch (e) {
      showToast("Network error", "error");
    }
  }, [loadLibrary]);

  const handleAddGame = () => {
    const id = parseInt(bggIdInput.trim());
    if (isNaN(id) || id <= 0) {
      showToast("Please enter a valid BGG ID", "error");
      return;
    }
    addGameByBggId(id);
    setBggIdInput("");
  };

  const openEditCategory = useCallback((game) => {
    setPendingGame(game);
    setModalMode("edit");
    setModalOpen(true);
  }, []);

  const handleModalSelect = async (catKey) => {
    setModalOpen(false);
    if (!pendingGame) return;

    try {
      if (modalMode === "edit") {
        await updateGame(pendingGame.id, { mana_meeple_category: catKey });
        showToast(`Updated to ${labelFor(catKey)}`, "success");
        await loadLibrary();
      }
    } catch {
      showToast("Action failed", "error");
    } finally {
      setPendingGame(null);
    }
  };

  const handleModalClose = () => {
    setModalOpen(false);
    setPendingGame(null);
  };

  const doBulkImport = useCallback(async () => {
    if (!csvImportText.trim()) return;
    try {
      const res = await bulkImportCsv(csvImportText);
      showToast(`Import finished`, "success");
      const ts = new Date().toISOString().replace(/[:.]/g, "-");
      const log = [
        "Added:",
        ...(res.added || []),
        "",
        "Skipped:",
        ...(res.skipped || []),
        "",
        "Errors:",
        ...(res.errors || []),
        "",
      ].join("\n");
      downloadText(`bulk-import-${ts}.log.txt`, log);
      await loadLibrary();
      setCsvImportText("");
    } catch {
      showToast("CSV import failed.", "error");
    }
  }, [csvImportText, loadLibrary]);

  const doBulkCategorize = useCallback(async () => {
    if (!csvCategorizeText.trim()) return;
    try {
      const res = await bulkCategorizeCsv(csvCategorizeText);
      const msg = `Updated: ${res.updated?.length || 0}, Not found: ${
        res.not_found?.length || 0
      }, Errors: ${res.errors?.length || 0}`;
      showToast(msg, "success");
      const ts = new Date().toISOString().replace(/[:.]/g, "-");
      const log = [
        "Updated:",
        ...(res.updated || []),
        "",
        "Not found:",
        ...(res.not_found || []),
        "",
        "Errors:",
        ...(res.errors || []),
        "",
      ].join("\n");
      downloadText(`bulk-categorize-${ts}.log.txt`, log);
      await loadLibrary();
      setCsvCategorizeText("");
    } catch {
      showToast("Bulk categorize failed.", "error");
    }
  }, [csvCategorizeText, loadLibrary]);

  return (
    <div className="min-h-screen bg-gray-50 text-gray-800">
      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-2xl font-bold">Mana & Meeples — Library (Staff)</h1>
          <div className="text-sm text-gray-600">
            Games: <b>{stats.total}</b> · Available: <b>{stats.available}</b> · Avg rating:{" "}
            <b>{stats.avgRating}</b>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-8">
        <section className="bg-white rounded-2xl p-6 shadow">
          <h2 className="text-xl font-semibold mb-3">Add Game by BGG ID</h2>
          <div className="flex flex-wrap gap-2 items-center">
            <input
              className="flex-1 min-w-[240px] border rounded-lg px-3 py-2"
              placeholder="Enter BoardGameGeek ID (e.g., 30549 for Pandemic)"
              value={bggIdInput}
              onChange={(e) => setBggIdInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAddGame()}
            />
            <button
              className="px-4 py-2 rounded-lg bg-purple-600 text-white hover:bg-purple-700"
              onClick={handleAddGame}
            >
              Add Game
            </button>
          </div>
          <p className="text-sm text-gray-600 mt-2">
            Find BGG IDs at boardgamegeek.com - they're in the URL (e.g., /boardgame/30549/pandemic)
          </p>
        </section>

        <section className="bg-white rounded-2xl p-6 shadow">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">Your Library</h2>
          </div>

          <CategoryFilter selected={selectedCategory} counts={counts} onChange={setSelectedCategory} />

          <div className="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredLibrary.map((game) => (
              <LibraryCard
                key={game.id}
                game={game}
                onEditCategory={(g) => openEditCategory(g)}
                onDelete={async (g) => {
                  if (!window.confirm(`Delete "${g.title}"?`)) return;
                  try {
                    await deleteGame(g.id);
                    showToast("Deleted", "success");
                    await loadLibrary();
                  } catch {
                    showToast("Delete failed", "error");
                  }
                }}
              />
            ))}
            {filteredLibrary.length === 0 && (
              <div className="text-gray-500">No games in this view.</div>
            )}
          </div>
        </section>

        <section className="grid md:grid-cols-2 gap-6">
          <BulkImportPanel
            value={csvImportText}
            onChange={setCsvImportText}
            onSubmit={doBulkImport}
          />
          <BulkCategorizePanel
            value={csvCategorizeText}
            onChange={setCsvCategorizeText}
            onSubmit={doBulkCategorize}
          />
        </section>
      </main>

      <CategorySelectModal
        open={modalOpen}
        gameTitle={pendingGame?.title}
        onSelect={handleModalSelect}
        onClose={handleModalClose}
      />

      <Toast message={toast.message} type={toast.type} />
    </div>
  );
}

/** -------------------------------
 * Router: public & staff - FIXED ROUTING
 * -------------------------------- */
export default function App() {
  return (
    <Routes>
      {/* Fixed: Remove leading slashes for nested routing */}
      <Route path="/" element={<PublicCatalogue />} />
      <Route path="game/:id" element={<GameDetails />} />
      <Route path="staff/login" element={<AdminLogin />} />
      <Route path="staff" element={<StaffView />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}