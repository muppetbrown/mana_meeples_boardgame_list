/**
 * DashboardTab tests - Landing page with overview and quick actions
 */
import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DashboardTab } from '../DashboardTab';
import * as apiClient from '../../../../api/client';

// Mock API client
vi.mock('../../../../api/client', () => ({
  getHealthCheck: vi.fn(),
  getDbHealthCheck: vi.fn(),
}));

// Mock useStaff hook
vi.mock('../../../../context/StaffContext', () => ({
  useStaff: vi.fn(),
}));

import { useStaff } from '../../../../context/StaffContext';

describe('DashboardTab', () => {
  const mockOnTabChange = vi.fn();

  const defaultStaffContext = {
    stats: {
      total: 150,
      avgRating: '7.8',
    },
    counts: {
      all: 150,
      COOP_ADVENTURE: 30,
      CORE_STRATEGY: 40,
      GATEWAY_STRATEGY: 50,
      KIDS_FAMILIES: 20,
      PARTY_ICEBREAKERS: 10,
      uncategorized: 5,
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Default successful health checks
    apiClient.getHealthCheck.mockResolvedValue({ status: 'healthy' });
    apiClient.getDbHealthCheck.mockResolvedValue({ status: 'healthy' });

    // Mock useStaff hook with default context
    useStaff.mockReturnValue(defaultStaffContext);
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  describe('Rendering', () => {
    test('renders dashboard with all sections', async () => {
      render(<DashboardTab onTabChange={mockOnTabChange} />);

      // System Status section
      expect(screen.getByText('System Status')).toBeInTheDocument();

      // Quick Stats section
      expect(screen.getByText('Total Games')).toBeInTheDocument();
      expect(screen.getByText('Average BGG Rating')).toBeInTheDocument();
      expect(screen.getByText('Uncategorized')).toBeInTheDocument();

      // Quick Actions section
      expect(screen.getByText('Quick Actions')).toBeInTheDocument();

      // Tips section
      expect(screen.getByText('💡 Quick Tips')).toBeInTheDocument();
    });

    test('displays correct stats from context', () => {
      render(<DashboardTab onTabChange={mockOnTabChange} />);

      expect(screen.getByText('150')).toBeInTheDocument(); // Total games
      expect(screen.getByText('7.8')).toBeInTheDocument(); // Average rating
      expect(screen.getByText('5')).toBeInTheDocument(); // Uncategorized count
    });

    test('displays zero values correctly', () => {
      const zeroStaffContext = {
        stats: { total: 0, avgRating: 'N/A' },
        counts: { all: 0, uncategorized: 0 },
      };

      useStaff.mockReturnValue(zeroStaffContext);
      render(<DashboardTab onTabChange={mockOnTabChange} />);

      // Check for "0" in Total Games stat (using getAllByText to verify it's present)
      const zeroElements = screen.getAllByText('0');
      expect(zeroElements.length).toBeGreaterThan(0);

      expect(screen.getByText('N/A')).toBeInTheDocument();
    });
  });

  describe('System Health', () => {
    test('shows loading state initially', () => {
      render(<DashboardTab onTabChange={mockOnTabChange} />);

      expect(screen.getByText('Checking...')).toBeInTheDocument();
      expect(screen.getAllByText('...')).toHaveLength(2); // API and DB status
    });

    test('shows healthy status when all systems operational', async () => {
      apiClient.getHealthCheck.mockResolvedValue({ status: 'healthy' });
      apiClient.getDbHealthCheck.mockResolvedValue({ status: 'healthy' });

      render(<DashboardTab onTabChange={mockOnTabChange} />);

      await waitFor(() => {
        expect(screen.getByText('All Systems Operational')).toBeInTheDocument();
      });

      expect(screen.getAllByText('healthy')).toHaveLength(2);
    });

    test('shows unknown status when health checks fail', async () => {
      apiClient.getHealthCheck.mockRejectedValue(new Error('Network error'));
      apiClient.getDbHealthCheck.mockRejectedValue(new Error('Network error'));

      render(<DashboardTab onTabChange={mockOnTabChange} />);

      await waitFor(() => {
        expect(screen.getByText('System Status Unknown')).toBeInTheDocument();
      });

      expect(screen.getAllByText('Unknown')).toHaveLength(2);
    });

    test('shows issues detected when API unhealthy', async () => {
      apiClient.getHealthCheck.mockResolvedValue({ status: 'unhealthy' });
      apiClient.getDbHealthCheck.mockResolvedValue({ status: 'healthy' });

      render(<DashboardTab onTabChange={mockOnTabChange} />);

      await waitFor(() => {
        expect(screen.getByText('System Issues Detected')).toBeInTheDocument();
      });
    });

    test('shows issues detected when DB unhealthy', async () => {
      apiClient.getHealthCheck.mockResolvedValue({ status: 'healthy' });
      apiClient.getDbHealthCheck.mockResolvedValue({ status: 'unhealthy' });

      render(<DashboardTab onTabChange={mockOnTabChange} />);

      await waitFor(() => {
        expect(screen.getByText('System Issues Detected')).toBeInTheDocument();
      });
    });

    test('fetches health status on mount', async () => {
      render(<DashboardTab onTabChange={mockOnTabChange} />);

      await waitFor(() => {
        expect(apiClient.getHealthCheck).toHaveBeenCalledTimes(1);
        expect(apiClient.getDbHealthCheck).toHaveBeenCalledTimes(1);
      });
    });

    test('handles partial health check failures', async () => {
      apiClient.getHealthCheck.mockResolvedValue({ status: 'healthy' });
      apiClient.getDbHealthCheck.mockRejectedValue(new Error('DB error'));

      render(<DashboardTab onTabChange={mockOnTabChange} />);

      await waitFor(() => {
        expect(screen.getByText('System Status Unknown')).toBeInTheDocument();
      });
    });
  });

  describe('Quick Actions', () => {
    test('renders all quick action buttons', () => {
      render(<DashboardTab onTabChange={mockOnTabChange} />);

      expect(screen.getByText('📥 Add New Games')).toBeInTheDocument();
      expect(screen.getByText('📚 Manage Library')).toBeInTheDocument();
      expect(screen.getByText('🏷️ Manage Categories')).toBeInTheDocument();
      expect(screen.getByText('⚙️ Advanced Tools')).toBeInTheDocument();
    });

    test('navigates to add-games tab when Add New Games clicked', async () => {
      const user = userEvent.setup();

      render(<DashboardTab onTabChange={mockOnTabChange} />);

      const addGamesButton = screen.getByText('📥 Add New Games').closest('button');
      await user.click(addGamesButton);

      expect(mockOnTabChange).toHaveBeenCalledWith('add-games');
      expect(mockOnTabChange).toHaveBeenCalledTimes(1);
    });

    test('navigates to manage-library tab when Manage Library clicked', async () => {
      const user = userEvent.setup();

      render(<DashboardTab onTabChange={mockOnTabChange} />);

      const manageLibraryButton = screen.getByText('📚 Manage Library').closest('button');
      await user.click(manageLibraryButton);

      expect(mockOnTabChange).toHaveBeenCalledWith('manage-library');
    });

    test('navigates to categories tab when Manage Categories clicked', async () => {
      const user = userEvent.setup();

      render(<DashboardTab onTabChange={mockOnTabChange} />);

      const categoriesButton = screen.getByText('🏷️ Manage Categories').closest('button');
      await user.click(categoriesButton);

      expect(mockOnTabChange).toHaveBeenCalledWith('categories');
    });

    test('navigates to advanced tab when Advanced Tools clicked', async () => {
      const user = userEvent.setup();

      render(<DashboardTab onTabChange={mockOnTabChange} />);

      const advancedButton = screen.getByText('⚙️ Advanced Tools').closest('button');
      await user.click(advancedButton);

      expect(mockOnTabChange).toHaveBeenCalledWith('advanced');
    });

    test('shows uncategorized badge on categories button when games exist', () => {
      render(<DashboardTab onTabChange={mockOnTabChange} />);

      expect(screen.getByText('5 uncategorized')).toBeInTheDocument();
    });

    test('hides uncategorized badge when count is zero', () => {
      const contextWithZeroUncategorized = {
        ...defaultStaffContext,
        counts: { ...defaultStaffContext.counts, uncategorized: 0 },
      };

      useStaff.mockReturnValue(contextWithZeroUncategorized);

      render(<DashboardTab onTabChange={mockOnTabChange} />);

      expect(screen.queryByText('0 uncategorized')).not.toBeInTheDocument();
    });

    test('shows correct uncategorized count in badge', () => {
      const contextWithManyUncategorized = {
        ...defaultStaffContext,
        counts: { ...defaultStaffContext.counts, uncategorized: 25 },
      };

      useStaff.mockReturnValue(contextWithManyUncategorized);

      render(<DashboardTab onTabChange={mockOnTabChange} />);

      expect(screen.getByText('25 uncategorized')).toBeInTheDocument();
    });
  });

  describe('Quick Tips', () => {
    test('renders all quick tips', () => {
      render(<DashboardTab onTabChange={mockOnTabChange} />);

      expect(screen.getByText(/Adding games\?/)).toBeInTheDocument();
      expect(screen.getByText(/Need to categorize many games\?/)).toBeInTheDocument();
      expect(screen.getByText(/System running slow\?/)).toBeInTheDocument();
    });

    test('tips mention relevant features', () => {
      render(<DashboardTab onTabChange={mockOnTabChange} />);

      expect(screen.getByText(/BGG ID import/)).toBeInTheDocument();
      expect(screen.getByText(/bulk categorize CSV/)).toBeInTheDocument();
      expect(screen.getByText(/Performance Stats/)).toBeInTheDocument();
    });
  });

  describe('Integration with StaffContext', () => {
    test('updates when context stats change', () => {
      useStaff.mockReturnValue(defaultStaffContext);

      const { rerender } = render(<DashboardTab onTabChange={mockOnTabChange} />);

      expect(screen.getByText('150')).toBeInTheDocument();

      const updatedContext = {
        stats: { total: 200, avgRating: '8.2' },
        counts: { ...defaultStaffContext.counts, uncategorized: 10 },
      };

      // Update mock return value for rerender
      useStaff.mockReturnValue(updatedContext);

      rerender(<DashboardTab onTabChange={mockOnTabChange} />);

      expect(screen.getByText('200')).toBeInTheDocument();
      expect(screen.getByText('8.2')).toBeInTheDocument();
      expect(screen.getByText('10')).toBeInTheDocument();
    });

    test('handles missing context gracefully', () => {
      const minimalContext = {
        stats: { total: 0, avgRating: 'N/A' },
        counts: {},
      };

      useStaff.mockReturnValue(minimalContext);

      render(<DashboardTab onTabChange={mockOnTabChange} />);

      // Check for "0" in Total Games stat (using getAllByText to verify it's present)
      const zeroElements = screen.getAllByText('0');
      expect(zeroElements.length).toBeGreaterThan(0);

      expect(screen.getByText('N/A')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    test('quick action buttons are keyboard accessible', async () => {
      const user = userEvent.setup();

      render(<DashboardTab onTabChange={mockOnTabChange} />);

      const addGamesButton = screen.getByText('📥 Add New Games').closest('button');

      addGamesButton.focus();
      expect(addGamesButton).toHaveFocus();

      await user.keyboard('{Enter}');
      expect(mockOnTabChange).toHaveBeenCalledWith('add-games');
    });

    test('all action buttons have descriptive text', () => {
      render(<DashboardTab onTabChange={mockOnTabChange} />);

      expect(screen.getByText(/Import games from BoardGameGeek/)).toBeInTheDocument();
      expect(screen.getByText(/Browse, edit, and organize/)).toBeInTheDocument();
      expect(screen.getByText(/Categorize games and manage/)).toBeInTheDocument();
      expect(screen.getByText(/System maintenance, debugging/)).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    test('handles console errors gracefully during health check', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      apiClient.getHealthCheck.mockRejectedValue(new Error('Network failure'));
      apiClient.getDbHealthCheck.mockRejectedValue(new Error('Network failure'));

      render(<DashboardTab onTabChange={mockOnTabChange} />);

      await waitFor(() => {
        expect(consoleErrorSpy).toHaveBeenCalledWith(
          'Failed to load health status:',
          expect.any(Error)
        );
      });

      consoleErrorSpy.mockRestore();
    });

    test('component remains functional after health check errors', async () => {
      const user = userEvent.setup();

      apiClient.getHealthCheck.mockRejectedValue(new Error('Error'));
      apiClient.getDbHealthCheck.mockRejectedValue(new Error('Error'));

      render(<DashboardTab onTabChange={mockOnTabChange} />);

      await waitFor(() => {
        expect(screen.getByText('System Status Unknown')).toBeInTheDocument();
      });

      // Quick actions should still work
      const addGamesButton = screen.getByText('📥 Add New Games').closest('button');
      await user.click(addGamesButton);

      expect(mockOnTabChange).toHaveBeenCalledWith('add-games');
    });
  });
});
