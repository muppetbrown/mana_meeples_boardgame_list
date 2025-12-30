// frontend/src/hooks/__tests__/useOnboarding.test.js
import { describe, test, expect, beforeEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useOnboarding } from '../useOnboarding';

const STORAGE_KEY = 'mana_meeples_onboarding';

describe('useOnboarding Hook', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  test('initializes with default state on first visit', () => {
    const { result } = renderHook(() => useOnboarding());

    expect(result.current.isFirstVisit).toBe(true);
    expect(result.current.hasExpandedCard).toBe(false);
  });

  test('persists state to localStorage', () => {
    const { result } = renderHook(() => useOnboarding());

    act(() => {
      result.current.markCardExpanded();
    });

    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY));
    expect(stored.hasExpandedCard).toBe(true);
  });

  test('marks card as expanded', () => {
    const { result } = renderHook(() => useOnboarding());

    expect(result.current.hasExpandedCard).toBe(false);

    act(() => {
      result.current.markCardExpanded();
    });

    expect(result.current.hasExpandedCard).toBe(true);
  });

  test('dismisses specific hints', () => {
    const { result } = renderHook(() => useOnboarding());

    expect(result.current.isHintDismissed('card-expand')).toBe(false);

    act(() => {
      result.current.dismissHint('card-expand');
    });

    expect(result.current.isHintDismissed('card-expand')).toBe(true);
  });

  test('resets all onboarding state', () => {
    const { result } = renderHook(() => useOnboarding());

    act(() => {
      result.current.markCardExpanded();
      result.current.dismissHint('test-hint');
    });

    expect(result.current.hasExpandedCard).toBe(true);

    act(() => {
      result.current.reset();
    });

    expect(result.current.hasExpandedCard).toBe(false);
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

  test('loads existing state from localStorage', () => {
    // Pre-populate localStorage
    const existingState = {
      version: '1.0',
      firstVisit: '2024-01-01T00:00:00.000Z',
      lastVisit: '2024-01-01T00:00:00.000Z',
      hasExpandedCard: true,
      hasClickedAfterGame: true,
      hasOpenedHelp: true,
      dismissedHints: ['card-expand'],
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(existingState));

    const { result } = renderHook(() => useOnboarding());

    expect(result.current.hasExpandedCard).toBe(true);
    expect(result.current.hasClickedAfterGame).toBe(true);
    expect(result.current.hasOpenedHelp).toBe(true);
    expect(result.current.isHintDismissed('card-expand')).toBe(true);
  });

  test('handles corrupted localStorage data gracefully', () => {
    const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    // Put invalid JSON in localStorage
    localStorage.setItem(STORAGE_KEY, 'invalid json');

    const { result } = renderHook(() => useOnboarding());

    // Should initialize with default state
    expect(result.current.isFirstVisit).toBe(true);
    expect(result.current.hasExpandedCard).toBe(false);
    expect(consoleSpy).toHaveBeenCalledWith(
      'Failed to load onboarding state:',
      expect.any(Error)
    );

    consoleSpy.mockRestore();
  });

  test('handles localStorage save errors gracefully', () => {
    // Clear any existing data first
    localStorage.clear();

    const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const originalSetItem = localStorage.setItem;

    // Mock localStorage.setItem to always throw an error
    localStorage.setItem = vi.fn(() => {
      throw new Error('Storage full');
    });

    // Hook should still work even if saves fail
    const { result } = renderHook(() => useOnboarding());

    // State changes should still work even though saves fail
    act(() => {
      result.current.markCardExpanded();
    });

    // Hook should still function despite errors
    expect(result.current.hasExpandedCard).toBe(true);

    // Restore
    localStorage.setItem = originalSetItem;
    consoleSpy.mockRestore();
  });

  test('handles version mismatch by resetting state', () => {
    // Pre-populate localStorage with wrong version
    const oldState = {
      version: '0.5',
      firstVisit: '2024-01-01T00:00:00.000Z',
      lastVisit: '2024-01-01T00:00:00.000Z',
      hasExpandedCard: true,
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(oldState));

    const { result } = renderHook(() => useOnboarding());

    // Should reset to defaults despite old data
    expect(result.current.hasExpandedCard).toBe(false);
    expect(result.current.isFirstVisit).toBe(true);
  });

  test('shouldShowCardHint is false after card expanded', () => {
    const { result } = renderHook(() => useOnboarding());

    expect(result.current.shouldShowCardHint).toBe(true);

    act(() => {
      result.current.markCardExpanded();
    });

    expect(result.current.shouldShowCardHint).toBe(false);
  });

  test('shouldShowCardHint is false after hint dismissed', () => {
    const { result } = renderHook(() => useOnboarding());

    expect(result.current.shouldShowCardHint).toBe(true);

    act(() => {
      result.current.dismissHint('card-expand');
    });

    expect(result.current.shouldShowCardHint).toBe(false);
  });

  test('shouldShowAfterGameHint is false after hint dismissed', () => {
    const { result } = renderHook(() => useOnboarding());

    expect(result.current.shouldShowAfterGameHint).toBe(true);

    act(() => {
      result.current.dismissHint('aftergame');
    });

    expect(result.current.shouldShowAfterGameHint).toBe(false);
  });

  test('dismissHint prevents duplicates', () => {
    const { result } = renderHook(() => useOnboarding());

    act(() => {
      result.current.dismissHint('test');
      result.current.dismissHint('test');
      result.current.dismissHint('test');
    });

    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY));
    const testCount = stored.dismissedHints.filter(h => h === 'test').length;
    expect(testCount).toBe(1);
  });
});
