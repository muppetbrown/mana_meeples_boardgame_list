// frontend/src/hooks/__tests__/useToast.test.js
import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useToast } from '../useToast.jsx';

describe('useToast Hook', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  test('initializes with empty toast', () => {
    const { result } = renderHook(() => useToast());

    expect(result.current.toast.message).toBe('');
  });

  test('shows toast message', () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.showToast('Test message', 'info', 3000);
    });

    expect(result.current.toast.message).toBe('Test message');
    expect(result.current.toast.type).toBe('info');
  });

  test('shows success toast', () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.success('Success message');
    });

    expect(result.current.toast.message).toBe('Success message');
    expect(result.current.toast.type).toBe('success');
  });

  test('auto-hides toast after duration', () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.showToast('Test message', 'info', 3000);
    });

    expect(result.current.toast.message).toBe('Test message');

    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(result.current.toast.message).toBe('');
  });

  test('hides toast manually', () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.showToast('Test message', 'info', 3000);
    });

    expect(result.current.toast.message).toBe('Test message');

    act(() => {
      result.current.hideToast();
    });

    expect(result.current.toast.message).toBe('');
  });
});
