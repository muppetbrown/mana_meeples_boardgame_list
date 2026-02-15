/**
 * SleeveShoppingListModal tests - Aggregated sleeve shopping list modal
 */
import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SleeveShoppingListModal from '../SleeveShoppingListModal';

// Mock the API client to prevent real HTTP requests
vi.mock('../../../api/client', () => ({
  getSleeveProducts: vi.fn().mockResolvedValue([]),
}));

import { getSleeveProducts } from '../../../api/client';

describe('SleeveShoppingListModal', () => {
  const mockOnClose = vi.fn();

  const mockShoppingList = [
    {
      width_mm: 63.5,
      height_mm: 88,
      total_quantity: 150,
      games_count: 2,
      variations_grouped: 1,
      game_names: ['Pandemic', 'Ticket to Ride'],
    },
    {
      width_mm: 41,
      height_mm: 63,
      total_quantity: 100,
      games_count: 3,
      variations_grouped: 2,
      game_names: ['Game A', 'Game B', 'Game C'],
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    getSleeveProducts.mockResolvedValue([]);

    // Mock DOM APIs for CSV download
    global.URL.createObjectURL = vi.fn(() => 'mock-url');
    global.URL.revokeObjectURL = vi.fn();

    // Mock anchor element click
    HTMLAnchorElement.prototype.click = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Rendering', () => {
    test('renders modal title', () => {
      render(<SleeveShoppingListModal shoppingList={mockShoppingList} onClose={mockOnClose} />);

      expect(screen.getByText('Sleeve Shopping List')).toBeInTheDocument();
    });

    test('returns null when shoppingList is not provided', () => {
      const { container } = render(<SleeveShoppingListModal shoppingList={null} onClose={mockOnClose} />);

      expect(container.firstChild).toBeNull();
    });

    test('renders table with headers', () => {
      render(<SleeveShoppingListModal shoppingList={mockShoppingList} onClose={mockOnClose} />);

      expect(screen.getByText('Size (mm)')).toBeInTheDocument();
      expect(screen.getByText('Total Qty')).toBeInTheDocument();
      expect(screen.getByText('Games')).toBeInTheDocument();
      expect(screen.getByText('Matched Product')).toBeInTheDocument();
      expect(screen.getByText('Stock')).toBeInTheDocument();
      expect(screen.getByText('Price/Pack')).toBeInTheDocument();
      expect(screen.getByText('Game Names')).toBeInTheDocument();
    });

    test('renders download and close buttons', () => {
      render(<SleeveShoppingListModal shoppingList={mockShoppingList} onClose={mockOnClose} />);

      expect(screen.getByRole('button', { name: 'Download CSV' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Close' })).toBeInTheDocument();
    });

    test('renders note about product matching', () => {
      render(<SleeveShoppingListModal shoppingList={mockShoppingList} onClose={mockOnClose} />);

      expect(screen.getByText(/Product matches use tolerance/)).toBeInTheDocument();
    });
  });

  describe('Table Content', () => {
    test('displays sleeve sizes', () => {
      render(<SleeveShoppingListModal shoppingList={mockShoppingList} onClose={mockOnClose} />);

      expect(screen.getByText('63.5 × 88')).toBeInTheDocument();
      expect(screen.getByText('41 × 63')).toBeInTheDocument();
    });

    test('displays total quantities', () => {
      render(<SleeveShoppingListModal shoppingList={mockShoppingList} onClose={mockOnClose} />);

      expect(screen.getByText('150')).toBeInTheDocument();
      expect(screen.getByText('100')).toBeInTheDocument();
    });

    test('displays games counts', () => {
      render(<SleeveShoppingListModal shoppingList={mockShoppingList} onClose={mockOnClose} />);

      const gamesCountCells = screen.getAllByText(/^[0-9]+$/);
      expect(gamesCountCells.length).toBeGreaterThan(0);
    });

    test('displays game names as comma-separated list', () => {
      render(<SleeveShoppingListModal shoppingList={mockShoppingList} onClose={mockOnClose} />);

      expect(screen.getByText('Pandemic, Ticket to Ride')).toBeInTheDocument();
      expect(screen.getByText('Game A, Game B, Game C')).toBeInTheDocument();
    });

    test('shows "No match" when no products loaded', () => {
      render(<SleeveShoppingListModal shoppingList={mockShoppingList} onClose={mockOnClose} />);

      const noMatchElements = screen.getAllByText('No match');
      expect(noMatchElements.length).toBe(2);
    });

    test('shows matched product info when products match', async () => {
      getSleeveProducts.mockResolvedValue([
        {
          id: 1,
          distributor: 'TestCo',
          name: 'Standard Sleeves',
          width_mm: 64,
          height_mm: 89,
          sleeves_per_pack: 100,
          price: 5.99,
          in_stock: 200,
          ordered: 0,
          ordered_sleeves: 0,
        },
      ]);

      render(<SleeveShoppingListModal shoppingList={mockShoppingList} onClose={mockOnClose} />);

      await waitFor(() => {
        expect(screen.getByText('Standard Sleeves')).toBeInTheDocument();
        expect(screen.getByText('TestCo')).toBeInTheDocument();
        expect(screen.getByText('200')).toBeInTheDocument();
        expect(screen.getByText('$5.99')).toBeInTheDocument();
      });
    });
  });

  describe('Close Button', () => {
    test('calls onClose when close button clicked', async () => {
      const user = userEvent.setup();

      render(<SleeveShoppingListModal shoppingList={mockShoppingList} onClose={mockOnClose} />);

      await user.click(screen.getByRole('button', { name: 'Close' }));

      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });
  });

  describe('CSV Download', () => {
    test('triggers CSV download when download button clicked', async () => {
      const user = userEvent.setup();

      render(<SleeveShoppingListModal shoppingList={mockShoppingList} onClose={mockOnClose} />);

      const downloadButton = screen.getByRole('button', { name: 'Download CSV' });
      await user.click(downloadButton);

      expect(HTMLAnchorElement.prototype.click).toHaveBeenCalled();
      expect(global.URL.createObjectURL).toHaveBeenCalled();
      expect(global.URL.revokeObjectURL).toHaveBeenCalledWith('mock-url');
    });

    test('generates CSV with correct headers', async () => {
      const user = userEvent.setup();

      render(<SleeveShoppingListModal shoppingList={mockShoppingList} onClose={mockOnClose} />);

      await user.click(screen.getByRole('button', { name: 'Download CSV' }));

      const blobCall = global.URL.createObjectURL.mock.calls[0][0];
      expect(blobCall.type).toBe('text/csv');
    });

    test('sets correct filename for download', async () => {
      const user = userEvent.setup();

      // Spy on createElement to capture the anchor element
      let capturedAnchor;
      const originalCreateElement = document.createElement.bind(document);
      vi.spyOn(document, 'createElement').mockImplementation((tag) => {
        const element = originalCreateElement(tag);
        if (tag === 'a') {
          capturedAnchor = element;
        }
        return element;
      });

      render(<SleeveShoppingListModal shoppingList={mockShoppingList} onClose={mockOnClose} />);

      await user.click(screen.getByRole('button', { name: 'Download CSV' }));

      expect(capturedAnchor.download).toBe('sleeve-shopping-list.csv');

      document.createElement.mockRestore();
    });

    test('includes all shopping list items in CSV', async () => {
      const user = userEvent.setup();

      render(<SleeveShoppingListModal shoppingList={mockShoppingList} onClose={mockOnClose} />);

      await user.click(screen.getByRole('button', { name: 'Download CSV' }));

      expect(global.URL.createObjectURL).toHaveBeenCalled();
    });
  });

  describe('Empty Shopping List', () => {
    test('renders empty table when shopping list is empty array', () => {
      render(<SleeveShoppingListModal shoppingList={[]} onClose={mockOnClose} />);

      // Table headers should still be present
      expect(screen.getByText('Size (mm)')).toBeInTheDocument();

      // But no data rows
      const table = screen.getByRole('table');
      const tbody = table.querySelector('tbody');
      expect(tbody.children.length).toBe(0);
    });
  });

  describe('Long Game Names', () => {
    test('handles long list of game names', () => {
      const manyGames = [
        {
          width_mm: 63.5,
          height_mm: 88,
          total_quantity: 500,
          games_count: 10,
          variations_grouped: 1,
          game_names: [
            'Game 1',
            'Game 2',
            'Game 3',
            'Game 4',
            'Game 5',
            'Game 6',
            'Game 7',
            'Game 8',
            'Game 9',
            'Game 10',
          ],
        },
      ];

      render(<SleeveShoppingListModal shoppingList={manyGames} onClose={mockOnClose} />);

      expect(
        screen.getByText(
          'Game 1, Game 2, Game 3, Game 4, Game 5, Game 6, Game 7, Game 8, Game 9, Game 10'
        )
      ).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    test('buttons are keyboard accessible', async () => {
      const user = userEvent.setup();

      render(<SleeveShoppingListModal shoppingList={mockShoppingList} onClose={mockOnClose} />);

      const closeButton = screen.getByRole('button', { name: 'Close' });
      closeButton.focus();
      expect(closeButton).toHaveFocus();

      await user.keyboard('{Enter}');
      expect(mockOnClose).toHaveBeenCalled();
    });

    test('table has proper structure', () => {
      render(<SleeveShoppingListModal shoppingList={mockShoppingList} onClose={mockOnClose} />);

      const table = screen.getByRole('table');
      expect(table).toBeInTheDocument();

      expect(screen.getByRole('columnheader', { name: 'Size (mm)' })).toBeInTheDocument();
      expect(screen.getByRole('columnheader', { name: 'Total Qty' })).toBeInTheDocument();
    });
  });

  describe('Special Characters in Game Names', () => {
    test('handles game names with commas', () => {
      const specialNames = [
        {
          width_mm: 70,
          height_mm: 120,
          total_quantity: 50,
          games_count: 2,
          variations_grouped: 1,
          game_names: ['Game, With Comma', 'Another Game'],
        },
      ];

      render(<SleeveShoppingListModal shoppingList={specialNames} onClose={mockOnClose} />);

      expect(screen.getByText('Game, With Comma, Another Game')).toBeInTheDocument();
    });
  });

  describe('Decimal Sizes', () => {
    test('displays decimal sleeve sizes correctly', () => {
      const decimalSizes = [
        {
          width_mm: 63.5,
          height_mm: 88.9,
          total_quantity: 100,
          games_count: 1,
          variations_grouped: 1,
          game_names: ['Test Game'],
        },
      ];

      render(<SleeveShoppingListModal shoppingList={decimalSizes} onClose={mockOnClose} />);

      expect(screen.getByText('63.5 × 88.9')).toBeInTheDocument();
    });
  });
});
