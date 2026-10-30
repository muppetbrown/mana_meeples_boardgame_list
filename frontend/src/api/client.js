// frontend/src/api/client.js
/**
 * API client with axios instance and all API methods
 * Uses centralized configuration from config/api.js
 * Phase 1 Performance: Added request deduplication
 */
import axios from "axios";
import { getApiUrl, imageProxyUrl as proxyUrl, generateSrcSet } from "../config/api";
import { safeStorage } from "../utils/storage";

/**
 * Axios instance configured for API communication
 * - Uses versioned API base URL (/api/v1)
 * - Includes credentials for cookie-based authentication (legacy)
 * - Automatically adds JWT token to Authorization header
 * - Has error interceptor for debugging and error handling
 * - 5 minute timeout for long-running operations (price imports, bulk operations)
 *
 * All API paths are automatically prefixed with the version (e.g., /api/v1)
 *
 * Note: Request deduplication is handled at the UI layer via useCallback and debouncing
 * to avoid interfering with test mocks.
 */
export const api = axios.create({
  baseURL: getApiUrl(''), // Use empty string to get versioned base: /api/v1
  withCredentials: true, // Enable cookie-based authentication (legacy support)
  timeout: 300000, // 5 minutes (300,000ms) - handles long imports without freezing
});

/**
 * Request interceptor to add JWT token to all requests
 */
api.interceptors.request.use(
  (config) => {
    // Get JWT token from safe storage (handles tracking prevention)
    const token = safeStorage.getItem("JWT_TOKEN");

    // Add Authorization header if token exists
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

/**
 * Debug overlay for development error visualization
 */
function showOverlay(msg) {
  // Dev-only: in production the staff UI shows toasts/inline errors instead of
  // a raw API dump covering the page header.
  if (!import.meta.env.DEV) return;
  try {
    let el = document.getElementById("debug-overlay");
    if (!el) {
      el = document.createElement("pre");
      el.id = "debug-overlay";
      el.style.cssText = `
        position:fixed; inset:10px 10px auto 10px; z-index:99999;
        background:#111; color:#0f0; padding:8px; max-height:40vh; overflow:auto;
        font:12px/1.3 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        border-radius:8px; opacity:.95;
      `;
      document.body.appendChild(el);
    }
    el.textContent = msg;
  } catch {
    // Fail silently if DOM manipulation fails
  }
}

/**
 * Response interceptor for error handling
 */
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const cfg = err.config || {};
    const status = err.response?.status;
    const statusText = err.response?.statusText;
    const body =
      typeof err.response?.data === "string"
        ? err.response.data.slice(0, 400)
        : JSON.stringify(err.response?.data, null, 2);

    // Handle timeout errors with clearer messaging
    if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
      const timeoutMsg = `API REQUEST TIMEOUT
URL: ${cfg.url}
The operation took too long (>5 minutes) and was cancelled.
This may happen with large imports or slow operations.
Try refreshing the page and checking if the operation completed.`;
      console.error(timeoutMsg);
      showOverlay(timeoutMsg);
      return Promise.reject(new Error('Request timeout - operation may still be processing. Please refresh and check results.'));
    }

    const msg = `API ERROR
URL: ${cfg.url}
Method: ${cfg.method}
Status: ${status ?? "—"} ${statusText ?? ""}
Message: ${err.message}
Body (first 400 chars):
${body}`;

    console.error(msg);
    showOverlay(msg);

    // Handle 401 errors by redirecting to login
    // (cfg.url is relative to the versioned baseURL, e.g. "/admin/games")
    const isAdminCall = /^\/?(api\/(v\d+\/)?)?admin\//.test(cfg.url || "");
    const isLoginCall = /admin\/login/.test(cfg.url || "");
    if (status === 401 && isAdminCall && !isLoginCall) {
      console.warn("Admin session invalid or expired, redirecting to login");
      safeStorage.removeItem("JWT_TOKEN");
      if (!window.location.pathname.includes("/staff/login")) {
        window.location.href = window.location.origin + window.location.pathname.replace(/\/staff.*/, "/staff/login");
      }
    }

    return Promise.reject(err);
  }
);

