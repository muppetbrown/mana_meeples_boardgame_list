// src/pages/StaffView.jsx
import React, { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

// ---- Context ----
import { StaffProvider, useStaff } from "../context/StaffContext";

// ---- API ----
import { adminLogout } from "../api/client";

// ---- UI components ----
import CategorySelectModal from "../components/CategorySelectModal";
import { FullPageLoader } from "../components/common/LoadingSpinner";
import Toast from "../components/common/Toast";
import Icon from "../components/common/Icon";
import { BackgroundTasksMenu } from "../components/staff/BackgroundTasksMenu";
import { buttonClass } from "../components/common/Button";

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

// Tabs are grouped (a divider is drawn when `group` changes): overview, library
// curation, sourcing, sleeves, system.
const TABS = [
  { id: "dashboard", label: "Dashboard", icon: "dashboard", group: "overview" },
  { id: "add-games", label: "Add Games", icon: "download", group: "library" },
  { id: "manage-library", label: "Manage Library", icon: "library", group: "library" },
  { id: "categories", label: "Categories", icon: "tag", group: "library" },
  { id: "quick-picks", label: "Quick Picks", icon: "target", group: "library" },
  { id: "buy-list", label: "Buy List", icon: "cart", group: "sourcing" },
  { id: "sleeve-inventory", label: "Sleeve Inventory", icon: "layers", group: "sleeves" },
  { id: "advanced", label: "Advanced Tools", icon: "settings", group: "system" },
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
    ownedLibrary,
    recentOperations,
    dismissRecentOperation,
    dismissToast,
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
    const update = (_entries, _observer) => {
      document.documentElement.style.setProperty("--staff-header-h", `${headerEl.offsetHeight}px`);
      document.documentElement.style.setProperty("--staff-topbar-h", `${topBarEl.offsetHeight}px`);
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(headerEl);
    observer.observe(topBarEl);
    return () => observer.disconnect();
  }, []);

  // Count badges on tabs that have outstanding work
  const uncategorizedCount = useMemo(
    () => (ownedLibrary || []).filter((g) => !g.mana_meeple_category).length,
    [ownedLibrary]
  );
  const tabs = useMemo(
    () => TABS.map((t) => (t.id === "categories" ? { ...t, badge: uncategorizedCount } : t)),
    [uncategorizedCount]
  );

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
    <div className="staff-root min-h-screen text-gray-800">
      {/* The wrapper is the sticky element (a sticky child can't escape a wrapper that is only
          as tall as itself), so header + tabs stay pinned together. Its measured height feeds
          --staff-topbar-h for the sticky toolbars further down. */}
      <div ref={topBarRef} className="sticky top-0 z-40">
        <header ref={headerRef} className="bg-white border-b border-gray-200 relative">
          <div className="max-w-screen-2xl mx-auto px-3 lg:px-6 h-12 flex items-center justify-between">
            <h1 className="text-base font-bold tracking-tight">Mana & Meeples — Admin Panel</h1>
            <div className="flex items-center gap-3">
              <div className="text-xs text-gray-500 hidden md:block tabular">
                <span className="font-semibold text-gray-700">{stats.total}</span> games ·{" "}
                <span className="font-semibold text-gray-700">{stats.avgRating}</span> avg BGG rating
              </div>
              <BackgroundTasksMenu operations={recentOperations} onDismiss={dismissRecentOperation} />
              <a
                href="/"
                target="_blank"
                rel="noopener noreferrer"
                className={buttonClass({ variant: "secondary", size: "sm" })}
              >
                View public site
                <Icon name="external" size={13} />
              </a>
              <button
                onClick={handleLogout}
                className={buttonClass({ variant: "secondary", size: "sm" })}
                title="Logout"
              >
                Logout
              </button>
            </div>
          </div>
        </header>

        <TabNavigation activeTab={activeTab} onTabChange={handleTabChange} tabs={tabs} />
      </div>

      {/* Tab Content */}
      <main id="main-content" className="max-w-screen-2xl mx-auto px-3 lg:px-6 py-5">
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
      <Toast message={toast.message} type={toast.type} onDismiss={dismissToast} />
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
