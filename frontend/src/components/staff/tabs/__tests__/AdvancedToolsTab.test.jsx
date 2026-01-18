/**
 * AdvancedToolsTab tests - System maintenance, debugging, and data export
 */
import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AdvancedToolsTab } from '../AdvancedToolsTab';

// Mock useStaff hook
vi.mock('../../../../context/StaffContext', () => ({
  useStaff: vi.fn(),
}));

// Mock AdminToolsPanel component
vi.mock('../../AdminToolsPanel', () => ({
  AdminToolsPanel: vi.fn(({ onToast, onLibraryReload }) => (
    <div data-testid="admin-tools-panel">
      <button onClick={() => onToast('Test toast', 'success')}>Test Toast</button>
      <button onClick={() => onLibraryReload()}>Reload Library</button>
    </div>
  )),
}));

import { useStaff } from '../../../../context/StaffContext';
import { AdminToolsPanel } from '../../AdminToolsPanel';

describe('AdvancedToolsTab', () => {
  const mockShowToast = vi.fn();
  const mockLoadLibrary = vi.fn();

  const defaultStaffContext = {
    showToast: mockShowToast,
    loadLibrary: mockLoadLibrary,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    useStaff.mockReturnValue(defaultStaffContext);
  });

  describe('Rendering', () => {
    test('renders warning banner', () => {
      render(<AdvancedToolsTab />);

      expect(screen.getByText('⚠️')).toBeInTheDocument();
      expect(screen.getByText('Advanced System Tools')).toBeInTheDocument();
      expect(screen.getByText(/These tools are designed for system maintenance/)).toBeInTheDocument();
      expect(screen.getByText('Use with caution.')).toBeInTheDocument();
    });

    test('renders system maintenance section', () => {
      render(<AdvancedToolsTab />);

      expect(screen.getByText('System Maintenance')).toBeInTheDocument();
      expect(screen.getByText('Critical operations for database integrity and data management')).toBeInTheDocument();
    });

    test('renders debug & monitoring section', () => {
      render(<AdvancedToolsTab />);

      expect(screen.getByText('Debug & Monitoring')).toBeInTheDocument();
      expect(screen.getByText('System health checks and performance diagnostics')).toBeInTheDocument();
    });

    test('renders help & documentation section', () => {
      render(<AdvancedToolsTab />);

      expect(screen.getByText('📖 Need Help?')).toBeInTheDocument();
    });
  });

  describe('System Maintenance Cards', () => {
    test('renders re-import all games card', () => {
      render(<AdvancedToolsTab />);

      expect(screen.getByText('Re-import All Games')).toBeInTheDocument();
      expect(screen.getByText(/Fetches latest BoardGameGeek data/)).toBeInTheDocument();
      // "several minutes" appears in both warning banner and this card
      expect(screen.getAllByText(/several minutes/).length).toBeGreaterThan(0);
    });

    test('shows re-import all games details', () => {
      render(<AdvancedToolsTab />);

      // "Use when:" appears in all 3 maintenance cards
      expect(screen.getAllByText(/Use when:/).length).toBeGreaterThan(0);
      expect(screen.getByText(/BGG data needs refreshing/)).toBeInTheDocument();
      expect(screen.getByText(/~2-5 minutes for 100 games/)).toBeInTheDocument();
      expect(screen.getByText(/existing manual data is preserved/)).toBeInTheDocument();
    });

    test('renders fix database sequence card', () => {
      render(<AdvancedToolsTab />);

      expect(screen.getByText('Fix Database Sequence')).toBeInTheDocument();
      expect(screen.getByText(/Resets the PostgreSQL ID sequence/)).toBeInTheDocument();
      expect(screen.getByText(/duplicate key/)).toBeInTheDocument();
    });

    test('shows fix database sequence details', () => {
      render(<AdvancedToolsTab />);

      expect(screen.getByText(/duplicate primary key/)).toBeInTheDocument();
      // "Instant" appears multiple times (duration in multiple cards)
      expect(screen.getAllByText(/Instant/).length).toBeGreaterThan(0);
      expect(screen.getByText(/only resets ID counter/)).toBeInTheDocument();
    });

    test('renders export games CSV card', () => {
      render(<AdvancedToolsTab />);

      expect(screen.getByText('Export Games CSV')).toBeInTheDocument();
      expect(screen.getByText(/Downloads complete game database as CSV/)).toBeInTheDocument();
      expect(screen.getByText(/timestamped filename/)).toBeInTheDocument();
    });

    test('shows export games CSV details', () => {
      render(<AdvancedToolsTab />);

      expect(screen.getByText(/backups, analysis, or migration/)).toBeInTheDocument();
      // "read-only operation" contains "Safe:" which appears multiple times
      expect(screen.getByText(/read-only operation/)).toBeInTheDocument();
    });
  });

  describe('Debug & Monitoring Cards', () => {
    test('renders system health card', () => {
      render(<AdvancedToolsTab />);

      expect(screen.getByText('System Health')).toBeInTheDocument();
      expect(screen.getByText(/Check API and database connectivity/)).toBeInTheDocument();
    });

    test('renders performance stats card', () => {
      render(<AdvancedToolsTab />);

      expect(screen.getByText('Performance Stats')).toBeInTheDocument();
      expect(screen.getByText(/View request timing, slow query tracking/)).toBeInTheDocument();
    });

    test('renders database info card', () => {
      render(<AdvancedToolsTab />);

      expect(screen.getByText('Database Info')).toBeInTheDocument();
      expect(screen.getByText(/Inspect database structure/)).toBeInTheDocument();
    });

    test('renders BGG categories card', () => {
      render(<AdvancedToolsTab />);

      expect(screen.getByText('BGG Categories')).toBeInTheDocument();
      expect(screen.getByText(/View all unique BoardGameGeek categories/)).toBeInTheDocument();
    });

    test('shows debug tip', () => {
      render(<AdvancedToolsTab />);

      // Check for debug tip text (using more specific text to avoid duplicates)
      expect(screen.getByText(/All debug data can be downloaded as JSON files/)).toBeInTheDocument();
    });
  });

  describe('Help Documentation', () => {
    test('renders performance issues help', () => {
      render(<AdvancedToolsTab />);

      expect(screen.getByText(/Performance issues?/)).toBeInTheDocument();
      expect(screen.getByText(/Check Performance Stats to identify slow queries/)).toBeInTheDocument();
    });

    test('renders database errors help', () => {
      render(<AdvancedToolsTab />);

      expect(screen.getByText(/Database errors?/)).toBeInTheDocument();
      expect(screen.getByText(/Try Fix Database Sequence first/)).toBeInTheDocument();
    });

    test('renders outdated game data help', () => {
      render(<AdvancedToolsTab />);

      expect(screen.getByText(/Outdated game data?/)).toBeInTheDocument();
      expect(screen.getByText(/Use Re-import All Games to refresh from BoardGameGeek/)).toBeInTheDocument();
    });

    test('renders regular backups help', () => {
      render(<AdvancedToolsTab />);

      expect(screen.getByText(/Regular backups:/)).toBeInTheDocument();
      expect(screen.getByText(/Export Games CSV monthly/)).toBeInTheDocument();
    });
  });

  describe('AdminToolsPanel Integration', () => {
    test('renders AdminToolsPanel component', () => {
      render(<AdvancedToolsTab />);

      expect(screen.getByTestId('admin-tools-panel')).toBeInTheDocument();
    });

    test('passes showToast to AdminToolsPanel', async () => {
      const user = require('@testing-library/user-event').default.setup();
      render(<AdvancedToolsTab />);

      const toastButton = screen.getByText('Test Toast');
      await user.click(toastButton);

      expect(mockShowToast).toHaveBeenCalledWith('Test toast', 'success');
    });

    test('passes loadLibrary to AdminToolsPanel', async () => {
      const user = require('@testing-library/user-event').default.setup();
      render(<AdvancedToolsTab />);

      const reloadButton = screen.getByText('Reload Library');
      await user.click(reloadButton);

      expect(mockLoadLibrary).toHaveBeenCalled();
    });

    test('passes correct props to AdminToolsPanel', () => {
      render(<AdvancedToolsTab />);

      // Check that AdminToolsPanel was called with correct props
      // The second parameter (context) is undefined in React function components
      expect(AdminToolsPanel).toHaveBeenCalled();
      const callArgs = AdminToolsPanel.mock.calls[0][0];
      expect(callArgs).toHaveProperty('onToast', mockShowToast);
      expect(callArgs).toHaveProperty('onLibraryReload', mockLoadLibrary);
    });
  });

  describe('Context Integration', () => {
    test('uses showToast from StaffContext', () => {
      render(<AdvancedToolsTab />);

      expect(useStaff).toHaveBeenCalled();
    });

    test('uses loadLibrary from StaffContext', () => {
      render(<AdvancedToolsTab />);

      expect(useStaff).toHaveBeenCalled();
    });
  });

  describe('Visual Hierarchy', () => {
    test('displays sections in correct order', () => {
      render(<AdvancedToolsTab />);

      const sections = screen.getAllByRole('heading', { level: 2 });
      expect(sections[0]).toHaveTextContent('System Maintenance');
      expect(sections[1]).toHaveTextContent('Debug & Monitoring');
    });

    test('uses appropriate warning colors for maintenance cards', () => {
      const { container } = render(<AdvancedToolsTab />);

      // Re-import card should have red styling (most critical)
      const reimportCard = container.querySelector('.border-red-200');
      expect(reimportCard).toBeInTheDocument();

      // Fix sequence card should have yellow styling (less critical)
      const fixCard = container.querySelector('.border-yellow-200');
      expect(fixCard).toBeInTheDocument();

      // Export card should have teal styling (safe operation)
      const exportCard = container.querySelector('.border-teal-200');
      expect(exportCard).toBeInTheDocument();
    });

    test('uses consistent styling for debug cards', () => {
      const { container } = render(<AdvancedToolsTab />);

      // All debug cards should have blue styling
      const blueCards = container.querySelectorAll('.border-blue-200');
      expect(blueCards.length).toBe(4); // System Health, Performance Stats, Database Info, BGG Categories
    });
  });

  describe('Accessibility', () => {
    test('has descriptive section headings', () => {
      render(<AdvancedToolsTab />);

      expect(screen.getByRole('heading', { name: 'System Maintenance' })).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: 'Debug & Monitoring' })).toBeInTheDocument();
    });

    test('uses semantic HTML structure', () => {
      const { container } = render(<AdvancedToolsTab />);

      // Check for proper heading hierarchy
      const h2Headings = container.querySelectorAll('h2');
      expect(h2Headings.length).toBeGreaterThan(0);

      const h3Headings = container.querySelectorAll('h3');
      expect(h3Headings.length).toBeGreaterThan(0);
    });
  });
});
