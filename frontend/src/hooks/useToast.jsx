// frontend/src/hooks/useToast.js
/**
 * Custom hook for managing toast notifications
 * Provides functions to show success, error, info, and warning toasts
 * with automatic timeout
 */
import { useState, useCallback, useEffect, useRef } from "react";

/**
 * Hook for managing toast notifications
 * @param {number} defaultDuration - Default duration in ms before toast auto-hides (default: 3000)
 * @returns {Object} Toast state and control functions
 */
export function useToast(defaultDuration = 3000) {
  const [toast, setToast] = useState({ message: "", type: "info", duration: defaultDuration });
  const timeoutRef = useRef(null);

  // Clear any existing timeout when component unmounts
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  /**
   * Show a toast notification
   * @param {string} message - Message to display
   * @param {string} type - Type of toast (info, success, warning, error)
   * @param {number} duration - Duration in ms (0 = no auto-hide)
   */
  const showToast = useCallback((message, type = "info", duration = defaultDuration) => {
    // Clear any existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    // Set the new toast
    setToast({ message, type, duration });

    // Auto-hide after duration (unless duration is 0)
    if (duration > 0) {
      timeoutRef.current = setTimeout(() => {
        hideToast();
      }, duration);
    }
  }, [defaultDuration]);

  /**
   * Hide the current toast
   */
  const hideToast = useCallback(() => {
    setToast({ message: "", type: "info", duration: defaultDuration });
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, [defaultDuration]);

  /**
   * Show success toast
   * @param {string} message - Success message
   * @param {number} duration - Duration in ms
   */
  const success = useCallback((message, duration) => {
    showToast(message, "success", duration);
  }, [showToast]);

  /**
   * Show error toast
   * @param {string} message - Error message
   * @param {number} duration - Duration in ms (default: 5000 for errors)
   */
  const error = useCallback((message, duration = 5000) => {
    showToast(message, "error", duration);
  }, [showToast]);

  /**
   * Show info toast
   * @param {string} message - Info message
   * @param {number} duration - Duration in ms
   */
  const info = useCallback((message, duration) => {
    showToast(message, "info", duration);
  }, [showToast]);

  /**
   * Show warning toast
   * @param {string} message - Warning message
   * @param {number} duration - Duration in ms
   */
  const warning = useCallback((message, duration) => {
    showToast(message, "warning", duration);
  }, [showToast]);

  return {
    toast,
    showToast,
    hideToast,
    success,
    error,
    info,
    warning
  };
}

/**
 * Toast component that can be used with useToast hook
 * Usage:
 *   const { toast, success } = useToast();
 *   return <div><Toast {...toast} /><button onClick={() => success("Done!")}>Click me</button></div>
 */
export function Toast({ message, type = "info" }) {
  if (!message) return null;

  const baseClasses = "fixed bottom-4 left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded-lg shadow-lg text-white";
  const typeClasses = {
    info: "bg-gray-800",
    success: "bg-green-600",
    warning: "bg-amber-600",
    error: "bg-red-600",
  };

  return (
    <div className={`${baseClasses} ${typeClasses[type] || typeClasses.info}`}>
      {message}
    </div>
  );
}
