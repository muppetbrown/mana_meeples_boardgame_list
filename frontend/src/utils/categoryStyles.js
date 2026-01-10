/**
 * Category Styling Utilities
 * Centralized category color definitions for consistent styling across the application
 */

/**
 * Solid background category styles (for cards, badges, compact displays)
 * WCAG AAA contrast ratios for accessibility
 */
export const CATEGORY_STYLES = {
  "GATEWAY_STRATEGY": "bg-emerald-700 text-white border-emerald-800",
  "KIDS_FAMILIES": "bg-purple-700 text-white border-purple-800",
  "CORE_STRATEGY": "bg-blue-800 text-white border-blue-900",
  "COOP_ADVENTURE": "bg-orange-700 text-white border-orange-800",
  "PARTY_ICEBREAKERS": "bg-amber-800 text-white border-amber-900",
  "default": "bg-slate-700 text-white border-slate-800"
};

/**
 * Gradient background category styles (for detail pages, headers)
 */
export const CATEGORY_GRADIENT_STYLES = {
  "GATEWAY_STRATEGY": "bg-linear-to-r from-emerald-500 to-teal-500 text-white",
  "KIDS_FAMILIES": "bg-linear-to-r from-purple-500 to-pink-500 text-white",
  "CORE_STRATEGY": "bg-linear-to-r from-blue-600 to-indigo-600 text-white",
  "COOP_ADVENTURE": "bg-linear-to-r from-orange-500 to-red-500 text-white",
  "PARTY_ICEBREAKERS": "bg-linear-to-r from-yellow-500 to-amber-500 text-white",
  "default": "bg-linear-to-r from-slate-500 to-gray-500 text-white"
};

/**
 * Get category style classes
 * @param {string} category - The mana_meeple_category value
 * @param {boolean} gradient - Whether to use gradient styles (default: false)
 * @returns {string} Tailwind CSS classes for the category
 */
export function getCategoryStyle(category, gradient = false) {
  const styles = gradient ? CATEGORY_GRADIENT_STYLES : CATEGORY_STYLES;
  return styles[category] || styles.default;
}
