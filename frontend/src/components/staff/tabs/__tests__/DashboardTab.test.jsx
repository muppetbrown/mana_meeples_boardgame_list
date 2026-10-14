/**
 * DashboardTab tests - needs-attention checks, system health, monitoring
 */
import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DashboardTab } from '../DashboardTab';
import * as apiClient from '../../../../api/client';

vi.mock('../../../../api/client', () => ({
  getHealthCheck: vi.fn(),
  getDbHealthCheck: vi.fn(),
  getBackgroundFailures: vi.fn(),
  resolveBackgroundFailure: vi.fn(),
  getCircuitBreakerStatus: vi.fn(),
}));

vi.mock('../../../../context/StaffContext', () => ({
  useStaff: vi.fn(),
}));

import { useStaff } from '../../../../context/StaffContext';

const game = (over) => ({
  id: Math.random(),
  title: 'Game',
  status: 'OWNED',
  mana_meeple_category: 'CORE_STRATEGY',
  has_sleeves: 'found',
  image_url: 'x.jpg',
  designers: ['A'],
  complexity: 2.5,
  bgg_id: 1,
  date_added: '2025-01-02T00:00:00Z',
  ...over,
});

describe('DashboardTab', () => {
  const onTabChange = vi.fn();
  const setAttentionFilter = vi.fn();
  const setSelectedCategory = vi.fn();
  const showToast = vi.fn();

  const owned = [
    game({ id: 1, title: 'Clean Game' }),
    game({ id: 2, title: 'Needs Category', mana_meeple_category: null }),
    game({ id: 3, title: 'No Image', image_url: null }),
    game({ id: 4, title: 'Unknown Sleeves', has_sleeves: null }),
  ];

  const ctx = (over = {}) => ({
    stats: { total: 4, avgRating: '7.8' },
    ownedLibrary: owned,
    library: [...owned, game({ id: 9, status: 'BUY_LIST' })],
    setAttentionFilter,
    setSelectedCategory,
    showToast,
    ...over,
  });

  beforeEach(() => {
    vi.clearAllMocks();
    apiClient.getHealthCheck.mockResolvedValue({ status: 'healthy' });
    apiClient.getDbHealthCheck.mockResolvedValue({ status: 'healthy' });
    apiClient.getBackgroundFailures.mockResolvedValue({
      unresolved_failures: 0,
      failures: [],
    });
    apiClient.getCircuitBreakerStatus.mockResolvedValue({ state: 'closed', description: 'ok' });
    useStaff.mockReturnValue(ctx());
  });

  test('shows stats from context including buy list count', async () => {
    render(<DashboardTab onTabChange={onTabChange} />);
    expect(screen.getByText('Games in library')).toBeInTheDocument();
    expect(screen.getByText('7.8')).toBeInTheDocument();
    expect(screen.getByText('On the buy list').nextSibling).toHaveTextContent('1');
    await screen.findByText('All Systems Operational');
  });

  test('shows counts for each needs-attention check', async () => {
    render(<DashboardTab onTabChange={onTabChange} />);
    await screen.findByText('All Systems Operational');
    expect(screen.getByText('Uncategorized').previousSibling).toHaveTextContent('1');
    expect(screen.getByText('Missing image').previousSibling).toHaveTextContent('1');
    expect(screen.getByText('Sleeve status unknown').previousSibling).toHaveTextContent('1');
    expect(screen.getByText('Missing designers').previousSibling).toHaveTextContent('0');
  });

  test('clicking an attention card applies the filter and opens Manage Library', async () => {
    const user = userEvent.setup();
    render(<DashboardTab onTabChange={onTabChange} />);
    await screen.findByText('All Systems Operational');
    await user.click(screen.getByText('Missing image'));
    expect(setSelectedCategory).toHaveBeenCalledWith('all');
    expect(setAttentionFilter).toHaveBeenCalledWith('no_image');
    expect(onTabChange).toHaveBeenCalledWith('manage-library');
  });

  test('uncategorized card jumps to the Categories tab', async () => {
    const user = userEvent.setup();
    render(<DashboardTab onTabChange={onTabChange} />);
    await screen.findByText('All Systems Operational');
    await user.click(screen.getByText('Uncategorized'));
    expect(onTabChange).toHaveBeenCalledWith('categories');
  });

  test('zero-count cards are disabled', async () => {
    render(<DashboardTab onTabChange={onTabChange} />);
    await screen.findByText('All Systems Operational');
    expect(screen.getByText('Missing designers').closest('button')).toBeDisabled();
  });

  test('shows all clear when nothing needs attention', async () => {
    useStaff.mockReturnValue(ctx({ ownedLibrary: [owned[0]] }));
    render(<DashboardTab onTabChange={onTabChange} />);
    expect(await screen.findByText(/All clear/)).toBeInTheDocument();
  });

  test('reports issues when the database is unhealthy', async () => {
    apiClient.getDbHealthCheck.mockResolvedValue({ status: 'unhealthy' });
    render(<DashboardTab onTabChange={onTabChange} />);
    expect(await screen.findByText('System Issues Detected')).toBeInTheDocument();
  });

  test('reports unknown status when health checks fail', async () => {
    apiClient.getHealthCheck.mockRejectedValue(new Error('down'));
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    render(<DashboardTab onTabChange={onTabChange} />);
    expect(await screen.findByText('System Status Unknown')).toBeInTheDocument();
    spy.mockRestore();
  });

  test('warns when the BGG circuit breaker is open', async () => {
    apiClient.getCircuitBreakerStatus.mockResolvedValue({ state: 'open', description: 'Service is down' });
    render(<DashboardTab onTabChange={onTabChange} />);
    expect(await screen.findByText(/BoardGameGeek requests are being limited/)).toBeInTheDocument();
  });

  test('lists unresolved background failures and resolves one', async () => {
    const user = userEvent.setup();
    apiClient.getBackgroundFailures.mockResolvedValue({
      unresolved_failures: 1,
      failures: [{ id: 7, task_type: 'bgg_import', game_id: 3, error_message: 'timeout' }],
    });
    apiClient.resolveBackgroundFailure.mockResolvedValue({ success: true });
    render(<DashboardTab onTabChange={onTabChange} />);
    expect(await screen.findByText(/bgg_import/)).toBeInTheDocument();
    await user.click(screen.getByText('Resolve'));
    await waitFor(() => expect(apiClient.resolveBackgroundFailure).toHaveBeenCalledWith(7));
    expect(showToast).toHaveBeenCalledWith('Marked as resolved', 'success');
  });

  test('tolerates monitoring endpoints failing', async () => {
    apiClient.getBackgroundFailures.mockRejectedValue(new Error('500'));
    apiClient.getCircuitBreakerStatus.mockRejectedValue(new Error('500'));
    render(<DashboardTab onTabChange={onTabChange} />);
    expect(await screen.findByText('Failure data unavailable.')).toBeInTheDocument();
  });

  test('refresh re-fetches health and monitoring data', async () => {
    const user = userEvent.setup();
    render(<DashboardTab onTabChange={onTabChange} />);
    await screen.findByText('All Systems Operational');
    await user.click(screen.getByText(/Refresh/));
    await waitFor(() => expect(apiClient.getHealthCheck).toHaveBeenCalledTimes(2));
    expect(apiClient.getBackgroundFailures).toHaveBeenCalledTimes(2);
  });

  test('quick actions navigate to their tabs', async () => {
    const user = userEvent.setup();
    render(<DashboardTab onTabChange={onTabChange} />);
    await screen.findByText('All Systems Operational');
    await user.click(screen.getByText('📥 Add games'));
    expect(onTabChange).toHaveBeenCalledWith('add-games');
    await user.click(screen.getByText('⚙️ Advanced tools'));
    expect(onTabChange).toHaveBeenCalledWith('advanced');
  });

  test('lists recently added games, newest first', async () => {
    useStaff.mockReturnValue(
      ctx({
        ownedLibrary: [
          game({ id: 1, title: 'Older', date_added: '2025-01-01T00:00:00Z' }),
          game({ id: 2, title: 'Newer', date_added: '2025-03-01T00:00:00Z' }),
        ],
      })
    );
    render(<DashboardTab onTabChange={onTabChange} />);
    const items = await screen.findAllByText(/^(Older|Newer)$/);
    expect(items[0]).toHaveTextContent('Newer');
  });
});
