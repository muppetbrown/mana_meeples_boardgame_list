import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import LiveRegion from '../LiveRegion';

describe('LiveRegion', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('rendering', () => {
    it('renders with message', () => {
      render(<LiveRegion message="Test message" />);
      expect(screen.getByText('Test message')).toBeInTheDocument();
    });

    it('renders empty when no message', () => {
      const { container } = render(<LiveRegion message="" />);
      const liveRegion = container.querySelector('[role="status"]');
      expect(liveRegion).toBeInTheDocument();
      expect(liveRegion.textContent).toBe('');
    });

    it('updates when message changes', () => {
      const { rerender } = render(<LiveRegion message="First message" />);
      expect(screen.getByText('First message')).toBeInTheDocument();

      rerender(<LiveRegion message="Second message" />);
      expect(screen.getByText('Second message')).toBeInTheDocument();
    });
  });

  describe('accessibility attributes', () => {
    it('has status role by default', () => {
      render(<LiveRegion message="Test" />);
      expect(screen.getByRole('status')).toBeInTheDocument();
    });

    it('has polite aria-live by default', () => {
      const { container } = render(<LiveRegion message="Test" />);
      const liveRegion = container.querySelector('[role="status"]');
      expect(liveRegion).toHaveAttribute('aria-live', 'polite');
    });

    it('accepts assertive politeness level', () => {
      const { container } = render(<LiveRegion message="Test" politeness="assertive" />);
      const liveRegion = container.querySelector('[role="status"]');
      expect(liveRegion).toHaveAttribute('aria-live', 'assertive');
    });

    it('has atomic attribute true by default', () => {
      const { container } = render(<LiveRegion message="Test" />);
      const liveRegion = container.querySelector('[role="status"]');
      expect(liveRegion).toHaveAttribute('aria-atomic', 'true');
    });

    it('accepts atomic false', () => {
      const { container } = render(<LiveRegion message="Test" atomic={false} />);
      const liveRegion = container.querySelector('[role="status"]');
      expect(liveRegion).toHaveAttribute('aria-atomic', 'false');
    });
  });

  describe('screen reader only styling', () => {
    it('has sr-only class', () => {
      const { container } = render(<LiveRegion message="Test" />);
      const liveRegion = container.querySelector('[role="status"]');
      expect(liveRegion).toHaveClass('sr-only');
    });

    it('has visually hidden inline styles', () => {
      const { container } = render(<LiveRegion message="Test" />);
      const liveRegion = container.querySelector('[role="status"]');

      expect(liveRegion).toHaveStyle({
        position: 'absolute',
        width: '1px',
        height: '1px',
        padding: '0',
        margin: '-1px',
        overflow: 'hidden',
      });
    });

    it('has clip path for full visual hiding', () => {
      const { container } = render(<LiveRegion message="Test" />);
      const liveRegion = container.querySelector('[role="status"]');
      expect(liveRegion).toHaveStyle({ clip: 'rect(0, 0, 0, 0)' });
    });

    it('has whiteSpace nowrap', () => {
      const { container } = render(<LiveRegion message="Test" />);
      const liveRegion = container.querySelector('[role="status"]');
      expect(liveRegion).toHaveStyle({ whiteSpace: 'nowrap' });
    });

    it('has borderWidth 0', () => {
      const { container } = render(<LiveRegion message="Test" />);
      const liveRegion = container.querySelector('[role="status"]');
      expect(liveRegion).toHaveStyle({ borderWidth: '0' });
    });
  });

  describe('auto-clear functionality', () => {
    it('clears message after default timeout (5000ms)', () => {
      const { container } = render(<LiveRegion message="Test message" />);
      const liveRegion = container.querySelector('[role="status"]');

      expect(liveRegion.textContent).toBe('Test message');

      // Fast-forward time by 5000ms
      vi.advanceTimersByTime(5000);

      expect(liveRegion.textContent).toBe('');
    });

    it('clears message after custom timeout', () => {
      const { container } = render(<LiveRegion message="Test message" clearAfter={2000} />);
      const liveRegion = container.querySelector('[role="status"]');

      expect(liveRegion.textContent).toBe('Test message');

      // Fast-forward time by 2000ms
      vi.advanceTimersByTime(2000);

      expect(liveRegion.textContent).toBe('');
    });

    it('does not clear when clearAfter is 0', () => {
      const { container } = render(<LiveRegion message="Test message" clearAfter={0} />);
      const liveRegion = container.querySelector('[role="status"]');

      expect(liveRegion.textContent).toBe('Test message');

      vi.advanceTimersByTime(10000);

      expect(liveRegion.textContent).toBe('Test message');
    });

    it('does not clear when clearAfter is false', () => {
      const { container } = render(<LiveRegion message="Test message" clearAfter={false} />);
      const liveRegion = container.querySelector('[role="status"]');

      expect(liveRegion.textContent).toBe('Test message');

      vi.advanceTimersByTime(10000);

      expect(liveRegion.textContent).toBe('Test message');
    });

    it('does not clear when message is empty', () => {
      const { container } = render(<LiveRegion message="" />);
      const liveRegion = container.querySelector('[role="status"]');

      expect(liveRegion.textContent).toBe('');

      vi.advanceTimersByTime(5000);

      expect(liveRegion.textContent).toBe('');
    });

    it('resets timer when message changes', () => {
      const { container, rerender } = render(<LiveRegion message="First" clearAfter={2000} />);
      const liveRegion = container.querySelector('[role="status"]');

      // Advance time partway
      vi.advanceTimersByTime(1000);

      // Change message
      rerender(<LiveRegion message="Second" clearAfter={2000} />);

      // Advance time by another 1500ms (total 2500ms from first message)
      vi.advanceTimersByTime(1500);

      // Should still show second message (only 1500ms since it appeared)
      expect(liveRegion.textContent).toBe('Second');

      // Advance another 500ms to complete the 2000ms for second message
      vi.advanceTimersByTime(500);

      expect(liveRegion.textContent).toBe('');
    });
  });

  describe('cleanup', () => {
    it('cleans up timer on unmount', () => {
      const { unmount } = render(<LiveRegion message="Test" />);
      const clearTimeoutSpy = vi.spyOn(global, 'clearTimeout');

      unmount();

      expect(clearTimeoutSpy).toHaveBeenCalled();
    });

    it('cleans up timer when message changes', () => {
      const { rerender } = render(<LiveRegion message="First" />);
      const clearTimeoutSpy = vi.spyOn(global, 'clearTimeout');

      rerender(<LiveRegion message="Second" />);

      expect(clearTimeoutSpy).toHaveBeenCalled();
    });
  });

  describe('edge cases', () => {
    it('handles very long messages', () => {
      const longMessage = 'A'.repeat(1000);
      render(<LiveRegion message={longMessage} />);
      expect(screen.getByText(longMessage)).toBeInTheDocument();
    });

    it('handles special characters', () => {
      const specialMessage = '<>&"\'';
      render(<LiveRegion message={specialMessage} />);
      expect(screen.getByText(specialMessage)).toBeInTheDocument();
    });

    it('handles unicode and emojis', () => {
      const unicodeMessage = '🎮 Game loaded! 日本語';
      render(<LiveRegion message={unicodeMessage} />);
      expect(screen.getByText(unicodeMessage)).toBeInTheDocument();
    });

    it('handles null message gracefully', () => {
      const { container } = render(<LiveRegion message={null} />);
      const liveRegion = container.querySelector('[role="status"]');
      expect(liveRegion.textContent).toBe('');
    });

    it('handles undefined message gracefully', () => {
      const { container } = render(<LiveRegion message={undefined} />);
      const liveRegion = container.querySelector('[role="status"]');
      expect(liveRegion.textContent).toBe('');
    });
  });

  describe('WCAG compliance', () => {
    it('follows WCAG 2.1 Level A - Status Messages (4.1.3)', () => {
      const { container } = render(<LiveRegion message="Status update" />);
      const liveRegion = container.querySelector('[role="status"]');

      // Should have proper role
      expect(liveRegion).toHaveAttribute('role', 'status');

      // Should have aria-live
      expect(liveRegion).toHaveAttribute('aria-live');

      // Should be in the DOM but visually hidden
      expect(liveRegion).toBeInTheDocument();
      expect(liveRegion).toHaveClass('sr-only');
    });
  });
});
