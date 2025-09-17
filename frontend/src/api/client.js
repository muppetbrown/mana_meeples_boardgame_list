// src/api/client.js
import axios from "axios";

// FIXED: Match the variable name used in index.html and api.js
const API_BASE =
  (window.__API_BASE__ && String(window.__API_BASE__)) ||
  document.querySelector('meta[name="api-base"]')?.content ||
  "https://manaandmeeples.co.nz/library/api-proxy.php?path=";

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
  const r = await api.put(`/api/games/${gameId}`, patch, { headers: getAdminHeaders() });
  return r.data;
}

export async function deleteGame(gameId) {
  const r = await api.delete(`/api/games/${gameId}`, { headers: getAdminHeaders() });
  return r.data;
}