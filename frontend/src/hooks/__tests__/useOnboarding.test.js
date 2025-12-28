// frontend/src/hooks/__tests__/useOnboarding.test.js
import { renderHook, act } from '@testing-library/react';
import { useOnboarding } from '../useOnboarding';

const STORAGE_KEY = 'mana_meeples_onboarding';

describe('useOnboarding Hook', () => {
  beforeEach(() => {
    localStorage.clear();
    jest.clearAllMocks();
  });

  test('initializes with default state on first visit', () => {
    const { result } = renderHook(() => useOnboarding());

    expect(result.current.isFirstVisit).toBe(true);
    expect(result.current.hasExpandedCard).toBe(false);
    expect(result.current.hasClickedAfterGame).toBe(false);
    expect(result.current.hasOpenedHelp).toBe(false);
    expect(result.current.shouldShowCardHint).toBe(true);
    expect(result.current.shouldShowAfterGameHint).toBe(true);
  });

  test('persists state to localStorage', () => {
    const { result } = renderHook(() => useOnboarding());

    act(() => {
      result.current.markCardExpanded();
    });

    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY));
    expect(stored.hasExpandedCard).toBe(true);
  });

  test('loads state from localStorage on subsequent visits', () => {
    // Simulate previous visit
    const previousState = {
      version: '1.0',
      firstVisit: '2024-01-01T00:00:00.000Z',
      lastVisit: '2024-01-01T00:00:00.000Z',
      hasExpandedCard: true,
      hasClickedAfterGame: false,
      hasOpenedHelp: false,
      dismissedHints: [],
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(previousState));

    const { result } = renderHook(() => useOnboarding());

    expect(result.current.isFirstVisit).toBe(false);
    expect(result.current.hasExpandedCard).toBe(true);
  });

  test('marks card as expanded', () => {
    const { result } = renderHook(() => useOnboarding());

    expect(result.current.hasExpandedCard).toBe(false);
    expect(result.current.shouldShowCardHint).toBe(true);

    act(() => {
      result.current.markCardExpanded();
    });

    expect(result.current.hasExpandedCard).toBe(true);
    expect(result.current.shouldShowCardHint).toBe(false);
  });

  test('marks AfterGame as clicked', () => {
    const { result } = renderHook(() => useOnboarding());

    expect(result.current.hasClickedAfterGame).toBe(false);
    expect(result.current.shouldShowAfterGameHint).toBe(true);

    act(() => {
      result.current.markAfterGameClicked();
    });

    expect(result.current.hasClickedAfterGame).toBe(true);
    expect(result.current.shouldShowAfterGameHint).toBe(false);
  });

  test('marks help as opened', () => {
    const { result } = renderHook(() => useOnboarding());

    expect(result.current.hasOpenedHelp).toBe(false);

    act(() => {
      result.current.markHelpOpened();
    });

    expect(result.current.hasOpenedHelp).toBe(true);
  });

  test('dismisses specific hints', () => {
    const { result } = renderHook(() => useOnboarding());

    expect(result.current.isHintDismissed('card-expand')).toBe(false);

    act(() => {
      result.current.dismissHint('card-expand');
    });

    expect(result.current.isHintDismissed('card-expand')).toBe(true);
    expect(result.current.shouldShowCardHint).toBe(false);
  });

  test('dismisses multiple hints', () => {
    const { result } = renderHook(() => useOnboarding());

    act(() => {
      result.current.dismissHint('card-expand');
      result.current.dismissHint('aftergame');
    });

    expect(result.current.isHintDismissed('card-expand')).toBe(true);
    expect(result.current.isHintDismissed('aftergame')).toBe(true);
  });

  test('does not add duplicate dismissed hints', () => {
    const { result } = renderHook(() => useOnboarding());

    act(() => {
      result.current.dismissHint('card-expand');
      result.current.dismissHint('card-expand');
      result.current.dismissHint('card-expand');
    });

    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY));
    const cardHintCount = stored.dismissedHints.filter(h => h === 'card-expand').length;
    expect(cardHintCount).toBe(1);
  });

  test('resets all onboarding state', () => {
    const { result } = renderHook(() => useOnboarding());

    // Set some state
    act(() => {
      result.current.markCardExpanded();
      result.current.markAfterGameClicked();
      result.current.dismissHint('test-hint');
    });

    expect(result.current.hasExpandedCard).toBe(true);
    expect(result.current.hasClickedAfterGame).toBe(true);
    expect(result.current.isHintDismissed('test-hint')).toBe(true);

    // Reset
    act(() => {
      result.current.reset();
    });

    expect(result.current.hasExpandedCard).toBe(false);
    expect(result.current.hasClickedAfterGame).toBe(false);
    expect(result.current.hasOpenedHelp).toBe(false);
    expect(result.current.isHintDismissed('test-hint')).toBe(false);
    expect(result.current.isFirstVisit).toBe(true);
  });

  test('handles corrupted localStorage data gracefully', () => {
    localStorage.setItem(STORAGE_KEY, 'invalid-json');

    const consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation();

    const { result } = renderHook(() => useOnboarding());

    // Should fall back to default state
    expect(result.current.isFirstVisit).toBe(true);
    expect(consoleWarnSpy).toHaveBeenCalledWith(
      'Failed to load onboarding state:',
      expect.any(Error)
    );

    consoleWarnSpy.mockRestore();
  });

  test('ignores incompatible version in localStorage', () => {
    const oldVersionState = {
      version: '0.9',
      firstVisit: '2024-01-01T00:00:00.000Z',
      hasExpandedCard: true,
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(oldVersionState));

    const { result } = renderHook(() => useOnboarding());

    // Should initialize as first visit since version is incompatible
    expect(result.current.isFirstVisit).toBe(true);
    expect(result.current.hasExpandedCard).toBe(false);
  });

  test('updates lastVisit timestamp on subsequent renders', () => {
    const firstVisitTime = '2024-01-01T00:00:00.000Z';
    const previousState = {
      version: '1.0',
      firstVisit: firstVisitTime,
      lastVisit: firstVisitTime,
      hasExpandedCard: false,
      hasClickedAfterGame: false,
      hasOpenedHelp: false,
      dismissedHints: [],
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(previousState));

    renderHook(() => useOnboarding());

    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY));
    expect(stored.firstVisit).toBe(firstVisitTime);
    expect(stored.lastVisit).not.toBe(firstVisitTime); // Should be updated
  });
});
