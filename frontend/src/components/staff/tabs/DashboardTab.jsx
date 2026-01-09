// src/components/staff/tabs/DashboardTab.jsx
import React, { useState, useEffect } from "react";
import { useStaff } from "../../../context/StaffContext";
import { getHealthCheck, getDbHealthCheck } from "../../../api/client";

/**
 * Dashboard tab - Landing page with overview and quick actions
 */
export function DashboardTab({ onTabChange }) {
  const { stats, counts } = useStaff();
  const [health, setHealth] = useState({ api: null, db: null, loading: true });

  // Load health status on mount
  useEffect(() => {
    const loadHealth = async () => {
      try {
        const [apiHealth, dbHealth] = await Promise.all([
          getHealthCheck(),
          getDbHealthCheck(),
        ]);
        setHealth({ api: apiHealth, db: dbHealth, loading: false });
      } catch (error) {
        console.error("Failed to load health status:", error);
        setHealth({ api: null, db: null, loading: false });
      }
    };

    loadHealth();
  }, []);

  const getHealthStatus = () => {
    if (health.loading) return { label: "Checking...", color: "bg-gray-100 text-gray-600" };
    if (health.api?.status === "healthy" && health.db?.status === "healthy") {
      return { label: "All Systems Operational", color: "bg-green-100 text-green-700" };
    }
    if (!health.api || !health.db) {
      return { label: "System Status Unknown", color: "bg-yellow-100 text-yellow-700" };
    }
    return { label: "System Issues Detected", color: "bg-red-100 text-red-700" };
  };

  const healthStatus = getHealthStatus();
  const uncategorizedCount = counts.uncategorized || 0;

  return (
    <div className="space-y-6">
      {/* System Health Widget */}
      <div className="bg-white rounded-2xl p-6 shadow">
        <h2 className="text-xl font-semibold mb-4">System Status</h2>
        <div className="grid md:grid-cols-3 gap-4">
          <div className={`p-4 rounded-lg ${healthStatus.color}`}>
            <div className="text-sm font-medium mb-1">Overall Status</div>
            <div className="text-lg font-semibold">{healthStatus.label}</div>
          </div>
          <div className="p-4 rounded-lg bg-blue-50 border border-blue-100">
            <div className="text-sm text-blue-600 font-medium mb-1">API Status</div>
            <div className="text-lg font-semibold text-blue-800">
              {health.loading ? "..." : health.api?.status || "Unknown"}
            </div>
          </div>
          <div className="p-4 rounded-lg bg-blue-50 border border-blue-100">
            <div className="text-sm text-blue-600 font-medium mb-1">Database Status</div>
            <div className="text-lg font-semibold text-blue-800">
              {health.loading ? "..." : health.db?.status || "Unknown"}
            </div>
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg p-5 shadow">
          <div className="text-sm text-gray-600 mb-1">Total Games</div>
          <div className="text-3xl font-bold text-purple-700">{stats.total}</div>
        </div>
        <div className="bg-white rounded-lg p-5 shadow">
          <div className="text-sm text-gray-600 mb-1">Average BGG Rating</div>
          <div className="text-3xl font-bold text-blue-700">{stats.avgRating}</div>
        </div>
        <div className="bg-white rounded-lg p-5 shadow">
          <div className="text-sm text-gray-600 mb-1">Uncategorized</div>
          <div className="text-3xl font-bold text-orange-700">{uncategorizedCount}</div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-2xl p-6 shadow">
        <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
        <div className="grid md:grid-cols-2 gap-4">
          <button
            onClick={() => onTabChange("add-games")}
            className="p-6 text-left rounded-lg border-2 border-purple-200 hover:border-purple-400 hover:bg-purple-50 transition-colors group"
          >
            <div className="text-lg font-semibold text-purple-700 mb-2 group-hover:text-purple-800">
              📥 Add New Games
            </div>
            <div className="text-sm text-gray-600">
              Import games from BoardGameGeek or add manually
            </div>
          </button>

          <button
            onClick={() => onTabChange("manage-library")}
            className="p-6 text-left rounded-lg border-2 border-blue-200 hover:border-blue-400 hover:bg-blue-50 transition-colors group"
          >
            <div className="text-lg font-semibold text-blue-700 mb-2 group-hover:text-blue-800">
              📚 Manage Library
            </div>
            <div className="text-sm text-gray-600">
              Browse, edit, and organize your game collection
            </div>
          </button>

          <button
            onClick={() => onTabChange("categories")}
            className="p-6 text-left rounded-lg border-2 border-green-200 hover:border-green-400 hover:bg-green-50 transition-colors group"
          >
            <div className="text-lg font-semibold text-green-700 mb-2 group-hover:text-green-800">
              🏷️ Manage Categories
            </div>
            <div className="text-sm text-gray-600">
              Categorize games and manage NZ designer flags
              {uncategorizedCount > 0 && (
                <span className="ml-2 px-2 py-0.5 bg-orange-100 text-orange-700 rounded-full text-xs font-medium">
                  {uncategorizedCount} uncategorized
                </span>
              )}
            </div>
          </button>

          <button
            onClick={() => onTabChange("advanced")}
            className="p-6 text-left rounded-lg border-2 border-gray-200 hover:border-gray-400 hover:bg-gray-50 transition-colors group"
          >
            <div className="text-lg font-semibold text-gray-700 mb-2 group-hover:text-gray-800">
              ⚙️ Advanced Tools
            </div>
            <div className="text-sm text-gray-600">
              System maintenance, debugging, and data export
            </div>
          </button>
        </div>
      </div>

      {/* Tips & Shortcuts */}
      <div className="bg-linear-to-r from-purple-50 to-blue-50 rounded-2xl p-6 border border-purple-100">
        <h3 className="text-lg font-semibold text-gray-800 mb-3">💡 Quick Tips</h3>
        <ul className="space-y-2 text-sm text-gray-700">
          <li className="flex items-start gap-2">
            <span className="text-purple-600 font-bold">•</span>
            <span>
              <strong>Adding games?</strong> Use BGG ID import for automatic data retrieval. Find IDs in the URL on boardgamegeek.com
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-purple-600 font-bold">•</span>
            <span>
              <strong>Need to categorize many games?</strong> Use the bulk categorize CSV feature in the Categories tab
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-purple-600 font-bold">•</span>
            <span>
              <strong>System running slow?</strong> Check Performance Stats in Advanced Tools to diagnose issues
            </span>
          </li>
        </ul>
      </div>
    </div>
  );
}