// ============================================================================
// PUBLIC API METHODS
// ============================================================================

/**
 * Get paginated list of games with filtering
 * @param {Object} params - Query parameters (q, category, players, page, page_size, etc.)
 * @returns {Promise<Object>} Response with total, page, page_size, items
 */
export async function getPublicGames(params = {}) {
  const r = await api.get("/public/games", { params });
  return r.data;
}

/**
 * Get single game by ID
 * @param {number} id - Game ID
 * @returns {Promise<Object>} Game data
 */
export async function getPublicGame(id) {
  const r = await api.get(`/public/games/${id}`);
  return r.data;
}

/**
 * Get category counts for filter buttons
 * @returns {Promise<Object>} Category counts object
 */
export async function getPublicCategoryCounts() {
  const r = await api.get("/public/category-counts");
  return r.data;
}

// ============================================================================
// ADMIN API METHODS - Game Management
// ============================================================================

/**
 * Get all games for admin interface
 * @returns {Promise<Array>} Array of all games
 */
export const getGames = async () => {
  try {
    const response = await api.get("/admin/games");
    return response.data || [];
  } catch (error) {
    console.error("Failed to load games:", error);
    return [];
  }
};

/**
 * Add a new game
 * @param {Object} payload - Game data
 * @returns {Promise<Object>} Created game data
 */
export const addGame = (payload) =>
  api.post("/admin/games", payload).then(r => r.data);

/**
 * Update game by ID
 * @param {number} gameId - Game ID
 * @param {Object} patch - Fields to update
 * @returns {Promise<Object>} Updated game data
 */
export async function updateGame(gameId, patch) {
  try {
    const r = await api.post(`/admin/games/${gameId}/update`, patch);
    return r.data;
  } catch (error) {
    console.warn("Update game API returned error but operation might have succeeded:", error);
    if (error.response?.status === 500 && error.response?.data) {
      console.log("500 error response data:", error.response.data);
    }
    throw error;
  }
}

/**
 * Delete game by ID
 * @param {number} gameId - Game ID
 * @returns {Promise<Object>} Deletion confirmation
 */
export async function deleteGame(gameId) {
  const r = await api.delete(`/admin/games/${gameId}`);
  return r.data;
}

/**
 * Get every game matching a quick-pick's auto-selection logic, for the
 * staff Quick Picks curation panel. Ignores exclusions so the full
 * algorithmic candidate list is visible.
 * @param {string} key - Quick-pick key: 'first' | 'kids' | 'group' | 'coop'
 * @returns {Promise<Array>} Array of games with their current excluded_quick_picks
 */
export async function getQuickPickCandidates(key) {
  const r = await api.get(`/admin/quick-picks/${key}/candidates`);
  return r.data;
}

// ============================================================================
// ADMIN API METHODS - Bulk Operations
// ============================================================================

/**
 * Bulk import games from CSV
 * @param {string} csv_data - CSV text data
 * @returns {Promise<Object>} Import results
 */
export const bulkImportCsv = (csv_data) =>
  api.post("/admin/bulk-import-csv", { csv_data }).then(r => r.data);

/**
 * Bulk categorize games from CSV
 * @param {string} csv_data - CSV text data
 * @returns {Promise<Object>} Categorization results
 */
export const bulkCategorizeCsv = (csv_data) =>
  api.post("/admin/bulk-categorize-csv", { csv_data }).then(r => r.data);

/**
 * Bulk update NZ designer flags from CSV
 * @param {string} csv_data - CSV text data
 * @returns {Promise<Object>} Update results
 */
export async function bulkUpdateNZDesigners(csv_data) {
  const r = await api.post("/admin/bulk-update-nz-designers", { csv_data });
  return r.data;
}

