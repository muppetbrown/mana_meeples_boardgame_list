// src/pages/GameDetails.jsx
import React from "react";
import { useParams, useNavigate } from "react-router-dom";
import { fetchJson, imageProxyUrl } from "../utils/api";
import { labelFor } from "../constants/categories";

export default function GameDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [game, setGame] = React.useState(null);
  const [error, setError] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const handleDesignerClick = (designerName) => {navigate(`/?designer=${encodeURIComponent(designerName)}`);};

  React.useEffect(() => {
    let alive = true;
    setLoading(true);
    (async () => {
      try {
        const data = await fetchJson(`/api/public/games/${id}`);
        if (alive) {
          setGame(data);
          setError(null);
        }
      } catch (e) {
        if (alive) {
          setError(e?.message || "Failed to load game details");
        }
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [id]);

  // Category color mapping
  const getCategoryStyle = (category) => {
    const styles = {
      "GATEWAY_STRATEGY": "bg-gradient-to-r from-emerald-500 to-teal-500 text-white",
      "KIDS_FAMILIES": "bg-gradient-to-r from-purple-500 to-pink-500 text-white", 
      "CORE_STRATEGY": "bg-gradient-to-r from-blue-600 to-indigo-600 text-white",
      "COOP_ADVENTURE": "bg-gradient-to-r from-orange-500 to-red-500 text-white",
      "PARTY_ICEBREAKERS": "bg-gradient-to-r from-yellow-500 to-amber-500 text-white",
      "default": "bg-gradient-to-r from-slate-500 to-gray-500 text-white"
    };
    return styles[category] || styles.default;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-amber-50 via-emerald-50 to-teal-50">
        <div className="max-w-6xl mx-auto px-4 py-8">
          <div className="text-center py-16" role="status" aria-live="polite">
            <div className="inline-flex items-center px-6 py-3 rounded-full bg-white/80 text-slate-600">
              <div className="animate-spin rounded-full h-5 w-5 border-2 border-emerald-500 border-t-transparent mr-3" aria-hidden="true"></div>
              <span>Loading game details...</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-amber-50 via-emerald-50 to-teal-50">
        <div className="max-w-6xl mx-auto px-4 py-8">
          <div className="text-center py-16">
            <div className="bg-red-50 border border-red-200 rounded-xl p-8 max-w-md mx-auto" role="alert">
              <h1 className="text-red-600 font-medium text-lg mb-2">Couldn't load game</h1>
              <p className="text-red-500 text-sm mb-4">{error}</p>
              <button
                onClick={() => navigate(-1)}
                className="inline-flex items-center px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2"
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                Go Back
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!game) return null;

  const img = game.image_url ? imageProxyUrl(game.image_url) : null;
  const cat = labelFor(game.mana_meeple_category);

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 via-emerald-50 to-teal-50">
      <div className="mx-auto max-w-6xl px-4 py-8">
        {/* Back Button */}
        <nav className="mb-8">
          <button
            onClick={() => navigate(-1)}
            className="group inline-flex items-center px-6 py-3 bg-white/80 backdrop-blur-sm rounded-xl border border-white/50 shadow-lg hover:shadow-xl transition-all duration-300 hover:-translate-y-1 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2"
            aria-label="Go back to previous page"
          >
            <svg className="w-5 h-5 mr-3 transition-transform group-hover:-translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            <span className="font-medium text-slate-700">Back to games</span>
          </button>
        </nav>

        {/* Main Content */}
        <main>
          <article className="bg-white/90 backdrop-blur-sm rounded-3xl shadow-2xl border border-white/50 overflow-hidden">
            <div className="grid grid-cols-1 lg:grid-cols-[400px,1fr] gap-0">
              {/* Image Section */}
              <div className="relative bg-gradient-to-br from-slate-100 to-slate-200 lg:aspect-square">
                {img ? (
                  <img
                    src={img}
                    alt={`${game.title} board game cover`}
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                ) : (
                  <div className="w-full h-64 lg:h-full flex flex-col items-center justify-center text-slate-400">
                    <div className="w-20 h-20 rounded-full bg-slate-300 flex items-center justify-center mb-4">
                      <svg className="w-10 h-10" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                        <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
                      </svg>
                    </div>
                    <span className="text-lg font-medium">No Image Available</span>
                  </div>
                )}
                
                {/* Category Badge */}
                {cat && (
                  <div className="absolute top-6 right-6">
                    <span className={`px-4 py-2 rounded-full text-sm font-bold shadow-xl ${getCategoryStyle(game.mana_meeple_category)}`}>
                      {cat}
                    </span>
                  </div>
                )}
              </div>

              {/* Content Section */}
              <div className="p-8 lg:p-12">
                {/* Title and Basic Info */}
                <header className="mb-8">
                  <h1 className="text-4xl lg:text-5xl font-bold bg-gradient-to-r from-slate-800 to-slate-600 bg-clip-text text-transparent mb-4">
                    {game.title}
                  </h1>
                  
                  {/* Game Stats */}
                  <div className="flex flex-wrap gap-4 text-sm">
                    <div className="flex items-center bg-emerald-100 rounded-full px-4 py-2">
                      <span className="w-2 h-2 rounded-full bg-emerald-500 mr-2" aria-hidden="true"></span>
                      <span className="font-medium text-emerald-800">Players: </span>
                      <span className="font-bold text-emerald-900 ml-1">
                        {game.min_players ?? "?"}-{game.max_players ?? "?"}
                      </span>
                    </div>
                    
                    <div className="flex items-center bg-amber-100 rounded-full px-4 py-2">
                      <span className="w-2 h-2 rounded-full bg-amber-500 mr-2" aria-hidden="true"></span>
                      <span className="font-medium text-amber-800">Time: </span>
                      <span className="font-bold text-amber-900 ml-1">
                        {game.playing_time ?? "?"} min
                      </span>
                    </div>
                    
                    <div className="flex items-center bg-blue-100 rounded-full px-4 py-2">
                      <span className="w-2 h-2 rounded-full bg-blue-500 mr-2" aria-hidden="true"></span>
                      <span className="font-medium text-blue-800">Year: </span>
                      <span className="font-bold text-blue-900 ml-1">
                        {game.year_published || "–"}
                      </span>
                    </div>
                  </div>
                </header>

                {/* Game Details */}
                <div className="space-y-6">
                  {/* Designers & Publishers */}
                    {game.designers?.length && (
                      <div>
                        <dt className="font-medium text-slate-600">Designer:</dt>
                        <dd className="text-slate-800">
                          {game.designers.map((designer, index) => (
                            <span key={designer}>
                              <button
                                onClick={() => handleDesignerClick(designer)}
                                className="text-emerald-600 hover:text-emerald-700 hover:underline cursor-pointer font-medium"
                              >
                                {designer}
                              </button>
                              {index < game.designers.length - 1 && ", "}
                            </span>
                          ))}
                        </dd>
                      </div>
                    )}

                  {/* Game Mechanics */}
                  {Array.isArray(game.mechanics) && game.mechanics.length > 0 && (
                    <section>
                      <h2 className="font-bold text-slate-800 mb-4">Game Mechanics</h2>
                      <div className="flex flex-wrap gap-2">
                        {game.mechanics.map((mechanic, i) => (
                          <span
                            key={`${mechanic}-${i}`}
                            className="px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
                          >
                            {mechanic}
                          </span>
                        ))}
                      </div>
                    </section>
                  )}

                  {/* Description */}
                  {game.description && (
                    <section>
                      <h2 className="font-bold text-slate-800 mb-4">About This Game</h2>
                      <div className="prose prose-slate max-w-none">
                        <p className="text-slate-700 leading-relaxed whitespace-pre-wrap">
                          {game.description}
                        </p>
                      </div>
                    </section>
                  )}

                  {/* BoardGameGeek Link */}
                  {game.bgg_id && (
                    <section className="pt-4">
                      <a
                        href={`https://boardgamegeek.com/boardgame/${game.bgg_id}`}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-amber-500 to-orange-500 text-white font-medium rounded-xl hover:from-amber-600 hover:to-orange-600 transition-all duration-300 shadow-lg hover:shadow-xl transform hover:-translate-y-1 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2"
                        aria-label={`View ${game.title} on BoardGameGeek (opens in new tab)`}
                      >
                        <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                          <path fillRule="evenodd" d="M12.586 4.586a2 2 0 112.828 2.828l-3 3a2 2 0 01-2.828 0 1 1 0 00-1.414 1.414 4 4 0 005.656 0l3-3a4 4 0 00-5.656-5.656l-1.5 1.5a1 1 0 101.414 1.414l1.5-1.5zm-5 5a2 2 0 012.828 0 1 1 0 101.414-1.414 4 4 0 00-5.656 0l-3 3a4 4 0 105.656 5.656l1.5-1.5a1 1 0 10-1.414-1.414l-1.5 1.5a2 2 0 11-2.828-2.828l3-3z" clipRule="evenodd" />
                        </svg>
                        View on BoardGameGeek
                        <span className="sr-only"> (opens in new tab)</span>
                      </a>
                    </section>
                  )}
                </div>
              </div>
            </div>
          </article>
        </main>
      </div>
    </div>
  );
}