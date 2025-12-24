import React, { useEffect, useRef } from "react";

/**
 * ARIA Live Region Component
 * Announces dynamic content changes to screen readers
 * WCAG 2.1 Level A - Status Messages (4.1.3)
 *
 * @param {string} message - Message to announce
 * @param {string} politeness - "polite" (default) or "assertive"
 * @param {boolean} atomic - Whether to read entire region
 */
export default function LiveRegion({
  message,
  politeness = "polite",
  atomic = true,
  clearAfter = 5000, // Clear message after 5 seconds
}) {
  const regionRef = useRef(null);

  useEffect(() => {
    if (message && clearAfter) {
      const timer = setTimeout(() => {
        if (regionRef.current) {
          regionRef.current.textContent = "";
        }
      }, clearAfter);

      return () => clearTimeout(timer);
    }
  }, [message, clearAfter]);

  return (
    <div
      ref={regionRef}
      role="status"
      aria-live={politeness}
      aria-atomic={atomic}
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
      {message}
    </div>
  );
}
