// src/pages/StaffView.jsx
import React from "react";
import { useNavigate } from "react-router-dom";

// ---- Context ----
import { StaffProvider, useStaff } from "../context/StaffContext";

// ---- API ----
import { adminLogout } from "../api/client";

// ---- UI components ----
import CategoryFilter from "../components/CategoryFilter";
import CategorySelectModal from "../components/CategorySelectModal";
import { FullPageLoader } from "../components/common/LoadingSpinner";
import Toast from "../components/common/Toast";

// ---- Staff components ----
import LibraryCard from "../components/staff/LibraryCard";
import { BulkImportPanel, BulkCategorizePanel } from "../components/staff/BulkPanels";
import { AdminToolsPanel } from "../components/staff/AdminToolsPanel";

/**
 * Staff view content - uses StaffContext for all state management
 */
function StaffViewContent() {
  const navigate = useNavigate();

  // Use context instead of local state - eliminates 200+ lines of code!
  const {
    isValidating,
    selectedCategory,
    setSelectedCategory,
    csvImportText,
    setCsvImportText,
    csvCategorizeText,
    setCsvCategorizeText,
    bggIdInput,
    setBggIdInput,
    toast,
    modalOpen,
    pendingGame,
    stats,
    counts,
    filteredLibrary,
    handleAddGame,
    openEditCategory,
    handleModalSelect,
    handleModalClose,
    doBulkImport,
    doBulkCategorize,
    deleteGameData,
    showToast,
  } = useStaff();

  const handleLogout = async () => {
    if (window.confirm("Are you sure you want to logout?")) {
      try {
        // Call logout endpoint to clear session cookie
        await adminLogout();
      } catch (error) {
        console.error("Logout error:", error);
      } finally {
        // Always navigate to login, even if logout API fails
        navigate("/staff/login");
      }
    }
  };

  // Show loading state while validating token
  if (isValidating) {
    return <FullPageLoader text="Validating credentials..." />;
  }

  return (
    <div className="min-h-screen bg-gray-50 text-gray-800">
      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-2xl font-bold">Mana & Meeples — Library (Staff)</h1>
          <div className="flex items-center gap-4">
            <div className="text-sm text-gray-600">
              Games: <b>{stats.total}</b> · Available: <b>{stats.available}</b> · Avg rating:{" "}
              <b>{stats.avgRating}</b>
            </div>
            <button
              onClick={handleLogout}
              className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors"
              title="Logout"
            >
              Logout
            </button>
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
                    await deleteGameData(g.id);
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

        {/* Advanced Admin Tools */}
        <section>
          <h2 className="text-xl font-semibold mb-4">Advanced Admin Tools</h2>
          <AdminToolsPanel
            onToast={showToast}
            onLibraryReload={() => {}}
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

/**
 * StaffView - Wraps content with StaffProvider
 */
export default function StaffView() {
  return (
    <StaffProvider>
      <StaffViewContent />
    </StaffProvider>
  );
}
