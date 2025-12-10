// frontend/src/api/client.js
/**
 * API client with axios instance and all API methods
 * Uses centralized configuration from config/api.js
 */
import axios from "axios";
import { API_BASE, imageProxyUrl as proxyUrl } from "../config/api";

/**
 * Axios instance configured for API communication
 * - Includes credentials for cookie-based authentication
 * - Has error interceptor for debugging and error handling
 */
export const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true, // Enable cookie-based authentication
});

/**
 * Debug overlay for development error visualization
 */
function showOverlay(msg) {
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
    if (status === 401 && cfg.url?.includes("/api/admin")) {
      console.warn("Admin session invalid or expired, redirecting to login");
      if (!window.location.pathname.includes("/staff/login")) {
        window.location.href = window.location.origin + window.location.pathname.replace(/\/staff.*/, "/staff/login");
      }
    }

    return Promise.reject(err);
  }
);

/**
 * Helper to get admin token from localStorage (legacy fallback)
 * @returns {Object} Headers object with admin token if available
 *
 * NOTE: This is kept for backward compatibility but the primary authentication
 * method is now cookie-based via the admin_session cookie set by the login endpoint.
 * Most admin operations should work without explicit headers.
 */
function getAdminHeaders() {
  const token = localStorage.getItem("ADMIN_TOKEN");
  return token ? { "X-Admin-Token": token } : {};
}

// ============================================================================
// PUBLIC API METHODS
// ============================================================================

/**
 * Get paginated list of games with filtering
 * @param {Object} params - Query parameters (q, category, players, page, page_size, etc.)
 * @returns {Promise<Object>} Response with total, page, page_size, items
 */
export async function getPublicGames(params = {}) {
  const r = await api.get("/api/public/games", { params });
  return r.data;
}

/**
 * Get single game by ID
 * @param {number} id - Game ID
 * @returns {Promise<Object>} Game data
 */
export async function getPublicGame(id) {
  const r = await api.get(`/api/public/games/${id}`);
  return r.data;
}

/**
 * Get category counts for filter buttons
 * @returns {Promise<Object>} Category counts object
 */
