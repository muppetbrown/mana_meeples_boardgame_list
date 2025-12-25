import { HelpCircle } from 'lucide-react';

/**
 * Floating help button - always accessible
 * Positioned at bottom-center on mobile, bottom-right on desktop
 */
export function HelpButton({ onClick, showPulse = false }) {
  return (
    <button
      onClick={onClick}
      className={`
        fixed z-40
        bottom-4 left-1/2 -translate-x-1/2
        md:left-auto md:right-6 md:bottom-6 md:translate-x-0
        flex items-center gap-2
        px-4 py-3 md:px-5 md:py-3
        bg-gradient-to-r from-emerald-600 to-teal-600
        text-white font-medium
        rounded-full
        shadow-lg hover:shadow-xl
        hover:from-emerald-700 hover:to-teal-700
        transition-all duration-200
        ${showPulse ? 'animate-pulse' : ''}
      `}
      aria-label="Open help guide"
    >
      <HelpCircle className="w-5 h-5" />
      <span className="text-sm md:text-base">Help</span>
    </button>
  );
}

export default HelpButton;
