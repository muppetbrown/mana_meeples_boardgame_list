/**
 * StatBadge tests - Reusable stat badge component
 */
import { describe, test, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatBadge } from '../StatBadge';

// Mock icon component
const MockIcon = ({ className, ...props }) => (
  <svg className={className} data-testid="mock-icon" {...props}>
    <circle cx="12" cy="12" r="10" />
  </svg>
);

describe('StatBadge', () => {
  describe('Rendering', () => {
    test('renders label', () => {
      render(<StatBadge label="2-4" />);

      expect(screen.getByText('2-4')).toBeInTheDocument();
    });

    test('renders icon when provided', () => {
      render(<StatBadge icon={MockIcon} label="Test" />);

      expect(screen.getByTestId('mock-icon')).toBeInTheDocument();
    });

    test('renders without icon', () => {
      render(<StatBadge label="Test" />);

      expect(screen.queryByTestId('mock-icon')).not.toBeInTheDocument();
      expect(screen.getByText('Test')).toBeInTheDocument();
    });

    test('shows dash when label is missing', () => {
      render(<StatBadge />);

      expect(screen.getByText('—')).toBeInTheDocument();
    });

    test('shows dash when label is empty string', () => {
      render(<StatBadge label="" />);

      expect(screen.getByText('—')).toBeInTheDocument();
    });
  });

  describe('ARIA Attributes', () => {
    test('uses label as aria-label by default', () => {
      const { container } = render(<StatBadge label="2-4 players" />);
      const badge = container.querySelector('[aria-label]');

      expect(badge).toHaveAttribute('aria-label', '2-4 players');
    });

    test('uses custom ariaLabel when provided', () => {
      const { container } = render(
        <StatBadge label="2-4" ariaLabel="Two to four players" />
      );
      const badge = container.querySelector('[aria-label]');

      expect(badge).toHaveAttribute('aria-label', 'Two to four players');
    });

    test('icon has aria-hidden', () => {
      render(<StatBadge icon={MockIcon} label="Test" />);

      const icon = screen.getByTestId('mock-icon');
      expect(icon).toHaveAttribute('aria-hidden', 'true');
    });
  });

  describe('Styling', () => {
    test('applies default classes', () => {
      const { container } = render(<StatBadge label="Test" />);
      const badge = container.firstChild;

      expect(badge).toHaveClass('flex');
      expect(badge).toHaveClass('flex-col');
      expect(badge).toHaveClass('bg-slate-50');
      expect(badge).toHaveClass('rounded-lg');
    });

    test('applies custom className', () => {
      const { container } = render(<StatBadge label="Test" className="custom-class" />);
      const badge = container.firstChild;

      expect(badge).toHaveClass('custom-class');
      expect(badge).toHaveClass('bg-slate-50'); // Still has default classes
    });

    test('icon has correct styling classes', () => {
      render(<StatBadge icon={MockIcon} label="Test" />);

      const icon = screen.getByTestId('mock-icon');
      expect(icon).toHaveClass('text-emerald-600');
      expect(icon).toHaveClass('w-3.5');
    });
  });

  describe('Layout', () => {
    test('renders in column layout', () => {
      const { container } = render(<StatBadge icon={MockIcon} label="Test" />);
      const badge = container.firstChild;

      expect(badge).toHaveClass('flex-col');
      expect(badge).toHaveClass('items-center');
      expect(badge).toHaveClass('justify-center');
    });

    test('has gap between icon and label', () => {
      const { container } = render(<StatBadge icon={MockIcon} label="Test" />);
      const badge = container.firstChild;

      expect(badge).toHaveClass('gap-0.5');
    });
  });

  describe('Edge Cases', () => {
    test('renders with null icon', () => {
      render(<StatBadge icon={null} label="Test" />);

      expect(screen.getByText('Test')).toBeInTheDocument();
      expect(screen.queryByTestId('mock-icon')).not.toBeInTheDocument();
    });

    test('renders with undefined icon', () => {
      render(<StatBadge icon={undefined} label="Test" />);

      expect(screen.getByText('Test')).toBeInTheDocument();
    });

    test('handles numeric label', () => {
      render(<StatBadge label="42" />);

      expect(screen.getByText('42')).toBeInTheDocument();
    });

    test('handles special characters in label', () => {
      render(<StatBadge label="2–4+" />);

      expect(screen.getByText('2–4+')).toBeInTheDocument();
    });
  });
});
