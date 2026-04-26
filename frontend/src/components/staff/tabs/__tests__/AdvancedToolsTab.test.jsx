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

    test('renders help & documentation section', () => {
      render(<AdvancedToolsTab />);

      expect(screen.getByText('📖 Need Help?')).toBeInTheDocument();
    });

    test('renders AdminToolsPanel', () => {
      render(<AdvancedToolsTab />);

      expect(screen.getByTestId('admin-tools-panel')).toBeInTheDocument();
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

      expect(AdminToolsPanel).toHaveBeenCalled();
      const callArgs = AdminToolsPanel.mock.calls[0][0];
      expect(callArgs).toHaveProperty('onToast', mockShowToast);
      expect(callArgs).toHaveProperty('onLibraryReload', mockLoadLibrary);
    });
  });

  describe('Context Integration', () => {
    test('uses showToast and loadLibrary from StaffContext', () => {
      render(<AdvancedToolsTab />);

      expect(useStaff).toHaveBeenCalled();
    });
  });

  describe('Accessibility', () => {
    test('uses semantic HTML structure', () => {
      const { container } = render(<AdvancedToolsTab />);

      const h3Headings = container.querySelectorAll('h3');
      expect(h3Headings.length).toBeGreaterThan(0);
    });
  });
});
