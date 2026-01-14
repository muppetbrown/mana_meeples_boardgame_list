/**
 * StatBadge - Reusable stat badge component for game cards
 * Displays an icon with a label in a consistent styled container
 */
import React from 'react';
import PropTypes from 'prop-types';

export function StatBadge({ icon: Icon, label, ariaLabel, className = '' }) {
  return (
    <div
      className={`flex flex-col items-center justify-center gap-0.5 md:gap-1 bg-slate-50 rounded-lg py-1.5 md:py-2 px-1 ${className}`}
      aria-label={ariaLabel || label}
    >
      {Icon && (
        <Icon
          className="w-3.5 h-3.5 md:w-4 md:h-4 text-emerald-600"
          aria-hidden="true"
        />
      )}
      <span className="font-semibold text-xs md:text-sm text-slate-700">
        {label || '—'}
      </span>
    </div>
  );
}

StatBadge.propTypes = {
  icon: PropTypes.elementType,
  label: PropTypes.string,
  ariaLabel: PropTypes.string,
  className: PropTypes.string,
};

export default StatBadge;
