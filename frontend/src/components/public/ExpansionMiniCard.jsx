// src/components/public/ExpansionMiniCard.jsx
import React from "react";
import { Link } from "react-router-dom";
import GameImage from "../GameImage";

export default function ExpansionMiniCard({ expansion }) {
  // Guard against missing expansion data
  if (!expansion || !expansion.id) {
    console.warn('ExpansionMiniCard received invalid expansion data:', expansion);
    return null;
  }

  const imgSrc = expansion?.image_url;

  return (
    <Link
      to={`/game/${expansion.id}`}
      className="group border-2 border-slate-200 rounded-xl p-3 hover:shadow-lg hover:border-purple-300 transition-all duration-200 focus:outline-none focus:ring-4 focus:ring-purple-200 focus:ring-offset-2"
    >
      <div className="flex gap-3">
        {/* Thumbnail */}
        <div className="shrink-0 w-20 h-20 rounded-lg overflow-hidden bg-linear-to-br from-slate-100 to-slate-200">
          <GameImage
            url={imgSrc}
            alt={`Cover for ${expansion?.title || 'expansion'}`}
            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-200"
            fallbackClass="w-full h-full flex items-center justify-center text-slate-400 bg-linear-to-br from-slate-100 to-slate-200"
            loading="lazy"
            aspectRatio="1/1"
          />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-sm text-slate-900 line-clamp-2 group-hover:text-purple-700 transition-colors">
            {expansion?.title || 'Untitled Expansion'}
          </h3>

          {/* Player count modification */}
          {expansion?.modifies_players_max && (
            <p className="text-xs text-purple-600 mt-1 font-medium">
              Expands to {expansion?.modifies_players_min || expansion?.players_min || '?'}-
              {expansion?.modifies_players_max} players
            </p>
          )}

          {/* Expansion type badge */}
          <div className="mt-2">
            <span
              className={`inline-block text-xs px-2 py-0.5 rounded-full font-semibold ${
                expansion?.expansion_type === 'both' || expansion?.expansion_type === 'standalone'
                  ? 'bg-indigo-100 text-indigo-800'
                  : expansion?.expansion_type === 'requires_base'
                  ? 'bg-purple-100 text-purple-800'
                  : 'bg-slate-100 text-slate-800'
              }`}
            >
              {expansion?.expansion_type === 'both' || expansion?.expansion_type === 'standalone'
                ? 'Standalone'
                : expansion?.expansion_type === 'requires_base'
                ? 'Requires Base'
                : 'Expansion'}
            </span>
          </div>
        </div>
      </div>
    </Link>
  );
}
