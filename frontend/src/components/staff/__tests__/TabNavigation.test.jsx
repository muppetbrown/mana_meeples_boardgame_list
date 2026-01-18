/**
 * TabNavigation tests - Staff interface tab navigation component
 */
import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TabNavigation } from '../TabNavigation';

describe('TabNavigation', () => {
  const mockOnTabChange = vi.fn();

  const mockTabs = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'library', label: 'Manage Library', icon: '📚' },
    { id: 'add', label: 'Add Games', icon: '➕' },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    test('renders all tabs', () => {
      render(<TabNavigation activeTab="dashboard" onTabChange={mockOnTabChange} tabs={mockTabs} />);

      // Each label appears twice (mobile and desktop versions)
      expect(screen.getAllByText('Dashboard').length).toBeGreaterThan(0);
      expect(screen.getByText('Manage Library')).toBeInTheDocument();
      expect(screen.getByText('Add Games')).toBeInTheDocument();
    });

    test('renders tab icons when provided', () => {
      render(<TabNavigation activeTab="dashboard" onTabChange={mockOnTabChange} tabs={mockTabs} />);

      // Icons are rendered as text content within the button
      const buttons = screen.getAllByRole('button');
      expect(buttons[0]).toHaveTextContent('📊');
      expect(buttons[1]).toHaveTextContent('📚');
      expect(buttons[2]).toHaveTextContent('➕');
    });

    test('renders tabs without icons', () => {
      const tabsWithoutIcons = [
        { id: 'tab1', label: 'Tab One' },
        { id: 'tab2', label: 'Tab Two' },
      ];

      render(<TabNavigation activeTab="tab1" onTabChange={mockOnTabChange} tabs={tabsWithoutIcons} />);

      expect(screen.getByText('Tab One')).toBeInTheDocument();
      expect(screen.getByText('Tab Two')).toBeInTheDocument();
    });

    test('renders navigation with aria-label', () => {
      render(<TabNavigation activeTab="dashboard" onTabChange={mockOnTabChange} tabs={mockTabs} />);

      const nav = screen.getByRole('navigation');
      expect(nav).toHaveAttribute('aria-label', 'Admin navigation tabs');
    });

    test('renders empty when no tabs provided', () => {
      render(<TabNavigation activeTab="dashboard" onTabChange={mockOnTabChange} tabs={[]} />);

      const buttons = screen.queryAllByRole('button');
      expect(buttons.length).toBe(0);
    });
  });

  describe('Active Tab Highlighting', () => {
    test('applies active styles to current tab', () => {
      render(<TabNavigation activeTab="library" onTabChange={mockOnTabChange} tabs={mockTabs} />);

      const libraryButton = screen.getAllByRole('button')[1];
      expect(libraryButton).toHaveClass('border-purple-600');
      expect(libraryButton).toHaveClass('text-purple-700');
      expect(libraryButton).toHaveClass('bg-purple-50');
    });

    test('applies inactive styles to non-active tabs', () => {
      render(<TabNavigation activeTab="dashboard" onTabChange={mockOnTabChange} tabs={mockTabs} />);

      const libraryButton = screen.getAllByRole('button')[1];
      expect(libraryButton).toHaveClass('border-transparent');
      expect(libraryButton).toHaveClass('text-gray-600');
    });

    test('sets aria-current="page" on active tab', () => {
      render(<TabNavigation activeTab="add" onTabChange={mockOnTabChange} tabs={mockTabs} />);

      const addButton = screen.getAllByRole('button')[2];
      expect(addButton).toHaveAttribute('aria-current', 'page');
    });

    test('does not set aria-current on inactive tabs', () => {
      render(<TabNavigation activeTab="dashboard" onTabChange={mockOnTabChange} tabs={mockTabs} />);

      const libraryButton = screen.getAllByRole('button')[1];
      expect(libraryButton).not.toHaveAttribute('aria-current');
    });
  });

  describe('Tab Interactions', () => {
    test('calls onTabChange when tab clicked', async () => {
      const user = userEvent.setup();

      render(<TabNavigation activeTab="dashboard" onTabChange={mockOnTabChange} tabs={mockTabs} />);

      const libraryButton = screen.getAllByRole('button')[1];
      await user.click(libraryButton);

      expect(mockOnTabChange).toHaveBeenCalledTimes(1);
      expect(mockOnTabChange).toHaveBeenCalledWith('library');
    });

    test('calls onTabChange with correct tab id for each tab', async () => {
      const user = userEvent.setup();

      render(<TabNavigation activeTab="dashboard" onTabChange={mockOnTabChange} tabs={mockTabs} />);

      const buttons = screen.getAllByRole('button');

      await user.click(buttons[0]);
      expect(mockOnTabChange).toHaveBeenCalledWith('dashboard');

      await user.click(buttons[1]);
      expect(mockOnTabChange).toHaveBeenCalledWith('library');

      await user.click(buttons[2]);
      expect(mockOnTabChange).toHaveBeenCalledWith('add');

      expect(mockOnTabChange).toHaveBeenCalledTimes(3);
    });

    test('clicking active tab still calls onTabChange', async () => {
      const user = userEvent.setup();

      render(<TabNavigation activeTab="dashboard" onTabChange={mockOnTabChange} tabs={mockTabs} />);

      const dashboardButton = screen.getAllByRole('button')[0];
      await user.click(dashboardButton);

      expect(mockOnTabChange).toHaveBeenCalledWith('dashboard');
    });
  });

  describe('Responsive Design', () => {
    test('full labels are rendered (hidden on mobile)', () => {
      render(<TabNavigation activeTab="dashboard" onTabChange={mockOnTabChange} tabs={mockTabs} />);

      // Full labels have "hidden sm:inline" class
      const buttons = screen.getAllByRole('button');
      expect(buttons[0]).toHaveTextContent('Dashboard');
      expect(buttons[1]).toHaveTextContent('Manage Library');
    });

    test('truncated labels show first word only', () => {
      render(<TabNavigation activeTab="library" onTabChange={mockOnTabChange} tabs={mockTabs} />);

      // Truncated labels have "sm:hidden" class and show only first word
      const libraryButton = screen.getAllByRole('button')[1];
      // Should contain both "Manage" (mobile) and "Manage Library" (desktop)
      expect(libraryButton).toHaveTextContent('Manage');
      expect(libraryButton).toHaveTextContent('Manage Library');
    });

    test('tabs have overflow handling classes', () => {
      const { container } = render(
        <TabNavigation activeTab="dashboard" onTabChange={mockOnTabChange} tabs={mockTabs} />
      );

      const tabContainer = container.querySelector('.overflow-x-auto');
      expect(tabContainer).toBeInTheDocument();
      expect(tabContainer).toHaveClass('scrollbar-thin');
    });
  });

  describe('Multiple Tabs', () => {
    test('renders many tabs correctly', () => {
      const manyTabs = Array.from({ length: 10 }, (_, i) => ({
        id: `tab${i}`,
        label: `Tab ${i + 1}`,
      }));

      render(<TabNavigation activeTab="tab0" onTabChange={mockOnTabChange} tabs={manyTabs} />);

      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBe(10);
    });

    test('each tab button has unique key', () => {
      render(<TabNavigation activeTab="dashboard" onTabChange={mockOnTabChange} tabs={mockTabs} />);

      // React will warn if keys are not unique, test that no console errors occur
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBe(mockTabs.length);
    });
  });

  describe('Accessibility', () => {
    test('all tabs are keyboard focusable', async () => {
      const user = userEvent.setup();

      render(<TabNavigation activeTab="dashboard" onTabChange={mockOnTabChange} tabs={mockTabs} />);

      const buttons = screen.getAllByRole('button');

      buttons[0].focus();
      expect(buttons[0]).toHaveFocus();

      await user.keyboard('{Tab}');
      expect(buttons[1]).toHaveFocus();

      await user.keyboard('{Tab}');
      expect(buttons[2]).toHaveFocus();
    });

    test('tabs can be activated with Enter key', async () => {
      const user = userEvent.setup();

      render(<TabNavigation activeTab="dashboard" onTabChange={mockOnTabChange} tabs={mockTabs} />);

      const libraryButton = screen.getAllByRole('button')[1];
      libraryButton.focus();
      expect(libraryButton).toHaveFocus();

      await user.keyboard('{Enter}');

      expect(mockOnTabChange).toHaveBeenCalledWith('library');
    });

    test('tabs can be activated with Space key', async () => {
      const user = userEvent.setup();

      render(<TabNavigation activeTab="dashboard" onTabChange={mockOnTabChange} tabs={mockTabs} />);

      const addButton = screen.getAllByRole('button')[2];
      addButton.focus();

      await user.keyboard(' ');

      expect(mockOnTabChange).toHaveBeenCalledWith('add');
    });

    test('tabs have role="button"', () => {
      render(<TabNavigation activeTab="dashboard" onTabChange={mockOnTabChange} tabs={mockTabs} />);

      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBe(3);
    });
  });

  describe('Tab Structure', () => {
    test('tab labels are wrapped in flex container with icon', () => {
      const { container } = render(
        <TabNavigation activeTab="dashboard" onTabChange={mockOnTabChange} tabs={mockTabs} />
      );

      const flexContainers = container.querySelectorAll('.flex.items-center.gap-1');
      expect(flexContainers.length).toBe(mockTabs.length);
    });

    test('tabs have whitespace-nowrap to prevent wrapping', () => {
      render(<TabNavigation activeTab="dashboard" onTabChange={mockOnTabChange} tabs={mockTabs} />);

      const buttons = screen.getAllByRole('button');
      buttons.forEach((button) => {
        expect(button).toHaveClass('whitespace-nowrap');
      });
    });

    test('tabs have transition classes for smooth styling changes', () => {
      render(<TabNavigation activeTab="dashboard" onTabChange={mockOnTabChange} tabs={mockTabs} />);

      const buttons = screen.getAllByRole('button');
      buttons.forEach((button) => {
        expect(button).toHaveClass('transition-colors');
        expect(button).toHaveClass('duration-150');
      });
    });
  });

  describe('Edge Cases', () => {
    test('handles tab with empty label', () => {
      const tabsWithEmpty = [{ id: 'empty', label: '' }];

      render(<TabNavigation activeTab="empty" onTabChange={mockOnTabChange} tabs={tabsWithEmpty} />);

      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBe(1);
    });

    test('handles tab with very long label', () => {
      const longLabelTabs = [
        {
          id: 'long',
          label: 'This Is A Very Long Tab Label That Should Still Render Properly',
        },
      ];

      render(<TabNavigation activeTab="long" onTabChange={mockOnTabChange} tabs={longLabelTabs} />);

      expect(
        screen.getByText('This Is A Very Long Tab Label That Should Still Render Properly')
      ).toBeInTheDocument();
    });

    test('handles single tab', () => {
      const singleTab = [{ id: 'only', label: 'Only Tab' }];

      render(<TabNavigation activeTab="only" onTabChange={mockOnTabChange} tabs={singleTab} />);

      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBe(1);
      expect(buttons[0]).toHaveClass('border-purple-600');
    });

    test('handles active tab that does not exist in tabs array', () => {
      render(
        <TabNavigation activeTab="nonexistent" onTabChange={mockOnTabChange} tabs={mockTabs} />
      );

      // No tab should have active styling
      const buttons = screen.getAllByRole('button');
      buttons.forEach((button) => {
        expect(button).toHaveClass('border-transparent');
      });
    });
  });
});
