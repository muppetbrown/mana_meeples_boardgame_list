import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import VisuallyHidden from '../VisuallyHidden';

describe('VisuallyHidden', () => {
  describe('Content rendering', () => {
    it('renders children text', () => {
      render(<VisuallyHidden>Screen reader only text</VisuallyHidden>);
      expect(screen.getByText('Screen reader only text')).toBeInTheDocument();
    });

    it('renders complex children', () => {
      render(
        <VisuallyHidden>
          <span>Complex</span> content
        </VisuallyHidden>
      );
      expect(screen.getByText('Complex')).toBeInTheDocument();
      expect(screen.getByText(/Complex/)).toBeInTheDocument();
    });

    it('renders multiple children', () => {
      const { container } = render(
        <VisuallyHidden>
          First <strong>Second</strong> Third
        </VisuallyHidden>
      );
      // Check that the container has the content
      expect(container.textContent).toContain('First');
      expect(container.textContent).toContain('Second');
      expect(container.textContent).toContain('Third');
    });
  });

  describe('Element type', () => {
    it('renders as span by default', () => {
      const { container } = render(<VisuallyHidden>Text</VisuallyHidden>);
      const element = container.firstChild;
      expect(element.tagName).toBe('SPAN');
    });

    it('renders as custom element when "as" prop provided', () => {
      const { container } = render(<VisuallyHidden as="div">Text</VisuallyHidden>);
      const element = container.firstChild;
      expect(element.tagName).toBe('DIV');
    });

    it('renders as h1 when specified', () => {
      const { container } = render(<VisuallyHidden as="h1">Heading</VisuallyHidden>);
      const element = container.firstChild;
      expect(element.tagName).toBe('H1');
    });

    it('renders as p when specified', () => {
      const { container } = render(<VisuallyHidden as="p">Paragraph</VisuallyHidden>);
      const element = container.firstChild;
      expect(element.tagName).toBe('P');
    });
  });

  describe('CSS classes and styles', () => {
    it('has sr-only class', () => {
      const { container } = render(<VisuallyHidden>Text</VisuallyHidden>);
      const element = container.firstChild;
      expect(element).toHaveClass('sr-only');
    });

    it('has correct visually hidden styles', () => {
      const { container } = render(<VisuallyHidden>Text</VisuallyHidden>);
      const element = container.firstChild;
      const styles = window.getComputedStyle(element);

      // Check key visually hidden styles
      expect(element.style.position).toBe('absolute');
      expect(element.style.width).toBe('1px');
      expect(element.style.height).toBe('1px');
      expect(element.style.padding).toBe('0px');
      expect(element.style.margin).toBe('-1px');
      expect(element.style.overflow).toBe('hidden');
      expect(element.style.clip).toMatch(/rect\(0(px)?, 0(px)?, 0(px)?, 0(px)?\)/);
      expect(element.style.whiteSpace).toBe('nowrap');
      expect(element.style.borderWidth).toBe('0px');
    });

    it('element is visually hidden but accessible to screen readers', () => {
      const { container } = render(<VisuallyHidden>Accessible text</VisuallyHidden>);
      const element = container.firstChild;

      // Element exists in DOM (screen readers can access it)
      expect(element).toBeInTheDocument();

      // Element is visually hidden (1px size, absolute positioning)
      expect(element.style.width).toBe('1px');
      expect(element.style.height).toBe('1px');
      expect(element.style.position).toBe('absolute');
    });
  });

  describe('Accessibility', () => {
    it('content is still accessible via getByText', () => {
      render(<VisuallyHidden>Important for screen readers</VisuallyHidden>);
      // If screen readers can find it, so can our test utilities
      expect(screen.getByText('Important for screen readers')).toBeInTheDocument();
    });

    it('maintains semantic structure with heading', () => {
      render(<VisuallyHidden as="h2">Hidden heading</VisuallyHidden>);
      const heading = screen.getByText('Hidden heading');
      expect(heading.tagName).toBe('H2');
    });

    it('works with labels for form inputs', () => {
      render(
        <div>
          <VisuallyHidden as="label">
            Search games
          </VisuallyHidden>
          <input id="search" type="text" />
        </div>
      );

      const label = screen.getByText('Search games');
      expect(label).toBeInTheDocument();
      expect(label.tagName).toBe('LABEL');
    });
  });

  describe('Edge cases', () => {
    it('handles empty children', () => {
      const { container } = render(<VisuallyHidden></VisuallyHidden>);
      expect(container.firstChild).toBeInTheDocument();
    });

    it('handles null children gracefully', () => {
      const { container } = render(<VisuallyHidden>{null}</VisuallyHidden>);
      expect(container.firstChild).toBeInTheDocument();
    });

    it('handles undefined children gracefully', () => {
      const { container } = render(<VisuallyHidden>{undefined}</VisuallyHidden>);
      expect(container.firstChild).toBeInTheDocument();
    });

    it('handles number children', () => {
      render(<VisuallyHidden>{42}</VisuallyHidden>);
      expect(screen.getByText('42')).toBeInTheDocument();
    });

    it('handles boolean children (renders nothing)', () => {
      const { container } = render(<VisuallyHidden>{true}</VisuallyHidden>);
      expect(container.firstChild).toBeInTheDocument();
      // Booleans don't render in React, but the wrapper should still be there
    });
  });

  describe('Common use cases', () => {
    it('works for skip navigation content', () => {
      render(
        <VisuallyHidden>
          Skip to main content
        </VisuallyHidden>
      );
      const content = screen.getByText('Skip to main content');
      expect(content).toBeInTheDocument();
    });

    it('works for form field instructions', () => {
      render(
        <div>
          <label htmlFor="password">Password</label>
          <VisuallyHidden as="p">
            Must be at least 8 characters
          </VisuallyHidden>
          <input id="password" type="password" />
        </div>
      );
      const hint = screen.getByText('Must be at least 8 characters');
      expect(hint).toBeInTheDocument();
      expect(hint.tagName).toBe('P');
    });

    it('works for loading announcements', () => {
      render(
        <VisuallyHidden>
          Loading games...
        </VisuallyHidden>
      );
      const status = screen.getByText('Loading games...');
      expect(status).toBeInTheDocument();
    });
  });
});
