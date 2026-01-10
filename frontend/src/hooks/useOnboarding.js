import { useState, useEffect, useCallback } from 'react';
import { safeStorage } from '../utils/storage';

const STORAGE_KEY = 'mana_meeples_onboarding';
const STORAGE_VERSION = '1.0';

const defaultState = {
  version: STORAGE_VERSION,
  firstVisit: null,
  lastVisit: null,
  hasExpandedCard: false,
  hasClickedAfterGame: false,
  hasOpenedHelp: false,
  dismissedHints: [],
};

/**
 * Custom hook for managing onboarding state with localStorage persistence
 * Tracks user interactions to progressively hide hints on mobile
 */
export function useOnboarding() {
  const [state, setState] = useState(() => {
    try {
      // SECURITY: Use safeStorage instead of direct localStorage to handle tracking prevention
      const stored = safeStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        // Check version compatibility
        if (parsed.version === STORAGE_VERSION) {
          return { ...defaultState, ...parsed, lastVisit: new Date().toISOString() };
        }
      }
    } catch (error) {
      console.warn('Failed to load onboarding state:', error);
    }

    // First visit
    const now = new Date().toISOString();
    return {
      ...defaultState,
      firstVisit: now,
      lastVisit: now,
    };
  });

  // Persist to localStorage whenever state changes
  useEffect(() => {
    try {
      // SECURITY: Use safeStorage instead of direct localStorage to handle tracking prevention
      safeStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (error) {
      console.warn('Failed to save onboarding state:', error);
    }
  }, [state]);

  // Check if this is the first visit
  const isFirstVisit = !state.firstVisit || state.firstVisit === state.lastVisit;

  // Track card expansion
  const markCardExpanded = useCallback(() => {
    setState(prev => ({ ...prev, hasExpandedCard: true }));
  }, []);

  // Track AfterGame click
  const markAfterGameClicked = useCallback(() => {
    setState(prev => ({ ...prev, hasClickedAfterGame: true }));
  }, []);

  // Track help modal opened
  const markHelpOpened = useCallback(() => {
    setState(prev => ({ ...prev, hasOpenedHelp: true }));
  }, []);

  // Dismiss a specific hint
  const dismissHint = useCallback((hintId) => {
    setState(prev => ({
      ...prev,
      dismissedHints: [...new Set([...prev.dismissedHints, hintId])],
    }));
  }, []);

  // Check if a hint has been dismissed
  const isHintDismissed = useCallback((hintId) => {
    return state.dismissedHints.includes(hintId);
  }, [state.dismissedHints]);

  // Reset all onboarding state (useful for testing)
  const reset = useCallback(() => {
    const now = new Date().toISOString();
    setState({
      ...defaultState,
      firstVisit: now,
      lastVisit: now,
    });
  }, []);

  // Should show card expansion hint?
  const shouldShowCardHint = !state.hasExpandedCard && !isHintDismissed('card-expand');

  // Should show AfterGame hint?
  const shouldShowAfterGameHint = !state.hasClickedAfterGame && !isHintDismissed('aftergame');

  return {
    // State flags
    isFirstVisit,
    hasExpandedCard: state.hasExpandedCard,
    hasClickedAfterGame: state.hasClickedAfterGame,
    hasOpenedHelp: state.hasOpenedHelp,

    // Hint visibility helpers
    shouldShowCardHint,
    shouldShowAfterGameHint,
    isHintDismissed,

    // Actions
    markCardExpanded,
    markAfterGameClicked,
    markHelpOpened,
    dismissHint,
    reset,
  };
}

export default useOnboarding;
