import React from "react";
import "./SkipNav.css";

/**
 * Skip Navigation Links
 * Allows keyboard users to skip to main content, bypassing navigation
 * WCAG 2.1 Level A - Bypass Blocks (2.4.1)
 */
export default function SkipNav() {
  return (
    <div className="skip-nav">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <a href="#search-box" className="skip-link">
        Skip to search
      </a>
      <a href="#category-filters" className="skip-link">
        Skip to filters
      </a>
    </div>
  );
}
