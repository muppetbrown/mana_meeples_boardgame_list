// frontend/src/hooks/__tests__/useToast.test.js
import { renderHook, act } from '@testing-library/react';
import { useToast } from '../useToast';

describe('useToast Hook', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  test('initializes with empty toast', () => {
    const { result } = renderHook(() => useToast());

    expect(result.current.toast).toEqual({
      message: '',
      type: 'info',
      duration: 3000,
    });
  });

  test('initializes with custom default duration', () => {
    const { result } = renderHook(() => useToast(5000));

    expect(result.current.toast.duration).toBe(5000);
  });

  test('shows toast message', () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.showToast('Test message', 'info', 3000);
    });

    expect(result.current.toast).toEqual({
      message: 'Test message',
      type: 'info',
      duration: 3000,
    });
  });

  test('shows success toast', () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.success('Success message');
    });

    expect(result.current.toast.message).toBe('Success message');
    expect(result.current.toast.type).toBe('success');
  });

  test('shows error toast', () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.error('Error message');
    });

    expect(result.current.toast.message).toBe('Error message');
    expect(result.current.toast.type).toBe('error');
    expect(result.current.toast.duration).toBe(5000); // Errors have longer default duration
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

  test('auto-hides toast after duration', () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.showToast('Test message', 'info', 3000);
    });

    expect(result.current.toast.message).toBe('Test message');

    // Fast-forward time
    act(() => {
      jest.advanceTimersByTime(3000);
    });

    expect(result.current.toast.message).toBe('');
  });

  test('does not auto-hide when duration is 0', () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.showToast('Persistent message', 'info', 0);
    });

    expect(result.current.toast.message).toBe('Persistent message');

    // Fast-forward time
    act(() => {
      jest.advanceTimersByTime(10000);
    });

    // Message should still be there
    expect(result.current.toast.message).toBe('Persistent message');
  });

  test('clears previous timeout when showing new toast', () => {
    const { result } = renderHook(() => useToast());

    // Show first toast
    act(() => {
      result.current.showToast('First message', 'info', 3000);
    });

    expect(result.current.toast.message).toBe('First message');

    // Advance time partway
    act(() => {
      jest.advanceTimersByTime(1500);
    });

    // Show second toast before first timeout completes
    act(() => {
      result.current.showToast('Second message', 'info', 3000);
    });

    expect(result.current.toast.message).toBe('Second message');

    // Advance time by the remaining time from first timeout
    act(() => {
      jest.advanceTimersByTime(1500);
    });

    // First timeout should have been cleared, so message should still be visible
    expect(result.current.toast.message).toBe('Second message');

    // Advance by second timeout duration
    act(() => {
      jest.advanceTimersByTime(3000);
    });

    // Now it should be hidden
    expect(result.current.toast.message).toBe('');
  });

  test('uses custom duration for success toast', () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.success('Success message', 2000);
    });

    expect(result.current.toast.duration).toBe(2000);

    act(() => {
      jest.advanceTimersByTime(2000);
    });

    expect(result.current.toast.message).toBe('');
  });

  test('clears timeout on unmount', () => {
    const { result, unmount } = renderHook(() => useToast());

    act(() => {
      result.current.showToast('Test message', 'info', 3000);
    });

    const clearTimeoutSpy = jest.spyOn(global, 'clearTimeout');

    unmount();

    expect(clearTimeoutSpy).toHaveBeenCalled();

    clearTimeoutSpy.mockRestore();
  });

  test('multiple toast types work correctly', () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.info('Info');
    });
    expect(result.current.toast.type).toBe('info');

    act(() => {
      result.current.success('Success');
    });
    expect(result.current.toast.type).toBe('success');

    act(() => {
      result.current.warning('Warning');
    });
    expect(result.current.toast.type).toBe('warning');

    act(() => {
      result.current.error('Error');
    });
    expect(result.current.toast.type).toBe('error');
  });
});
