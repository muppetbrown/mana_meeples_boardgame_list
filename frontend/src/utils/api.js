// src/utils/api.js
function resolveApiBase() {
  // 1) Hard override set in index.html for prod
  try {
    if (typeof window !== "undefined" && window.__API_BASE__) return window.__API_BASE__;
  } catch { /* noop */ }

  // 2) Meta tag in index.html
  const m = document.querySelector('meta[name="api-base"]');
  if (m && m.content) return m.content;

  // 3) CRA env (baked at build time)
  if (process.env.REACT_APP_API_BASE) return process.env.REACT_APP_API_BASE;

  // 4) Dev fallback
  return "http://127.0.0.1:8000";
}

export const API_BASE = resolveApiBase().replace(/\/+$/, "");

// Enhanced image proxy for better desktop quality
export const imageProxyUrl = (url) => {
  if (!url) return null;
  
  // For BGG images, try to get highest resolution available
  if (url.includes('cf.geekdo-images.com')) {
    let largerUrl = url;
    
    // Priority order for BGG image sizes (best to worst quality):
    // _original, _d (detail), _md (medium detail), _mt (medium thumb), _t (thumbnail)
    
    // First try to get original size (best quality)
    if (!largerUrl.includes('_original.')) {
      largerUrl = largerUrl.replace('_t.', '_original.');
      largerUrl = largerUrl.replace('_mt.', '_original.'); 
      largerUrl = largerUrl.replace('_md.', '_original.');
      largerUrl = largerUrl.replace('_d.', '_original.');
    }
    
    // If original doesn't work, backend can fallback to detail size
    // The backend should handle the fallback chain: original -> detail -> medium -> thumbnail
    
    return `${API_BASE}/api/public/image-proxy?url=${encodeURIComponent(largerUrl)}`;
  }
  
  return `${API_BASE}/api/public/image-proxy?url=${encodeURIComponent(url)}`;
};

export async function fetchJson(path, init = {}) {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  const res = await fetch(url, {
    credentials: "omit",
    headers: { Accept: "application/json", ...(init.headers || {}) },
    ...init,
  });

  if (!res.ok) throw new Error(`HTTP ${res.status}`);

  const ct = res.headers.get("content-type") || "";
  if (!ct.includes("application/json")) {
    const text = await res.text();
    throw new Error(`Non-JSON response (status ${res.status}): ${text.slice(0, 200)}…`);
  }
  return res.json();
}