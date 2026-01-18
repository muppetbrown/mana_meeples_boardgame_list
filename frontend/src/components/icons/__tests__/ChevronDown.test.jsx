/**
 * ChevronDown icon tests
 */
import { describe, test, expect } from 'vitest';
import { render } from '@testing-library/react';
import { ChevronDown } from '../ChevronDown';

describe('ChevronDown', () => {
  test('renders SVG element', () => {
    const { container } = render(<ChevronDown />);
    const svg = container.querySelector('svg');

    expect(svg).toBeInTheDocument();
  });

  test('applies className prop', () => {
    const { container } = render(<ChevronDown className="test-class" />);
    const svg = container.querySelector('svg');

    expect(svg).toHaveClass('test-class');
  });

  test('has correct SVG attributes', () => {
    const { container } = render(<ChevronDown />);
    const svg = container.querySelector('svg');

    expect(svg).toHaveAttribute('width', '24');
    expect(svg).toHaveAttribute('height', '24');
    expect(svg).toHaveAttribute('viewBox', '0 0 24 24');
  });

  test('passes through additional props', () => {
    const { container } = render(<ChevronDown data-testid="chevron" aria-label="Expand" />);
    const svg = container.querySelector('svg');

    expect(svg).toHaveAttribute('data-testid', 'chevron');
    expect(svg).toHaveAttribute('aria-label', 'Expand');
  });

  test('renders polyline path', () => {
    const { container } = render(<ChevronDown />);
    const polyline = container.querySelector('polyline');

    expect(polyline).toBeInTheDocument();
    expect(polyline).toHaveAttribute('points', '6 9 12 15 18 9');
  });
});
