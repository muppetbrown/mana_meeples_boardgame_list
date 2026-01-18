/**
 * UpdateNotification tests - Version update notification banner
 */
import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import UpdateNotification from '../UpdateNotification';
import * as versionCheck from '../../utils/versionCheck';

// Mock version check utilities
vi.mock('../../utils/versionCheck', () => ({
  startVersionCheck: vi.fn(),
  reloadApp: vi.fn(),
}));

describe('UpdateNotification', () => {
  let mockUnsubscribe;
  let updateCallback;
  const originalUserAgent = navigator.userAgent;
  const originalInnerWidth = window.innerWidth;

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();

    mockUnsubscribe = vi.fn();

    // Capture the callback passed to startVersionCheck
    versionCheck.startVersionCheck.mockImplementation((callback) => {
      updateCallback = callback;
      return mockUnsubscribe;
    });

    // Reset window size to desktop by default
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1024,
    });
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();

    // Restore original values
    Object.defineProperty(navigator, 'userAgent', {
      writable: true,
      configurable: true,
      value: originalUserAgent,
    });
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: originalInnerWidth,
    });
  });

  describe('Initial State', () => {
    test('renders nothing when no update detected', () => {
      const { container } = render(<UpdateNotification />);

      expect(container.firstChild).toBeNull();
    });

    test('starts version checking on mount', () => {
      render(<UpdateNotification />);

      expect(versionCheck.startVersionCheck).toHaveBeenCalledTimes(1);
      expect(versionCheck.startVersionCheck).toHaveBeenCalledWith(expect.any(Function));
    });

    test('provides unsubscribe function', () => {
      render(<UpdateNotification />);

      expect(versionCheck.startVersionCheck).toHaveReturnedWith(mockUnsubscribe);
    });
  });

  describe('Update Detection', () => {
    test('shows notification when update detected', () => {
      render(<UpdateNotification />);

      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText(/new version/i)).toBeInTheDocument();
    });

    test('logs update detection', () => {
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});

      render(<UpdateNotification />);
      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      expect(consoleSpy).toHaveBeenCalledWith('Update detected:', {
        newVersion: '2.0.0',
        currentVersion: '1.0.0',
      });

      consoleSpy.mockRestore();
    });

    test('notification has proper ARIA attributes', () => {
      render(<UpdateNotification />);
      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      const alert = screen.getByRole('alert');
      expect(alert).toHaveAttribute('aria-live', 'assertive');
      expect(alert).toHaveAttribute('aria-atomic', 'true');
    });
  });

  describe('Desktop Behavior', () => {
    beforeEach(() => {
      Object.defineProperty(navigator, 'userAgent', {
        writable: true,
        configurable: true,
        value: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
      });
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 1024,
      });
    });

    test('shows desktop message', () => {
      render(<UpdateNotification />);
      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      expect(screen.getByText('A new version is available')).toBeInTheDocument();
      expect(screen.getByText(/Refresh to get the latest features/)).toBeInTheDocument();
    });

    test('does not start auto-refresh countdown on desktop', () => {
      render(<UpdateNotification />);
      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      expect(screen.queryByText(/Auto-refreshing in/)).not.toBeInTheDocument();
    });

    test('shows refresh button', () => {
      render(<UpdateNotification />);
      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      expect(screen.getByRole('button', { name: 'Refresh' })).toBeInTheDocument();
    });

    test('shows dismiss button with X icon', () => {
      render(<UpdateNotification />);
      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      const dismissButton = screen.getByRole('button', { name: 'Dismiss notification' });
      expect(dismissButton).toBeInTheDocument();
    });

    test('refresh button calls reloadApp', async () => {
      render(<UpdateNotification />);
      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      const refreshButton = screen.getByRole('button', { name: 'Refresh' });
      act(() => {
        refreshButton.click();
      });

      expect(versionCheck.reloadApp).toHaveBeenCalledTimes(1);
    });

    test('dismiss button hides notification', async () => {
      render(<UpdateNotification />);
      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      const dismissButton = screen.getByRole('button', { name: 'Dismiss notification' });
      act(() => {
        dismissButton.click();
      });

      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });
  });

  describe('Mobile Behavior', () => {
    beforeEach(() => {
      Object.defineProperty(navigator, 'userAgent', {
        writable: true,
        configurable: true,
        value: 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
      });
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 375,
      });
    });

    test('shows mobile message', () => {
      render(<UpdateNotification />);
      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      expect(screen.getByText('New version available!')).toBeInTheDocument();
    });

    test('starts auto-refresh countdown', () => {
      render(<UpdateNotification />);
      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      expect(screen.getByText(/Auto-refreshing in 10 seconds/)).toBeInTheDocument();
    });

    test('countdown decrements every second', () => {
      render(<UpdateNotification />);
      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      expect(screen.getByText(/Auto-refreshing in 10 seconds/)).toBeInTheDocument();

      act(() => {
        vi.advanceTimersByTime(1000);
      });
      expect(screen.getByText(/Auto-refreshing in 9 seconds/)).toBeInTheDocument();

      act(() => {
        vi.advanceTimersByTime(1000);
      });
      expect(screen.getByText(/Auto-refreshing in 8 seconds/)).toBeInTheDocument();
    });

    test('uses singular form for 1 second', () => {
      render(<UpdateNotification />);
      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      act(() => {
        vi.advanceTimersByTime(9000);
      });
      // Check for singular "second" (not "seconds")
      expect(screen.getByText('Auto-refreshing in 1 second...')).toBeInTheDocument();
    });

    test('auto-refreshes after countdown completes', () => {
      render(<UpdateNotification />);
      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      vi.advanceTimersByTime(10000);

      expect(versionCheck.reloadApp).toHaveBeenCalledTimes(1);
    });

    test('shows "Refresh Now" button during countdown', () => {
      render(<UpdateNotification />);
      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      expect(screen.getByRole('button', { name: 'Refresh Now' })).toBeInTheDocument();
    });

    test('shows "Cancel" button during countdown', () => {
      render(<UpdateNotification />);
      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      // Cancel button has text content "Cancel" but aria-label is "Dismiss notification"
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });

    test('manual refresh stops countdown and reloads', async () => {
      render(<UpdateNotification />);
      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      const refreshButton = screen.getByRole('button', { name: 'Refresh Now' });
      act(() => {
        refreshButton.click();
      });

      expect(versionCheck.reloadApp).toHaveBeenCalledTimes(1);

      // Advance timers to verify countdown was stopped
      act(() => {
        vi.advanceTimersByTime(10000);
      });
      expect(versionCheck.reloadApp).toHaveBeenCalledTimes(1); // Still just once
    });

    test('cancel button stops countdown and hides notification', async () => {
      render(<UpdateNotification />);
      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      const cancelButton = screen.getByText('Cancel');
      act(() => {
        cancelButton.click();
      });

      expect(screen.queryByRole('alert')).not.toBeInTheDocument();

      // Verify countdown was stopped
      act(() => {
        vi.advanceTimersByTime(10000);
      });
      expect(versionCheck.reloadApp).not.toHaveBeenCalled();
    });
  });

  describe('Mobile Device Detection', () => {
    test('detects iPhone', () => {
      Object.defineProperty(navigator, 'userAgent', {
        writable: true,
        configurable: true,
        value: 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
      });

      render(<UpdateNotification />);
      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      expect(screen.getByText('New version available!')).toBeInTheDocument();
    });

    test('detects Android', () => {
      Object.defineProperty(navigator, 'userAgent', {
        writable: true,
        configurable: true,
        value: 'Mozilla/5.0 (Linux; Android 11)',
      });

      render(<UpdateNotification />);
      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      expect(screen.getByText('New version available!')).toBeInTheDocument();
    });

    test('detects iPad', () => {
      Object.defineProperty(navigator, 'userAgent', {
        writable: true,
        configurable: true,
        value: 'Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X)',
      });

      render(<UpdateNotification />);
      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      expect(screen.getByText('New version available!')).toBeInTheDocument();
    });

    test('detects narrow viewport as mobile', () => {
      Object.defineProperty(navigator, 'userAgent', {
        writable: true,
        configurable: true,
        value: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
      });
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 500,
      });

      render(<UpdateNotification />);
      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      expect(screen.getByText('New version available!')).toBeInTheDocument();
    });

    test('treats 768px as mobile boundary', () => {
      Object.defineProperty(navigator, 'userAgent', {
        writable: true,
        configurable: true,
        value: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
      });
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 767,
      });

      render(<UpdateNotification />);
      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      expect(screen.getByText('New version available!')).toBeInTheDocument();
    });
  });

  describe('Cleanup', () => {
    test('unsubscribes from version check on unmount', () => {
      const { unmount } = render(<UpdateNotification />);

      unmount();

      expect(mockUnsubscribe).toHaveBeenCalledTimes(1);
    });

    test('clears countdown timer on unmount', () => {
      Object.defineProperty(navigator, 'userAgent', {
        writable: true,
        configurable: true,
        value: 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
      });

      const { unmount } = render(<UpdateNotification />);
      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      // Verify countdown started
      expect(screen.getByText(/Auto-refreshing in/)).toBeInTheDocument();

      // Unmounting should clean up the timer (test passes if no errors/warnings)
      expect(() => unmount()).not.toThrow();
    });

    test('does not crash if unsubscribe is null', () => {
      versionCheck.startVersionCheck.mockReturnValue(null);

      const { unmount } = render(<UpdateNotification />);

      expect(() => unmount()).not.toThrow();
    });
  });

  describe('Timer Management', () => {
    test('clears timer when manually refreshing', async () => {
      const clearIntervalSpy = vi.spyOn(global, 'clearInterval');

      Object.defineProperty(navigator, 'userAgent', {
        writable: true,
        configurable: true,
        value: 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
      });

      render(<UpdateNotification />);
      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      const refreshButton = screen.getByRole('button', { name: 'Refresh Now' });
      act(() => {
        refreshButton.click();
      });

      expect(clearIntervalSpy).toHaveBeenCalled();

      clearIntervalSpy.mockRestore();
    });

    test('clears timer when dismissing notification', async () => {
      const clearIntervalSpy = vi.spyOn(global, 'clearInterval');

      Object.defineProperty(navigator, 'userAgent', {
        writable: true,
        configurable: true,
        value: 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
      });

      render(<UpdateNotification />);
      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      const cancelButton = screen.getByText('Cancel');
      act(() => {
        cancelButton.click();
      });

      expect(clearIntervalSpy).toHaveBeenCalled();

      clearIntervalSpy.mockRestore();
    });
  });

  describe('Accessibility', () => {
    test('refresh button is keyboard accessible', async () => {
      render(<UpdateNotification />);
      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      const refreshButton = screen.getByRole('button', { name: 'Refresh' });
      refreshButton.focus();
      expect(refreshButton).toHaveFocus();

      // Click simulates keyboard activation
      act(() => {
        refreshButton.click();
      });
      expect(versionCheck.reloadApp).toHaveBeenCalled();
    });

    test('dismiss button has aria-label', () => {
      render(<UpdateNotification />);
      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      const dismissButton = screen.getByRole('button', { name: 'Dismiss notification' });
      expect(dismissButton).toHaveAttribute('aria-label', 'Dismiss notification');
    });

    test('icons have aria-hidden', () => {
      const { container } = render(<UpdateNotification />);
      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      const icons = container.querySelectorAll('svg[aria-hidden="true"]');
      expect(icons.length).toBeGreaterThan(0);
    });
  });

  describe('Visual Elements', () => {
    test('displays animated refresh icon', () => {
      const { container } = render(<UpdateNotification />);
      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      const animatedIcon = container.querySelector('.animate-pulse');
      expect(animatedIcon).toBeInTheDocument();
    });

    test('uses proper color scheme', () => {
      const { container } = render(<UpdateNotification />);
      act(() => {
        updateCallback('2.0.0', '1.0.0');
      });

      const banner = container.querySelector('.bg-linear-to-r');
      expect(banner).toBeInTheDocument();
    });
  });
});