export async function getPublicCategoryCounts() {
  const r = await api.get("/api/public/category-counts");
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
    const response = await api.get("/api/public/games", {
      params: { page_size: 1000 }
    });
    return response.data.items || [];
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
  api.post("/api/admin/games", payload).then(r => r.data);

/**
 * Update game by ID
 * @param {number} gameId - Game ID
 * @param {Object} patch - Fields to update
 * @returns {Promise<Object>} Updated game data
 */
export async function updateGame(gameId, patch) {
  try {
    const r = await api.post(`/api/admin/games/${gameId}/update`, patch);
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
  const r = await api.delete(`/api/admin/games/${gameId}`);
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
  api.post("/api/admin/bulk-import-csv", { csv_data }).then(r => r.data);

/**
 * Bulk categorize games from CSV
 * @param {string} csv_data - CSV text data
 * @returns {Promise<Object>} Categorization results
 */
export const bulkCategorizeCsv = (csv_data) =>
  api.post("/api/admin/bulk-categorize-csv", { csv_data }).then(r => r.data);

/**
 * Bulk update NZ designer flags from CSV
 * @param {string} csv_data - CSV text data
 * @returns {Promise<Object>} Update results
 */
export async function bulkUpdateNZDesigners(csv_data) {
  const r = await api.post("/api/admin/bulk-update-nz-designers", { csv_data });
  return r.data;
}

/**
 * Re-import all games with enhanced BGG data
 * @returns {Promise<Object>} Re-import initiation confirmation
 */
export async function reimportAllGames() {
  const r = await api.post("/api/admin/reimport-all-games", {});
  return r.data;
}

/**
 * Fix PostgreSQL sequence for boardgames table
 * Resolves "duplicate key value violates unique constraint" errors
 * @returns {Promise<Object>} Sequence fix result with max_id and next_id
 */
export async function fixDatabaseSequence() {
  const r = await api.post("/api/admin/fix-sequence", {});
  return r.data;
}

// ============================================================================
// ADMIN API METHODS - Authentication
// ============================================================================

/**
 * Admin login with token
 * @param {string} token - Admin token
 * @returns {Promise<Object>} Login response
 */
export async function adminLogin(token) {
  const r = await api.post("/api/admin/login", { token });
  return r.data;
}

/**
 * Admin logout
 * @returns {Promise<Object>} Logout confirmation
 */
export async function adminLogout() {
  const r = await api.post("/api/admin/logout");
  return r.data;
}

/**
 * Validate admin token/session
 * @returns {Promise<Object>} Validation response
 */
export async function validateAdminToken() {
  const r = await api.get("/api/admin/validate");
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
  const r = await api.get("/api/debug/categories");
  return r.data;
}

/**
 * Get database structure and sample data
 * @param {number} limit - Number of sample games to return
 * @returns {Promise<Object>} Database info
 */
export async function getDebugDatabaseInfo(limit = 50) {
  const r = await api.get("/api/debug/database-info", { params: { limit } });
  return r.data;
}

/**
 * Get performance metrics
 * @returns {Promise<Object>} Performance stats
 */
export async function getDebugPerformance() {
  const r = await api.get("/api/debug/performance");
  return r.data;
}

/**
 * Export games as CSV
 * @param {number} limit - Optional limit on number of games
 * @returns {Promise<Object>} CSV data
 */
export async function exportGamesCSV(limit = null) {
  const params = limit ? { limit } : {};
  const r = await api.get("/api/debug/export-games-csv", { params });
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
  const r = await api.get("/api/health");
  return r.data;
}

/**
 * Database health check
 * @returns {Promise<Object>} Database health status
 */
export async function getDbHealthCheck() {
  const r = await api.get("/api/health/db");
  return r.data;
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Re-export image proxy URL helper from centralized config
 */
export const imageProxyUrl = proxyUrl;

// Import game from BoardGameGeek by BGG ID
export async function importFromBGG(bggId, force = false) {
  const r = await api.post("/api/admin/import/bgg", null, {
    params: { bgg_id: bggId, force }
  });
  return r.data;
}

// ============================================================================
// BUY LIST API METHODS
// ============================================================================

/**
 * Get all games on the buy list with pricing data
 * @param {Object} params - Query parameters (on_buy_list, lpg_status, buy_filter, sort_by, sort_desc)
 * @returns {Promise<Object>} Response with total and items array
 */
export async function getBuyListGames(params = {}) {
  const r = await api.get("/api/admin/buy-list/games", { params });
  return r.data;
}

/**
 * Add a game to the buy list
 * @param {Object} data - Buy list game data (game_id, rank, bgo_link, lpg_rrp, lpg_status)
 * @returns {Promise<Object>} Created buy list entry
 */
export async function addToBuyList(data) {
  const r = await api.post("/api/admin/buy-list/games", data);
  return r.data;
}

/**
 * Update buy list game details
 * @param {number} buyListId - Buy list entry ID
 * @param {Object} data - Updated fields (rank, bgo_link, lpg_rrp, lpg_status, on_buy_list)
 * @returns {Promise<Object>} Updated buy list entry
 */
export async function updateBuyListGame(buyListId, data) {
  const r = await api.put(`/api/admin/buy-list/games/${buyListId}`, data);
  return r.data;
}

/**
 * Remove a game from the buy list
 * @param {number} buyListId - Buy list entry ID
 * @returns {Promise<Object>} Success message
 */
export async function removeFromBuyList(buyListId) {
  const r = await api.delete(`/api/admin/buy-list/games/${buyListId}`);
  return r.data;
}

/**
 * Import price data from JSON file
 * @param {string} sourceFile - Filename of JSON price data
 * @returns {Promise<Object>} Import result with counts
 */
export async function importPrices(sourceFile) {
  const r = await api.post("/api/admin/buy-list/import-prices", null, {
    params: { source_file: sourceFile }
  });
  return r.data;
}

/**
 * Get last price update timestamp
 * @returns {Promise<Object>} Last update info (last_updated, source_file)
 */
export async function getLastPriceUpdate() {
  const r = await api.get("/api/admin/buy-list/last-updated");
  return r.data;
}

/**
 * Bulk import buy list games from CSV file
 * @param {File} file - CSV file with columns: bgg_id (required), rank, bgo_link, lpg_rrp, lpg_status
 * @returns {Promise<Object>} Import result with added, updated, skipped, errors counts
 */
export async function bulkImportBuyListCSV(file) {
  const formData = new FormData();
  formData.append("file", file);
  const r = await api.post("/api/admin/buy-list/bulk-import-csv", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return r.data;
}
