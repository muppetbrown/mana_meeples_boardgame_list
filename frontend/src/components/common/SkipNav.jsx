import React from "react";

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
      <style jsx>{`
        .skip-nav {
          position: relative;
          z-index: 9999;
        }

        .skip-link {
          position: absolute;
          top: -100px;
          left: 8px;
          z-index: 10000;
          padding: 12px 24px;
          background-color: #7c3aed;
          color: white;
          text-decoration: none;
          font-weight: 600;
          font-size: 1rem;
          border-radius: 4px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
          transition: top 0.3s ease;
        }

        .skip-link:focus {
          top: 8px;
          outline: 3px solid #fbbf24;
          outline-offset: 2px;
        }

        .skip-link:hover:focus {
          background-color: #6d28d9;
        }
      `}</style>
    </div>
  );
}
