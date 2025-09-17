// src/components/GameImage.jsx
import React from "react";
import { imageProxyUrl } from "../utils/api";

export default function GameImage({ url, alt, className, fallbackClass }) {
  if (!url) {
    return (
      <div className={fallbackClass || "w-20 h-20 bg-gray-200 rounded-xl flex items-center justify-center text-gray-500 text-sm"}>
        No Image
      </div>
    );
  }
  return (
    <img
      src={imageProxyUrl(url)}   // absolute URL to backend
      alt={alt}
      className={className}
      onError={(e)=>{ e.currentTarget.style.display="none"; }}
    />
  );
}
