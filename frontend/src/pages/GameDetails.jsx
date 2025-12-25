// src/pages/GameDetails.jsx
import React from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { getPublicGame } from "../api/client";
import { labelFor } from "../constants/categories";
import { GameDetailsSkeleton } from "../components/common/SkeletonLoader";
import ExpansionMiniCard from "../components/public/ExpansionMiniCard";
import GameImage from "../components/GameImage";
import { getAfterGameCreateUrl } from "../constants/aftergame";

export default function GameDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [game, setGame] = React.useState(null);
  const [error, setError] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [DOMPurify, setDOMPurify] = React.useState(null);
  const handleDesignerClick = (designerName) => {navigate(`/?designer=${encodeURIComponent(designerName)}`);};

  // Lazy load DOMPurify (only needed for game description)
  React.useEffect(() => {
    import('dompurify')
      .then(module => {
        setDOMPurify(module.default);
      })
      .catch(err => {
        console.error('Failed to load DOMPurify:', err);
      });
  }, []);

  React.useEffect(() => {
    let alive = true;
    setLoading(true);
    (async () => {
      try {
        const data = await getPublicGame(id);
        if (alive) {
          // Log the game data for debugging
          console.log('Game details loaded:', {
            id: data?.id,
            title: data?.title,
            hasDescription: !!data?.description,
            descriptionType: typeof data?.description,
            hasExpansions: Array.isArray(data?.expansions),
            expansionsCount: data?.expansions?.length || 0
          });
          setGame(data);
          setError(null);
        }
      } catch (e) {
        if (alive) {
          // Log detailed error for debugging
          console.error('Game details error:', {
            gameId: id,
            error: e,
            message: e?.message,
            response: e?.response?.data
          });

          // Extract error message from various sources
          const errorMessage =
            e?.response?.data?.detail ||
            e?.response?.data?.message ||
            e?.message ||
            "Failed to load game details";

          setError(errorMessage);
        }
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [id]);

  // Category color mapping with fallback
  const getCategoryStyle = (category) => {
    if (!category) return "bg-gradient-to-r from-slate-500 to-gray-500 text-white";

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
          <GameDetailsSkeleton />
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

  // Safely extract values with fallbacks
  const img = game?.image_url || null;
  const cat = labelFor(game?.mana_meeple_category);

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 via-emerald-50 to-teal-50">
      <div className="mx-auto max-w-6xl px-3 sm:px-4 py-4 sm:py-8">
        {/* Back Button */}
        <nav className="mb-4 sm:mb-8">
          <button
            onClick={() => navigate(-1)}
            className="group inline-flex items-center px-4 sm:px-6 py-2.5 sm:py-3 bg-white/80 backdrop-blur-sm rounded-xl border border-white/50 shadow-lg hover:shadow-xl transition-all duration-300 hover:-translate-y-1 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 min-h-[44px] touch-manipulation"
            aria-label="Go back to previous page"
          >
            <svg className="w-4 h-4 sm:w-5 sm:h-5 mr-2 sm:mr-3 transition-transform group-hover:-translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            <span className="font-medium text-slate-700 text-sm sm:text-base">Back to games</span>
          </button>
        </nav>

        {/* Main Content */}
        <main>
          <article className="bg-white/90 backdrop-blur-sm rounded-2xl sm:rounded-3xl shadow-2xl border border-white/50 overflow-hidden">
            <div className="grid grid-cols-1 lg:grid-cols-[400px,1fr] gap-0">
              {/* Image Section */}
              <div className="relative bg-gradient-to-br from-slate-100 to-slate-200 aspect-[4/3] sm:aspect-square lg:aspect-square">
                <GameImage
                  url={img}
                  alt={`${game?.title || 'Board game'} board game cover`}
                  className="w-full h-full object-cover"
                  fallbackClass="w-full h-full flex flex-col items-center justify-center text-slate-600 bg-gradient-to-br from-slate-100 to-slate-200"
                  loading="eager"
                  fetchPriority="high"
                  aspectRatio="1/1"
                />

                {/* Category Badge */}
                {cat && cat !== "—" && (
                  <div className="absolute top-2 right-2 sm:top-3 sm:right-3 lg:top-6 lg:right-6">
                    <span className={`px-2 py-1 sm:px-3 sm:py-1.5 lg:px-4 lg:py-2 rounded-full text-xs sm:text-sm font-bold shadow-xl ${getCategoryStyle(game?.mana_meeple_category)}`}>
                      {cat}
                    </span>
                  </div>
                )}
              </div>

              {/* Content Section */}
              <div className="p-4 sm:p-6 lg:p-8 xl:p-12">
                {/* Title and Basic Info */}
                <header className="mb-6 sm:mb-8">
                  <h1 className="text-2xl sm:text-3xl lg:text-4xl xl:text-5xl font-bold bg-gradient-to-r from-slate-800 to-slate-600 bg-clip-text text-transparent mb-3 sm:mb-4">
                    {game?.title || "Untitled Game"}
                  </h1>
                  
                  {/* Game Stats */}
                  <div className="flex flex-wrap gap-2 sm:gap-3 lg:gap-4 text-sm">
                    <div className="flex items-center bg-emerald-100 rounded-full px-2 py-1 sm:px-3 sm:py-1.5 lg:px-4 lg:py-2 min-h-[44px] sm:min-h-auto">
                      <span className="w-2 h-2 rounded-full bg-emerald-500 mr-2" aria-hidden="true"></span>
                      <span className="font-medium text-emerald-800">Players: </span>
                      <span className="font-bold text-emerald-900 ml-1">
                        {game?.has_player_expansion && game?.players_max_with_expansions > (game?.max_players || 0)
                          ? `${game?.players_min_with_expansions ?? game?.min_players ?? "?"}-${game?.players_max_with_expansions ?? "?"}*`
                          : `${game?.min_players ?? "?"}-${game?.max_players ?? "?"}`
                        }
                      </span>
                    </div>
                    
                    <div className="flex items-center bg-amber-100 rounded-full px-2 py-1 sm:px-3 sm:py-1.5 lg:px-4 lg:py-2 min-h-[44px] sm:min-h-auto">
                      <span className="w-2 h-2 rounded-full bg-amber-500 mr-2" aria-hidden="true"></span>
                      <span className="font-medium text-amber-800">Time: </span>
                      <span className="font-bold text-amber-900 ml-1">
                        {game?.playing_time ?? "?"} min
                      </span>
                    </div>

                    <div className="flex items-center bg-blue-100 rounded-full px-2 py-1 sm:px-3 sm:py-1.5 lg:px-4 lg:py-2 min-h-[44px] sm:min-h-auto">
                      <span className="w-2 h-2 rounded-full bg-blue-500 mr-2" aria-hidden="true"></span>
                      <span className="font-medium text-blue-800">Year: </span>
                      <span className="font-bold text-blue-900 ml-1">
                        {game?.year_published || "–"}
                      </span>
                    </div>

                    {game?.game_type && (
                      <div className="flex items-center bg-purple-100 rounded-full px-2 py-1 sm:px-3 sm:py-1.5 lg:px-4 lg:py-2 min-h-[44px] sm:min-h-auto">
                        <span className="w-2 h-2 rounded-full bg-purple-500 mr-2" aria-hidden="true"></span>
                        <span className="font-medium text-purple-800">Type: </span>
                        <span className="font-bold text-purple-900 ml-1">
                          {game?.game_type}
                        </span>
                      </div>
                    )}
                  </div>
                </header>

                {/* Game Details */}
                <div className="space-y-6">
                  {/* Designers & Publishers */}
                    {Array.isArray(game?.designers) && game.designers.length > 0 && (
                      <div>
                        <dt className="font-medium text-slate-600">Designer:</dt>
                        <dd className="text-slate-800">
                          {game.designers.map((designer, index) => (
                            <span key={`designer-${index}-${designer}`}>
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
                  {Array.isArray(game?.mechanics) && game.mechanics.length > 0 && (
                    <section>
                      <h2 className="font-bold text-slate-800 mb-4">Game Mechanics</h2>
                      <div className="flex flex-wrap gap-2">
                        {game.mechanics.map((mechanic, i) => (
                          <span
                            key={`mechanic-${i}-${mechanic}`}
                            className="px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
                          >
                            {mechanic}
                          </span>
                        ))}
                      </div>
                    </section>
                  )}

                  {/* Description */}
                  {game?.description && DOMPurify && typeof game.description === 'string' && (
                    <section>
                      <h2 className="font-bold text-slate-800 mb-4">About This Game</h2>
                      <div className="prose prose-slate max-w-none">
                        <div
                          className="text-slate-700 leading-relaxed"
                          dangerouslySetInnerHTML={{
                            __html: (() => {
                              try {
                                return DOMPurify.sanitize(game.description, {
                                  ALLOWED_TAGS: ['p', 'br', 'b', 'i', 'em', 'strong', 'a', 'ul', 'ol', 'li'],
                                  ALLOWED_ATTR: ['href', 'target', 'rel']
                                });
                              } catch (err) {
                                console.error('DOMPurify sanitize error:', err);
                                return '<p>Description unavailable</p>';
                              }
                            })()
                          }}
                        />
                      </div>
                    </section>
                  )}

                  {/* Base Game Info (if this is an expansion) */}
                  {game?.is_expansion && game?.base_game && game.base_game.id && game.base_game.title && (
                    <section>
                      <div className="p-4 bg-purple-50 border-l-4 border-purple-600 rounded-lg">
                        <p className="text-sm text-slate-600 mb-2">
                          This is an expansion for:
                        </p>
                        <Link
                          to={`/game/${game.base_game.id}`}
                          className="inline-flex items-center text-lg font-semibold text-purple-600 hover:text-purple-800 transition-colors group"
                        >
                          {game.base_game.title}
                          <svg
                            className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                            aria-hidden="true"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M9 5l7 7-7 7"
                            />
                          </svg>
                        </Link>
                      </div>
                    </section>
                  )}

                  {/* Available Expansions */}
                  {Array.isArray(game?.expansions) && game.expansions.length > 0 && (
                    <section>
                      <h2 className="font-bold text-slate-800 mb-4">
                        Available Expansions ({game.expansions.length})
                      </h2>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                        {game.expansions.map((expansion) => (
                          <ExpansionMiniCard
                            key={expansion?.id || expansion?.title}
                            expansion={expansion}
                          />
                        ))}
                      </div>
                    </section>
                  )}

                  {/* Action Buttons */}
                  <section className="pt-4">
                    <div className="flex flex-wrap gap-3">
                      {/* Plan a Game Button */}
                      <a
                        href={getAfterGameCreateUrl(game.aftergame_game_id)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-teal-500 to-emerald-500 text-white font-medium rounded-xl hover:from-teal-600 hover:to-emerald-600 transition-all duration-300 shadow-lg hover:shadow-xl transform hover:-translate-y-1 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2"
                        aria-label="Plan a game session on AfterGame (opens in new tab)"
                      >
                        <img
                          src="/Aftergame_Icon_Logo_V3-Light.webp"
                          alt="AfterGame"
                          className="w-6 h-6 mr-2"
                        />
                        Plan a Game
                        <span className="sr-only"> (opens in new tab)</span>
                      </a>

                      {/* BoardGameGeek Link */}
                      {game?.bgg_id && (
                        <a
                          href={`https://boardgamegeek.com/boardgame/${game.bgg_id}`}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-amber-500 to-orange-500 text-white font-medium rounded-xl hover:from-amber-600 hover:to-orange-600 transition-all duration-300 shadow-lg hover:shadow-xl transform hover:-translate-y-1 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2"
                          aria-label={`View ${game?.title || 'game'} on BoardGameGeek (opens in new tab)`}
                        >
                          <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                            <path fillRule="evenodd" d="M12.586 4.586a2 2 0 112.828 2.828l-3 3a2 2 0 01-2.828 0 1 1 0 00-1.414 1.414 4 4 0 005.656 0l3-3a4 4 0 00-5.656-5.656l-1.5 1.5a1 1 0 101.414 1.414l1.5-1.5zm-5 5a2 2 0 012.828 0 1 1 0 101.414-1.414 4 4 0 00-5.656 0l-3 3a4 4 0 105.656 5.656l1.5-1.5a1 1 0 10-1.414-1.414l-1.5 1.5a2 2 0 11-2.828-2.828l3-3z" clipRule="evenodd" />
                          </svg>
                          View on BoardGameGeek
                          <span className="sr-only"> (opens in new tab)</span>
                        </a>
                      )}
                    </div>
                  </section>
                </div>
              </div>
            </div>
          </article>
        </main>
      </div>
    </div>
  );
}