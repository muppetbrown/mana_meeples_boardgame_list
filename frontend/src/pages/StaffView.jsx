// src/pages/StaffView.jsx
import React, { useState, useEffect, useCallback, useRef } from "react";
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
import { QuickPicksTab } from "../components/staff/tabs/QuickPicksTab";
import { AdvancedToolsTab } from "../components/staff/tabs/AdvancedToolsTab";
import { BuyListTab } from "../components/staff/tabs/BuyListTab";
import { SleeveInventoryTab } from "../components/staff/tabs/SleeveInventoryTab";

const TABS = [
  { id: "dashboard", label: "Dashboard", icon: "📊" },
  { id: "add-games", label: "Add Games", icon: "📥" },
  { id: "manage-library", label: "Manage Library", icon: "📚" },
  { id: "categories", label: "Categories", icon: "🏷️" },
  { id: "quick-picks", label: "Quick Picks", icon: "🎯" },
  { id: "buy-list", label: "Buy List", icon: "🛒" },
  { id: "sleeve-inventory", label: "Sleeve Inventory", icon: "🃏" },
  { id: "advanced", label: "Advanced Tools", icon: "⚙️" },
];
const TAB_IDS = TABS.map((t) => t.id);

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
    confirm,
    handleModalSelect,
    handleModalClose,
  } = useStaff();

  // Tab state with URL persistence
  const initialTab = TAB_IDS.includes(searchParams.get("tab")) ? searchParams.get("tab") : "dashboard";
  const [activeTab, setActiveTab] = useState(initialTab);
  // Tabs stay mounted once visited so search/filters/selections survive tab switches
  const [visitedTabs, setVisitedTabs] = useState(() => new Set([initialTab]));

  // Measures the actual rendered height of the header, and of header+tabs
  // combined, exposing both as CSS variables. Sticky elements further down
  // (the tab nav itself, and Manage Library's selection bar) read these instead
  // of a hardcoded pixel offset that would drift whenever the header wraps
  // (narrow screens, longer stats text, etc.) or its content changes.
  const headerRef = useRef(null);
  const topBarRef = useRef(null);
  useEffect(() => {
    const headerEl = headerRef.current;
    const topBarEl = topBarRef.current;
    if (!headerEl || !topBarEl || typeof ResizeObserver === "undefined") return undefined;
    const update = () => {
      document.documentElement.style.setProperty("--staff-header-h", `${headerEl.offsetHeight}px`);
      document.documentElement.style.setProperty("--staff-topbar-h", `${topBarEl.offsetHeight}px`);
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(headerEl);
    observer.observe(topBarEl);
    return () => observer.disconnect();
  }, []);

  const handleTabChange = useCallback(
    (tabId) => {
      setActiveTab(tabId);
      setVisitedTabs((prev) => (prev.has(tabId) ? prev : new Set(prev).add(tabId)));
      setSearchParams({ tab: tabId });
    },
    [setSearchParams]
  );

  // Sync with URL (browser back/forward)
  useEffect(() => {
    const urlTab = searchParams.get("tab");
    if (urlTab && TAB_IDS.includes(urlTab)) {
      setActiveTab(urlTab);
      setVisitedTabs((prev) => (prev.has(urlTab) ? prev : new Set(prev).add(urlTab)));
    }
  }, [searchParams]);

  const handleLogout = async () => {
    const ok = await confirm({
      title: "Log out?",
      message: "You will need your admin token to sign back in.",
      confirmLabel: "Log out",
    });
    if (ok) {
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

  const renderTab = (id) => {
    switch (id) {
      case "add-games":
        return <AddGamesTab />;
      case "manage-library":
        return <ManageLibraryTab />;
      case "categories":
        return <CategoriesTab />;
      case "quick-picks":
        return <QuickPicksTab />;
      case "buy-list":
        return <BuyListTab />;
      case "sleeve-inventory":
        return <SleeveInventoryTab />;
      case "advanced":
        return <AdvancedToolsTab />;
      default:
        return <DashboardTab onTabChange={handleTabChange} />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 text-gray-800">
      {/* Header and Tab Navigation are each independently sticky; this wrapper only
          measures their combined height (see effect above) for content further down. */}
      <div ref={topBarRef}>
        <header ref={headerRef} className="bg-white shadow-sm sticky top-0 z-40">
          <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
            <h1 className="text-2xl font-bold">Mana & Meeples — Admin Panel</h1>
            <div className="flex items-center gap-4">
              <div className="text-sm text-gray-600 hidden md:block">
                <span className="font-semibold">{stats.total}</span> games ·{" "}
                <span className="font-semibold">{stats.avgRating}</span> avg BGG rating
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

        <TabNavigation activeTab={activeTab} onTabChange={handleTabChange} tabs={TABS} />
      </div>

      {/* Tab Content */}
      <main id="main-content" className="max-w-7xl mx-auto px-4 py-6">
        {TABS.filter((t) => visitedTabs.has(t.id)).map((t) => (
          <div
            key={t.id}
            role="tabpanel"
            id={`panel-${t.id}`}
            aria-labelledby={`tab-${t.id}`}
            hidden={t.id !== activeTab}
          >
            {renderTab(t.id)}
          </div>
        ))}
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
