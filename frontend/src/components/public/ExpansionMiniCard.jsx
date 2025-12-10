// src/components/public/ExpansionMiniCard.jsx
import React from "react";
import { Link } from "react-router-dom";
import { imageProxyUrl } from "../../config/api";

export default function ExpansionMiniCard({ expansion }) {
  const imgSrc = expansion.image_url ? imageProxyUrl(expansion.image_url) : null;

  return (
    <Link
      to={`/game/${expansion.id}`}
      className="group border-2 border-slate-200 rounded-xl p-3 hover:shadow-lg hover:border-purple-300 transition-all duration-200 focus:outline-none focus:ring-4 focus:ring-purple-200 focus:ring-offset-2"
    >
      <div className="flex gap-3">
        {/* Thumbnail */}
        <div className="flex-shrink-0 w-20 h-20 rounded-lg overflow-hidden bg-gradient-to-br from-slate-100 to-slate-200">
          {imgSrc ? (
            <img
              src={imgSrc}
              alt={`Cover for ${expansion.title}`}
              className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-200"
              loading="lazy"
              onError={(e) => {
                e.target.style.display = 'none';
                e.target.nextElementSibling.style.display = 'flex';
              }}
            />
          ) : null}

          {/* Fallback when no image */}
          <div className={`w-full h-full flex items-center justify-center text-slate-400 ${imgSrc ? 'hidden' : 'flex'}`}>
            <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
              <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
            </svg>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-sm text-slate-900 line-clamp-2 group-hover:text-purple-700 transition-colors">
            {expansion.title}
          </h3>

          {/* Player count modification */}
          {expansion.modifies_players_max && (
            <p className="text-xs text-purple-600 mt-1 font-medium">
              Expands to {expansion.modifies_players_min || expansion.players_min}-
              {expansion.modifies_players_max} players
            </p>
          )}

          {/* Expansion type badge */}
          <div className="mt-2">
            <span
              className={`inline-block text-xs px-2 py-0.5 rounded-full font-semibold ${
                expansion.expansion_type === 'both' || expansion.expansion_type === 'standalone'
                  ? 'bg-indigo-100 text-indigo-800'
                  : expansion.expansion_type === 'requires_base'
                  ? 'bg-purple-100 text-purple-800'
                  : 'bg-slate-100 text-slate-800'
              }`}
            >
              {expansion.expansion_type === 'both' || expansion.expansion_type === 'standalone'
                ? 'Standalone'
                : expansion.expansion_type === 'requires_base'
                ? 'Requires Base'
                : 'Expansion'}
            </span>
          </div>
        </div>
      </div>
    </Link>
  );
}
