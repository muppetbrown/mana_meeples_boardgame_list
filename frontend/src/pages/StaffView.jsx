// src/pages/StaffView.jsx
import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

// ---- Context ----
import { StaffProvider, useStaff } from "../context/StaffContext";

// ---- API ----
import { adminLogout } from "../api/client";

// ---- UI components ----
import CategorySelectModal from "../components/CategorySelectModal";
import { FullPageLoader } from "../components/common/LoadingSpinner";
import Toast from "../components/common/Toast";

// ---- Staff components ----
import { TabNavigation } from "../components/staff/TabNavigation";
import { DashboardTab } from "../components/staff/tabs/DashboardTab";
import { AddGamesTab } from "../components/staff/tabs/AddGamesTab";
import { ManageLibraryTab } from "../components/staff/tabs/ManageLibraryTab";
import { CategoriesTab } from "../components/staff/tabs/CategoriesTab";
import { AdvancedToolsTab } from "../components/staff/tabs/AdvancedToolsTab";

/**
 * Staff view content - uses StaffContext for all state management
 * Now with tabbed navigation for better organization
 */
function StaffViewContent() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // Use context instead of local state
  const {
    isValidating,
    toast,
    modalOpen,
    pendingGame,
    stats,
    handleModalSelect,
    handleModalClose,
  } = useStaff();

  // Tab state with URL persistence
  const [activeTab, setActiveTab] = useState(() => {
    return searchParams.get("tab") || "dashboard";
  });

  // Tab configuration
  const tabs = [
    { id: "dashboard", label: "Dashboard", icon: "📊" },
    { id: "add-games", label: "Add Games", icon: "📥" },
    { id: "manage-library", label: "Manage Library", icon: "📚" },
    { id: "categories", label: "Categories", icon: "🏷️" },
    { id: "advanced", label: "Advanced Tools", icon: "⚙️" },
  ];

  // Update URL when tab changes
  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
    setSearchParams({ tab: tabId });
  };

  // Sync with URL on mount and when URL changes
  useEffect(() => {
    const urlTab = searchParams.get("tab");
    if (urlTab && tabs.find((t) => t.id === urlTab)) {
      setActiveTab(urlTab);
    }
  }, [searchParams]);

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

  // Render active tab content
  const renderTabContent = () => {
    switch (activeTab) {
      case "dashboard":
        return <DashboardTab onTabChange={handleTabChange} />;
      case "add-games":
        return <AddGamesTab />;
      case "manage-library":
        return <ManageLibraryTab />;
      case "categories":
        return <CategoriesTab />;
      case "advanced":
        return <AdvancedToolsTab />;
      default:
        return <DashboardTab onTabChange={handleTabChange} />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 text-gray-800">
      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-2xl font-bold">Mana & Meeples — Admin Panel</h1>
          <div className="flex items-center gap-4">
            <div className="text-sm text-gray-600 hidden md:block">
              <span className="font-semibold">{stats.total}</span> games ·{" "}
              <span className="font-semibold">{stats.available}</span> available ·{" "}
              <span className="font-semibold">{stats.avgRating}</span> avg rating
            </div>
            <button
              onClick={handleLogout}
              className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors"
              title="Logout"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Tab Navigation */}
      <TabNavigation activeTab={activeTab} onTabChange={handleTabChange} tabs={tabs} />

      {/* Tab Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {renderTabContent()}
      </main>

      {/* Global Modals */}
      <CategorySelectModal
        open={modalOpen}
        gameTitle={pendingGame?.title}
        onSelect={handleModalSelect}
        onClose={handleModalClose}
      />

      {/* Global Toast Notifications */}
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
