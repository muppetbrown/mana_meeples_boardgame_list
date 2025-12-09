// src/components/staff/TabNavigation.jsx
import React from "react";

/**
 * Tab navigation component for staff admin interface
 * Displays tabs with active state highlighting and optional icons
 */
export function TabNavigation({ activeTab, onTabChange, tabs }) {
  return (
    <div className="border-b border-gray-200 bg-white sticky top-16 z-30">
      <nav className="max-w-7xl mx-auto px-4" aria-label="Admin navigation tabs">
        <div className="flex gap-1 -mb-px overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`
                px-4 py-3 text-sm font-medium whitespace-nowrap
                border-b-2 transition-colors duration-150
                ${
                  activeTab === tab.id
                    ? "border-purple-600 text-purple-700 bg-purple-50"
                    : "border-transparent text-gray-600 hover:text-gray-800 hover:border-gray-300"
                }
              `}
              aria-current={activeTab === tab.id ? "page" : undefined}
            >
              <span className="flex items-center gap-2">
                {tab.icon && <span>{tab.icon}</span>}
                {tab.label}
              </span>
            </button>
          ))}
        </div>
      </nav>
    </div>
  );
}
