// frontend/src/hooks/useAuth.js
/**
 * Custom hook for managing admin authentication
 * Provides authentication state and methods
 */
import { useState, useCallback, useEffect } from "react";
import { validateAdminToken, adminLogin as apiAdminLogin, adminLogout as apiAdminLogout } from "../api/client";

/**
 * Hook for managing admin authentication
 * @returns {Object} Authentication state and control functions
 */
export function useAuth() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isValidating, setIsValidating] = useState(true);
  const [error, setError] = useState(null);

  /**
   * Validate current authentication status
   */
  const validate = useCallback(async () => {
    setIsValidating(true);
    setError(null);

    try {
      await validateAdminToken();
      setIsAuthenticated(true);
    } catch (err) {
      setIsAuthenticated(false);
      // Don't set error for validation failures - it's expected when not logged in
    } finally {
      setIsValidating(false);
    }
  }, []);

  /**
   * Login with admin token
   * @param {string} token - Admin token
   * @returns {Promise<boolean>} Success status
   */
  const login = useCallback(async (token) => {
    setError(null);

    try {
      await apiAdminLogin(token);
      setIsAuthenticated(true);
      return true;
    } catch (err) {
      setIsAuthenticated(false);
      setError(err.response?.data?.detail || err.message || "Login failed");
      return false;
    }
  }, []);

  /**
   * Logout
   * @returns {Promise<boolean>} Success status
   */
  const logout = useCallback(async () => {
    setError(null);

    try {
      await apiAdminLogout();
      setIsAuthenticated(false);
      // Clear any stored tokens
      localStorage.removeItem("ADMIN_TOKEN");
      return true;
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Logout failed");
      return false;
    }
  }, []);

  // Validate on mount
  useEffect(() => {
    validate();
  }, [validate]);

  return {
    isAuthenticated,
    isValidating,
    error,
    login,
    logout,
    validate
  };
}