/**
 * Bulk update AfterGame game IDs from CSV
 * @param {string} csv_data - CSV text data (format: bgg_id,aftergame_game_id[,title])
 * @returns {Promise<Object>} Update results
 */
export async function bulkUpdateAfterGameIDs(csv_data) {
  const r = await api.post("/admin/bulk-update-aftergame-ids", { csv_data });
  return r.data;
}

/**
 * Re-import all games with enhanced BGG data
 * @returns {Promise<Object>} Re-import initiation confirmation
 */
export async function reimportAllGames() {
  const r = await api.post("/admin/reimport-all-games", {});
  return r.data;
}

/**
 * Re-import a selection of games with enhanced BGG data
 * @param {number[]} gameIds - Array of game IDs to re-import
 * @returns {Promise<Object>} Re-import initiation confirmation
 */
export async function reimportSelectedGames(gameIds) {
  const r = await api.post("/admin/reimport-selected-games", { game_ids: gameIds });
  return r.data;
}

/**
 * Fetch sleeve data for all games (sleeve data only, no full re-import)
 * @returns {Promise<Object>} Sleeve fetch initiation confirmation
 */
export async function fetchAllSleeveData() {
  const r = await api.post("/admin/fetch-all-sleeve-data", {});
  return r.data;
}

/**
 * Backfill Cloudinary URLs for all games with images
 * Pre-generates optimized Cloudinary URLs to eliminate redirect overhead
 * @returns {Promise<Object>} Backfill results with counts and errors
 */
export async function backfillCloudinaryUrls() {
  const r = await api.post("/admin/backfill-cloudinary-urls", {});
  return r.data;
}

/**
 * Fix PostgreSQL sequence for boardgames table
 * Resolves "duplicate key value violates unique constraint" errors
 * @returns {Promise<Object>} Sequence fix result with max_id and next_id
 */
export async function fixDatabaseSequence() {
  const r = await api.post("/admin/fix-sequence", {});
  return r.data;
}

// ============================================================================
// ADMIN API METHODS - Authentication
// ============================================================================

/**
 * Admin login with token
 * @param {string} token - Admin token
 * @returns {Promise<Object>} Login response with JWT
 */
export async function adminLogin(token) {
  const r = await api.post("/admin/login", { token });

  // Store JWT token in safe storage (handles tracking prevention)
  if (r.data.token) {
    safeStorage.setItem("JWT_TOKEN", r.data.token);
  }

  return r.data;
}

/**
 * Admin logout
 * @returns {Promise<Object>} Logout confirmation
 */
export async function adminLogout() {
  try {
    const r = await api.post("/admin/logout");
    return r.data;
  } finally {
    // Always clear the JWT locally, even if the API call fails
    safeStorage.removeItem("JWT_TOKEN");
  }
}

/**
 * Validate admin token/session
 * @returns {Promise<Object>} Validation response
 */
export async function validateAdminToken() {
  const r = await api.get("/admin/validate");
  return r.data;
}

// ============================================================================
// DEBUG & MONITORING API METHODS
// ============================================================================

/**
 * Get all unique BGG categories in database
 * @returns {Promise<Object>} Categories data
 */
export async function getDebugCategories() {
  const r = await api.get("/debug/categories");
  return r.data;
}

/**
 * Get database structure and sample data
 * @param {number} limit - Number of sample games to return
 * @returns {Promise<Object>} Database info
 */
export async function getDebugDatabaseInfo(limit = 50) {
  const r = await api.get("/debug/database-info", { params: { limit } });
  return r.data;
}

/**
 * Get performance metrics
 * @returns {Promise<Object>} Performance stats
 */
export async function getDebugPerformance() {
  const r = await api.get("/debug/performance");
  return r.data;
}

/**
 * Export games as CSV
 * @param {number} limit - Optional limit on number of games
 * @returns {Promise<Object>} CSV data
 */
export async function exportGamesCSV(limit = null) {
  const params = limit ? { limit } : {};
  const r = await api.get("/debug/export-games-csv", { params });
  return r.data;
}

