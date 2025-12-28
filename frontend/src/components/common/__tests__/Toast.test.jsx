import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Toast } from '../Toast';

describe('Toast', () => {
  describe('rendering', () => {
    it('renders with message', () => {
      render(<Toast message="Test message" />);
      expect(screen.getByText('Test message')).toBeInTheDocument();
    });

    it('returns null when message is empty', () => {
      const { container } = render(<Toast message="" />);
      expect(container.firstChild).toBeNull();
    });

    it('returns null when message is undefined', () => {
      const { container } = render(<Toast message={undefined} />);
      expect(container.firstChild).toBeNull();
    });

    it('returns null when message is null', () => {
      const { container } = render(<Toast message={null} />);
      expect(container.firstChild).toBeNull();
    });
  });

  describe('type variants', () => {
    it('renders with info type by default', () => {
      const { container } = render(<Toast message="Info message" />);
      const toast = container.firstChild;
      expect(toast).toHaveClass('bg-gray-800');
    });

    it('renders with success type', () => {
      const { container } = render(<Toast message="Success message" type="success" />);
      const toast = container.firstChild;
      expect(toast).toHaveClass('bg-green-600');
    });

    it('renders with warning type', () => {
      const { container } = render(<Toast message="Warning message" type="warning" />);
      const toast = container.firstChild;
      expect(toast).toHaveClass('bg-amber-600');
    });

    it('renders with error type', () => {
      const { container} = render(<Toast message="Error message" type="error" />);
      const toast = container.firstChild;
      expect(toast).toHaveClass('bg-red-600');
    });
  });

  describe('styling', () => {
    it('has fixed positioning', () => {
      const { container } = render(<Toast message="Test" />);
      const toast = container.firstChild;
      expect(toast).toHaveClass('fixed', 'bottom-4');
    });

    it('is centered horizontally', () => {
      const { container } = render(<Toast message="Test" />);
      const toast = container.firstChild;
      expect(toast).toHaveClass('left-1/2', '-translate-x-1/2');
    });

    it('has proper z-index for overlay', () => {
      const { container } = render(<Toast message="Test" />);
      const toast = container.firstChild;
      expect(toast).toHaveClass('z-50');
    });

    it('has rounded corners and shadow', () => {
      const { container } = render(<Toast message="Test" />);
      const toast = container.firstChild;
      expect(toast).toHaveClass('rounded-lg', 'shadow-lg');
    });

    it('has proper text styling', () => {
      const { container } = render(<Toast message="Test" />);
      const toast = container.firstChild;
      expect(toast).toHaveClass('text-white', 'font-medium');
    });

    it('has animation class', () => {
      const { container } = render(<Toast message="Test" />);
      const toast = container.firstChild;
      expect(toast).toHaveClass('animate-slide-up');
    });
  });

  describe('icons', () => {
    it('renders info icon for info type', () => {
      const { container } = render(<Toast message="Info" type="info" />);
      const icon = container.querySelector('svg');
      expect(icon).toBeInTheDocument();
      expect(icon).toHaveClass('w-5', 'h-5');
    });

    it('renders success icon for success type', () => {
      const { container } = render(<Toast message="Success" type="success" />);
      const icon = container.querySelector('svg');
      expect(icon).toBeInTheDocument();
    });

    it('renders warning icon for warning type', () => {
      const { container } = render(<Toast message="Warning" type="warning" />);
      const icon = container.querySelector('svg');
      expect(icon).toBeInTheDocument();
    });

    it('renders error icon for error type', () => {
      const { container } = render(<Toast message="Error" type="error" />);
      const icon = container.querySelector('svg');
      expect(icon).toBeInTheDocument();
    });

    it('icons have aria-hidden attribute', () => {
      const { container } = render(<Toast message="Test" />);
      const icon = container.querySelector('svg');
      expect(icon).toHaveAttribute('aria-hidden', 'true');
    });
  });

  describe('accessibility', () => {
    it('has status role for info type', () => {
      render(<Toast message="Info" type="info" />);
      expect(screen.getByRole('status')).toBeInTheDocument();
    });

    it('has status role for success type', () => {
      render(<Toast message="Success" type="success" />);
      expect(screen.getByRole('status')).toBeInTheDocument();
    });

    it('has alert role for warning type', () => {
      render(<Toast message="Warning" type="warning" />);
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });

    it('has alert role for error type', () => {
      render(<Toast message="Error" type="error" />);
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });

    it('has polite aria-live for info type', () => {
      const { container } = render(<Toast message="Info" type="info" />);
      const toast = container.firstChild;
      expect(toast).toHaveAttribute('aria-live', 'polite');
    });

    it('has polite aria-live for success type', () => {
      const { container } = render(<Toast message="Success" type="success" />);
      const toast = container.firstChild;
      expect(toast).toHaveAttribute('aria-live', 'polite');
    });

    it('has assertive aria-live for warning type', () => {
      const { container } = render(<Toast message="Warning" type="warning" />);
      const toast = container.firstChild;
      expect(toast).toHaveAttribute('aria-live', 'assertive');
    });

    it('has assertive aria-live for error type', () => {
      const { container } = render(<Toast message="Error" type="error" />);
      const toast = container.firstChild;
      expect(toast).toHaveAttribute('aria-live', 'assertive');
    });
  });

  describe('layout', () => {
    it('uses flexbox layout', () => {
      const { container } = render(<Toast message="Test" />);
      const toast = container.firstChild;
      expect(toast).toHaveClass('flex', 'items-center', 'gap-2');
    });

    it('renders icon and message in correct order', () => {
      const { container } = render(<Toast message="Test message" />);
      const toast = container.firstChild;
      const svg = toast.querySelector('svg');
      const span = toast.querySelector('span');

      expect(svg).toBeTruthy();
      expect(span).toBeTruthy();
      expect(span.textContent).toBe('Test message');
    });
  });

  describe('edge cases', () => {
    it('handles long messages', () => {
      const longMessage = 'A'.repeat(200);
      render(<Toast message={longMessage} />);
      expect(screen.getByText(longMessage)).toBeInTheDocument();
    });

    it('handles special characters in message', () => {
      const specialMessage = '<script>alert("xss")</script>';
      render(<Toast message={specialMessage} />);
      expect(screen.getByText(specialMessage)).toBeInTheDocument();
    });

    it('handles unicode characters', () => {
      const unicodeMessage = '🎮 Game saved successfully! 🎉';
      render(<Toast message={unicodeMessage} />);
      expect(screen.getByText(unicodeMessage)).toBeInTheDocument();
    });
  });
});
