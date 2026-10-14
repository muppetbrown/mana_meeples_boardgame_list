// src/utils/sleeveGroups.js
/**
 * Common sleeve size groups, so inventory and order lists can be browsed by
 * the names people actually use ("Mini American", "Standard European", ...).
 *
 * Nominal sizes are the card sizes each group is made for, in mm. Sleeve
 * products store *inner* size, which is the card size plus up to ~1mm wide /
 * ~5mm tall slack (see backend services/sleeve_matching.py), so classification
 * accepts a window around the nominal size.
 *
 * A group keyword in the product name (e.g. "... Mini American ...") always
 * wins over size, because a few sizes sit close together.
 */
export const SLEEVE_GROUPS = [
  { key: "mini_american", label: "Mini American", width: 41, height: 63, keyword: /mini[\s_-]*(american|us)\b/i },
  { key: "mini_european", label: "Mini European", width: 45, height: 68, keyword: /mini[\s_-]*(european|euro)\b/i },
  { key: "standard_american", label: "Standard American", width: 56, height: 87, keyword: /standard[\s_-]*(american|us)\b/i },
  { key: "standard_european", label: "Standard European", width: 59, height: 92, keyword: /standard[\s_-]*(european|euro)\b/i },
  { key: "standard_card", label: "Standard Card Game", width: 63.5, height: 88, keyword: /standard[\s_-]*card|poker|\bmtg\b/i },
  { key: "square", label: "Square", width: 73, height: 73, keyword: /(?<!mini[\s_-])square/i },
  { key: "tarot", label: "Tarot", width: 70, height: 120, keyword: /tarot/i },
];

export const OTHER_GROUP = { key: "other", label: "Other sizes" };

// Accepted window around a nominal size (inner size vs card size)
const WIDTH_WINDOW = [-1.5, 2.5];
const HEIGHT_WINDOW = [-2.5, 6];

const inWindow = (delta, [lo, hi]) => delta >= lo && delta <= hi;

/**
 * Classify a sleeve product or card requirement.
 * @param {{name?: string, width_mm: number, height_mm: number}} item
 * @returns {{key: string, label: string}} one of SLEEVE_GROUPS or OTHER_GROUP
 */
export function classifySleeve({ name, width_mm, height_mm }) {
  if (name) {
    const byName = SLEEVE_GROUPS.find((g) => g.keyword.test(name));
    if (byName) return byName;
  }
  const w = Number(width_mm);
  const h = Number(height_mm);
  if (!Number.isFinite(w) || !Number.isFinite(h)) return OTHER_GROUP;

  let best = null;
  let bestScore = Infinity;
  for (const g of SLEEVE_GROUPS) {
    const dw = w - g.width;
    const dh = h - g.height;
    if (!inWindow(dw, WIDTH_WINDOW) || !inWindow(dh, HEIGHT_WINDOW)) continue;
    const score = Math.abs(dw) / 2 + Math.abs(dh) / 4;
    if (score < bestScore) {
      best = g;
      bestScore = score;
    }
  }
  return best || OTHER_GROUP;
}

export const groupSizeLabel = (g) => (g.width ? `${g.width} × ${g.height} mm` : "");

/**
 * Bucket items into ordered groups: SLEEVE_GROUPS order first, "Other" last.
 * Empty groups are omitted.
 * @returns {Array<{group, items}>}
 */
export function groupItems(items, getSleeve) {
  const buckets = new Map();
  items.forEach((item) => {
    const g = classifySleeve(getSleeve(item));
    if (!buckets.has(g.key)) buckets.set(g.key, { group: g, items: [] });
    buckets.get(g.key).items.push(item);
  });
  return [...SLEEVE_GROUPS, OTHER_GROUP].map((g) => buckets.get(g.key)).filter(Boolean);
}
