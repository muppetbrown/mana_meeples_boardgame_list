import { useEffect, useState } from 'react';
import { X } from 'lucide-react';

/**
 * Mobile-first help modal explaining game card interactions and AfterGame
 * Full-screen on mobile, centered modal on desktop
 */
export function HelpModal({ isOpen, onClose }) {
  const [activeTab, setActiveTab] = useState('cards');

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }

    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="help-modal-title"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal content - full screen on mobile, centered on desktop */}
      <div className="relative w-full h-full md:h-auto md:max-w-2xl md:max-h-[85vh] bg-white md:rounded-xl shadow-2xl flex flex-col overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between p-4 md:p-6 border-b border-gray-200 bg-gradient-to-r from-emerald-50 to-teal-50">
          <h2
            id="help-modal-title"
            className="text-2xl font-bold text-gray-900"
          >
            Library Guide
          </h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-white/50 transition-colors"
            aria-label="Close help"
          >
            <X className="w-6 h-6 text-gray-600" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200 bg-gray-50 px-4 md:px-6">
          <button
            onClick={() => setActiveTab('cards')}
            className={`px-4 py-3 font-medium transition-colors border-b-2 ${
              activeTab === 'cards'
                ? 'border-emerald-600 text-emerald-700'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            Game Cards
          </button>
          <button
            onClick={() => setActiveTab('aftergame')}
            className={`px-4 py-3 font-medium transition-colors border-b-2 ${
              activeTab === 'aftergame'
                ? 'border-emerald-600 text-emerald-700'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            Plan a Game
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6">
          {activeTab === 'cards' && <GameCardsTab />}
          {activeTab === 'aftergame' && <AfterGameTab />}
        </div>

        {/* Footer */}
        <div className="p-4 md:p-6 border-t border-gray-200 bg-gray-50">
          <button
            onClick={onClose}
            className="w-full px-6 py-3 bg-gradient-to-r from-emerald-600 to-teal-600 text-white font-medium rounded-lg hover:from-emerald-700 hover:to-teal-700 transition-all shadow-md hover:shadow-lg"
          >
            Got it, thanks!
          </button>
        </div>
      </div>
    </div>
  );
}

function GameCardsTab() {
  return (
    <div className="space-y-6">
      <section>
        <h3 className="text-lg font-semibold text-gray-900 mb-3">
          📱 Tap to Expand Cards
        </h3>
        <p className="text-gray-700 mb-3">
          Each game card starts in a <strong>compact view</strong> showing just the essentials.
          Tap anywhere on a card to expand it and see:
        </p>
        <ul className="space-y-2 ml-4">
          <li className="flex items-start">
            <span className="text-emerald-600 mr-2">•</span>
            <span className="text-gray-700"><strong>Rating & Complexity</strong> - BoardGameGeek community ratings</span>
          </li>
          <li className="flex items-start">
            <span className="text-emerald-600 mr-2">•</span>
            <span className="text-gray-700"><strong>Designers</strong> - Who created the game</span>
          </li>
          <li className="flex items-start">
            <span className="text-emerald-600 mr-2">•</span>
            <span className="text-gray-700"><strong>Description</strong> - What the game is about</span>
          </li>
          <li className="flex items-start">
            <span className="text-emerald-600 mr-2">•</span>
            <span className="text-gray-700"><strong>Plan a Game button</strong> - Schedule a session</span>
          </li>
        </ul>
      </section>

      <section className="bg-emerald-50 rounded-lg p-4">
        <h4 className="font-semibold text-gray-900 mb-2">💡 Quick Tip</h4>
        <p className="text-gray-700 text-sm">
          Tap the card title or anywhere on the card to toggle between compact and expanded views.
          Tap "View Full Details" to see everything on a dedicated page.
        </p>
      </section>

      <section>
        <h3 className="text-lg font-semibold text-gray-900 mb-3">
          🎮 What the Icons Mean
        </h3>
        <div className="space-y-3">
          <div className="flex items-start">
            <div className="w-12 flex-shrink-0">
              <span className="text-2xl">👥</span>
            </div>
            <div>
              <p className="font-medium text-gray-900">Player Count</p>
              <p className="text-sm text-gray-600">
                Shows min-max players. An asterisk (*) means more players possible with expansions.
              </p>
            </div>
          </div>

          <div className="flex items-start">
            <div className="w-12 flex-shrink-0">
              <span className="text-2xl">⏱️</span>
            </div>
            <div>
              <p className="font-medium text-gray-900">Play Time</p>
              <p className="text-sm text-gray-600">
                Estimated time range for a typical game session.
              </p>
            </div>
          </div>

          <div className="flex items-start">
            <div className="w-12 flex-shrink-0">
              <span className="text-2xl">⭐</span>
            </div>
            <div>
              <p className="font-medium text-gray-900">Rating</p>
              <p className="text-sm text-gray-600">
                BoardGameGeek community average rating (out of 10).
              </p>
            </div>
          </div>

          <div className="flex items-start">
            <div className="w-12 flex-shrink-0">
              <span className="text-2xl">🧩</span>
            </div>
            <div>
              <p className="font-medium text-gray-900">Complexity</p>
              <p className="text-sm text-gray-600">
                How complex the rules are (1 = simple, 5 = very complex).
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="bg-teal-50 rounded-lg p-4">
        <h4 className="font-semibold text-gray-900 mb-2">🏷️ Category Badges</h4>
        <p className="text-gray-700 text-sm mb-2">
          Games are organized into categories to help you find the right game:
        </p>
        <div className="space-y-1 text-sm text-gray-700">
          <p><strong className="text-emerald-700">Gateway Strategy</strong> - Great for newcomers</p>
          <p><strong className="text-purple-700">Kids & Families</strong> - Fun for all ages</p>
          <p><strong className="text-blue-700">Core Strategy</strong> - Deeper, longer games</p>
          <p><strong className="text-amber-700">Co-op & Adventure</strong> - Work together</p>
          <p><strong className="text-pink-700">Party & Icebreakers</strong> - Social fun</p>
        </div>
      </section>
    </div>
  );
}

