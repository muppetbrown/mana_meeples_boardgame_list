// src/components/staff/tabs/QuickPicksTab.jsx
import React, { useState, useEffect, useCallback } from "react";
import { useStaff } from "../../../context/StaffContext";
import { getQuickPickCandidates, updateGame } from "../../../api/client";
import { QUICK_PICKS } from "../../../utils/libraryFilters";

/**
 * Per quick-pick, which game field to surface as the "why it's here" hint,
 * plus a short explanation of the auto-selection rule shown to staff.
 */
const QUICK_PICK_INFO = {
  first: {
    rule: "Auto-included when complexity < 1.5.",
    stat: (g) => (g.complexity ? `Complexity ${g.complexity.toFixed(2)}` : "—"),
  },
  kids: {
    rule: "Auto-included when categorized Kids & Families, or complexity < 1.5 and min age ≤ 10.",
    stat: (g) => [g.mana_meeple_category === "KIDS_FAMILIES" ? "Kids & Families" : null, g.min_age != null ? `Min age ${g.min_age}` : null].filter(Boolean).join(" · ") || "—",
  },
  group: {
    rule: "Auto-included when max players ≥ 6.",
    stat: (g) => (g.players_max ? `Up to ${g.players_max} players` : "—"),
  },
  coop: {
    rule: "Auto-included when cooperative, or categorized Co-op & Adventure.",
    stat: (g) => [g.is_cooperative ? "Cooperative" : null, g.mana_meeple_category === "COOP_ADVENTURE" ? "Co-op & Adventure" : null].filter(Boolean).join(" · ") || "—",
  },
};

export function QuickPicksTab() {
  const { showToast } = useStaff();
  const [activeKey, setActiveKey] = useState(QUICK_PICKS[0].key);
  const [games, setGames] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [pendingIds, setPendingIds] = useState(() => new Set());

  const loadCandidates = useCallback(async (key) => {
    setIsLoading(true);
    try {
      const data = await getQuickPickCandidates(key);
      setGames(data);
    } catch (error) {
      showToast("Failed to load quick-pick candidates", "error");
      setGames([]);
    } finally {
      setIsLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    loadCandidates(activeKey);
  }, [activeKey, loadCandidates]);

  const toggleExclusion = async (game) => {
    const currentlyExcluded = (game.excluded_quick_picks || []).includes(activeKey);
    const nextExcluded = currentlyExcluded
      ? game.excluded_quick_picks.filter((k) => k !== activeKey)
      : [...(game.excluded_quick_picks || []), activeKey];

    setPendingIds((prev) => new Set(prev).add(game.id));
    try {
      await updateGame(game.id, { excluded_quick_picks: nextExcluded });
      setGames((prev) => prev.map((g) => (g.id === game.id ? { ...g, excluded_quick_picks: nextExcluded } : g)));
      showToast(
        currentlyExcluded
          ? `"${game.title}" restored to ${activeLabel}`
          : `"${game.title}" removed from ${activeLabel}`,
        "success"
      );
    } catch (error) {
      showToast("Failed to update game", "error");
    } finally {
      setPendingIds((prev) => {
        const next = new Set(prev);
        next.delete(game.id);
        return next;
      });
    }
  };

  const activePick = QUICK_PICKS.find((qp) => qp.key === activeKey);
  const activeLabel = activePick?.label || activeKey;
  const info = QUICK_PICK_INFO[activeKey];
  const includedCount = games.filter((g) => !(g.excluded_quick_picks || []).includes(activeKey)).length;
  const excludedCount = games.length - includedCount;

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl p-6 shadow">
        <h2 className="text-xl font-semibold mb-1">Quick Picks Curation</h2>
        <p className="text-sm text-gray-600 mb-4">
          Review the games each "Who's playing today?" quick-pick auto-selects on the public library, and remove
          any that are a bad fit (BGG data can't flag mature content, so this is where you catch it).
        </p>

        <div className="flex flex-wrap gap-2 mb-4" role="tablist" aria-label="Quick pick">
          {QUICK_PICKS.map((qp) => (
            <button
              key={qp.key}
              role="tab"
              aria-selected={activeKey === qp.key}
              onClick={() => setActiveKey(qp.key)}
              className={`px-4 py-2 rounded-lg text-sm font-medium border-2 transition-colors ${
                activeKey === qp.key
                  ? "bg-purple-600 text-white border-purple-600"
                  : "bg-white text-gray-700 border-gray-300 hover:border-purple-300"
              }`}
            >
              <span aria-hidden="true" className="mr-1.5">{qp.icon}</span>
              {qp.label}
            </button>
          ))}
        </div>

        {info && (
          <div className="mb-4 p-3 bg-purple-50 rounded-lg border border-purple-200 text-sm text-purple-900">
            {info.rule}
          </div>
        )}

        <div className="text-sm text-gray-600 mb-3">
          {isLoading ? (
            "Loading…"
          ) : (
            <>
              <span className="font-semibold text-gray-900">{includedCount}</span> currently shown
              {excludedCount > 0 && (
                <>
                  {" "}· <span className="font-semibold text-gray-900">{excludedCount}</span> excluded
                </>
              )}
            </>
          )}
        </div>

        {!isLoading && games.length === 0 && (
          <p className="text-sm text-gray-500 py-6 text-center">No games currently match this quick-pick's criteria.</p>
        )}

        <div className="divide-y divide-gray-200 max-h-[32rem] overflow-y-auto border border-gray-200 rounded-lg">
          {games.map((game) => {
            const excluded = (game.excluded_quick_picks || []).includes(activeKey);
            const isPending = pendingIds.has(game.id);
            return (
              <div
                key={game.id}
                className={`flex items-center justify-between gap-4 p-3 ${excluded ? "bg-gray-50" : ""}`}
              >
                <div className="min-w-0">
                  <div className={`font-medium truncate ${excluded ? "text-gray-400 line-through" : "text-gray-900"}`}>
                    {game.title}
                  </div>
                  <div className="text-xs text-gray-500">{info?.stat(game)}</div>
                </div>
                <button
                  onClick={() => toggleExclusion(game)}
                  disabled={isPending}
                  aria-pressed={!excluded}
                  className={`shrink-0 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors disabled:opacity-50 ${
                    excluded
                      ? "bg-purple-100 text-purple-700 hover:bg-purple-200"
                      : "bg-white text-gray-600 border border-gray-300 hover:border-red-300 hover:text-red-600"
                  }`}
                >
                  {isPending ? "Saving…" : excluded ? "Restore" : "Remove"}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default QuickPicksTab;
