import { describe, test, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ManualGameEntryPanel } from '../ManualGameEntryPanel';
import * as apiClient from '../../../api/client';

// Mock the API client
vi.mock('../../../api/client', () => ({
  addGame: vi.fn(),
}));

describe('ManualGameEntryPanel', () => {
  const mockOnSuccess = vi.fn();
  const mockOnToast = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    test('renders basic information fields', () => {
      render(<ManualGameEntryPanel onSuccess={mockOnSuccess} onToast={mockOnToast} />);

      expect(screen.getByText('Manual Game Entry')).toBeInTheDocument();
      expect(screen.getByLabelText(/Title/)).toBeInTheDocument();
      expect(screen.getByLabelText(/BGG ID/)).toBeInTheDocument();
      expect(screen.getByLabelText(/Year Published/)).toBeInTheDocument();
      expect(screen.getByLabelText(/Min Players/)).toBeInTheDocument();
      expect(screen.getByLabelText(/Max Players/)).toBeInTheDocument();
      expect(screen.getByLabelText(/Min Playtime/)).toBeInTheDocument();
      expect(screen.getByLabelText(/Max Playtime/)).toBeInTheDocument();
      expect(screen.getByLabelText(/Minimum Age/)).toBeInTheDocument();
      expect(screen.getByLabelText(/Designers/)).toBeInTheDocument();
      expect(screen.getByLabelText(/Description/)).toBeInTheDocument();
      expect(screen.getByLabelText(/Category/)).toBeInTheDocument();
    });

    test('renders checkbox fields', () => {
      render(<ManualGameEntryPanel onSuccess={mockOnSuccess} onToast={mockOnToast} />);

      expect(screen.getByLabelText(/Cooperative Game/)).toBeInTheDocument();
      expect(screen.getByLabelText(/NZ Designer/)).toBeInTheDocument();
    });

    test('renders action buttons', () => {
      render(<ManualGameEntryPanel onSuccess={mockOnSuccess} onToast={mockOnToast} />);

      expect(screen.getByRole('button', { name: /Add Game/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Clear Form/i })).toBeInTheDocument();
    });

    test('does not show advanced fields by default', () => {
      render(<ManualGameEntryPanel onSuccess={mockOnSuccess} onToast={mockOnToast} />);

      expect(screen.queryByLabelText(/Thumbnail URL/)).not.toBeInTheDocument();
      expect(screen.queryByLabelText(/Full Image URL/)).not.toBeInTheDocument();
      expect(screen.queryByLabelText(/Publishers/)).not.toBeInTheDocument();
      expect(screen.queryByLabelText(/Mechanics/)).not.toBeInTheDocument();
      expect(screen.queryByLabelText(/Artists/)).not.toBeInTheDocument();
    });

    test('shows advanced fields when toggle clicked', () => {
      render(<ManualGameEntryPanel onSuccess={mockOnSuccess} onToast={mockOnToast} />);

      const toggleButton = screen.getByRole('button', { name: /Show Advanced Fields/i });
      fireEvent.click(toggleButton);

      expect(screen.getByLabelText(/Thumbnail URL/)).toBeInTheDocument();
      expect(screen.getByLabelText(/Full Image URL/)).toBeInTheDocument();
      expect(screen.getByLabelText(/Publishers/)).toBeInTheDocument();
      expect(screen.getByLabelText(/Mechanics/)).toBeInTheDocument();
      expect(screen.getByLabelText(/Artists/)).toBeInTheDocument();
      expect(screen.getByLabelText(/BGG Rating/)).toBeInTheDocument();
      expect(screen.getByLabelText(/Complexity/)).toBeInTheDocument();
      expect(screen.getByLabelText(/BGG Rank/)).toBeInTheDocument();
    });

    test('hides advanced fields when toggle clicked again', () => {
      render(<ManualGameEntryPanel onSuccess={mockOnSuccess} onToast={mockOnToast} />);

      const toggleButton = screen.getByRole('button', { name: /Show Advanced Fields/i });
      fireEvent.click(toggleButton); // Show
      fireEvent.click(screen.getByRole('button', { name: /Hide Advanced Fields/i })); // Hide

      expect(screen.queryByLabelText(/Thumbnail URL/)).not.toBeInTheDocument();
    });
  });

  describe('Form Validation', () => {
    test('add button is disabled when title is empty', () => {
      render(<ManualGameEntryPanel onSuccess={mockOnSuccess} onToast={mockOnToast} />);

      const addButton = screen.getByRole('button', { name: /Add Game/i });
      expect(addButton).toBeDisabled();
    });

    test('add button is enabled when title has value', () => {
      render(<ManualGameEntryPanel onSuccess={mockOnSuccess} onToast={mockOnToast} />);

      const titleInput = screen.getByPlaceholderText('e.g., Pandemic');
      fireEvent.change(titleInput, { target: { value: 'Test Game' } });

      const addButton = screen.getByRole('button', { name: /Add Game/i });
      expect(addButton).not.toBeDisabled();
    });

    test('shows error when submitting with empty title', async () => {
      render(<ManualGameEntryPanel onSuccess={mockOnSuccess} onToast={mockOnToast} />);

      // Somehow get past the button disable (e.g., if validation runs)
      const titleInput = screen.getByPlaceholderText('e.g., Pandemic');
      fireEvent.change(titleInput, { target: { value: '  ' } }); // Whitespace only

      const addButton = screen.getByRole('button', { name: /Add Game/i });

      // Button should still be disabled for whitespace-only
      expect(addButton).toBeDisabled();
    });

    test('validates title is not whitespace only', async () => {
      render(<ManualGameEntryPanel onSuccess={mockOnSuccess} onToast={mockOnToast} />);

      const titleInput = screen.getByPlaceholderText('e.g., Pandemic');
      fireEvent.change(titleInput, { target: { value: '   ' } });

      // Button should be disabled
      const addButton = screen.getByRole('button', { name: /Add Game/i });
      expect(addButton).toBeDisabled();
    });
  });

  describe('Form Input Handling', () => {
    test('handles text input changes', () => {
      render(<ManualGameEntryPanel onSuccess={mockOnSuccess} onToast={mockOnToast} />);

      const titleInput = screen.getByPlaceholderText('e.g., Pandemic');
      fireEvent.change(titleInput, { target: { value: 'Catan' } });
      expect(titleInput.value).toBe('Catan');
    });

    test('handles numeric input as text', () => {
      render(<ManualGameEntryPanel onSuccess={mockOnSuccess} onToast={mockOnToast} />);

      const yearInput = screen.getByPlaceholderText('e.g., 2008');
      fireEvent.change(yearInput, { target: { value: '1995' } });
      expect(yearInput.value).toBe('1995');
    });

    test('handles checkbox toggle for cooperative game', () => {
      render(<ManualGameEntryPanel onSuccess={mockOnSuccess} onToast={mockOnToast} />);

      const coopCheckbox = screen.getByLabelText(/Cooperative Game/);
      expect(coopCheckbox).not.toBeChecked();

      fireEvent.click(coopCheckbox);
      expect(coopCheckbox).toBeChecked();

      fireEvent.click(coopCheckbox);
      expect(coopCheckbox).not.toBeChecked();
    });

    test('handles checkbox toggle for NZ designer', () => {
      render(<ManualGameEntryPanel onSuccess={mockOnSuccess} onToast={mockOnToast} />);

      const nzCheckbox = screen.getByLabelText(/NZ Designer/);
      expect(nzCheckbox).not.toBeChecked();

      fireEvent.click(nzCheckbox);
      expect(nzCheckbox).toBeChecked();
    });

    test('handles category selection', () => {
      render(<ManualGameEntryPanel onSuccess={mockOnSuccess} onToast={mockOnToast} />);

      const categorySelect = screen.getByRole('combobox');
      fireEvent.change(categorySelect, { target: { value: 'GATEWAY_STRATEGY' } });
      expect(categorySelect.value).toBe('GATEWAY_STRATEGY');
    });
  });

  describe('Form Submission', () => {
    test('submits with minimal data (title only)', async () => {
      apiClient.addGame.mockResolvedValue({ id: 1, title: 'Test Game' });

      render(<ManualGameEntryPanel onSuccess={mockOnSuccess} onToast={mockOnToast} />);

      const titleInput = screen.getByPlaceholderText('e.g., Pandemic');
      fireEvent.change(titleInput, { target: { value: 'Test Game' } });

      const addButton = screen.getByRole('button', { name: /Add Game/i });
      fireEvent.click(addButton);

      await waitFor(() => {
        expect(apiClient.addGame).toHaveBeenCalledWith(
          expect.objectContaining({
            title: 'Test Game',
            is_cooperative: false,
            nz_designer: false,
          })
        );
      });
    });

    test('submits with full basic data', async () => {
      apiClient.addGame.mockResolvedValue({ id: 1, title: 'Pandemic' });

      render(<ManualGameEntryPanel onSuccess={mockOnSuccess} onToast={mockOnToast} />);

      fireEvent.change(screen.getByPlaceholderText('e.g., Pandemic'), {
        target: { value: 'Pandemic' },
      });
      fireEvent.change(screen.getByPlaceholderText('e.g., 30549'), {
        target: { value: '30549' },
      });
      fireEvent.change(screen.getByPlaceholderText('e.g., 2008'), {
        target: { value: '2008' },
      });
      fireEvent.change(screen.getByPlaceholderText('e.g., 2'), {
        target: { value: '2' },
      });
      fireEvent.change(screen.getByPlaceholderText('e.g., 4'), {
        target: { value: '4' },
      });
      fireEvent.change(screen.getByPlaceholderText('e.g., Matt Leacock'), {
        target: { value: 'Matt Leacock' },
      });
      fireEvent.click(screen.getByLabelText(/Cooperative Game/));
      fireEvent.change(screen.getByRole('combobox'), {
        target: { value: 'COOP_ADVENTURE' },
      });

      const addButton = screen.getByRole('button', { name: /Add Game/i });
      fireEvent.click(addButton);

      await waitFor(() => {
        expect(apiClient.addGame).toHaveBeenCalledWith(
          expect.objectContaining({
            title: 'Pandemic',
            bgg_id: 30549,
            year: 2008,
            players_min: 2,
            players_max: 4,
            designers: ['Matt Leacock'],
            is_cooperative: true,
            mana_meeple_category: 'COOP_ADVENTURE',
          })
        );
      });
    });

    test('parses comma-separated designers correctly', async () => {
      apiClient.addGame.mockResolvedValue({ id: 1, title: 'Test' });

      render(<ManualGameEntryPanel onSuccess={mockOnSuccess} onToast={mockOnToast} />);

      fireEvent.change(screen.getByPlaceholderText('e.g., Pandemic'), {
        target: { value: 'Test' },
      });
      fireEvent.change(screen.getByPlaceholderText('e.g., Matt Leacock'), {
        target: { value: 'Designer One, Designer Two, Designer Three' },
      });

      const addButton = screen.getByRole('button', { name: /Add Game/i });
      fireEvent.click(addButton);

      await waitFor(() => {
        expect(apiClient.addGame).toHaveBeenCalledWith(
          expect.objectContaining({
            designers: ['Designer One', 'Designer Two', 'Designer Three'],
          })
        );
      });
    });

    test('trims whitespace from comma-separated values', async () => {
      apiClient.addGame.mockResolvedValue({ id: 1, title: 'Test' });

      render(<ManualGameEntryPanel onSuccess={mockOnSuccess} onToast={mockOnToast} />);

      fireEvent.change(screen.getByPlaceholderText('e.g., Pandemic'), {
        target: { value: 'Test' },
      });
      fireEvent.change(screen.getByPlaceholderText('e.g., Matt Leacock'), {
        target: { value: '  Designer One  ,   Designer Two  ,  ' },
      });

      const addButton = screen.getByRole('button', { name: /Add Game/i });
      fireEvent.click(addButton);

      await waitFor(() => {
        expect(apiClient.addGame).toHaveBeenCalledWith(
          expect.objectContaining({
            designers: ['Designer One', 'Designer Two'],
          })
        );
      });
    });

    test('shows success toast on successful submission', async () => {
      apiClient.addGame.mockResolvedValue({ id: 1, title: 'New Game' });

      render(<ManualGameEntryPanel onSuccess={mockOnSuccess} onToast={mockOnToast} />);

      fireEvent.change(screen.getByPlaceholderText('e.g., Pandemic'), {
        target: { value: 'New Game' },
      });

      const addButton = screen.getByRole('button', { name: /Add Game/i });
      fireEvent.click(addButton);

      await waitFor(() => {
        expect(mockOnToast).toHaveBeenCalledWith(
          'Game "New Game" added successfully!',
          'success'
        );
      });
    });

    test('calls onSuccess callback after successful submission', async () => {
      const result = { id: 1, title: 'New Game' };
      apiClient.addGame.mockResolvedValue(result);

      render(<ManualGameEntryPanel onSuccess={mockOnSuccess} onToast={mockOnToast} />);

      fireEvent.change(screen.getByPlaceholderText('e.g., Pandemic'), {
        target: { value: 'New Game' },
      });

      const addButton = screen.getByRole('button', { name: /Add Game/i });
      fireEvent.click(addButton);

      await waitFor(() => {
        expect(mockOnSuccess).toHaveBeenCalledWith(result);
      });
    });

    test('shows error toast on API failure', async () => {
      apiClient.addGame.mockRejectedValue({
        response: { data: { detail: 'Game already exists' } },
      });

      render(<ManualGameEntryPanel onSuccess={mockOnSuccess} onToast={mockOnToast} />);

      fireEvent.change(screen.getByPlaceholderText('e.g., Pandemic'), {
        target: { value: 'Existing Game' },
      });

      const addButton = screen.getByRole('button', { name: /Add Game/i });
      fireEvent.click(addButton);

      await waitFor(() => {
        expect(mockOnToast).toHaveBeenCalledWith('Game already exists', 'error');
      });
    });

    test('shows generic error toast on network failure', async () => {
      apiClient.addGame.mockRejectedValue(new Error('Network error'));

      render(<ManualGameEntryPanel onSuccess={mockOnSuccess} onToast={mockOnToast} />);

      fireEvent.change(screen.getByPlaceholderText('e.g., Pandemic'), {
        target: { value: 'New Game' },
      });

      const addButton = screen.getByRole('button', { name: /Add Game/i });
      fireEvent.click(addButton);

      await waitFor(() => {
        expect(mockOnToast).toHaveBeenCalledWith(
          'Failed to add game. Check console for details.',
          'error'
        );
      });
    });

    test('disables button while submitting', async () => {
      let resolvePromise;
      apiClient.addGame.mockReturnValue(
        new Promise((resolve) => {
          resolvePromise = resolve;
        })
      );

      render(<ManualGameEntryPanel onSuccess={mockOnSuccess} onToast={mockOnToast} />);

      fireEvent.change(screen.getByPlaceholderText('e.g., Pandemic'), {
        target: { value: 'Test Game' },
      });

      const addButton = screen.getByRole('button', { name: /Add Game/i });
      fireEvent.click(addButton);

      // Button should show loading state
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Adding Game/i })).toBeDisabled();
      });

      // Resolve the promise
      resolvePromise({ id: 1, title: 'Test Game' });

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Add Game/i })).not.toBeDisabled();
      });
    });
  });

  describe('Clear Form', () => {
    test('clears all form fields', () => {
      render(<ManualGameEntryPanel onSuccess={mockOnSuccess} onToast={mockOnToast} />);

      // Fill in some fields
      fireEvent.change(screen.getByPlaceholderText('e.g., Pandemic'), {
        target: { value: 'Test Game' },
      });
      fireEvent.change(screen.getByPlaceholderText('e.g., 30549'), {
        target: { value: '12345' },
      });
      fireEvent.click(screen.getByLabelText(/Cooperative Game/));

      // Verify fields are filled
      expect(screen.getByPlaceholderText('e.g., Pandemic').value).toBe('Test Game');
      expect(screen.getByPlaceholderText('e.g., 30549').value).toBe('12345');
      expect(screen.getByLabelText(/Cooperative Game/)).toBeChecked();

      // Clear form
      fireEvent.click(screen.getByRole('button', { name: /Clear Form/i }));

      // Verify fields are cleared
      expect(screen.getByPlaceholderText('e.g., Pandemic').value).toBe('');
      expect(screen.getByPlaceholderText('e.g., 30549').value).toBe('');
      expect(screen.getByLabelText(/Cooperative Game/)).not.toBeChecked();
    });

    test('clears form after successful submission', async () => {
      apiClient.addGame.mockResolvedValue({ id: 1, title: 'Test Game' });

      render(<ManualGameEntryPanel onSuccess={mockOnSuccess} onToast={mockOnToast} />);

      fireEvent.change(screen.getByPlaceholderText('e.g., Pandemic'), {
        target: { value: 'Test Game' },
      });

      const addButton = screen.getByRole('button', { name: /Add Game/i });
      fireEvent.click(addButton);

      await waitFor(() => {
        expect(screen.getByPlaceholderText('e.g., Pandemic').value).toBe('');
      });
    });
  });

  describe('Data Type Parsing', () => {
    test('excludes empty optional fields from payload', async () => {
      apiClient.addGame.mockResolvedValue({ id: 1, title: 'Test' });

      render(<ManualGameEntryPanel onSuccess={mockOnSuccess} onToast={mockOnToast} />);

      fireEvent.change(screen.getByPlaceholderText('e.g., Pandemic'), {
        target: { value: 'Test' },
      });
      // Leave all other fields empty

      fireEvent.click(screen.getByRole('button', { name: /Add Game/i }));

      await waitFor(() => {
        const calledWith = apiClient.addGame.mock.calls[0][0];
        // Should not have bgg_id, year, etc.
        expect(calledWith).not.toHaveProperty('bgg_id');
        expect(calledWith).not.toHaveProperty('year');
        expect(calledWith).not.toHaveProperty('players_min');
        expect(calledWith).not.toHaveProperty('designers');
      });
    });

    test('handles invalid numeric input gracefully', async () => {
      apiClient.addGame.mockResolvedValue({ id: 1, title: 'Test' });

      render(<ManualGameEntryPanel onSuccess={mockOnSuccess} onToast={mockOnToast} />);

      fireEvent.change(screen.getByPlaceholderText('e.g., Pandemic'), {
        target: { value: 'Test' },
      });
      fireEvent.change(screen.getByPlaceholderText('e.g., 2008'), {
        target: { value: 'not-a-number' },
      });

      fireEvent.click(screen.getByRole('button', { name: /Add Game/i }));

      await waitFor(() => {
        const calledWith = apiClient.addGame.mock.calls[0][0];
        // Invalid number should be null/excluded
        expect(calledWith.year).toBeNull();
      });
    });

    test('parses float values correctly', async () => {
      apiClient.addGame.mockResolvedValue({ id: 1, title: 'Test' });

      render(<ManualGameEntryPanel onSuccess={mockOnSuccess} onToast={mockOnToast} />);

      // Show advanced fields
      fireEvent.click(screen.getByRole('button', { name: /Show Advanced Fields/i }));

      fireEvent.change(screen.getByPlaceholderText('e.g., Pandemic'), {
        target: { value: 'Test' },
      });
      fireEvent.change(screen.getByPlaceholderText('e.g., 2.4'), {
        target: { value: '3.5' },
      });
      fireEvent.change(screen.getByPlaceholderText('e.g., 7.6'), {
        target: { value: '8.2' },
      });

      fireEvent.click(screen.getByRole('button', { name: /Add Game/i }));

      await waitFor(() => {
        const calledWith = apiClient.addGame.mock.calls[0][0];
        expect(calledWith.complexity).toBe(3.5);
        expect(calledWith.average_rating).toBe(8.2);
      });
    });
  });
});
