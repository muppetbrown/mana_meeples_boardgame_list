// src/utils/libraryQuality.js
/**
 * "Needs attention" checks for owned games, shared by the Dashboard
 * (counts) and Manage Library (filtering).
 */
export const SLEEVE_UNKNOWN = (g) =>
  !g.has_sleeves || g.has_sleeves === "not_found" || g.has_sleeves === "check" || g.has_sleeves === "error";

export const ATTENTION_FILTERS = [
  { key: "uncategorized", label: "Uncategorized", test: (g) => !g.mana_meeple_category, tab: "categories" },
  { key: "sleeves_unknown", label: "Sleeve status unknown", test: SLEEVE_UNKNOWN },
  { key: "no_image", label: "Missing image", test: (g) => !g.cloudinary_url && !g.image_url },
  { key: "no_designers", label: "Missing designers", test: (g) => !Array.isArray(g.designers) || g.designers.length === 0 },
  { key: "no_complexity", label: "Missing complexity", test: (g) => !g.complexity },
  { key: "no_bgg_id", label: "No BGG link", test: (g) => !g.bgg_id },
];

export function attentionCounts(games) {
  const counts = {};
  ATTENTION_FILTERS.forEach((f) => {
    counts[f.key] = games.filter(f.test).length;
  });
  return counts;
}
