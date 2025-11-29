import React from "react";

export default function SortSelect({ sort, onChange, className, id, ...props }) {
  const sortOptions = React.useMemo(() => [
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
    },
    {
      key: 'date_added',
      label: 'Added',
      defaultDir: 'desc',
      description: 'Sort by date added to collection (most recent first by default)'
    }
  ], []);

  const getCurrentSortKey = React.useCallback(() => {
    // More robust parsing - handle edge cases
    const foundOption = sortOptions.find(option => sort.startsWith(option.key));
    if (!foundOption) {
      console.warn(`Unknown sort key in: ${sort}, defaulting to title`);
      return 'title';
    }
    return foundOption.key;
  }, [sort, sortOptions]);

  const getCurrentDirection = React.useCallback(() => {
    return sort.endsWith('_desc') ? 'desc' : 'asc';
  }, [sort]);

  // Debug current state
  React.useEffect(() => {
    console.log('Current sort state:', {
      sort,
      parsedKey: getCurrentSortKey(),
      parsedDirection: getCurrentDirection()
    });
  }, [sort, getCurrentSortKey, getCurrentDirection]);

  const handleFieldChange = (e) => {
    const newKey = e.target.value;
    const option = sortOptions.find(opt => opt.key === newKey);
    const newSort = `${newKey}_${option.defaultDir}`;
    console.log(`Changing sort field: ${sort} → ${newSort}`);
    onChange(newSort);
  };

  const handleDirectionToggle = () => {
    const currentKey = getCurrentSortKey();
    const currentDir = getCurrentDirection();
    const newDir = currentDir === 'asc' ? 'desc' : 'asc';
    const newSort = `${currentKey}_${newDir}`;
    console.log(`Toggling sort direction: ${sort} → ${newSort}`);
    onChange(newSort);
  };

  const currentKey = getCurrentSortKey();
  const currentDir = getCurrentDirection();
  const directionIcon = currentDir === 'desc' ? '↓' : '↑';
  const directionText = currentDir === 'desc' ? 'descending' : 'ascending';

  return (
    <div className={`w-full ${className || ''}`}>
      {/* Screen reader label */}
      <span className="sr-only">Choose how to sort games</span>

      {/* Dropdown + Direction Button Layout */}
      <div className="flex gap-2">
        {/* Dropdown for sort field */}
        <select
          id={id}
          value={currentKey}
          onChange={handleFieldChange}
          className="
            flex-1 px-3 py-2.5 text-sm font-medium rounded-lg border-2 border-slate-300
            bg-white text-slate-700
            hover:border-emerald-300 hover:bg-emerald-50
            focus:outline-none focus:ring-3 focus:ring-emerald-300 focus:ring-offset-2 focus:border-emerald-500
            transition-all duration-200 min-h-[44px] cursor-pointer
          "
          aria-label="Choose sort field"
          {...props}
        >
          {sortOptions.map(option => (
            <option key={option.key} value={option.key}>
              {option.label}
            </option>
          ))}
        </select>

        {/* Direction toggle button */}
        <button
          onClick={handleDirectionToggle}
          className="
            px-4 py-2.5 text-sm font-medium rounded-lg border-2
            bg-emerald-500 text-white border-emerald-500 shadow-lg
            hover:bg-emerald-600 hover:border-emerald-600
            focus:outline-none focus:ring-3 focus:ring-emerald-300 focus:ring-offset-2
            transition-all duration-200 min-h-[44px] min-w-[44px]
            flex items-center justify-center
          "
          title={`Currently sorting ${directionText}. Click to toggle direction.`}
          aria-label={`Toggle sort direction. Currently ${directionText}`}
        >
          <span className="text-lg" aria-hidden="true">
            {directionIcon}
          </span>
        </button>
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