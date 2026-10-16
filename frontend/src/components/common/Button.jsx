// src/components/common/Button.jsx
/**
 * Shared admin button. One place defines variants/sizes so the same action
 * looks the same on every tab.
 */
import React from "react";

const VARIANTS = {
  primary: "bg-purple-600 text-white hover:bg-purple-700 border border-purple-600",
  secondary: "bg-white text-gray-700 border border-gray-300 hover:bg-gray-50",
  danger: "bg-red-600 text-white hover:bg-red-700 border border-red-600",
  dangerGhost: "bg-white text-red-700 border border-red-200 hover:bg-red-50",
  ghost: "bg-transparent text-gray-600 border border-transparent hover:bg-gray-100",
};
const SIZES = {
  sm: "h-8 px-2.5 text-xs gap-1.5",
  md: "h-9 px-3.5 text-sm gap-2",
};

export function buttonClass({ variant = "secondary", size = "md", className = "" } = {}) {
  return `inline-flex items-center justify-center font-medium rounded-md whitespace-nowrap transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${VARIANTS[variant]} ${SIZES[size]} ${className}`;
}

export const Button = React.forwardRef(function Button(
  { variant, size, className, type = "button", children, ...rest },
  ref
) {
  return (
    <button ref={ref} type={type} className={buttonClass({ variant, size, className })} {...rest}>
      {children}
    </button>
  );
});

export default Button;
