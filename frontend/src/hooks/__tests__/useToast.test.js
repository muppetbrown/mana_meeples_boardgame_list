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

  test('shows error toast with default 5000ms duration', () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.error('Error message');
    });

    expect(result.current.toast.message).toBe('Error message');
    expect(result.current.toast.type).toBe('error');
    expect(result.current.toast.duration).toBe(5000);
  });

  test('shows info toast', () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.info('Info message');
    });

    expect(result.current.toast.message).toBe('Info message');
    expect(result.current.toast.type).toBe('info');
  });

  test('shows warning toast', () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.warning('Warning message');
    });

    expect(result.current.toast.message).toBe('Warning message');
    expect(result.current.toast.type).toBe('warning');
  });

  test('does not auto-hide when duration is 0', () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.showToast('Persistent message', 'info', 0);
    });

    expect(result.current.toast.message).toBe('Persistent message');

    act(() => {
      vi.advanceTimersByTime(10000);
    });

    // Should still be visible
    expect(result.current.toast.message).toBe('Persistent message');
  });

  test('clears previous timeout when showing new toast', () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.showToast('First message', 'info', 1000);
    });

    expect(result.current.toast.message).toBe('First message');

    // Show another toast before first one expires
    act(() => {
      result.current.showToast('Second message', 'success', 2000);
    });

    expect(result.current.toast.message).toBe('Second message');
    expect(result.current.toast.type).toBe('success');

    // Advance by 1000ms (first toast duration)
    act(() => {
      vi.advanceTimersByTime(1000);
    });

    // Second toast should still be visible
    expect(result.current.toast.message).toBe('Second message');
  });

  test('uses custom default duration', () => {
    const { result } = renderHook(() => useToast(5000));

    act(() => {
      result.current.showToast('Test message');
    });

    expect(result.current.toast.duration).toBe(5000);

    // Should not hide after 3000ms
    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(result.current.toast.message).toBe('Test message');

    // Should hide after 5000ms
    act(() => {
      vi.advanceTimersByTime(2000);
    });

    expect(result.current.toast.message).toBe('');
  });

  test('cleans up timeout on unmount', () => {
    const { result, unmount } = renderHook(() => useToast());

    act(() => {
      result.current.showToast('Test message', 'info', 3000);
    });

    expect(result.current.toast.message).toBe('Test message');

    // Unmount before timeout expires
    unmount();

    // No errors should occur
    act(() => {
      vi.advanceTimersByTime(3000);
    });
  });

  test('allows custom duration for success', () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.success('Success message', 1000);
    });

    expect(result.current.toast.duration).toBe(1000);
  });

  test('allows custom duration for error', () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.error('Error message', 10000);
    });

    expect(result.current.toast.duration).toBe(10000);
  });
});
