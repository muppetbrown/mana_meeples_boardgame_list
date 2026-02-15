/**
 * SleevesListTable tests - Sleeve requirements table with status management
 */
import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SleevesListTable from '../SleevesListTable';
import * as apiClient from '../../../api/client';

// Mock API client
vi.mock('../../../api/client', () => ({
  getGameSleeves: vi.fn(),
  updateSleeveStatus: vi.fn(),
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

      // Should show empty state after error
      await waitFor(() => {
        expect(screen.getByText('No sleeve requirements defined for this game.')).toBeInTheDocument();
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
});
