// src/components/common/Thumbnail.jsx
import React, { useState } from "react";
import { imageProxyUrl } from "../../api/client";

/** Small square game thumbnail with a "No img" fallback (no innerHTML). */
export function Thumbnail({ src, alt = "", size = "w-12 h-12" }) {
  const [failed, setFailed] = useState(false);
  return (
    <div className={`${size} rounded overflow-hidden bg-gray-100 flex items-center justify-center shrink-0`}>
      {src && !failed ? (
        <img
          src={imageProxyUrl(src)}
          alt={alt}
          loading="lazy"
          className="w-full h-full object-cover"
          onError={() => setFailed(true)}
        />
      ) : (
        <span className="text-xs text-gray-400">No img</span>
      )}
    </div>
  );
}

export default Thumbnail;
