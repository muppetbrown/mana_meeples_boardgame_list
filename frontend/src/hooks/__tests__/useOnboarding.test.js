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
});
