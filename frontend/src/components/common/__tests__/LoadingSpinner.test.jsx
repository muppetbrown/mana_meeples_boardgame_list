import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { LoadingSpinner, FullPageLoader, InlineLoader } from '../LoadingSpinner';

describe('LoadingSpinner', () => {
  describe('default behavior', () => {
    it('renders with default medium size', () => {
      render(<LoadingSpinner />);
      const spinner = screen.getByRole('status');
      expect(spinner).toBeInTheDocument();
      expect(spinner).toHaveClass('w-12', 'h-12');
    });

    it('has accessible aria-label', () => {
      render(<LoadingSpinner />);
      const spinner = screen.getByRole('status');
      expect(spinner).toHaveAttribute('aria-label', 'Loading');
    });

    it('includes sr-only text for screen readers', () => {
      render(<LoadingSpinner />);
      const srText = screen.getByText('Loading...', { selector: '.sr-only' });
      expect(srText).toBeInTheDocument();
    });
  });

  describe('size variants', () => {
    it('renders small size correctly', () => {
      render(<LoadingSpinner size="sm" />);
      const spinner = screen.getByRole('status');
      expect(spinner).toHaveClass('w-6', 'h-6');
    });

    it('renders medium size correctly', () => {
      render(<LoadingSpinner size="md" />);
      const spinner = screen.getByRole('status');
      expect(spinner).toHaveClass('w-12', 'h-12');
    });

    it('renders large size correctly', () => {
      render(<LoadingSpinner size="lg" />);
      const spinner = screen.getByRole('status');
      expect(spinner).toHaveClass('w-16', 'h-16');
    });
  });

  describe('with text prop', () => {
    it('displays custom text below spinner', () => {
      render(<LoadingSpinner text="Loading games..." />);
      const texts = screen.getAllByText('Loading games...');
      expect(texts.length).toBeGreaterThan(0);
    });

    it('uses custom text for aria-label', () => {
      render(<LoadingSpinner text="Fetching data" />);
      const spinner = screen.getByRole('status');
      expect(spinner).toHaveAttribute('aria-label', 'Fetching data');
    });

    it('updates sr-only text with custom text', () => {
      render(<LoadingSpinner text="Custom loading" />);
      const srText = screen.getByText('Custom loading', { selector: '.sr-only' });
      expect(srText).toBeInTheDocument();
    });
  });

  describe('custom className', () => {
    it('applies additional className to wrapper', () => {
      const { container } = render(<LoadingSpinner className="my-custom-class" />);
      const wrapper = container.firstChild;
      expect(wrapper).toHaveClass('my-custom-class');
    });

    it('maintains default classes with custom className', () => {
      const { container } = render(<LoadingSpinner className="extra-class" />);
      const wrapper = container.firstChild;
      expect(wrapper).toHaveClass('flex', 'flex-col', 'items-center', 'extra-class');
    });
  });

  describe('spinner animation', () => {
    it('has animate-spin class for rotation', () => {
      render(<LoadingSpinner />);
      const spinner = screen.getByRole('status');
      expect(spinner).toHaveClass('animate-spin');
    });

    it('has rounded-full class for circular shape', () => {
      render(<LoadingSpinner />);
      const spinner = screen.getByRole('status');
      expect(spinner).toHaveClass('rounded-full');
    });
  });
});

describe('FullPageLoader', () => {
  it('renders with default loading text', () => {
    render(<FullPageLoader />);
    const texts = screen.getAllByText('Loading...');
    expect(texts.length).toBeGreaterThan(0);
  });

  it('renders with custom text', () => {
    render(<FullPageLoader text="Please wait..." />);
    const texts = screen.getAllByText('Please wait...');
    expect(texts.length).toBeGreaterThan(0);
  });

  it('has full screen height', () => {
    const { container } = render(<FullPageLoader />);
    const wrapper = container.firstChild;
    expect(wrapper).toHaveClass('min-h-screen');
  });

  it('centers content vertically and horizontally', () => {
    const { container } = render(<FullPageLoader />);
    const wrapper = container.firstChild;
    expect(wrapper).toHaveClass('flex', 'items-center', 'justify-center');
  });

  it('uses large spinner size', () => {
    render(<FullPageLoader />);
    const spinner = screen.getByRole('status');
    expect(spinner).toHaveClass('w-16', 'h-16');
  });

  it('has accessible background color', () => {
    const { container } = render(<FullPageLoader />);
    const wrapper = container.firstChild;
    expect(wrapper).toHaveClass('bg-slate-50');
  });
});

describe('InlineLoader', () => {
  it('renders without text', () => {
    const { container } = render(<InlineLoader />);
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('renders with custom text', () => {
    render(<InlineLoader text="Processing..." />);
    expect(screen.getByText('Processing...')).toBeInTheDocument();
  });

  it('has inline flex layout', () => {
    const { container } = render(<InlineLoader />);
    const wrapper = container.firstChild;
    expect(wrapper).toHaveClass('flex', 'items-center');
  });

  it('uses small compact spinner size', () => {
    const { container } = render(<InlineLoader />);
    const spinner = container.querySelector('.animate-spin');
    expect(spinner).toHaveClass('w-4', 'h-4');
  });

  it('has appropriate gap between spinner and text', () => {
    const { container } = render(<InlineLoader text="Loading" />);
    const wrapper = container.firstChild;
    expect(wrapper).toHaveClass('gap-2');
  });

  it('text has correct styling when provided', () => {
    render(<InlineLoader text="Inline loading" />);
    const text = screen.getByText('Inline loading');
    expect(text).toHaveClass('text-sm', 'text-slate-600');
  });
});

describe('accessibility', () => {
  it('LoadingSpinner has proper ARIA role', () => {
    render(<LoadingSpinner />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('FullPageLoader has proper ARIA role', () => {
    render(<FullPageLoader />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('all variants include screen reader only text', () => {
    const { container: container1 } = render(<LoadingSpinner />);
    const { container: container2 } = render(<FullPageLoader />);

    expect(container1.querySelector('.sr-only')).toBeInTheDocument();
    expect(container2.querySelector('.sr-only')).toBeInTheDocument();
  });
});