function AfterGameTab() {
  return (
    <div className="space-y-6">
      <section>
        <h3 className="text-lg font-semibold text-gray-900 mb-3">
          🎲 What is "Plan a Game"?
        </h3>
        <p className="text-gray-700 mb-3">
          The <strong className="text-emerald-700">"Plan a Game"</strong> button connects you to
          <strong> AfterGame</strong>, a platform where you can schedule game sessions with the
          Mana & Meeples community.
        </p>
      </section>

      <section className="bg-gradient-to-r from-emerald-50 to-teal-50 rounded-lg p-4 border border-emerald-200">
        <h4 className="font-semibold text-gray-900 mb-3">✨ How it Works</h4>
        <ol className="space-y-3">
          <li className="flex items-start">
            <span className="bg-emerald-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold mr-3 flex-shrink-0 mt-0.5">1</span>
            <div>
              <p className="font-medium text-gray-900">Find a game you want to play</p>
              <p className="text-sm text-gray-600">Browse the library and expand cards to see details</p>
            </div>
          </li>
          <li className="flex items-start">
            <span className="bg-emerald-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold mr-3 flex-shrink-0 mt-0.5">2</span>
            <div>
              <p className="font-medium text-gray-900">Click "Plan a Game"</p>
              <p className="text-sm text-gray-600">This opens AfterGame with the game pre-selected</p>
            </div>
          </li>
          <li className="flex items-start">
            <span className="bg-emerald-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold mr-3 flex-shrink-0 mt-0.5">3</span>
            <div>
              <p className="font-medium text-gray-900">Schedule your session</p>
              <p className="text-sm text-gray-600">Pick a date, time, and invite other players</p>
            </div>
          </li>
          <li className="flex items-start">
            <span className="bg-emerald-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold mr-3 flex-shrink-0 mt-0.5">4</span>
            <div>
              <p className="font-medium text-gray-900">Meet up and play!</p>
              <p className="text-sm text-gray-600">Join your scheduled session at Mana & Meeples</p>
            </div>
          </li>
        </ol>
      </section>

      <section>
        <h3 className="text-lg font-semibold text-gray-900 mb-3">
          🤝 Why Schedule Games?
        </h3>
        <ul className="space-y-2">
          <li className="flex items-start">
            <span className="text-emerald-600 mr-2 text-xl">•</span>
            <span className="text-gray-700">
              <strong>Find players</strong> - Connect with others who want to play the same game
            </span>
          </li>
          <li className="flex items-start">
            <span className="text-emerald-600 mr-2 text-xl">•</span>
            <span className="text-gray-700">
              <strong>Plan ahead</strong> - Coordinate times that work for everyone
            </span>
          </li>
          <li className="flex items-start">
            <span className="text-emerald-600 mr-2 text-xl">•</span>
            <span className="text-gray-700">
              <strong>Build community</strong> - Meet fellow board game enthusiasts
            </span>
          </li>
          <li className="flex items-start">
            <span className="text-emerald-600 mr-2 text-xl">•</span>
            <span className="text-gray-700">
              <strong>Try new games</strong> - Easier to learn with others
            </span>
          </li>
        </ul>
      </section>

      <section className="bg-amber-50 rounded-lg p-4 border border-amber-200">
        <h4 className="font-semibold text-gray-900 mb-2">💡 Pro Tip</h4>
        <p className="text-gray-700 text-sm">
          New to a game? Schedule a session and mention you're learning! Experienced players
          in the community often enjoy teaching newcomers.
        </p>
      </section>

      <section>
        <h3 className="text-lg font-semibold text-gray-900 mb-3">
          🔗 About AfterGame
        </h3>
        <p className="text-gray-700 mb-2">
          AfterGame is a free platform specifically designed for organizing board game sessions.
          When you click "Plan a Game" from our library, it automatically:
        </p>
        <ul className="space-y-2 ml-4 mb-3">
          <li className="flex items-start">
            <span className="text-emerald-600 mr-2">•</span>
            <span className="text-gray-700">Pre-fills the game you selected</span>
          </li>
          <li className="flex items-start">
            <span className="text-emerald-600 mr-2">•</span>
            <span className="text-gray-700">Sets the location to Mana & Meeples</span>
          </li>
          <li className="flex items-start">
            <span className="text-emerald-600 mr-2">•</span>
            <span className="text-gray-700">Connects you to our gaming group</span>
          </li>
        </ul>
        <p className="text-sm text-gray-600 italic">
          You'll need to create a free AfterGame account to schedule sessions.
        </p>
      </section>
    </div>
  );
}

export default HelpModal;
