// src/components/staff/TabNavigation.jsx
import React, { useRef } from "react";
import Icon, { hasIcon } from "../common/Icon";

/**
 * Tab navigation for the staff admin interface.
 * Implements the WAI-ARIA tabs pattern (roving tabindex + arrow/Home/End keys).
 *
 * Each tab: { id, label, icon?, group?, badge? }
 *  - icon: an <Icon> name (anything else is rendered as plain text, e.g. an emoji)
 *  - group: tabs are visually separated whenever the group changes
 *  - badge: number shown as a count pill (hidden when 0/undefined)
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
    <div className="border-b border-gray-200 bg-white">
      <nav className="max-w-screen-2xl mx-auto px-3 lg:px-6" aria-label="Admin sections">
        <div
          role="tablist"
          aria-label="Admin sections"
          className="flex items-stretch gap-0.5 -mb-px overflow-x-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent"
        >
          {tabs.map((tab, index) => {
            const selected = activeTab === tab.id;
            const startsGroup = index > 0 && tab.group !== tabs[index - 1].group;
            return (
              <React.Fragment key={tab.id}>
                {startsGroup && (
                  <span role="presentation" className="self-center mx-1.5 h-5 w-px bg-gray-200 shrink-0" />
                )}
                <button
                  ref={(el) => (refs.current[tab.id] = el)}
                  role="tab"
                  id={`tab-${tab.id}`}
                  aria-selected={selected}
                  aria-controls={`panel-${tab.id}`}
                  tabIndex={selected ? 0 : -1}
                  onClick={() => onTabChange(tab.id)}
                  onKeyDown={(e) => onKeyDown(e, index)}
                  className={`px-3 h-11 text-sm font-medium whitespace-nowrap border-b-2 transition-colors duration-150 shrink-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:ring-inset ${
                    selected
                      ? "border-purple-600 text-purple-700 bg-purple-50/60"
                      : "border-transparent text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                  }`}
                >
                  <span className="flex items-center gap-2">
                    {tab.icon &&
                      (hasIcon(tab.icon) ? (
                        <Icon name={tab.icon} size={16} />
                      ) : (
                        <span className="text-base" aria-hidden="true">
                          {tab.icon}
                        </span>
                      ))}
                    <span>{tab.label}</span>
                    {tab.badge > 0 && (
                      <span
                        className="min-w-5 h-5 px-1.5 inline-flex items-center justify-center rounded-full text-[11px] font-semibold tabular bg-amber-100 text-amber-800"
                        aria-label={`${tab.badge} need attention`}
                      >
                        {tab.badge}
                      </span>
                    )}
                  </span>
                </button>
              </React.Fragment>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
