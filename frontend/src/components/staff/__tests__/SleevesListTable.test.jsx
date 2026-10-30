/**
 * SleevesListTable tests - Sleeve requirements table with status management
 */
import React from 'react';
import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SleevesListTable from '../SleevesListTable';
import * as apiClient from '../../../api/client';

// Mock API client
vi.mock('../../../api/client', () => ({
  getGameSleeves: vi.fn(),
  updateSleeveStatus: vi.fn(),
  createGameSleeve: vi.fn(),
  updateGameSleeve: vi.fn(),
  deleteGameSleeve: vi.fn(),
  updateGameSleeveStatus: vi.fn(),
}));

describe('SleevesListTable', () => {
  const mockOnSleeveUpdate = vi.fn();

  const mockSleeves = [
    {
      id: 1,
      card_name: 'Standard Cards',
      width_mm: 63.5,
      height_mm: 88,
      quantity: 100,
      is_sleeved: false,
      notes: 'Main deck',
      matched_product_id: null,
      matched_product_name: null,
      matched_product_stock: null,
    },
    {
      id: 2,
      card_name: 'Mini Cards',
      width_mm: 41,
      height_mm: 63,
      quantity: 50,
      is_sleeved: true,
      notes: null,
      matched_product_id: 1,
      matched_product_name: 'Test Sleeves',
      matched_product_stock: 200,
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    apiClient.getGameSleeves.mockResolvedValue(mockSleeves);
    apiClient.updateSleeveStatus.mockResolvedValue({ success: true, sleeve_id: 1, is_sleeved: true, stock_info: null });
  });

  describe('Loading State', () => {
    test('shows loading message initially', () => {
      apiClient.getGameSleeves.mockReturnValue(new Promise(() => {})); // Never resolves

      render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      expect(screen.getByText('Loading sleeve requirements...')).toBeInTheDocument();
    });

    test('loads sleeves on mount', async () => {
      render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await waitFor(() => {
        expect(apiClient.getGameSleeves).toHaveBeenCalledWith(1);
      });
    });

    test('reloads sleeves when gameId changes', async () => {
      const { rerender } = render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await waitFor(() => {
        expect(apiClient.getGameSleeves).toHaveBeenCalledWith(1);
      });

      rerender(<SleevesListTable gameId={2} onSleeveUpdate={mockOnSleeveUpdate} />);

      await waitFor(() => {
        expect(apiClient.getGameSleeves).toHaveBeenCalledWith(2);
      });
    });
  });

  describe('Empty State', () => {
    test('shows no sleeves message when array is empty', async () => {
      apiClient.getGameSleeves.mockResolvedValue([]);

      render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await waitFor(() => {
        expect(screen.getByText('No sleeve requirements defined for this game.')).toBeInTheDocument();
      });
    });

    test('does not show table when no sleeves', async () => {
      apiClient.getGameSleeves.mockResolvedValue([]);

      render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await waitFor(() => {
        expect(screen.queryByRole('table')).not.toBeInTheDocument();
      });
    });
  });

  describe('Table Rendering', () => {
    test('renders table with sleeves data', async () => {
      render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await waitFor(() => {
        expect(screen.getByRole('table')).toBeInTheDocument();
      });

      expect(screen.getByText('Standard Cards')).toBeInTheDocument();
      expect(screen.getByText('Mini Cards')).toBeInTheDocument();
    });

    test('renders table headers', async () => {
      render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await waitFor(() => {
        expect(screen.getByText('Sleeved')).toBeInTheDocument();
      });

      expect(screen.getByText('Card Type')).toBeInTheDocument();
      expect(screen.getByText('Size (mm)')).toBeInTheDocument();
      expect(screen.getByText('Quantity')).toBeInTheDocument();
      expect(screen.getByText('Matched Product')).toBeInTheDocument();
      expect(screen.getByText('Notes')).toBeInTheDocument();
    });

    test('renders card sizes correctly', async () => {
      render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await waitFor(() => {
        expect(screen.getByText('63.5 × 88')).toBeInTheDocument();
      });

      expect(screen.getByText('41 × 63')).toBeInTheDocument();
    });

    test('renders quantities', async () => {
      render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await waitFor(() => {
        expect(screen.getByText('100')).toBeInTheDocument();
      });

      expect(screen.getByText('50')).toBeInTheDocument();
    });

    test('renders notes when present', async () => {
      render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await waitFor(() => {
        expect(screen.getByText('Main deck')).toBeInTheDocument();
      });
    });

    test('shows dash when notes are missing', async () => {
      render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await waitFor(() => {
        const dashes = screen.getAllByText('—');
        expect(dashes.length).toBeGreaterThan(0);
      });
    });

    test('defaults to "Standard Cards" when card_name is missing', async () => {
      const sleeveWithoutName = {
        id: 3,
        card_name: null,
        width_mm: 70,
        height_mm: 120,
        quantity: 30,
        is_sleeved: false,
        notes: null,
      };

      apiClient.getGameSleeves.mockResolvedValue([sleeveWithoutName]);

      render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await waitFor(() => {
        expect(screen.getByText('Standard Cards')).toBeInTheDocument();
      });
    });
  });

  describe('Checkbox Status', () => {
    test('renders checkboxes for all sleeves', async () => {
      render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await waitFor(() => {
        const checkboxes = screen.getAllByRole('checkbox');
        expect(checkboxes).toHaveLength(2);
      });
    });

    test('shows correct checked state', async () => {
      render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await waitFor(() => {
        const checkboxes = screen.getAllByRole('checkbox');
        expect(checkboxes[0]).not.toBeChecked(); // First sleeve is not sleeved
        expect(checkboxes[1]).toBeChecked(); // Second sleeve is sleeved
      });
    });

    test('toggles sleeve status when checkbox clicked', async () => {
      const user = userEvent.setup();

      render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await waitFor(() => {
        expect(screen.getAllByRole('checkbox')).toHaveLength(2);
      });

      const firstCheckbox = screen.getAllByRole('checkbox')[0];
      await user.click(firstCheckbox);

      await waitFor(() => {
        expect(apiClient.updateSleeveStatus).toHaveBeenCalledWith(1, true);
      });
    });

    test('reloads sleeves after status update', async () => {
      const user = userEvent.setup();

      render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await waitFor(() => {
        expect(screen.getAllByRole('checkbox')).toHaveLength(2);
      });

      // Clear the initial load call
      apiClient.getGameSleeves.mockClear();

      const firstCheckbox = screen.getAllByRole('checkbox')[0];
      await user.click(firstCheckbox);

      await waitFor(() => {
        expect(apiClient.getGameSleeves).toHaveBeenCalledTimes(1);
      });
    });

    test('calls onSleeveUpdate callback after update', async () => {
      const user = userEvent.setup();

      render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await waitFor(() => {
        expect(screen.getAllByRole('checkbox')).toHaveLength(2);
      });

      const firstCheckbox = screen.getAllByRole('checkbox')[0];
      await user.click(firstCheckbox);

      await waitFor(() => {
        expect(mockOnSleeveUpdate).toHaveBeenCalledTimes(1);
      });
    });

    test('does not crash when onSleeveUpdate is not provided', async () => {
      const user = userEvent.setup();

      render(<SleevesListTable gameId={1} />); // No callback

      await waitFor(() => {
        expect(screen.getAllByRole('checkbox')).toHaveLength(2);
      });

      const firstCheckbox = screen.getAllByRole('checkbox')[0];
      await user.click(firstCheckbox);

      await waitFor(() => {
        expect(apiClient.updateSleeveStatus).toHaveBeenCalled();
      });
    });

    test('handles toggle error gracefully', async () => {
      const user = userEvent.setup();
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      apiClient.updateSleeveStatus.mockRejectedValue(new Error('Update failed'));

      render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await waitFor(() => {
        expect(screen.getAllByRole('checkbox')).toHaveLength(2);
      });

      const firstCheckbox = screen.getAllByRole('checkbox')[0];
      await user.click(firstCheckbox);

      await waitFor(() => {
        expect(consoleErrorSpy).toHaveBeenCalledWith(
          'Failed to update sleeve status:',
          expect.any(Error)
        );
      });

      consoleErrorSpy.mockRestore();
    });
  });

  describe('Fully Sleeved Indicator', () => {
    test('shows fully sleeved message when all sleeves are sleeved', async () => {
      const allSleeved = mockSleeves.map(s => ({ ...s, is_sleeved: true }));
      apiClient.getGameSleeves.mockResolvedValue(allSleeved);

      render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await waitFor(() => {
        expect(screen.getByText('All sleeve requirements are marked as sleeved!')).toBeInTheDocument();
      });
    });

    test('does not show fully sleeved message when some not sleeved', async () => {
      render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await waitFor(() => {
        expect(screen.queryByText('All sleeve requirements are marked as sleeved!')).not.toBeInTheDocument();
      });
    });

    test('does not show fully sleeved message when array is empty', async () => {
      apiClient.getGameSleeves.mockResolvedValue([]);

      render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await waitFor(() => {
        expect(screen.queryByText('All sleeve requirements are marked as sleeved!')).not.toBeInTheDocument();
      });
    });
  });

  describe('Summary', () => {
    test('displays correct summary count', async () => {
      render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await waitFor(() => {
        expect(screen.getByText(/1 of 2 sleeve types marked as sleeved/)).toBeInTheDocument();
      });
    });

    test('updates summary count correctly', async () => {
      const allSleeved = mockSleeves.map(s => ({ ...s, is_sleeved: true }));
      apiClient.getGameSleeves.mockResolvedValue(allSleeved);

      render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await waitFor(() => {
        expect(screen.getByText(/2 of 2 sleeve types marked as sleeved/)).toBeInTheDocument();
      });
    });

    test('shows 0 of N when none sleeved', async () => {
      const noneSleeved = mockSleeves.map(s => ({ ...s, is_sleeved: false }));
      apiClient.getGameSleeves.mockResolvedValue(noneSleeved);

      render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await waitFor(() => {
        expect(screen.getByText(/0 of 2 sleeve types marked as sleeved/)).toBeInTheDocument();
      });
    });
  });

  describe('Row Highlighting', () => {
    test('applies green background to sleeved rows', async () => {
      const { container } = render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await waitFor(() => {
        const rows = container.querySelectorAll('tbody tr');
        expect(rows[1]).toHaveClass('bg-green-50'); // Second row is sleeved
      });
    });

    test('does not apply green background to unsleeved rows', async () => {
      const { container } = render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await waitFor(() => {
        const rows = container.querySelectorAll('tbody tr');
        expect(rows[0]).not.toHaveClass('bg-green-50'); // First row is not sleeved
      });
    });
  });

  describe('Error Handling', () => {
    test('handles API error on load gracefully', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      apiClient.getGameSleeves.mockRejectedValue(new Error('API Error'));

      render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await waitFor(() => {
        expect(consoleErrorSpy).toHaveBeenCalledWith(
          'Failed to load sleeves:',
          expect.any(Error)
        );
      });

      // Should show a visible error state with a retry option, not silently
      // look like "no sleeves defined" (which is indistinguishable from a
      // real empty state and previously masked load failures).
      await waitFor(() => {
        expect(screen.getByText(/Failed to load sleeve data/)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument();
      });

      consoleErrorSpy.mockRestore();
    });
  });

  describe('Accessibility', () => {
    test('checkboxes are keyboard accessible', async () => {
      const user = userEvent.setup();

      render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await waitFor(() => {
        expect(screen.getAllByRole('checkbox')).toHaveLength(2);
      });

      const firstCheckbox = screen.getAllByRole('checkbox')[0];
      firstCheckbox.focus();
      expect(firstCheckbox).toHaveFocus();

      await user.keyboard(' ');

      await waitFor(() => {
        expect(apiClient.updateSleeveStatus).toHaveBeenCalled();
      });
    });

    test('table has proper structure', async () => {
      render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await waitFor(() => {
        expect(screen.getByRole('table')).toBeInTheDocument();
      });

      expect(screen.getByRole('columnheader', { name: /sleeved/i })).toBeInTheDocument();
      expect(screen.getByRole('columnheader', { name: /card type/i })).toBeInTheDocument();
    });
  });

  describe('Adding a sleeve requirement', () => {
    test('sends decimal width and height to the API without truncating them', async () => {
      const user = userEvent.setup();
      apiClient.createGameSleeve.mockResolvedValue({ id: 99 });

      render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await user.click(await screen.findByText('+ Add Sleeve Requirement'));

      const width = screen.getByLabelText('Card width (mm)');
      const height = screen.getByLabelText('Card height (mm)');

      // Decimal sizes must be accepted by the inputs (step="any")
      expect(width).toHaveAttribute('step', 'any');
      expect(height).toHaveAttribute('step', 'any');

      await user.type(width, '63.5');
      await user.type(height, '88.9');
      await user.type(screen.getByLabelText('Number of cards'), '60');
      await user.click(screen.getByRole('button', { name: 'Save' }));

      await waitFor(() => {
        expect(apiClient.createGameSleeve).toHaveBeenCalledWith(
          1,
          expect.objectContaining({ width_mm: 63.5, height_mm: 88.9, quantity: 60 })
        );
      });
    });

    test('rejects a zero or negative size', async () => {
      const user = userEvent.setup();

      render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await user.click(await screen.findByText('+ Add Sleeve Requirement'));
      await user.type(screen.getByLabelText('Card width (mm)'), '0');
      await user.type(screen.getByLabelText('Card height (mm)'), '88');
      await user.type(screen.getByLabelText('Number of cards'), '10');
      await user.click(screen.getByRole('button', { name: 'Save' }));

      expect(await screen.findByText('Width and height must be greater than zero.')).toBeInTheDocument();
      expect(apiClient.createGameSleeve).not.toHaveBeenCalled();
    });
  });

  describe('Editing a sleeve requirement', () => {
    test('saves corrected values via updateGameSleeve and refreshes', async () => {
      const user = userEvent.setup();
      apiClient.updateGameSleeve.mockResolvedValue({ id: 1 });

      render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await user.click((await screen.findAllByText('Edit'))[0]);
      const w = screen.getByLabelText('Card width (mm)');
      expect(w).toHaveValue(63.5);
      await user.clear(w);
      await user.type(w, '59');
      const h = screen.getByLabelText('Card height (mm)');
      await user.clear(h);
      await user.type(h, '91');
      await user.click(screen.getByRole('button', { name: 'Save changes' }));

      await waitFor(() => {
        expect(apiClient.updateGameSleeve).toHaveBeenCalledWith(
          1,
          expect.objectContaining({ width_mm: 59, height_mm: 91, quantity: 100, notes: 'Main deck' })
        );
      });
      expect(mockOnSleeveUpdate).toHaveBeenCalled();
    });

    test('rejects invalid values and shows API errors', async () => {
      const user = userEvent.setup();
      apiClient.updateGameSleeve.mockRejectedValue(new Error('x'));

      render(<SleevesListTable gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);

      await user.click((await screen.findAllByText('Edit'))[0]);
      const q = screen.getByLabelText('Number of cards');
      await user.clear(q);
      await user.click(screen.getByRole('button', { name: 'Save changes' }));
      expect(await screen.findByText('Width, height, and quantity must be numbers.')).toBeInTheDocument();

      await user.type(q, '0');
      await user.click(screen.getByRole('button', { name: 'Save changes' }));
      expect(await screen.findByText('Width, height, and quantity must be greater than zero.')).toBeInTheDocument();

      await user.clear(q);
      await user.type(q, '5');
      await user.click(screen.getByRole('button', { name: 'Save changes' }));
      expect(await screen.findByText('Failed to save changes. Please try again.')).toBeInTheDocument();

      await user.click(screen.getByRole('button', { name: 'Cancel' }));
      expect(screen.queryByLabelText('Card width (mm)')).not.toBeInTheDocument();
    });
  });
  describe('flushPending', () => {
    const renderWithRef = () => {
      const ref = React.createRef();
      render(<SleevesListTable ref={ref} gameId={1} onSleeveUpdate={mockOnSleeveUpdate} />);
      return ref;
    };

    test('resolves true and saves nothing when no form is open', async () => {
      const ref = renderWithRef();
      await screen.findByText('+ Add Sleeve Requirement');
      let ok;
      await act(async () => { ok = await ref.current.flushPending(); });
      expect(ok).toBe(true);
      expect(apiClient.createGameSleeve).not.toHaveBeenCalled();
      expect(apiClient.updateGameSleeve).not.toHaveBeenCalled();
    });

    test('ignores an open but empty add form', async () => {
      const user = userEvent.setup();
      const ref = renderWithRef();
      await user.click(await screen.findByText('+ Add Sleeve Requirement'));
      let ok;
      await act(async () => { ok = await ref.current.flushPending(); });
      expect(ok).toBe(true);
      expect(apiClient.createGameSleeve).not.toHaveBeenCalled();
    });

    test('saves a filled-in add form', async () => {
      const user = userEvent.setup();
      apiClient.createGameSleeve.mockResolvedValue({});
      const ref = renderWithRef();
      await user.click(await screen.findByText('+ Add Sleeve Requirement'));
      await user.type(screen.getByLabelText('Card width (mm)'), '59');
      await user.type(screen.getByLabelText('Card height (mm)'), '91');
      await user.type(screen.getByLabelText('Number of cards'), '110');
      let ok;
      await act(async () => { ok = await ref.current.flushPending(); });
      expect(ok).toBe(true);
      expect(apiClient.createGameSleeve).toHaveBeenCalledWith(1, expect.objectContaining({
        width_mm: 59, height_mm: 91, quantity: 110,
      }));
    });

    test('resolves false and keeps the form when the add form is invalid', async () => {
      const user = userEvent.setup();
      const ref = renderWithRef();
      await user.click(await screen.findByText('+ Add Sleeve Requirement'));
      await user.type(screen.getByLabelText('Card width (mm)'), '59');
      let ok;
      await act(async () => { ok = await ref.current.flushPending(); });
      expect(ok).toBe(false);
      expect(apiClient.createGameSleeve).not.toHaveBeenCalled();
      expect(screen.getByText('Width, height, and quantity must be numbers.')).toBeInTheDocument();
    });

    test('saves a changed edit form', async () => {
      const user = userEvent.setup();
      apiClient.updateGameSleeve.mockResolvedValue({});
      const ref = renderWithRef();
      await user.click((await screen.findAllByText('Edit'))[0]);
      const qty = screen.getByLabelText('Number of cards');
      await user.clear(qty);
      await user.type(qty, '120');
      let ok;
      await act(async () => { ok = await ref.current.flushPending(); });
      expect(ok).toBe(true);
      expect(apiClient.updateGameSleeve).toHaveBeenCalledWith(1, expect.objectContaining({ quantity: 120 }));
    });

    test('closes an unchanged edit form without saving', async () => {
      const user = userEvent.setup();
      const ref = renderWithRef();
      await user.click((await screen.findAllByText('Edit'))[0]);
      let ok;
      await act(async () => { ok = await ref.current.flushPending(); });
      expect(ok).toBe(true);
      expect(apiClient.updateGameSleeve).not.toHaveBeenCalled();
      expect(screen.queryByLabelText('Number of cards')).not.toBeInTheDocument();
    });
  });
});
