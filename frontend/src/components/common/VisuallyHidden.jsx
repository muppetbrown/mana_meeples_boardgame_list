import React from "react";

/**
 * Visually Hidden Component
 * Hides content visually but keeps it available to screen readers
 * WCAG 2.1 - Provides context for assistive technologies
 *
 * Usage:
 * <VisuallyHidden>This text is only for screen readers</VisuallyHidden>
 */
export default function VisuallyHidden({ children, as: Component = "span" }) {
  return (
    <Component
      className="sr-only"
      style={{
        position: "absolute",
        width: "1px",
        height: "1px",
        padding: 0,
        margin: "-1px",
        overflow: "hidden",
        clip: "rect(0, 0, 0, 0)",
        whiteSpace: "nowrap",
        borderWidth: 0,
      }}
    >
      {children}
    </Component>
  );
}
