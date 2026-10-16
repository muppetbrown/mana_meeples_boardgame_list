/**
 * TabNavigation tests - WAI-ARIA tabs pattern
 */
import { describe, test, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TabNavigation } from '../TabNavigation';

const tabs = [
  { id: 'dashboard', label: 'Dashboard', icon: '📊' },
  { id: 'add-games', label: 'Add Games', icon: '📥' },
  { id: 'manage-library', label: 'Manage Library', icon: '📚' },
];

const setup = (activeTab = 'dashboard') => {
  const onTabChange = vi.fn();
  render(<TabNavigation activeTab={activeTab} onTabChange={onTabChange} tabs={tabs} />);
  return onTabChange;
};

describe('TabNavigation', () => {
  test('renders a labelled tablist with one tab per entry', () => {
    setup();
    expect(screen.getByRole('tablist', { name: 'Admin sections' })).toBeInTheDocument();
    expect(screen.getAllByRole('tab')).toHaveLength(3);
  });

  test('renders full labels and hides icons from assistive tech', () => {
    setup();
    expect(screen.getByRole('tab', { name: 'Manage Library' })).toBeInTheDocument();
    expect(screen.getByText('📊')).toHaveAttribute('aria-hidden', 'true');
  });

  test('marks only the active tab as selected, with roving tabindex', () => {
    setup('add-games');
    const active = screen.getByRole('tab', { name: 'Add Games' });
    expect(active).toHaveAttribute('aria-selected', 'true');
    expect(active).toHaveAttribute('tabindex', '0');
    const other = screen.getByRole('tab', { name: 'Dashboard' });
    expect(other).toHaveAttribute('aria-selected', 'false');
    expect(other).toHaveAttribute('tabindex', '-1');
  });

  test('links tabs to their panels', () => {
    setup();
    const tab = screen.getByRole('tab', { name: 'Dashboard' });
    expect(tab).toHaveAttribute('id', 'tab-dashboard');
    expect(tab).toHaveAttribute('aria-controls', 'panel-dashboard');
  });

  test('calls onTabChange with the tab id on click', async () => {
    const user = userEvent.setup();
    const onTabChange = setup();
    await user.click(screen.getByRole('tab', { name: 'Manage Library' }));
    expect(onTabChange).toHaveBeenCalledWith('manage-library');
  });

  test('arrow keys move between tabs and wrap around', async () => {
    const user = userEvent.setup();
    const onTabChange = setup('dashboard');
    screen.getByRole('tab', { name: 'Dashboard' }).focus();
    await user.keyboard('{ArrowRight}');
    expect(onTabChange).toHaveBeenLastCalledWith('add-games');
    screen.getByRole('tab', { name: 'Dashboard' }).focus();
    await user.keyboard('{ArrowLeft}');
    expect(onTabChange).toHaveBeenLastCalledWith('manage-library'); // wraps
  });

  test('Home and End jump to first and last tab', async () => {
    const user = userEvent.setup();
    const onTabChange = setup('add-games');
    screen.getByRole('tab', { name: 'Add Games' }).focus();
    await user.keyboard('{End}');
    expect(onTabChange).toHaveBeenLastCalledWith('manage-library');
    await user.keyboard('{Home}');
    expect(onTabChange).toHaveBeenLastCalledWith('dashboard');
  });

  describe('icons, groups and badges', () => {
    const grouped = [
      { id: 'a', label: 'Alpha', icon: 'dashboard', group: 'one' },
      { id: 'b', label: 'Beta', icon: 'tag', group: 'two', badge: 7 },
      { id: 'c', label: 'Gamma', icon: '📚', group: 'two' },
    ];

    test('renders svg icons for known names and text for anything else', () => {
      const { container } = render(<TabNavigation activeTab="a" onTabChange={() => {}} tabs={grouped} />);
      expect(container.querySelectorAll('button svg')).toHaveLength(2);
      expect(screen.getByText('📚')).toHaveAttribute('aria-hidden', 'true');
    });

    test('shows a count badge only when badge > 0', () => {
      render(<TabNavigation activeTab="a" onTabChange={() => {}} tabs={grouped} />);
      expect(screen.getByLabelText('7 need attention')).toHaveTextContent('7');
      expect(screen.getAllByLabelText(/need attention/)).toHaveLength(1);
    });

    test('draws a divider when the group changes', () => {
      const { container } = render(<TabNavigation activeTab="a" onTabChange={() => {}} tabs={grouped} />);
      expect(container.querySelectorAll('[role="presentation"]')).toHaveLength(1);
    });
  });
});
