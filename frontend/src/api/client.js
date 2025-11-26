// src/api/client.js
import axios from "axios";

// API Base URL resolution - matches utils/api.js pattern
const API_BASE =
  (window.__API_BASE__ && String(window.__API_BASE__)) ||
  document.querySelector('meta[name="api-base"]')?.content ||
  process.env.REACT_APP_API_BASE ||
  "https://mana-meeples-boardgame-list.onrender.com";

export const api = axios.create({
  baseURL: API_BASE,
  withCredentials: false, // FIXED: Set to false for proxy setup
});

// --- move the overlay + interceptors HERE ---
function showOverlay(msg) {
  try {
    let el = document.getElementById("debug-overlay");
    if (!el) {
      el = document.createElement("pre");
      el.id = "debug-overlay";
      el.style.cssText = `
        position:fixed; inset:10px 10px auto 10px; z-index:99999;
        background:#111; color:#0f0; padding:8px; max-height:40vh; overflow:auto;
        font:12px/1.3 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; border-radius:8px; opacity:.95;
      `;
      document.body.appendChild(el);
    }
    el.textContent = msg;
  } catch {}
}

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

    // Handle 401 errors by clearing token and redirecting to login
    if (status === 401 && cfg.url?.includes("/api/admin")) {
      console.warn("Admin token invalid or expired, clearing and redirecting to login");
      localStorage.removeItem("ADMIN_TOKEN");
      // Only redirect if we're not already on the login page
      if (!window.location.pathname.includes("/staff/login")) {
        window.location.href = window.location.origin + window.location.pathname.replace(/\/staff.*/, "/staff/login");
      }
    }

    return Promise.reject(err);
  }
);

// FIXED: Add admin token header helper
function getAdminHeaders() {
  const token = localStorage.getItem("ADMIN_TOKEN");
  return token ? { "X-Admin-Token": token } : {};
}

// JSON helpers - FIXED to load all games for staff
export const getGames = async () => {
  try {
    // Load all games by requesting a large page size
    const response = await api.get("/api/public/games", { 
      params: { page_size: 1000 }, // Get up to 1000 games
      headers: getAdminHeaders() 
    });
    return response.data.items || [];
  } catch (error) {
    console.error("Failed to load games:", error);
    return [];
  }
};

export const searchBGG = (query) => {
  // Your backend doesn't have search-bgg endpoint, so return empty for now
  console.warn("BGG search not implemented in backend");
  return Promise.resolve([]);
};

export const bulkImportCsv = (csv_data) =>
  api.post("/api/admin/bulk-import-csv", { csv_data }, { headers: getAdminHeaders() }).then(r => r.data);

export const bulkCategorizeCsv = (csv_data) =>
  api.post("/api/admin/bulk-categorize-csv", { csv_data }, { headers: getAdminHeaders() }).then(r => r.data);

export const addGame = (payload) =>
  api.post("/api/admin/games", payload, { headers: getAdminHeaders() }).then(r => r.data);

// --- Public catalogue calls (no auth needed) ---
export async function getPublicGames(params = {}) {
  // params: { q, category, players, max_time, page, page_size }
  const r = await api.get("/api/public/games", { params });
  return r.data; // { total, page, page_size, items: [...] }
}

export async function getPublicGame(id) {
  const r = await api.get(`/api/public/games/${id}`);
  return r.data; // GamePublicOut
}

export async function getPublicCategoryCounts() {
  const r = await api.get("/api/public/category-counts");
  return r.data; // { all, uncategorized, CORE_STRATEGY: n, ... }
}

// IMPORTANT: Use the same API_BASE for image proxy
export const imageProxyUrl = (rawUrl) =>
  `${API_BASE}/api/public/image-proxy?url=${encodeURIComponent(rawUrl)}`;

export async function updateGame(gameId, patch) {
  try {
    const r = await api.post(`/api/admin/games/${gameId}/update`, patch, { headers: getAdminHeaders() });
    return r.data;
  } catch (error) {
    // Log the error for debugging but don't re-throw if the game was actually updated
    console.warn("Update game API returned error but operation might have succeeded:", error);
    // If it's a 500 error, check if the response contains any useful data
    if (error.response?.status === 500 && error.response?.data) {
      console.log("500 error response data:", error.response.data);
    }
    // Re-throw the error to maintain existing behavior
    throw error;
  }
}

export async function deleteGame(gameId) {
  const r = await api.delete(`/api/admin/games/${gameId}`, { headers: getAdminHeaders() });
  return r.data;
}

// Advanced admin operations
export async function bulkUpdateNZDesigners(csv_data) {
  const r = await api.post("/api/admin/bulk-update-nz-designers", { csv_data }, { headers: getAdminHeaders() });
  return r.data;
}

export async function reimportAllGames() {
  const r = await api.post("/api/admin/reimport-all-games", {}, { headers: getAdminHeaders() });
  return r.data;
}

// Debug and monitoring endpoints
export async function getDebugCategories() {
  const r = await api.get("/api/debug/categories");
  return r.data;
}

export async function getDebugDatabaseInfo(limit = 50) {
  const r = await api.get("/api/debug/database-info", { params: { limit } });
  return r.data;
}

export async function getDebugPerformance() {
  const r = await api.get("/api/debug/performance", { headers: getAdminHeaders() });
  return r.data;
}

export async function exportGamesCSV(limit = null) {
  const params = limit ? { limit } : {};
  const r = await api.get("/api/debug/export-games-csv", { params });
  return r.data;
}

// Health check endpoints
export async function getHealthCheck() {
  const r = await api.get("/api/health");
  return r.data;
}

export async function getDbHealthCheck() {
  const r = await api.get("/api/health/db");
  return r.data;
}

// Admin authentication
export async function validateAdminToken() {
  const r = await api.get("/api/admin/validate", { headers: getAdminHeaders() });
  return r.data;
}