/**
 * Game card icon components tests
 */
import { describe, test, expect } from 'vitest';
import { render } from '@testing-library/react';
import { UsersIcon, ClockIcon, CalendarIcon } from '../icons';

describe('Game Card Icons', () => {
  describe('UsersIcon', () => {
    test('renders SVG element', () => {
      const { container } = render(<UsersIcon />);
      const svg = container.querySelector('svg');

      expect(svg).toBeInTheDocument();
    });

    test('applies className prop', () => {
      const { container } = render(<UsersIcon className="test-class" />);
      const svg = container.querySelector('svg');

      expect(svg).toHaveClass('test-class');
    });

    test('has correct viewBox', () => {
      const { container } = render(<UsersIcon />);
      const svg = container.querySelector('svg');

      expect(svg).toHaveAttribute('viewBox', '0 0 20 20');
      expect(svg).toHaveAttribute('fill', 'currentColor');
    });

    test('renders path element', () => {
      const { container } = render(<UsersIcon />);
      const path = container.querySelector('path');

      expect(path).toBeInTheDocument();
    });

    test('passes through additional props', () => {
      const { container } = render(<UsersIcon data-testid="users" aria-label="Players" />);
      const svg = container.querySelector('svg');

      expect(svg).toHaveAttribute('data-testid', 'users');
      expect(svg).toHaveAttribute('aria-label', 'Players');
    });
  });

  describe('ClockIcon', () => {
    test('renders SVG element', () => {
      const { container } = render(<ClockIcon />);
      const svg = container.querySelector('svg');

      expect(svg).toBeInTheDocument();
    });

    test('applies className prop', () => {
      const { container } = render(<ClockIcon className="test-class" />);
      const svg = container.querySelector('svg');

      expect(svg).toHaveClass('test-class');
    });

    test('has correct viewBox', () => {
      const { container } = render(<ClockIcon />);
      const svg = container.querySelector('svg');

      expect(svg).toHaveAttribute('viewBox', '0 0 20 20');
      expect(svg).toHaveAttribute('fill', 'currentColor');
    });

    test('renders path with fillRule and clipRule', () => {
      const { container } = render(<ClockIcon />);
      const path = container.querySelector('path');

      expect(path).toBeInTheDocument();
      // React converts camelCase to lowercase for DOM attributes
      expect(path).toHaveAttribute('fill-rule', 'evenodd');
      expect(path).toHaveAttribute('clip-rule', 'evenodd');
    });

    test('passes through additional props', () => {
      const { container } = render(<ClockIcon data-testid="clock" aria-label="Playtime" />);
      const svg = container.querySelector('svg');

      expect(svg).toHaveAttribute('data-testid', 'clock');
      expect(svg).toHaveAttribute('aria-label', 'Playtime');
    });
  });

  describe('CalendarIcon', () => {
    test('renders SVG element', () => {
      const { container } = render(<CalendarIcon />);
      const svg = container.querySelector('svg');

      expect(svg).toBeInTheDocument();
    });

    test('applies className prop', () => {
      const { container } = render(<CalendarIcon className="test-class" />);
      const svg = container.querySelector('svg');

      expect(svg).toHaveClass('test-class');
    });

    test('has correct viewBox', () => {
      const { container} = render(<CalendarIcon />);
      const svg = container.querySelector('svg');

      expect(svg).toHaveAttribute('viewBox', '0 0 20 20');
      expect(svg).toHaveAttribute('fill', 'currentColor');
    });

    test('renders path with fillRule and clipRule', () => {
      const { container } = render(<CalendarIcon />);
      const path = container.querySelector('path');

      expect(path).toBeInTheDocument();
      // React converts camelCase to lowercase for DOM attributes
      expect(path).toHaveAttribute('fill-rule', 'evenodd');
      expect(path).toHaveAttribute('clip-rule', 'evenodd');
    });

    test('passes through additional props', () => {
      const { container } = render(<CalendarIcon data-testid="calendar" aria-label="Year" />);
      const svg = container.querySelector('svg');

      expect(svg).toHaveAttribute('data-testid', 'calendar');
      expect(svg).toHaveAttribute('aria-label', 'Year');
    });
  });

  describe('Icon Consistency', () => {
    test('all icons use same viewBox size', () => {
      const { container: usersContainer } = render(<UsersIcon />);
      const { container: clockContainer } = render(<ClockIcon />);
      const { container: calendarContainer } = render(<CalendarIcon />);

      const usersSvg = usersContainer.querySelector('svg');
      const clockSvg = clockContainer.querySelector('svg');
      const calendarSvg = calendarContainer.querySelector('svg');

      expect(usersSvg).toHaveAttribute('viewBox', '0 0 20 20');
      expect(clockSvg).toHaveAttribute('viewBox', '0 0 20 20');
      expect(calendarSvg).toHaveAttribute('viewBox', '0 0 20 20');
    });

    test('all icons use currentColor fill', () => {
      const { container: usersContainer } = render(<UsersIcon />);
      const { container: clockContainer } = render(<ClockIcon />);
      const { container: calendarContainer } = render(<CalendarIcon />);

      const usersSvg = usersContainer.querySelector('svg');
      const clockSvg = clockContainer.querySelector('svg');
      const calendarSvg = calendarContainer.querySelector('svg');

      expect(usersSvg).toHaveAttribute('fill', 'currentColor');
      expect(clockSvg).toHaveAttribute('fill', 'currentColor');
      expect(calendarSvg).toHaveAttribute('fill', 'currentColor');
    });
  });
});
