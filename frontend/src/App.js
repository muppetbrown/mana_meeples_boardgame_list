// src/App.js
import React, { lazy, Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";

// ---- UI components ----
import ErrorBoundary from "./components/ErrorBoundary";
import { FullPageLoader } from "./components/common/LoadingSpinner";

// ---- Code Splitting with React.lazy ----
// Load pages on-demand for better performance
const PublicCatalogue = lazy(() => import("./pages/PublicCatalogue"));
const GameDetails = lazy(() => import("./pages/GameDetails"));
const AdminLogin = lazy(() => import("./pages/AdminLogin"));

// Lazy load StaffView to keep it separate
const StaffView = lazy(() => import("./pages/StaffView"));

/** -------------------------------
 * Router: public & staff - WITH CODE SPLITTING
 * -------------------------------- */
export default function App() {
  return (
    <ErrorBoundary>
      <Suspense fallback={<FullPageLoader text="Loading page..." />}>
        <Routes>
          {/* Fixed: Remove leading slashes for nested routing */}
          <Route path="/" element={<ErrorBoundary><PublicCatalogue /></ErrorBoundary>} />
          <Route path="game/:id" element={<ErrorBoundary><GameDetails /></ErrorBoundary>} />
          <Route path="staff/login" element={<ErrorBoundary><AdminLogin /></ErrorBoundary>} />
          <Route path="staff" element={<ErrorBoundary><StaffView /></ErrorBoundary>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </ErrorBoundary>
  );
}