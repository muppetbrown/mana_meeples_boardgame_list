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

// In your utils/api.js or wherever imageProxyUrl is defined
export const imageProxyUrl = (url) => {
  if (!url) return null;
  
  // For BGG images, try to get higher resolution
  if (url.includes('cf.geekdo-images.com')) {
    let largerUrl = url;
    
    // Try multiple size replacements for better quality
    largerUrl = largerUrl.replace('_t.', '_d.');  // thumbnail to detail size
    largerUrl = largerUrl.replace('_mt.', '_d.'); // medium thumbnail to detail
    largerUrl = largerUrl.replace('_original.', '_d.'); // sometimes original is lower res than detail
    
    // Ensure we're not using tiny thumbnails
    if (largerUrl.includes('_t.') || largerUrl.includes('_mt.')) {
      largerUrl = largerUrl.replace('_t.', '_d.').replace('_mt.', '_d.');
    }
    
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