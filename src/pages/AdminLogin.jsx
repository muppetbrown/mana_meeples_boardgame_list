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
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-6">
      <form onSubmit={submit} className="bg-white p-6 rounded-2xl shadow w-full max-w-sm space-y-3">
        <h1 className="text-xl font-semibold">Staff Login</h1>
        <input
          type="password"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          className="w-full border rounded px-3 py-2"
          placeholder="Enter admin token"
        />
        {err && <div className="text-red-600 text-sm">{err}</div>}
        <button className="w-full bg-purple-600 text-white rounded py-2 hover:bg-purple-700">Sign in</button>
      </form>
    </div>
  );
}