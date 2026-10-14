// src/components/staff/tabs/DashboardTab.jsx
import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useStaff } from "../../../context/StaffContext";
import {
  getHealthCheck,
  getDbHealthCheck,
  getBackgroundFailures,
  resolveBackgroundFailure,
  getCircuitBreakerStatus,
} from "../../../api/client";
import { ATTENTION_FILTERS, attentionCounts } from "../../../utils/libraryQuality";

/**
 * Dashboard tab - what needs doing, system health, and quick actions
 */
export function DashboardTab({ onTabChange }) {
  const { stats, ownedLibrary, library, setAttentionFilter, setSelectedCategory, showToast } = useStaff();
  const [health, setHealth] = useState({ api: null, db: null, loading: true });
  const [monitoring, setMonitoring] = useState({ failures: null, breaker: null, loading: true });
  const [refreshedAt, setRefreshedAt] = useState(null);

  const loadHealth = useCallback(async () => {
    setHealth((h) => ({ ...h, loading: true }));
    try {
      const [apiHealth, dbHealth] = await Promise.all([getHealthCheck(), getDbHealthCheck()]);
      setHealth({ api: apiHealth, db: dbHealth, loading: false });
    } catch (error) {
      console.error("Failed to load health status:", error);
      setHealth({ api: null, db: null, loading: false });
    }
  }, []);

  const loadMonitoring = useCallback(async () => {
    setMonitoring((m) => ({ ...m, loading: true }));
    const [failures, breaker] = await Promise.allSettled([
      getBackgroundFailures({ resolved: false, limit: 10 }),
      getCircuitBreakerStatus(),
    ]);
    setMonitoring({
      failures: failures.status === "fulfilled" ? failures.value : null,
      breaker: breaker.status === "fulfilled" ? breaker.value : null,
      loading: false,
    });
  }, []);

  const refreshAll = useCallback(async () => {
    await Promise.all([loadHealth(), loadMonitoring()]);
    setRefreshedAt(new Date());
  }, [loadHealth, loadMonitoring]);

  useEffect(() => {
    refreshAll();
  }, [refreshAll]);

  const resolveFailure = async (id) => {
    try {
      await resolveBackgroundFailure(id);
      showToast("Marked as resolved", "success");
      loadMonitoring();
    } catch {
      showToast("Could not resolve failure", "error");
    }
  };

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
  const attention = useMemo(() => attentionCounts(ownedLibrary), [ownedLibrary]);
  const attentionTotal = ATTENTION_FILTERS.reduce((n, f) => n + (attention[f.key] > 0 ? 1 : 0), 0);
  const buyListCount = useMemo(
    () => library.filter((g) => g.status === "BUY_LIST").length,
    [library]
  );
  const recentlyAdded = useMemo(
    () =>
      [...ownedLibrary]
        .filter((g) => g.date_added)
        .sort((a, b) => new Date(b.date_added) - new Date(a.date_added))
        .slice(0, 5),
    [ownedLibrary]
  );

  const openAttention = (f) => {
    setSelectedCategory("all");
    setAttentionFilter(f.key);
    onTabChange("manage-library");
  };

  const failures = monitoring.failures;
  const breaker = monitoring.breaker;
  const unresolved = failures?.unresolved_failures ?? 0;

  return (
    <div className="space-y-6">
      {/* Quick Stats */}
      <div className="grid md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg p-5 shadow">
          <div className="text-sm text-gray-600 mb-1">Games in library</div>
          <div className="text-3xl font-bold text-purple-700">{stats.total}</div>
        </div>
        <div className="bg-white rounded-lg p-5 shadow">
          <div className="text-sm text-gray-600 mb-1">Average BGG rating</div>
          <div className="text-3xl font-bold text-blue-700">{stats.avgRating}</div>
        </div>
        <div className="bg-white rounded-lg p-5 shadow">
          <div className="text-sm text-gray-600 mb-1">On the buy list</div>
          <button
            onClick={() => onTabChange("buy-list")}
            className="text-3xl font-bold text-emerald-700 hover:underline"
          >
            {buyListCount}
          </button>
        </div>
        <div className="bg-white rounded-lg p-5 shadow">
          <div className="text-sm text-gray-600 mb-1">Open background failures</div>
          <div className={`text-3xl font-bold ${unresolved > 0 ? "text-red-700" : "text-gray-700"}`}>
            {monitoring.loading && !failures ? "…" : failures ? unresolved : "—"}
          </div>
        </div>
      </div>

      {/* Needs attention */}
      <div className="bg-white rounded-2xl p-6 shadow">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">Needs attention</h2>
          <span className="text-sm text-gray-500">
            {ownedLibrary.length === 0
              ? "No games loaded"
              : attentionTotal === 0
                ? "All clear 🎉"
                : `${attentionTotal} check${attentionTotal === 1 ? "" : "s"} with issues`}
          </span>
        </div>
        <div className="grid md:grid-cols-3 gap-3">
          {ATTENTION_FILTERS.map((f) => {
            const n = attention[f.key];
            return (
              <button
                key={f.key}
                onClick={() => (f.tab && n > 0 && f.key === "uncategorized" ? onTabChange(f.tab) : openAttention(f))}
                disabled={n === 0}
                className={`p-4 text-left rounded-lg border-2 transition-colors ${
                  n > 0
                    ? "border-orange-200 hover:border-orange-400 hover:bg-orange-50"
                    : "border-gray-100 bg-gray-50 text-gray-400 cursor-default"
                }`}
              >
                <div className={`text-2xl font-bold ${n > 0 ? "text-orange-700" : "text-gray-400"}`}>{n}</div>
                <div className="text-sm font-medium">{f.label}</div>
                {n > 0 && <div className="text-xs text-gray-500 mt-1">Click to review →</div>}
              </button>
            );
          })}
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* System health & monitoring */}
        <div className="bg-white rounded-2xl p-6 shadow">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">System status</h2>
            <button
              onClick={refreshAll}
              disabled={health.loading || monitoring.loading}
              className="text-sm px-3 py-1.5 rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50"
            >
              ↻ Refresh
            </button>
          </div>
          <div className="space-y-3">
            <div className={`p-4 rounded-lg ${healthStatus.color}`}>
              <div className="text-sm font-medium mb-1">Overall</div>
              <div className="text-lg font-semibold">{healthStatus.label}</div>
            </div>
            <div className="grid grid-cols-3 gap-3 text-sm">
              <div className="p-3 rounded-lg bg-blue-50 border border-blue-100">
                <div className="text-blue-600 font-medium">API</div>
                <div className="font-semibold text-blue-800">{health.loading ? "…" : health.api?.status || "Unknown"}</div>
              </div>
              <div className="p-3 rounded-lg bg-blue-50 border border-blue-100">
                <div className="text-blue-600 font-medium">Database</div>
                <div className="font-semibold text-blue-800">{health.loading ? "…" : health.db?.status || "Unknown"}</div>
              </div>
              <div
                className={`p-3 rounded-lg border ${
                  breaker?.state === "closed" ? "bg-blue-50 border-blue-100" : "bg-amber-50 border-amber-200"
                }`}
                title={breaker?.description}
              >
                <div className="text-blue-600 font-medium">BGG</div>
                <div className="font-semibold text-blue-800">
                  {monitoring.loading && !breaker ? "…" : breaker ? (breaker.state === "closed" ? "healthy" : breaker.state) : "Unknown"}
                </div>
              </div>
            </div>
            {breaker && breaker.state !== "closed" && (
              <p className="text-xs text-amber-800 bg-amber-50 rounded p-2">
                BoardGameGeek requests are being limited ({breaker.description}). Imports may fail until it recovers.
              </p>
            )}
            {refreshedAt && (
              <p className="text-xs text-gray-400">Updated {refreshedAt.toLocaleTimeString("en-NZ")}</p>
            )}
          </div>
        </div>

        {/* Failures */}
        <div className="bg-white rounded-2xl p-6 shadow">
          <h2 className="text-xl font-semibold mb-4">Background failures</h2>
          {!failures ? (
            <p className="text-sm text-gray-500">{monitoring.loading ? "Loading…" : "Failure data unavailable."}</p>
          ) : failures.failures.length === 0 ? (
            <p className="text-sm text-green-700">No unresolved failures. 👍</p>
          ) : (
            <ul className="divide-y divide-gray-100 max-h-64 overflow-y-auto">
              {failures.failures.map((f) => (
                <li key={f.id} className="py-2 flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-gray-800">
                      {f.task_type}
                      {f.game_id ? ` · game #${f.game_id}` : ""}
                    </div>
                    <div className="text-xs text-gray-500 truncate" title={f.error_message}>
                      {f.error_message}
                    </div>
                  </div>
                  <button
                    onClick={() => resolveFailure(f.id)}
                    className="shrink-0 text-xs px-2 py-1 rounded bg-gray-100 hover:bg-gray-200"
                  >
                    Resolve
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Recently added + quick actions */}
      <div className="grid lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl p-6 shadow">
          <h2 className="text-xl font-semibold mb-4">Recently added</h2>
          {recentlyAdded.length === 0 ? (
            <p className="text-sm text-gray-500">No games yet.</p>
          ) : (
            <ul className="divide-y divide-gray-100">
              {recentlyAdded.map((g) => (
                <li key={g.id} className="py-2 flex justify-between text-sm">
                  <span className="font-medium text-gray-800 truncate">{g.title}</span>
                  <span className="text-gray-500 shrink-0 ml-3">
                    {new Date(g.date_added).toLocaleDateString("en-NZ", { day: "numeric", month: "short" })}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="bg-white rounded-2xl p-6 shadow">
          <h2 className="text-xl font-semibold mb-4">Quick actions</h2>
          <div className="grid grid-cols-2 gap-3">
            {[
              ["add-games", "📥 Add games", "border-purple-200 hover:border-purple-400 hover:bg-purple-50"],
              ["manage-library", "📚 Manage library", "border-blue-200 hover:border-blue-400 hover:bg-blue-50"],
              ["categories", "🏷️ Categories", "border-green-200 hover:border-green-400 hover:bg-green-50"],
              ["advanced", "⚙️ Advanced tools", "border-gray-200 hover:border-gray-400 hover:bg-gray-50"],
            ].map(([id, label, cls]) => (
              <button
                key={id}
                onClick={() => onTabChange(id)}
                className={`p-4 text-left rounded-lg border-2 font-medium text-gray-800 transition-colors ${cls}`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
