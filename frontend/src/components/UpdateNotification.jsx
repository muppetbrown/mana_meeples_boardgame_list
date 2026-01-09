import { useState, useEffect } from 'react';
import { startVersionCheck, reloadApp } from '../utils/versionCheck';

/**
 * UpdateNotification Component
 * Displays a banner when a new version of the app is available
 * Mobile-friendly with auto-refresh option
 */
export default function UpdateNotification() {
  const [showNotification, setShowNotification] = useState(false);
  const [countdown, setCountdown] = useState(null);
  const [autoRefreshTimer, setAutoRefreshTimer] = useState(null);

  useEffect(() => {
    // Start checking for updates
    const unsubscribe = startVersionCheck((newVersion, currentVersion) => {
      console.log('Update detected:', { newVersion, currentVersion });
      setShowNotification(true);

      // On mobile, auto-refresh after 10 seconds (gives user time to save work)
      if (isMobileDevice()) {
        startAutoRefreshCountdown();
      }
    });

    // Cleanup on unmount
    return () => {
      if (unsubscribe) {
        unsubscribe();
      }
      if (autoRefreshTimer) {
        clearInterval(autoRefreshTimer);
      }
    };
  }, []);

  /**
   * Check if user is on a mobile device
   */
  function isMobileDevice() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
      navigator.userAgent
    ) || window.innerWidth < 768;
  }

  /**
   * Start countdown for auto-refresh on mobile
   */
  function startAutoRefreshCountdown() {
    let secondsLeft = 10;
    setCountdown(secondsLeft);

    const timer = setInterval(() => {
      secondsLeft--;
      setCountdown(secondsLeft);

      if (secondsLeft <= 0) {
        clearInterval(timer);
        handleRefresh();
      }
    }, 1000);

    setAutoRefreshTimer(timer);
  }

  /**
   * Cancel auto-refresh countdown
   */
  function cancelAutoRefresh() {
    if (autoRefreshTimer) {
      clearInterval(autoRefreshTimer);
      setAutoRefreshTimer(null);
      setCountdown(null);
    }
  }

  /**
   * Handle refresh button click
   */
  function handleRefresh() {
    cancelAutoRefresh();
    reloadApp();
  }

  /**
   * Dismiss notification (desktop only)
   */
  function handleDismiss() {
    cancelAutoRefresh();
    setShowNotification(false);
  }

  if (!showNotification) {
    return null;
  }

  const mobile = isMobileDevice();

  return (
    <div
      className="fixed top-0 left-0 right-0 z-50 bg-linear-to-r from-violet-600 to-purple-600 text-white shadow-lg"
      role="alert"
      aria-live="assertive"
      aria-atomic="true"
    >
      <div className="max-w-7xl mx-auto px-4 py-3 sm:px-6 lg:px-8">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
          {/* Message */}
          <div className="flex items-center gap-3 text-center sm:text-left">
            <div className="shrink-0">
              <svg
                className="w-6 h-6 animate-pulse"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
            </div>
            <div>
              <p className="font-semibold">
                {mobile ? 'New version available!' : 'A new version is available'}
              </p>
              {countdown !== null && mobile && (
                <p className="text-sm text-violet-100 mt-0.5">
                  Auto-refreshing in {countdown} second{countdown !== 1 ? 's' : ''}...
                </p>
              )}
              {!mobile && (
                <p className="text-sm text-violet-100 mt-0.5">
                  Refresh to get the latest features and improvements
                </p>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={handleRefresh}
              className="px-4 py-2 bg-white text-violet-700 rounded-md font-semibold hover:bg-violet-50 active:bg-violet-100 transition-colors focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-violet-600 min-w-25"
              type="button"
            >
              {countdown !== null ? 'Refresh Now' : 'Refresh'}
            </button>

            {/* Dismiss button (desktop only, or if countdown active on mobile) */}
            {(!mobile || countdown !== null) && (
              <button
                onClick={handleDismiss}
                className="px-3 py-2 text-white hover:text-violet-100 focus:outline-none focus:ring-2 focus:ring-white rounded-md transition-colors"
                type="button"
                aria-label="Dismiss notification"
              >
                {countdown !== null ? 'Cancel' : (
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
