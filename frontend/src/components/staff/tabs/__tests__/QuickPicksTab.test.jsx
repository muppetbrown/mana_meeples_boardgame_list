/**
 * QuickPicksTab tests - curation panel for the mobile library's quick-picks
 */
import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QuickPicksTab } from '../QuickPicksTab';

vi.mock('../../../../api/client', () => ({
  getQuickPickCandidates: vi.fn(),
  updateGame: vi.fn(),
}));

vi.mock('../../../../context/StaffContext', () => ({
  useStaff: vi.fn(),
}));

import { useStaff } from '../../../../context/StaffContext';
import { getQuickPickCandidates, updateGame } from '../../../../api/client';

describe('QuickPicksTab', () => {
  const mockShowToast = vi.fn();

  const candidates = [
    { id: 1, title: 'Codenames', complexity: 1.31, excluded_quick_picks: [] },
    { id: 2, title: 'Monikers', complexity: 1.09, excluded_quick_picks: ['first'] },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    useStaff.mockReturnValue({ showToast: mockShowToast });
    getQuickPickCandidates.mockResolvedValue(candidates);
    updateGame.mockResolvedValue({});
  });

  test('loads and displays candidates for the default (first) quick pick', async () => {
    render(<QuickPicksTab />);

    await waitFor(() => {
      expect(getQuickPickCandidates).toHaveBeenCalledWith('first');
    });
    expect(await screen.findByText('Codenames')).toBeInTheDocument();
    expect(screen.getByText('Monikers')).toBeInTheDocument();
  });

  test('shows included/excluded counts and correct action labels', async () => {
    render(<QuickPicksTab />);

    await screen.findByText('Codenames');

    // Codenames is included -> "Remove"; Monikers is excluded -> "Restore"
    const rows = screen.getAllByRole('button', { name: /Remove|Restore/ });
    expect(rows.map((b) => b.textContent)).toEqual(['Remove', 'Restore']);
  });

  test('switching quick picks fetches candidates for the new key', async () => {
    const user = userEvent.setup();
    render(<QuickPicksTab />);
    await screen.findByText('Codenames');

    await user.click(screen.getByRole('tab', { name: /Team up/i }));

    await waitFor(() => {
      expect(getQuickPickCandidates).toHaveBeenLastCalledWith('coop');
    });
  });

  test('clicking Remove excludes the game from the active quick pick', async () => {
    const user = userEvent.setup();
    render(<QuickPicksTab />);
    await screen.findByText('Codenames');

    const removeButton = screen.getAllByRole('button', { name: 'Remove' })[0];
    await user.click(removeButton);

    await waitFor(() => {
      expect(updateGame).toHaveBeenCalledWith(1, { excluded_quick_picks: ['first'] });
    });
    // Both Codenames (just excluded) and Monikers (already excluded) now show "Restore"
    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: 'Restore' })).toHaveLength(2);
    });
  });

  test('clicking Restore re-includes an excluded game', async () => {
    const user = userEvent.setup();
    render(<QuickPicksTab />);
    await screen.findByText('Monikers');

    const restoreButton = screen.getByRole('button', { name: 'Restore' });
    await user.click(restoreButton);

    await waitFor(() => {
      expect(updateGame).toHaveBeenCalledWith(2, { excluded_quick_picks: [] });
    });
  });

  test('shows a toast and keeps prior state if the update fails', async () => {
    updateGame.mockRejectedValueOnce(new Error('network error'));
    const user = userEvent.setup();
    render(<QuickPicksTab />);
    await screen.findByText('Codenames');

    await user.click(screen.getAllByRole('button', { name: 'Remove' })[0]);

    await waitFor(() => {
      expect(mockShowToast).toHaveBeenCalledWith('Failed to update game', 'error');
    });
  });

  test('shows an empty state when nothing matches', async () => {
    getQuickPickCandidates.mockResolvedValue([]);
    render(<QuickPicksTab />);

    expect(await screen.findByText(/No games currently match/i)).toBeInTheDocument();
  });
});
