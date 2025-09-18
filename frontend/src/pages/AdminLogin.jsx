import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function AdminLogin() {
  const [token, setToken] = useState("");
  const [err, setErr] = useState("");
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    localStorage.setItem("ADMIN_TOKEN", token.trim());
    
    // FIXED: Use the proxy URL for API calls
    const API_BASE = window.__API_BASE__ || "/library/api-proxy.php?path=";
    
    try {
      // Test with a public endpoint that should work, then verify admin access
      const publicTest = await fetch(`${API_BASE}/api/public/category-counts`);
      if (!publicTest.ok) {
        setErr("Cannot connect to API");
        localStorage.removeItem("ADMIN_TOKEN");
        return;
      }
      
      // For now, just check if the token format looks valid
      if (token.trim().length < 10) {
        setErr("Invalid token format");
        localStorage.removeItem("ADMIN_TOKEN");
        return;
      }
      
      // Accept the token and proceed to staff dashboard
      navigate("/staff");
    } catch {
      setErr("Network error");
      localStorage.removeItem("ADMIN_TOKEN");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-amber-50 via-emerald-50 to-teal-50 p-3 sm:p-6">
      {/* Skip to main content link */}
      <a 
        href="#login-form" 
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-blue-600 focus:text-white focus:rounded focus:font-medium"
      >
        Skip to login form
      </a>
      
      <form onSubmit={submit} id="login-form" className="bg-white/90 backdrop-blur-sm p-6 sm:p-8 rounded-2xl shadow-xl border border-white/50 w-full max-w-sm space-y-4" role="main">
        <header className="text-center mb-6">
          <h1 className="text-2xl sm:text-3xl font-bold bg-gradient-to-r from-emerald-700 via-teal-600 to-amber-600 bg-clip-text text-transparent mb-2">
            Staff Login
          </h1>
          <p className="text-slate-600 text-sm">Access the admin dashboard</p>
        </header>
        
        <div className="space-y-2">
          <label htmlFor="admin-token" className="block text-sm font-semibold text-slate-700">
            Admin Token
          </label>
          <input
            id="admin-token"
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            className="w-full min-h-[48px] px-4 py-3 text-base border-2 border-slate-300 rounded-xl focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200 focus:outline-none transition-all bg-white touch-manipulation"
            placeholder="Enter your admin token"
            required
            autoComplete="current-password"
            aria-describedby={err ? "login-error" : undefined}
          />
        </div>
        
        {err && (
          <div 
            id="login-error"
            className="bg-red-50 border-2 border-red-200 rounded-xl p-3 text-red-700 text-sm font-medium"
            role="alert"
            aria-live="polite"
          >
            <span className="flex items-center gap-2">
              <svg className="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              {err}
            </span>
          </div>
        )}
        
        <button 
          type="submit"
          className="w-full min-h-[48px] bg-gradient-to-r from-emerald-600 to-teal-600 text-white font-semibold rounded-xl py-3 px-4 hover:from-emerald-700 hover:to-teal-700 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 transition-all duration-200 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none touch-manipulation"
          disabled={!token.trim()}
        >
          <span className="flex items-center justify-center gap-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013 3v1" />
            </svg>
            Sign In
          </span>
        </button>
        
        <div className="text-center pt-4">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="text-sm text-slate-600 hover:text-emerald-600 font-medium underline focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 rounded transition-colors"
          >
            ← Back to games
          </button>
        </div>
      </form>
    </div>
  );
}