/**
 * StaffContext behaviour tests - toast timers, owned-only counts, confirm dialog,
 * in-place updates, add-game progress and bulk results.
 */
import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { StaffProvider, useStaff, useConfirm } from '../StaffContext';
import * as apiClient from '../../api/client';

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => vi.fn() };
});

vi.mock('../../api/client', () => ({
  validateAdminToken: vi.fn(),
  getGames: vi.fn(),
  bulkImportCsv: vi.fn(),
  bulkCategorizeCsv: vi.fn(),
  updateGame: vi.fn(),
  deleteGame: vi.fn(),
  importFromBGG: vi.fn(),
}));

const lib = [
  { id: 1, title: 'Owned A', status: 'OWNED', mana_meeple_category: 'CORE_STRATEGY', average_rating: 8 },
  { id: 2, title: 'Owned B', mana_meeple_category: null, average_rating: 6 },
  { id: 3, title: 'On Buy List', status: 'BUY_LIST', mana_meeple_category: null, average_rating: 9 },
];

let ctx;
function Probe() {
  ctx = useStaff();
  return <div data-testid="toast">{ctx.toast.message}</div>;
}

const mount = async () => {
  render(
    <MemoryRouter>
      <StaffProvider>
        <Probe />
      </StaffProvider>
    </MemoryRouter>
  );
  await waitFor(() => expect(ctx.library).toHaveLength(3));
};

describe('StaffContext behaviour', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiClient.validateAdminToken.mockResolvedValue({});
    apiClient.getGames.mockResolvedValue(lib);
  });
  afterEach(() => vi.useRealTimers());

  test('stats and counts only include owned games', async () => {
    await mount();
    expect(ctx.stats.total).toBe(2);
    expect(ctx.stats.avgRating).toBe('7.0');
    expect(ctx.counts.all).toBe(2);
    expect(ctx.counts.uncategorized).toBe(1);
    expect(ctx.ownedLibrary.map((g) => g.id)).toEqual([1, 2]);
  });

  test('an older toast timer cannot clear a newer toast', async () => {
    await mount();
    vi.useFakeTimers();
    act(() => ctx.showToast('first', 'info', 1000));
    act(() => vi.advanceTimersByTime(800));
    act(() => ctx.showToast('second', 'info', 1000));
    act(() => vi.advanceTimersByTime(500)); // first's original timer would fire here
    expect(ctx.toast.message).toBe('second');
    act(() => vi.advanceTimersByTime(600));
    expect(ctx.toast.message).toBe('');
  });

  test('error toasts stay visible for at least 4 seconds', async () => {
    await mount();
    vi.useFakeTimers();
    act(() => ctx.showToast('bad', 'error', 1000));
    act(() => vi.advanceTimersByTime(3500));
    expect(ctx.toast.message).toBe('bad');
    act(() => vi.advanceTimersByTime(600));
    expect(ctx.toast.message).toBe('');
  });

  test('updateGameData patches the game in place without refetching', async () => {
    await mount();
    apiClient.updateGame.mockResolvedValue({ id: 2, mana_meeple_category: 'KIDS_FAMILIES' });
    await act(async () => {
      await ctx.updateGameData(2, { mana_meeple_category: 'KIDS_FAMILIES' });
    });
    expect(apiClient.getGames).toHaveBeenCalledTimes(1);
    expect(ctx.library.find((g) => g.id === 2)).toMatchObject({
      title: 'Owned B',
      mana_meeple_category: 'KIDS_FAMILIES',
    });
    expect(ctx.counts.uncategorized).toBe(0);
  });

  test('confirm() resolves true/false from the in-app dialog', async () => {
    const user = userEvent.setup();
    await mount();

    let result;
    act(() => {
      result = ctx.confirm({ title: 'Delete it?', confirmLabel: 'Yes delete', tone: 'danger' });
    });
    const dialog = await screen.findByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    await user.click(screen.getByRole('button', { name: 'Yes delete' }));
    await expect(result).resolves.toBe(true);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

    act(() => {
      result = ctx.confirm({ title: 'Again?' });
    });
    await screen.findByRole('dialog');
    await user.keyboard('{Escape}');
    await expect(result).resolves.toBe(false);
  });

  test('requireText keeps the confirm button disabled until typed', async () => {
    const user = userEvent.setup();
    await mount();
    let result;
    act(() => {
      result = ctx.confirm({ title: 'Nuke', confirmLabel: 'Go', requireText: 'reimport' });
    });
    const go = await screen.findByRole('button', { name: 'Go' });
    expect(go).toBeDisabled();
    await user.type(screen.getByLabelText(/type reimport/i), 'reimport');
    expect(go).toBeEnabled();
    await user.click(go);
    await expect(result).resolves.toBe(true);
  });

  test('handleAddGame keeps the input after a failed import and clears it after success', async () => {
    await mount();
    act(() => ctx.setBggIdInput('999'));
    apiClient.importFromBGG.mockRejectedValue({ response: { status: 404, data: { detail: 'nope' } } });
    await act(async () => {
      await ctx.handleAddGame();
    });
    expect(ctx.bggIdInput).toBe('999');
    expect(ctx.isAddingGame).toBe(false);

    apiClient.importFromBGG.mockResolvedValue({ title: 'New Game' });
    await act(async () => {
      await ctx.handleAddGame();
    });
    expect(ctx.bggIdInput).toBe('');
  });

  test('handleAddGame accepts a pasted BGG URL', async () => {
    await mount();
    act(() => ctx.setBggIdInput('https://boardgamegeek.com/boardgame/30549/pandemic'));
    apiClient.importFromBGG.mockResolvedValue({ title: 'Pandemic' });
    await act(async () => {
      await ctx.handleAddGame();
    });
    expect(apiClient.importFromBGG).toHaveBeenCalledWith(30549);
  });

  test('bulk import reports what the server queued', async () => {
    await mount();
    apiClient.bulkImportCsv.mockResolvedValue({ message: 'Started importing 2 line(s)', count: 2 });
    act(() => ctx.setCsvImportText('1\n2'));
    await act(async () => {
      await ctx.doBulkImport();
    });
    expect(ctx.bulkImportResult).toMatchObject({ message: 'Started importing 2 line(s)', count: 2 });
  });

  test('bulk categorize exposes per-row results', async () => {
    await mount();
    apiClient.bulkCategorizeCsv.mockResolvedValue({ updated: ['a'], not_found: ['b'], errors: [] });
    act(() => ctx.setCsvCategorizeText('1,CORE_STRATEGY'));
    await act(async () => {
      await ctx.doBulkCategorize();
    });
    expect(ctx.bulkCategorizeResult).toMatchObject({ updated: ['a'], not_found: ['b'], errors: [] });
  });
});

describe('useConfirm outside a provider', () => {
  test('falls back to window.confirm', async () => {
    window.confirm = vi.fn(() => true);
    let fn;
    function C() {
      fn = useConfirm();
      return null;
    }
    render(<C />);
    await expect(fn({ title: 'T', message: 'M' })).resolves.toBe(true);
    expect(window.confirm).toHaveBeenCalledWith('T\n\nM');
  });
});
