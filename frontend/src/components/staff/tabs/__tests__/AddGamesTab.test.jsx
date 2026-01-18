/**
 * AddGamesTab tests - Game addition interface with BGG import, bulk import, and manual entry
 */
import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AddGamesTab } from '../AddGamesTab';

// Mock useStaff hook
vi.mock('../../../../context/StaffContext', () => ({
  useStaff: vi.fn(),
}));

// Mock child components
vi.mock('../../ManualGameEntryPanel', () => ({
  ManualGameEntryPanel: vi.fn(({ onSuccess, onToast }) => (
    <div data-testid="manual-game-entry-panel">
      <button onClick={() => onSuccess()}>Manual Submit</button>
      <button onClick={() => onToast('Test message', 'success')}>Test Toast</button>
    </div>
  )),
}));

vi.mock('../../BulkPanels', () => ({
  BulkImportPanel: vi.fn(({ value, onChange, onSubmit }) => (
    <div data-testid="bulk-import-panel">
      <textarea
        data-testid="bulk-import-textarea"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      <button onClick={onSubmit}>Bulk Submit</button>
    </div>
  )),
}));

import { useStaff } from '../../../../context/StaffContext';

describe('AddGamesTab', () => {
  const mockHandleAddGame = vi.fn();
  const mockSetBggIdInput = vi.fn();
  const mockSetCsvImportText = vi.fn();
  const mockDoBulkImport = vi.fn();
  const mockShowToast = vi.fn();

  const defaultStaffContext = {
    bggIdInput: '',
    setBggIdInput: mockSetBggIdInput,
    handleAddGame: mockHandleAddGame,
    csvImportText: '',
    setCsvImportText: mockSetCsvImportText,
    doBulkImport: mockDoBulkImport,
    showToast: mockShowToast,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    useStaff.mockReturnValue(defaultStaffContext);
  });

  describe('Rendering', () => {
    test('renders all three sections', () => {
      render(<AddGamesTab />);

      // BGG ID section
      expect(screen.getByText('Add Game by BGG ID')).toBeInTheDocument();
      expect(screen.getByText(/Recommended method/)).toBeInTheDocument();
      expect(screen.getByText('Primary Method')).toBeInTheDocument();

      // Bulk import section
      expect(screen.getByText('Bulk Import from CSV')).toBeInTheDocument();

      // Manual entry section
      expect(screen.getByText('Manual Game Entry')).toBeInTheDocument();
      expect(screen.getByText('Fallback Method')).toBeInTheDocument();
    });

    test('renders BGG ID instructions', () => {
      render(<AddGamesTab />);

      expect(screen.getByText('How to find BGG IDs:')).toBeInTheDocument();
      expect(screen.getByText(/boardgamegeek.com/)).toBeInTheDocument();
      expect(screen.getByText(/Search for your game/)).toBeInTheDocument();
    });

    test('renders BGG ID features list', () => {
      render(<AddGamesTab />);

      expect(screen.getByText(/Automatic retry with exponential backoff/)).toBeInTheDocument();
      expect(screen.getByText(/Fetches all game data/)).toBeInTheDocument();
      expect(screen.getByText(/Handles BGG API rate limiting/)).toBeInTheDocument();
    });

    test('renders bulk import warning', () => {
      render(<AddGamesTab />);

      expect(screen.getByText(/Bulk imports can take several minutes/)).toBeInTheDocument();
    });

    test('renders child components', () => {
      render(<AddGamesTab />);

      expect(screen.getByTestId('bulk-import-panel')).toBeInTheDocument();
      expect(screen.getByTestId('manual-game-entry-panel')).toBeInTheDocument();
    });
  });

  describe('BGG ID Input', () => {
    test('displays BGG ID input with placeholder', () => {
      render(<AddGamesTab />);

      const input = screen.getByPlaceholderText(/Enter BoardGameGeek ID/);
      expect(input).toBeInTheDocument();
      expect(input).toHaveValue('');
    });

    test('displays current BGG ID input value from context', () => {
      useStaff.mockReturnValue({
        ...defaultStaffContext,
        bggIdInput: '30549',
      });

      render(<AddGamesTab />);

      const input = screen.getByPlaceholderText(/Enter BoardGameGeek ID/);
      expect(input).toHaveValue('30549');
    });

    test('calls setBggIdInput when input changes', async () => {
      const user = userEvent.setup();
      render(<AddGamesTab />);

      const input = screen.getByPlaceholderText(/Enter BoardGameGeek ID/);
      await user.type(input, '12345');

      // Should be called for each character typed (5 times)
      expect(mockSetBggIdInput).toHaveBeenCalled();
      expect(mockSetBggIdInput).toHaveBeenCalledTimes(5);
      // Each call receives a single character
      expect(mockSetBggIdInput).toHaveBeenCalledWith('1');
      expect(mockSetBggIdInput).toHaveBeenCalledWith('2');
      expect(mockSetBggIdInput).toHaveBeenCalledWith('3');
      expect(mockSetBggIdInput).toHaveBeenCalledWith('4');
      expect(mockSetBggIdInput).toHaveBeenCalledWith('5');
    });

    test('calls handleAddGame when Enter key is pressed', async () => {
      const user = userEvent.setup();
      render(<AddGamesTab />);

      const input = screen.getByPlaceholderText(/Enter BoardGameGeek ID/);
      await user.type(input, '{Enter}');

      expect(mockHandleAddGame).toHaveBeenCalledTimes(1);
    });

    test('does not call handleAddGame on other keys', async () => {
      const user = userEvent.setup();
      render(<AddGamesTab />);

      const input = screen.getByPlaceholderText(/Enter BoardGameGeek ID/);
      await user.type(input, 'abc');

      expect(mockHandleAddGame).not.toHaveBeenCalled();
    });
  });

  describe('Add Game Button', () => {
    test('renders Add Game button', () => {
      render(<AddGamesTab />);

      const button = screen.getByRole('button', { name: 'Add Game' });
      expect(button).toBeInTheDocument();
    });

    test('calls handleAddGame when button clicked', async () => {
      const user = userEvent.setup();
      render(<AddGamesTab />);

      const button = screen.getByRole('button', { name: 'Add Game' });
      await user.click(button);

      expect(mockHandleAddGame).toHaveBeenCalledTimes(1);
    });

    test('can add game with BGG ID via button', async () => {
      const user = userEvent.setup();
      render(<AddGamesTab />);

      const input = screen.getByPlaceholderText(/Enter BoardGameGeek ID/);
      await user.type(input, '30549');

      const button = screen.getByRole('button', { name: 'Add Game' });
      await user.click(button);

      expect(mockSetBggIdInput).toHaveBeenCalled();
      expect(mockHandleAddGame).toHaveBeenCalledTimes(1);
    });
  });

  describe('Bulk Import Integration', () => {
    test('passes correct props to BulkImportPanel', () => {
      render(<AddGamesTab />);

      const textarea = screen.getByTestId('bulk-import-textarea');
      expect(textarea).toHaveValue('');
    });

    test('displays current CSV import text from context', () => {
      useStaff.mockReturnValue({
        ...defaultStaffContext,
        csvImportText: '12345\n67890',
      });

      render(<AddGamesTab />);

      const textarea = screen.getByTestId('bulk-import-textarea');
      expect(textarea).toHaveValue('12345\n67890');
    });

    test('calls setCsvImportText when bulk import text changes', async () => {
      const user = userEvent.setup();
      render(<AddGamesTab />);

      const textarea = screen.getByTestId('bulk-import-textarea');
      await user.type(textarea, '12345');

      expect(mockSetCsvImportText).toHaveBeenCalled();
    });

    test('calls doBulkImport when bulk submit clicked', async () => {
      const user = userEvent.setup();
      render(<AddGamesTab />);

      const button = screen.getByText('Bulk Submit');
      await user.click(button);

      expect(mockDoBulkImport).toHaveBeenCalledTimes(1);
    });
  });

  describe('Manual Entry Integration', () => {
    test('passes showToast to ManualGameEntryPanel', async () => {
      const user = userEvent.setup();
      render(<AddGamesTab />);

      const toastButton = screen.getByText('Test Toast');
      await user.click(toastButton);

      expect(mockShowToast).toHaveBeenCalledWith('Test message', 'success');
    });

    test('reloads page on manual entry success', async () => {
      const user = userEvent.setup();
      const reloadMock = vi.fn();

      // Mock window.location.reload using Object.defineProperty
      Object.defineProperty(window, 'location', {
        value: { reload: reloadMock },
        writable: true,
      });

      render(<AddGamesTab />);

      const submitButton = screen.getByText('Manual Submit');
      await user.click(submitButton);

      expect(reloadMock).toHaveBeenCalledTimes(1);
    });
  });

  describe('Context Integration', () => {
    test('uses all required context values', () => {
      render(<AddGamesTab />);

      expect(useStaff).toHaveBeenCalled();
    });

    test('updates when context bggIdInput changes', () => {
      const { rerender } = render(<AddGamesTab />);

      let input = screen.getByPlaceholderText(/Enter BoardGameGeek ID/);
      expect(input).toHaveValue('');

      // Update mock return value
      useStaff.mockReturnValue({
        ...defaultStaffContext,
        bggIdInput: '99999',
      });

      rerender(<AddGamesTab />);

      input = screen.getByPlaceholderText(/Enter BoardGameGeek ID/);
      expect(input).toHaveValue('99999');
    });

    test('updates when context csvImportText changes', () => {
      const { rerender } = render(<AddGamesTab />);

      let textarea = screen.getByTestId('bulk-import-textarea');
      expect(textarea).toHaveValue('');

      // Update mock return value
      useStaff.mockReturnValue({
        ...defaultStaffContext,
        csvImportText: 'new csv data',
      });

      rerender(<AddGamesTab />);

      textarea = screen.getByTestId('bulk-import-textarea');
      expect(textarea).toHaveValue('new csv data');
    });
  });

  describe('Accessibility', () => {
    test('BGG ID input is keyboard accessible', async () => {
      const user = userEvent.setup();
      render(<AddGamesTab />);

      const input = screen.getByPlaceholderText(/Enter BoardGameGeek ID/);

      input.focus();
      expect(input).toHaveFocus();

      await user.keyboard('12345{Enter}');

      expect(mockHandleAddGame).toHaveBeenCalled();
    });

    test('Add Game button is keyboard accessible', async () => {
      const user = userEvent.setup();
      render(<AddGamesTab />);

      const button = screen.getByRole('button', { name: 'Add Game' });

      button.focus();
      expect(button).toHaveFocus();

      await user.keyboard('{Enter}');

      expect(mockHandleAddGame).toHaveBeenCalled();
    });

    test('has clear section headings', () => {
      render(<AddGamesTab />);

      expect(screen.getByRole('heading', { name: 'Add Game by BGG ID' })).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: 'Bulk Import from CSV' })).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: 'Manual Game Entry' })).toBeInTheDocument();
    });

    test('external link has proper attributes', () => {
      render(<AddGamesTab />);

      const link = screen.getByRole('link', { name: /boardgamegeek.com/ });
      expect(link).toHaveAttribute('target', '_blank');
      expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    });
  });

  describe('Visual Hierarchy', () => {
    test('displays primary method badge on BGG ID section', () => {
      render(<AddGamesTab />);

      expect(screen.getByText('Primary Method')).toBeInTheDocument();
    });

    test('displays fallback method badge on manual entry section', () => {
      render(<AddGamesTab />);

      expect(screen.getByText('Fallback Method')).toBeInTheDocument();
    });

    test('shows recommended method indication', () => {
      render(<AddGamesTab />);

      expect(screen.getByText(/Recommended method/)).toBeInTheDocument();
    });

    test('shows fallback method warning', () => {
      render(<AddGamesTab />);

      expect(screen.getByText(/Use only when BGG import is unavailable/)).toBeInTheDocument();
    });
  });
});
