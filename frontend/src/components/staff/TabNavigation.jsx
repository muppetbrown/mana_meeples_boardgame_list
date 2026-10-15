// src/components/staff/TabNavigation.jsx
import React, { useRef } from "react";

/**
 * Tab navigation for the staff admin interface.
 * Implements the WAI-ARIA tabs pattern (roving tabindex + arrow/Home/End keys).
 */
export function TabNavigation({ activeTab, onTabChange, tabs }) {
  const refs = useRef({});

  const onKeyDown = (e, index) => {
    let next = null;
    if (e.key === "ArrowRight") next = (index + 1) % tabs.length;
    else if (e.key === "ArrowLeft") next = (index - 1 + tabs.length) % tabs.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = tabs.length - 1;
    if (next === null) return;
    e.preventDefault();
    const id = tabs[next].id;
    onTabChange(id);
    refs.current[id]?.focus();
  };

  return (
    <div
      className="border-b border-gray-200 bg-white sticky z-30"
      style={{ top: "var(--staff-header-h, 4rem)" }}
    >
      <nav className="max-w-7xl mx-auto px-2 sm:px-4" aria-label="Admin sections">
        <div
          role="tablist"
          aria-label="Admin sections"
          className="flex gap-1 sm:gap-2 -mb-px overflow-x-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent"
        >
          {tabs.map((tab, index) => {
            const selected = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                ref={(el) => (refs.current[tab.id] = el)}
                role="tab"
                id={`tab-${tab.id}`}
                aria-selected={selected}
                aria-controls={`panel-${tab.id}`}
                tabIndex={selected ? 0 : -1}
                onClick={() => onTabChange(tab.id)}
                onKeyDown={(e) => onKeyDown(e, index)}
                className={`px-3 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors duration-150 shrink-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:ring-inset ${
                  selected
                    ? "border-purple-600 text-purple-700 bg-purple-50"
                    : "border-transparent text-gray-600 hover:text-gray-800 hover:border-gray-300"
                }`}
              >
                <span className="flex items-center gap-2">
                  {tab.icon && (
                    <span className="text-base" aria-hidden="true">
                      {tab.icon}
                    </span>
                  )}
                  <span>{tab.label}</span>
                </span>
              </button>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