// ============================================================================
// HEALTH CHECK API METHODS
// ============================================================================

/**
 * Basic health check
 * @returns {Promise<Object>} Health status
 */
export async function getHealthCheck() {
  const r = await api.get("/health");
  return r.data;
}

/**
 * Database health check
 * @returns {Promise<Object>} Database health status
 */
export async function getDbHealthCheck() {
  const r = await api.get("/health/db");
  return r.data;
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Re-export image utilities from centralized config
 */
export const imageProxyUrl = proxyUrl;
export { generateSrcSet };

// Import game from BoardGameGeek by BGG ID
export async function importFromBGG(bggId, force = false) {
  const r = await api.post("/admin/import/bgg", null, {
    params: { bgg_id: bggId, force }
  });
  return r.data;
}

// ============================================================================
// GAMES TO ADD API METHODS
// ============================================================================

/**
 * Get all candidate games on the 'games to add' list, annotated with
 * which library gaps (if any) each one would help fill.
 * @param {Object} params - Query parameters (on_buy_list, sort_by, sort_desc)
 * @returns {Promise<Object>} Response with total and items array
 */
export async function getBuyListGames(params = {}) {
  const r = await api.get("/admin/buy-list/games", { params });
  return r.data;
}

/**
 * Add a candidate game to the 'games to add' list
 * @param {Object} data - Buy list game data (bgg_id, rank, notes)
 * @returns {Promise<Object>} Created buy list entry
 */
export async function addToBuyList(data) {
  const r = await api.post("/admin/buy-list/games", data);
  return r.data;
}

/**
 * Update a 'games to add' entry
 * @param {number} buyListId - Buy list entry ID
 * @param {Object} data - Updated fields (rank, notes, on_buy_list)
 * @returns {Promise<Object>} Updated buy list entry
 */
export async function updateBuyListGame(buyListId, data) {
  const r = await api.put(`/admin/buy-list/games/${buyListId}`, data);
  return r.data;
}

/**
 * Remove a game from the 'games to add' list
 * @param {number} buyListId - Buy list entry ID
 * @returns {Promise<Object>} Success message
 */
export async function removeFromBuyList(buyListId) {
  const r = await api.delete(`/admin/buy-list/games/${buyListId}`);
  return r.data;
}

/**
 * Get where the owned collection is thin: category balance and
 * player-count coverage, for the 'games to add' dashboard.
 * @returns {Promise<Object>} { total_games, category_gaps, player_count_gaps }
 */
export async function getLibraryGaps() {
  const r = await api.get("/admin/buy-list/gaps");
  return r.data;
}

/**
 * Bulk import candidate games to the 'games to add' list from CSV file
 * @param {File} file - CSV file with columns: bgg_id (required), rank, notes
 * @returns {Promise<Object>} Import result with added, updated, skipped, errors counts
 */
export async function bulkImportBuyListCSV(file) {
  const formData = new FormData();
  formData.append("file", file);
  const r = await api.post("/admin/buy-list/bulk-import-csv", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return r.data;
}

/**
 * Re-rank 'games to add' entries to match a given display order: the Nth id
 * in orderedIds gets rank N (1-based).
 * @param {number[]} orderedIds - Buy list entry IDs in desired priority order
 * @returns {Promise<Object>} Response with total and items array (freshly ranked)
 */
export async function reorderBuyList(orderedIds) {
  const r = await api.put("/admin/buy-list/reorder", { ordered_ids: orderedIds });
  return r.data;
}

/**
 * Ask Claude for games worth adding, grounded in this library's actual
 * collection and gap analysis. Each suggestion is best-effort matched to a
 * BGG ID so it can be added with one click; otherwise a BGG search link is
 * provided instead.
 * @param {number} count - How many suggestions to request (1-12)
 * @param {boolean} onlyAvailable - Drop suggestions no NZ distributor lists
 *   (each result carries distro_availability: per-distributor stock/cost)
 * @returns {Promise<Object>} { suggestions: [...] }
 */
export async function suggestBuyListGames(count = 6, onlyAvailable = true) {
  const r = await api.post("/admin/buy-list/suggest", { count, only_available: onlyAvailable });
  return r.data;
}

/**
 * Board games selling well / in stock at HL Timaru that aren't yet in this
 * library - a demand signal for what to add. Each item is tagged
 * match_status: "linked" (fuzzy-matched to an existing game) or "unmatched"
 * (a true new candidate).
 * @returns {Promise<Object>} Response with total and items array
 */
export async function getHLStockSignals() {
  const r = await api.get("/admin/buy-list/hl-signals");
  return r.data;
}

/**
 * Manually confirm or correct the link between an HL stock product and a
 * game already in this library.
 * @param {number} hlInternalId - HL Timaru product internal_id
 * @param {number} gameId - This library's game id to link it to
 */
export async function linkHLStockSignal(hlInternalId, gameId) {
  const r = await api.post(`/admin/buy-list/hl-signals/${hlInternalId}/link`, { game_id: gameId });
  return r.data;
}

/**
 * Search the HL distributor catalogue (distro_codes) by product name or code,
 * to find a code to manually link to a game.
 * @param {string} q - Search text (min 2 chars)
 * @returns {Promise<Object>} { items: [{ distributor, distro_code, distro_product_name, cost_price_ex_gst, qty_available }] }
 */
export async function searchDistroCodes(q) {
  const r = await api.get("/admin/buy-list/distro-codes/search", { params: { q } });
  return r.data;
}

/**
 * Manually link a game to one distributor product code, for when the
 * automatic title match misses it.
 * @returns {Promise<Object>} { link_id, distro_availability } - refreshed availability for the game
 */
export async function linkGameToDistroCode(gameId, distributor, distroCode) {
  const r = await api.post(`/admin/buy-list/games/${gameId}/distro-links`, {
    distributor,
    distro_code: distroCode,
  });
  return r.data;
}

/**
 * Remove a manual game <-> distributor code link.
 * @returns {Promise<Object>} { id, distro_availability } - refreshed availability for the game
 */
export async function unlinkGameDistroCode(linkId) {
  const r = await api.delete(`/admin/buy-list/distro-links/${linkId}`);
  return r.data;
}

/**
 * Mark an HL stock product as not a real board-game candidate (e.g.
 * miscategorized at HL), excluding it from future signal lists.
 * @param {number} hlInternalId - HL Timaru product internal_id
 */
export async function dismissHLStockSignal(hlInternalId) {
  const r = await api.post(`/admin/buy-list/hl-signals/${hlInternalId}/dismiss`);
  return r.data;
}

/**
 * BoardGameGeek's current "Hotness" list, annotated with whether each game
 * is already owned or already on the games-to-add list.
 * @param {number} limit - How many trending games to return (1-50)
 * @returns {Promise<Object>} { trending: [{ bgg_id, rank, title, year, thumbnail_url, status }] }
 */
export async function getTrendingGames(limit = 20) {
  const r = await api.get("/admin/buy-list/trending", { params: { limit } });
  return r.data;
}

/**
 * Curated Spiel des Jahres / Kennerspiel des Jahres / Kinderspiel des Jahres
 * winners, annotated with whether each is already owned or already on the
 * games-to-add list.
 * @param {number} years - How many most-recent award years to include, per award
 * @returns {Promise<Object>} { award_winners: [{ year, award, award_label, title, bgg_id, thumbnail_url, status, bgg_search_url }] }
 */
export async function getAwardWinners(years = 6) {
  const r = await api.get("/admin/buy-list/award-winners", { params: { years } });
  return r.data;
}

// ============================================================================
// SLEEVE MANAGEMENT API METHODS
// ============================================================================

/**
 * Generate sleeve shopping list for selected games
 * @param {Array<number>} gameIds - Array of game IDs
 * @returns {Promise<Array>} Shopping list items
 */
export async function generateSleeveShoppingList(gameIds) {
  const r = await api.post("/admin/sleeves/shopping-list", { game_ids: gameIds });
  return r.data;
}

/**
 * Trigger GitHub Actions workflow to fetch sleeve data for selected games
 * @param {Array<number>} gameIds - Array of game IDs
 * @returns {Promise<Object>} Workflow trigger confirmation
 */
export async function triggerSleeveFetch(gameIds) {
  const r = await api.post("/admin/trigger-sleeve-fetch", gameIds);
  return r.data;
}

/**
 * Get sleeve data for a specific game
 * @param {number} gameId - Game ID
 * @returns {Promise<Array>} Array of sleeve objects
 */
export async function getGameSleeves(gameId) {
  const r = await api.get(`/admin/sleeves/game/${gameId}`);
  return r.data;
}

/**
 * Manually add a sleeve requirement for a game (no BGG scrape needed)
 * @param {number} gameId - Game ID
 * @param {Object} data - { card_name, width_mm, height_mm, quantity, notes }
 * @returns {Promise<Object>} Created sleeve record
 */
export async function createGameSleeve(gameId, data) {
  const r = await api.post(`/admin/sleeves/game/${gameId}`, data);
  return r.data;
}

/**
 * Edit a sleeve requirement (name, size, quantity, notes); backend re-matches it
 * @param {number} sleeveId - Sleeve record ID
 * @param {Object} data - { card_name, width_mm, height_mm, quantity, notes }
 * @returns {Promise<Object>} Updated sleeve record
 */
export async function updateGameSleeve(sleeveId, data) {
  const r = await api.put(`/admin/sleeves/sleeve/${sleeveId}`, data);
  return r.data;
}

/**
 * Delete a sleeve requirement record
 * @param {number} sleeveId - Sleeve record ID
 * @returns {Promise<Object>} Deletion confirmation
 */
export async function deleteGameSleeve(sleeveId) {
  const r = await api.delete(`/admin/sleeves/sleeve/${sleeveId}`);
  return r.data;
}

/**
 * Manually set a game's sleeve-investigation status (no BGG scrape needed)
 * @param {number} gameId - Game ID
 * @param {'none'|'check'} status - 'none' = no cards to sleeve, 'check' = reset to needs-investigation
 * @returns {Promise<Object>} { success, game_id, has_sleeves }
 */
export async function updateGameSleeveStatus(gameId, status) {
  const r = await api.patch(`/admin/sleeves/game/${gameId}/status`, { status });
  return r.data;
}

/**
 * Update the sleeved status of a specific sleeve record
 * When marking as sleeved, auto-deducts stock from matched product
 * @param {number} sleeveId - Sleeve record ID
 * @param {boolean} isSleeved - Whether this sleeve type is sleeved
 * @returns {Promise<Object>} Update confirmation with stock_info
 */
export async function updateSleeveStatus(sleeveId, isSleeved) {
  const r = await api.patch(`/admin/sleeves/sleeve/${sleeveId}`, {
    is_sleeved: isSleeved
  });
  return r.data;
}

// ============================================================================
// SLEEVE INVENTORY API METHODS
// ============================================================================

/**
 * Get all sleeve products (inventory)
 * @param {string} [distributor] - Optional distributor filter
 * @returns {Promise<Array>} Array of sleeve products
 */
export async function getSleeveProducts(distributor) {
  const params = distributor ? { distributor } : {};
  const r = await api.get("/admin/sleeves/products", { params });
  return r.data;
}

/**
 * Create a new sleeve product
 * @param {Object} data - Product data
 * @returns {Promise<Object>} Created product
 */
export async function createSleeveProduct(data) {
  const r = await api.post("/admin/sleeves/products", data);
  return r.data;
}

/**
 * Update an existing sleeve product
 * @param {number} id - Product ID
 * @param {Object} data - Fields to update
 * @returns {Promise<Object>} Updated product
 */
export async function updateSleeveProduct(id, data) {
  const r = await api.put(`/admin/sleeves/products/${id}`, data);
  return r.data;
}

/**
 * Delete a sleeve product
 * @param {number} id - Product ID
 * @returns {Promise<Object>} Deletion confirmation
 */
export async function deleteSleeveProduct(id) {
  const r = await api.delete(`/admin/sleeves/products/${id}`);
  return r.data;
}

/**
 * Link unlinked sleeve products to the HL Timaru distro_codes catalogue
 * (by distributor + item id, then exact name).
 * @returns {Promise<Object>} { linked, already_linked, unmatched, linked_items }
 */
export async function autoLinkSleeveDistroCodes() {
  const r = await api.post("/admin/sleeves/distro/auto-link");
  return r.data;
}

/**
 * Remove a sleeve product's distro code link
 * @param {number} id - Product ID
 * @returns {Promise<Object>} Updated product
 */
export async function unlinkSleeveDistroCode(id) {
  const r = await api.delete(`/admin/sleeves/products/${id}/distro-link`);
  return r.data;
}

/**
 * Sleeves in the HL distributor catalogue that aren't in sleeve inventory,
 * with the currently-needed sizes each would fit.
 * @param {boolean} [includeAll] - Also include sleeves that fit no current need
 * @returns {Promise<Object>} { count, items }
 */
export async function getUnlistedCatalogueSleeves(includeAll = false) {
  const r = await api.get("/admin/sleeves/catalogue/unlisted", { params: { include_all: includeAll } });
  return r.data;
}

/**
 * Run matching across all unsleeved games
 * @returns {Promise<Object>} Matching results (matched, unmatched, total)
 */
export async function runSleeveMatching() {
  const r = await api.post("/admin/sleeves/match-all");
  return r.data;
}

/**
 * Get aggregated to-order list
 * @returns {Promise<Array>} Sleeve sizes needing orders with product recommendations
 */
export async function getToOrderList() {
  const r = await api.get("/admin/sleeves/to-order");
  return r.data;
}

/**
 * Get games ready to sleeve (all requirements covered by stock)
 * @returns {Promise<Array>} Games with full stock coverage
 */
export async function getToSleeveList() {
  const r = await api.get("/admin/sleeves/to-sleeve");
  return r.data;
}

/**
 * Get the status of the most recent "Fetch Sleeve Data" GitHub Actions run,
 * plus a DB-wide sleeve-coverage snapshot.
 * @returns {Promise<Object>} { workflow_configured, status, conclusion, html_url, coverage, ... }
 */
export async function getSleeveFetchStatus() {
  const r = await api.get("/admin/sleeves/fetch-status");
  return r.data;
}

/**
 * Generate PDF labels for selected games
 * @param {Array<number>} gameIds - Array of game IDs to generate labels for
 * @returns {Promise<Blob>} PDF blob ready for download
 */
export async function generateGameLabels(gameIds) {
  const response = await api.post('/admin/print-labels', {
    game_ids: gameIds
  }, {
    responseType: 'blob' // Important for PDF download
  });
  return response.data;
}


// ============================================================================
// ADMIN MONITORING
// ============================================================================

/**
 * Get recent background task failures (admin)
 * @param {Object} params - { resolved, task_type, limit }
 */
export async function getBackgroundFailures(params = {}) {
  const r = await api.get("/admin/monitoring/background-failures", { params });
  return r.data;
}

/**
 * Mark a background task failure as resolved (admin)
 */
export async function resolveBackgroundFailure(failureId) {
  const r = await api.post(`/admin/monitoring/background-failures/${failureId}/resolve`);
  return r.data;
}

/**
 * Get BGG circuit breaker status (admin)
 */
export async function getCircuitBreakerStatus() {
  const r = await api.get("/admin/monitoring/circuit-breaker-status");
  return r.data;
}
