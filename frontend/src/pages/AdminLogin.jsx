import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { adminLogin } from "../api/client";

// Mirrors the backend's RATE_LIMIT_WINDOW default (backend/config.py). The exact
// server-side window may differ if that env var is overridden; this is just a
// reasonable "please wait" estimate, not a precise readout of server state.
const RATE_LIMIT_COOLDOWN_SECONDS = 300;

function formatCountdown(seconds) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export default function AdminLogin() {
  const [token, setToken] = useState("");
  const [err, setErr] = useState("");
  const [showToken, setShowToken] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const navigate = useNavigate();
  const cooldownTimer = useRef(null);

  useEffect(() => {
    if (cooldown <= 0) return undefined;
    cooldownTimer.current = setInterval(() => {
      setCooldown((s) => (s <= 1 ? 0 : s - 1));
    }, 1000);
    return () => clearInterval(cooldownTimer.current);
  }, [cooldown > 0]);

  const submit = async (e) => {
    e.preventDefault();
    if (cooldown > 0) return;
    setErr("");

    // Basic validation
    if (token.trim().length < 10) {
      setErr("Token must be at least 10 characters");
      return;
    }

    try {
      // Use new secure cookie-based login
      await adminLogin(token.trim());
      // Login successful, cookie is set automatically
      navigate("/staff");
    } catch (error) {
      // Handle different error types
      if (error.response?.status === 401) {
        setErr("Invalid admin token");
      } else if (error.response?.status === 429) {
        setCooldown(RATE_LIMIT_COOLDOWN_SECONDS);
      } else if (error.message?.includes("Network Error") || error.code === "ERR_NETWORK") {
        setErr("Network error - cannot connect to API");
      } else {
        setErr("Authentication failed");
      }
    }
  };

  const displayErr =
    cooldown > 0 ? `Too many attempts. Please try again in ${formatCountdown(cooldown)}.` : err;

  return (
    <div className="min-h-screen flex items-center justify-center bg-linear-to-br from-amber-50 via-emerald-50 to-teal-50 p-3 sm:p-6">
      {/* Skip to main content link */}
      <a
        href="#login-form"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-blue-600 focus:text-white focus:rounded focus:font-medium"
      >
        Skip to login form
      </a>

      <main role="main" id="main-content">
        <form onSubmit={submit} id="login-form" aria-labelledby="login-heading" className="bg-white/90 backdrop-blur-sm p-6 sm:p-8 rounded-2xl shadow-xl border border-white/50 w-full max-w-sm space-y-4">
        <header className="text-center mb-6">
          <h1 id="login-heading" className="text-2xl sm:text-3xl font-bold bg-linear-to-r from-emerald-700 via-teal-600 to-amber-600 bg-clip-text text-transparent mb-2">
            Staff Login
          </h1>
          <p className="text-slate-600 text-sm">Access the admin dashboard</p>
        </header>
        
        <div className="space-y-2">
          <label htmlFor="admin-token" className="block text-sm font-semibold text-slate-700">
            Admin Token
          </label>
          <div className="relative">
            <input
              id="admin-token"
              name="token"
              type={showToken ? "text" : "password"}
              value={token}
              onChange={(e) => setToken(e.target.value)}
              className="w-full min-h-12 pl-4 pr-12 py-3 text-base border-2 border-slate-300 rounded-xl focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200 focus:outline-none transition-all bg-white touch-manipulation"
              placeholder="Enter your admin token"
              required
              autoComplete="current-password"
              aria-describedby={displayErr ? "login-error" : undefined}
            />
            <button
              type="button"
              onClick={() => setShowToken((v) => !v)}
              aria-label={showToken ? "Hide token" : "Show token"}
              aria-pressed={showToken}
              className="absolute inset-y-0 right-0 flex items-center justify-center w-11 min-h-11 text-slate-500 hover:text-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-1 rounded-r-xl"
            >
              {showToken ? (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.243 4.243L9.88 9.88" />
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              )}
            </button>
          </div>
        </div>

        {displayErr && (
          <div
            id="login-error"
            className="bg-red-50 border-2 border-red-200 rounded-xl p-3 text-red-700 text-sm font-medium"
            role="alert"
            aria-live="polite"
          >
            <span className="flex items-center gap-2">
              <svg className="w-4 h-4 shrink-0" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              {displayErr}
            </span>
          </div>
        )}
        
        <button 
          type="submit"
          className="w-full min-h-12 bg-linear-to-r from-emerald-600 to-teal-600 text-white font-semibold rounded-xl py-3 px-4 hover:from-emerald-700 hover:to-teal-700 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 transition-all duration-200 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none touch-manipulation"
          disabled={!token.trim() || cooldown > 0}
        >
          <span className="flex items-center justify-center gap-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013 3v1" />
            </svg>
            {cooldown > 0 ? `Try again in ${formatCountdown(cooldown)}` : "Sign In"}
          </span>
        </button>

        <div className="text-center pt-4">
          <button
            type="button"
            onClick={() => navigate("/")}
            className="text-sm text-slate-600 hover:text-emerald-600 font-medium underline focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 rounded transition-colors"
          >
            ← Back to games
          </button>
        </div>
      </form>
      </main>
    </div>
  );
}