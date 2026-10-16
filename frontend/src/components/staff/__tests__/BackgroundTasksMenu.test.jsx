import { describe, test, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BackgroundTasksMenu } from '../BackgroundTasksMenu';

describe('BackgroundTasksMenu', () => {
  test('renders nothing without operations', () => {
    const { container } = render(<BackgroundTasksMenu operations={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  test('shows running count and lists operations when opened', async () => {
    const user = userEvent.setup();
    const ops = [
      { id: 1, label: 'Re-import (3 games)', startedAt: Date.now(), etaMs: 600000 },
      { id: 2, label: 'Old import', startedAt: Date.now() - 600000, etaMs: 1000 },
    ];
    render(<BackgroundTasksMenu operations={ops} onDismiss={vi.fn()} />);
    const trigger = screen.getByRole('button', { name: /1 running/ });
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    await user.click(trigger);
    expect(screen.getByText('Re-import (3 games)')).toBeInTheDocument();
    expect(screen.getByText('Running…')).toBeInTheDocument();
    expect(screen.getByText('Likely done')).toBeInTheDocument();
  });

  test('dismisses an operation and closes on Escape', async () => {
    const user = userEvent.setup();
    const onDismiss = vi.fn();
    render(
      <BackgroundTasksMenu
        operations={[{ id: 7, label: 'Sleeve fetch', startedAt: Date.now(), etaMs: 60000 }]}
        onDismiss={onDismiss}
      />
    );
    await user.click(screen.getByRole('button', { name: /running/ }));
    await user.click(screen.getByRole('button', { name: 'Dismiss Sleeve fetch' }));
    expect(onDismiss).toHaveBeenCalledWith(7);
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('region', { name: 'Background tasks' })).not.toBeInTheDocument();
  });
});
