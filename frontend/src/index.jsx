import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import "./index.css";
import App from "./App";
import * as serviceWorkerRegistration from './utils/serviceWorkerRegistration';

// Phase 2 Performance: Configure React Query for API response caching
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000,        // Data stays fresh for 30 seconds (matches backend cache TTL)
      gcTime: 5 * 60 * 1000,       // Keep unused data in cache for 5 minutes (formerly cacheTime)
      refetchOnWindowFocus: false, // Don't refetch when user returns to tab (reduces unnecessary requests)
      refetchOnMount: false,       // Don't refetch on component mount if data is fresh
      retry: 2,                    // Retry failed requests twice before giving up
      retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000), // Exponential backoff
    },
  },
});

// BUNDLE SIZE OPTIMIZATION: Lazy load Sentry only when needed (production + DSN configured)
// This reduces initial bundle size by ~100KB for users who don't need error tracking
// Sentry will be loaded asynchronously after the main app renders
if (import.meta.env.VITE_SENTRY_DSN && import.meta.env.PROD) {
  import('@sentry/react').then(Sentry => {
    Sentry.init({
      dsn: import.meta.env.VITE_SENTRY_DSN,
      environment: import.meta.env.MODE || 'production',

      // Performance monitoring
      integrations: [
        Sentry.browserTracingIntegration(),
        Sentry.replayIntegration({
          maskAllText: false,
          blockAllMedia: false,
        }),
      ],

      // Set tracesSampleRate to 1.0 to capture 100% of transactions for performance monitoring.
      // Adjust this value in production to reduce volume
      tracesSampleRate: 0.1,

      // Capture Replay for 10% of all sessions,
      // plus 100% of sessions with an error
      replaysSessionSampleRate: 0.1,
      replaysOnErrorSampleRate: 1.0,
    });
  }).catch(err => {
    console.error('Failed to load Sentry:', err);
  });
}

// Accessibility testing in development
if (import.meta.env.DEV) {
  import('@axe-core/react').then(axe => {
    axe.default(React, ReactDOM, 1000);
  });
}

const base = import.meta.env.BASE_URL || "/";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename={base}>
        <App />
      </BrowserRouter>
      {/* React Query Devtools - only shows in development */}
      <ReactQueryDevtools initialIsOpen={false} position="bottom-right" />
    </QueryClientProvider>
  </React.StrictMode>
);

// Register service worker for offline support and caching
// In production, this enables:
// - Offline browsing of previously loaded games
// - Faster repeat visits through aggressive caching
// - Better performance on mobile and slow connections
// - PWA installation capability
serviceWorkerRegistration.register({
  onSuccess: () => {
    console.log('[App] Service worker registered - offline support enabled');
  },
  onUpdate: (registration) => {
    console.log('[App] New content available - please refresh the page');
    // Optionally: Show a toast notification to users that updates are available
    // You could dispatch an event here that a component listens to
  }
});