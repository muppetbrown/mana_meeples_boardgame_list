/**
 * Game Data Formatting Utilities
 * Centralized formatting functions for consistent game data display
 */

/**
 * Format BGG rating for display (0-10 scale with 1 decimal place)
 * @param {number|null} rating - The average rating value
 * @returns {string|null} Formatted rating or null if invalid
 */
export function formatRating(rating) {
  if (!rating || rating === 0) return null;
  return parseFloat(rating).toFixed(1);
}

/**
 * Format complexity rating for display (1-5 scale with 1 decimal place)
 * @param {number|null} complexity - The complexity value
 * @returns {string|null} Formatted complexity or null if invalid
 */
export function formatComplexity(complexity) {
  if (!complexity || complexity === 0) return null;
  return parseFloat(complexity).toFixed(1);
}

/**
 * Format playtime with range or single value
 * @param {number|null} min - Minimum playtime in minutes
 * @param {number|null} max - Maximum playtime in minutes
 * @returns {string} Formatted playtime string
 */
export function formatTime(min, max) {
  if (min && max && min !== max) {
    return `${min}-${max} min`;
  } else if (min || max) {
    return `${min || max} min`;
  } else {
    return "Time varies";
  }
}

/**
 * Format player count with expansion notation
 * Shows asterisk (*) if expansions extend the player count
 * @param {Object} game - The game object
 * @param {number} game.players_min - Base minimum players
 * @param {number} game.players_max - Base maximum players
 * @param {number} [game.players_min_with_expansions] - Minimum with expansions
 * @param {number} [game.players_max_with_expansions] - Maximum with expansions
 * @param {boolean} [game.has_player_expansion] - Whether game has player count expansion
 * @returns {string|null} Formatted player count or null if no data
 */
export function formatPlayerCount(game) {
  if (!game) return null;

  const baseMin = game.players_min;
  const baseMax = game.players_max;
  const expMin = game.players_min_with_expansions;
  const expMax = game.players_max_with_expansions;
  const hasExpansion = game.has_player_expansion;

  if (!baseMin || !baseMax) return null;

  // If expansion extends player count, show expanded range with asterisk
  if (hasExpansion && expMax > baseMax) {
    const displayMin = expMin || baseMin;
    const displayMax = expMax;
    const range = displayMin === displayMax ? `${displayMax}` : `${displayMin}-${displayMax}`;
    return `${range}*`;
  }

  // Otherwise just show base range
  return baseMin === baseMax ? `${baseMin}` : `${baseMin}-${baseMax}`;
}
