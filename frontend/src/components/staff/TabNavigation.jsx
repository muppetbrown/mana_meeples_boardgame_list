// src/components/staff/TabNavigation.jsx
import React from "react";

/**
 * Tab navigation component for staff admin interface
 * Displays tabs with active state highlighting and optional icons
 */
export function TabNavigation({ activeTab, onTabChange, tabs }) {
  return (
    <div className="border-b border-gray-200 bg-white sticky top-16 z-30">
      <nav className="max-w-7xl mx-auto px-2 sm:px-4" aria-label="Admin navigation tabs">
        <div className="flex gap-1 sm:gap-2 -mb-px overflow-x-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`
                px-2 py-2 sm:px-4 sm:py-3 text-xs sm:text-sm font-medium whitespace-nowrap
                border-b-2 transition-colors duration-150 flex-shrink-0
                ${
                  activeTab === tab.id
                    ? "border-purple-600 text-purple-700 bg-purple-50"
                    : "border-transparent text-gray-600 hover:text-gray-800 hover:border-gray-300"
                }
              `}
              aria-current={activeTab === tab.id ? "page" : undefined}
            >
              <span className="flex items-center gap-1 sm:gap-2">
                {tab.icon && <span className="text-sm sm:text-base">{tab.icon}</span>}
                <span className="hidden sm:inline">{tab.label}</span>
                <span className="sm:hidden">{tab.label.split(" ")[0]}</span>
              </span>
            </button>
          ))}
        </div>
      </nav>
    </div>
  );
}
