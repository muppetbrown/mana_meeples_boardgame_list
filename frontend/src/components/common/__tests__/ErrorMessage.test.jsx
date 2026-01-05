import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ErrorMessage, { InlineError, EmptyState } from '../ErrorMessage';

describe('ErrorMessage', () => {
  describe('Error message rendering', () => {
    it('renders default error message when no error provided', () => {
      render(<ErrorMessage />);
      expect(screen.getByText('An unexpected error occurred')).toBeInTheDocument();
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });

    it('renders string error message', () => {
      render(<ErrorMessage error="Custom error message" />);
      expect(screen.getByText('Custom error message')).toBeInTheDocument();
    });

    it('renders error with code mapping', () => {
      render(<ErrorMessage error={{ code: 'NETWORK_ERROR' }} />);
      expect(screen.getByText('Connection problem. Please check your internet and try again.')).toBeInTheDocument();
    });

    it('renders error with message property', () => {
      render(<ErrorMessage error={{ message: 'Error from API' }} />);
      expect(screen.getByText('Error from API')).toBeInTheDocument();
    });

    it('renders default fallback for unknown error', () => {
      render(<ErrorMessage error={{ unknown: 'data' }} />);
      expect(screen.getByText('Something went wrong. Please try again.')).toBeInTheDocument();
    });
  });

  describe('Error code mappings', () => {
    const errorCodes = [
      { code: 'NETWORK_ERROR', message: 'Connection problem. Please check your internet and try again.' },
      { code: 'BGG_FETCH_FAILED', message: "Couldn't load game from BoardGameGeek. Try again in a moment." },
      { code: 'GAME_NOT_FOUND', message: 'Game not found. It may have been removed.' },
      { code: 'UNAUTHORIZED', message: 'Admin access required. Please log in.' },
      { code: 'VALIDATION_ERROR', message: 'Please check your input and try again.' },
      { code: 'SERVER_ERROR', message: 'Server error. Please try again later.' },
    ];

    errorCodes.forEach(({ code, message }) => {
      it(`maps ${code} to correct message`, () => {
        render(<ErrorMessage error={{ code }} />);
        expect(screen.getByText(message)).toBeInTheDocument();
      });
    });
  });

  describe('Retry functionality', () => {
    it('does not show retry button when onRetry not provided', () => {
      render(<ErrorMessage error="Error" />);
      expect(screen.queryByText('Try again')).not.toBeInTheDocument();
    });

    it('shows retry button when onRetry is a function', () => {
      const onRetry = vi.fn();
      render(<ErrorMessage error="Error" onRetry={onRetry} />);
      expect(screen.getByText('Try again')).toBeInTheDocument();
    });

    it('calls onRetry when retry button clicked', async () => {
      const onRetry = vi.fn();
      render(<ErrorMessage error="Error" onRetry={onRetry} />);

      await userEvent.click(screen.getByText('Try again'));
      expect(onRetry).toHaveBeenCalledOnce();
    });

    it('does not show retry button for non-function onRetry', () => {
      render(<ErrorMessage error="Error" onRetry="not a function" />);
      expect(screen.queryByText('Try again')).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has role="alert"', () => {
      render(<ErrorMessage error="Error" />);
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });

    it('has aria-live="assertive"', () => {
      const { container } = render(<ErrorMessage error="Error" />);
      const alert = container.querySelector('[aria-live="assertive"]');
      expect(alert).toBeInTheDocument();
    });

    it('has aria-label on retry button', () => {
      const onRetry = vi.fn();
      render(<ErrorMessage error="Error" onRetry={onRetry} />);
      expect(screen.getByLabelText('Retry the failed operation')).toBeInTheDocument();
    });

    it('error icon has aria-hidden="true"', () => {
      const { container } = render(<ErrorMessage error="Error" />);
      const icon = container.querySelector('svg[aria-hidden="true"]');
      expect(icon).toBeInTheDocument();
    });
  });

  describe('Custom className', () => {
    it('applies custom className', () => {
      const { container } = render(<ErrorMessage error="Error" className="custom-class" />);
      const alert = container.querySelector('.custom-class');
      expect(alert).toBeInTheDocument();
    });

    it('applies default styles without className', () => {
      const { container } = render(<ErrorMessage error="Error" />);
      const alert = container.querySelector('[role="alert"]');
      expect(alert).toHaveClass('bg-red-50', 'border-l-4', 'border-red-500');
    });
  });
});

describe('InlineError', () => {
  it('renders error message', () => {
    render(<InlineError message="Field is required" />);
    expect(screen.getByText('Field is required')).toBeInTheDocument();
  });

  it('returns null when no message provided', () => {
    const { container } = render(<InlineError />);
    expect(container.firstChild).toBeNull();
  });

  it('returns null when message is empty string', () => {
    const { container } = render(<InlineError message="" />);
    expect(container.firstChild).toBeNull();
  });

  it('has role="alert"', () => {
    render(<InlineError message="Error" />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<InlineError message="Error" className="custom" />);
    expect(container.querySelector('.custom')).toBeInTheDocument();
  });

  it('contains error icon', () => {
    const { container } = render(<InlineError message="Error" />);
    const icon = container.querySelector('svg');
    expect(icon).toBeInTheDocument();
    expect(icon).toHaveAttribute('aria-hidden', 'true');
  });

  it('applies correct text color and size', () => {
    const { container } = render(<InlineError message="Error" />);
    const alert = screen.getByRole('alert');
    expect(alert).toHaveClass('text-red-600', 'text-sm');
  });
});

describe('EmptyState', () => {
  it('renders title', () => {
    render(<EmptyState title="No games found" />);
    expect(screen.getByText('No games found')).toBeInTheDocument();
  });

  it('renders title and message', () => {
    render(<EmptyState title="No results" message="Try different filters" />);
    expect(screen.getByText('No results')).toBeInTheDocument();
    expect(screen.getByText('Try different filters')).toBeInTheDocument();
  });

  it('does not render message when not provided', () => {
    const { container } = render(<EmptyState title="No results" />);
    const paragraphs = container.querySelectorAll('p');
    expect(paragraphs).toHaveLength(0);
  });

  it('renders action button when provided', () => {
    const action = <button>Clear filters</button>;
    render(<EmptyState title="No results" action={action} />);
    expect(screen.getByRole('button', { name: 'Clear filters' })).toBeInTheDocument();
  });

  it('does not render action div when action not provided', () => {
    const { container } = render(<EmptyState title="No results" />);
    // Should only have icon, h3, no action div
    const divs = container.querySelectorAll('div');
    const actionDiv = Array.from(divs).find(div => div.className.includes('mt-6'));
    expect(actionDiv).toBeUndefined();
  });

  it('contains decorative icon', () => {
    const { container } = render(<EmptyState title="Empty" />);
    const icon = container.querySelector('svg');
    expect(icon).toBeInTheDocument();
    expect(icon).toHaveAttribute('aria-hidden', 'true');
  });

  it('has centered layout', () => {
    const { container } = render(<EmptyState title="Empty" />);
    const wrapper = container.querySelector('.text-center');
    expect(wrapper).toBeInTheDocument();
  });

  it('applies correct heading styles', () => {
    render(<EmptyState title="No results" />);
    const heading = screen.getByText('No results');
    expect(heading).toHaveClass('text-lg', 'font-medium', 'text-slate-900');
  });
});
