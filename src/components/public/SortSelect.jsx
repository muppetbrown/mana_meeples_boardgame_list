import React from "react";

export default function SortSelect({ sort, onChange, className, id, ...props }) {
  const sortOptions = [
    { 
      key: 'title', 
      label: 'Title', 
      defaultDir: 'asc',
      description: 'Sort alphabetically by game title'
    },
    { 
      key: 'year', 
      label: 'Year', 
      defaultDir: 'desc',
      description: 'Sort by publication year (newest first by default)'
    },
    { 
      key: 'rating', 
      label: 'Rating', 
      defaultDir: 'desc',
      description: 'Sort by BGG rating (highest first by default)'
    },
    { 
      key: 'time', 
      label: 'Time', 
      defaultDir: 'asc',
      description: 'Sort by average playing time (shortest first by default)'
    }
  ];

  const getCurrentSortKey = () => {
    // More robust parsing - handle edge cases
    const foundOption = sortOptions.find(option => sort.startsWith(option.key));
    if (!foundOption) {
      console.warn(`Unknown sort key in: ${sort}, defaulting to title`);
      return 'title';
    }
    return foundOption.key;
  };

  const getCurrentDirection = () => {
    return sort.endsWith('_desc') ? 'desc' : 'asc';
  };

  const handleSortClick = (key) => {
    const currentKey = getCurrentSortKey();
    const currentDir = getCurrentDirection();
    const option = sortOptions.find(opt => opt.key === key);
    
    if (key === currentKey) {
      // Toggle direction for same option
      const newDir = currentDir === 'asc' ? 'desc' : 'asc';
      const newSort = `${key}_${newDir}`;
      console.log(`Toggling sort direction: ${sort} → ${newSort}`);
      onChange(newSort);
    } else {
      // New option - use its default direction
      const newSort = `${key}_${option.defaultDir}`;
      console.log(`Changing sort option: ${sort} → ${newSort}`);
      onChange(newSort);
    }
  };

  // Debug current state
  React.useEffect(() => {
    console.log('Current sort state:', {
      sort,
      parsedKey: getCurrentSortKey(),
      parsedDirection: getCurrentDirection()
    });
  }, [sort]);

  return (
    <div className="w-full">
      {/* Screen reader label */}
      <span className="sr-only">Choose how to sort games</span>
      
      {/* Grid layout for sort buttons */}
      <div className="grid grid-cols-2 gap-2">
        {sortOptions.map(option => {
          const isActive = getCurrentSortKey() === option.key;
          const direction = isActive ? getCurrentDirection() : option.defaultDir;
          const directionIcon = direction === 'desc' ? '↓' : '↑';
          const directionText = direction === 'desc' ? 'descending' : 'ascending';
          
          return (
            <button
              key={option.key}
              onClick={() => handleSortClick(option.key)}
              className={`
                group relative px-3 py-2.5 text-sm font-medium rounded-lg border-2 
                transition-all duration-200 min-h-[44px]
                focus:outline-none focus:ring-3 focus:ring-offset-2
                ${isActive 
                  ? 'bg-emerald-500 text-white border-emerald-500 shadow-lg focus:ring-emerald-300 transform scale-105' 
                  : 'bg-white text-slate-700 border-slate-300 hover:bg-emerald-50 hover:border-emerald-300 focus:ring-emerald-300 hover:shadow-md'
                }
              `}
              title={`${option.description}. Currently ${directionText}. Click to ${isActive ? 'toggle direction' : 'select this sort option'}.`}
              aria-pressed={isActive}
              aria-describedby={`sort-${option.key}-help`}
            >
              <span className="flex items-center justify-center gap-1.5">
                <span>{option.label}</span>
                <span 
                  className={`text-sm transition-transform duration-200 ${
                    isActive ? 'scale-110' : 'opacity-75'
                  }`}
                  aria-hidden="true"
                >
                  {directionIcon}
                </span>
              </span>
              
              {/* Hidden help text for screen readers */}
              <span id={`sort-${option.key}-help`} className="sr-only">
                {option.description}. Current direction: {directionText}.
              </span>
            </button>
          );
        })}
      </div>
      
      {/* Debug info - remove in production */}
      {process.env.NODE_ENV === 'development' && (
        <div className="mt-2 p-2 bg-gray-100 rounded text-xs text-gray-600">
          <strong>Debug:</strong> sort="{sort}", key="{getCurrentSortKey()}", dir="{getCurrentDirection()}"
        </div>
      )}
      
      {/* Current sort status for screen readers */}
      <div className="sr-only" aria-live="polite" role="status">
        Currently sorting by {getCurrentSortKey()} in {getCurrentDirection() === 'desc' ? 'descending' : 'ascending'} order
      </div>
    </div>
  );
}