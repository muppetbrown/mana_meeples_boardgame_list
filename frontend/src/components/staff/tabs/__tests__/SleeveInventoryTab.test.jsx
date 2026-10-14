/**
 * SleeveInventoryTab tests - products, auto-match, ready-to-sleeve, to-order, CSV export
 */
import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SleeveInventoryTab } from '../SleeveInventoryTab';
import * as apiClient from '../../../../api/client';

vi.mock('../../../../api/client', () => ({
  getSleeveProducts: vi.fn(),
  createSleeveProduct: vi.fn(),
  updateSleeveProduct: vi.fn(),
  deleteSleeveProduct: vi.fn(),
  runSleeveMatching: vi.fn(),
  getToOrderList: vi.fn(),
  getToSleeveList: vi.fn(),
  updateSleeveStatus: vi.fn(),
}));

const product = {
  id: 1, distributor: 'Games Dist', item_id: 'SKU1', name: 'Std Card Sleeves',
  width_mm: 63, height_mm: 88, sleeves_per_pack: 100, price: 4.5, in_stock: 200, ordered: 2, ordered_sleeves: 200,
};

const toSleeve = [
  {
    game_id: 10, game_title: 'Wingspan', all_ready: false, ready_count: 1, total_count: 2,
    sleeves: [
      { sleeve_id: 100, ready: true, card_name: 'Birds', width_mm: 57, height_mm: 87, quantity: 50, product_name: 'P', product_stock: 80 },
      { sleeve_id: 101, ready: false, card_name: null, width_mm: 40, height_mm: 60, quantity: 10, product_name: null, product_stock: null },
    ],
  },
];

const toOrder = [
  {
    width_mm: 63, height_mm: 88, total_needed: 300, deficit: 100,
    product: { product_name: 'Std, "Premium"', distributor: 'D', item_id: '=SKU', packs_to_buy: 1, price_per_pack: 4.5, total_cost: 4.5 },
    game_names: ['Catan, Seafarers', 'Azul'],
  },
  { width_mm: 10, height_mm: 20, total_needed: 5, deficit: 5, product: null, game_names: ['Tiny'] },
];

describe('SleeveInventoryTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.confirm = vi.fn(() => true);
    apiClient.getSleeveProducts.mockResolvedValue([product]);
    apiClient.getToSleeveList.mockResolvedValue(toSleeve);
    apiClient.getToOrderList.mockResolvedValue(toOrder);
  });
  afterEach(() => vi.restoreAllMocks());

  test('loads and lists products with a stock summary', async () => {
    render(<SleeveInventoryTab />);
    expect(await screen.findByText('Std Card Sleeves')).toBeInTheDocument();
    expect(screen.getByText(/total sleeves in stock/)).toBeInTheDocument();
  });

  test('deleting a product asks for confirmation and can be cancelled', async () => {
    const user = userEvent.setup();
    window.confirm = vi.fn(() => false);
    render(<SleeveInventoryTab />);
    await user.click(await screen.findByText('Del'));
    expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining('Std Card Sleeves'));
    expect(apiClient.deleteSleeveProduct).not.toHaveBeenCalled();
  });

  test('confirmed delete removes the product and reloads', async () => {
    const user = userEvent.setup();
    apiClient.deleteSleeveProduct.mockResolvedValue({});
    render(<SleeveInventoryTab />);
    await user.click(await screen.findByText('Del'));
    await waitFor(() => expect(apiClient.deleteSleeveProduct).toHaveBeenCalledWith(1));
    expect(await screen.findByText('Product deleted')).toBeInTheDocument();
    expect(apiClient.getSleeveProducts).toHaveBeenCalledTimes(2);
  });

  test('shows an error banner when loading products fails', async () => {
    apiClient.getSleeveProducts.mockRejectedValue(new Error('boom'));
    render(<SleeveInventoryTab />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Failed to load products');
  });

  test('auto-match shows progress only on its own button and reports results', async () => {
    const user = userEvent.setup();
    let resolve;
    apiClient.runSleeveMatching.mockReturnValue(new Promise((r) => (resolve = r)));
    render(<SleeveInventoryTab />);
    await screen.findByText('Std Card Sleeves');
    await user.click(screen.getByText('Run Auto-Match'));
    expect(screen.getByRole('button', { name: 'Running...' })).toBeDisabled();
    // Product table is still visible (shared loading flag no longer blanks it)
    expect(screen.getByText('Std Card Sleeves')).toBeInTheDocument();
    resolve({ matched: 3, unmatched: 1, total: 4 });
    expect(await screen.findByText('Matching complete: 3 matched, 1 unmatched out of 4')).toBeInTheDocument();
  });

  test('auto-match failure shows an error', async () => {
    const user = userEvent.setup();
    apiClient.runSleeveMatching.mockRejectedValue(new Error('x'));
    render(<SleeveInventoryTab />);
    await screen.findByText('Std Card Sleeves');
    await user.click(screen.getByText('Run Auto-Match'));
    expect(await screen.findByText('Matching failed')).toBeInTheDocument();
  });

  test('adds a product via the form', async () => {
    const user = userEvent.setup();
    apiClient.createSleeveProduct.mockResolvedValue({});
    render(<SleeveInventoryTab />);
    await user.click(await screen.findByText('+ Add Product'));
    await user.type(screen.getByPlaceholderText('Distributor *'), 'Dist');
    await user.type(screen.getByPlaceholderText('Product Name *'), 'New');
    await user.type(screen.getByPlaceholderText('Width (mm) *'), '60');
    await user.type(screen.getByPlaceholderText('Height (mm) *'), '90');
    await user.type(screen.getByPlaceholderText('Sleeves/Pack *'), '50');
    await user.type(screen.getByPlaceholderText('Price/Pack *'), '3.5');
    await user.click(screen.getByRole('button', { name: 'Add Product' }));
    await waitFor(() =>
      expect(apiClient.createSleeveProduct).toHaveBeenCalledWith(
        expect.objectContaining({ distributor: 'Dist', name: 'New', width_mm: 60, height_mm: 90, sleeves_per_pack: 50, price: 3.5 })
      )
    );
    expect(await screen.findByText('Product added')).toBeInTheDocument();
  });

  test('edits stock inline', async () => {
    const user = userEvent.setup();
    apiClient.updateSleeveProduct.mockResolvedValue({});
    render(<SleeveInventoryTab />);
    await user.click(await screen.findByText('Edit'));
    const stock = screen.getAllByRole('spinbutton')[1];
    await user.clear(stock);
    await user.type(stock, '250');
    await user.click(screen.getByText('Save'));
    await waitFor(() =>
      expect(apiClient.updateSleeveProduct).toHaveBeenCalledWith(1, expect.objectContaining({ in_stock: 250 }))
    );
  });

  test('ready-to-sleeve marks only ready sleeves and reports partial progress', async () => {
    const user = userEvent.setup();
    apiClient.updateSleeveStatus.mockResolvedValue({});
    render(<SleeveInventoryTab />);
    await user.click(await screen.findByText('Ready to Sleeve'));
    await user.click(await screen.findByText('Mark 1 of 2 Sleeved'));
    await waitFor(() => expect(apiClient.updateSleeveStatus).toHaveBeenCalledTimes(1));
    expect(apiClient.updateSleeveStatus).toHaveBeenCalledWith(100, true);
    expect(await screen.findByText('"Wingspan" partially (1/2) sleeved')).toBeInTheDocument();
  });

  test('ready-to-sleeve reports failures (e.g. insufficient stock)', async () => {
    const user = userEvent.setup();
    apiClient.updateSleeveStatus.mockRejectedValue(new Error('stock'));
    render(<SleeveInventoryTab />);
    await user.click(await screen.findByText('Ready to Sleeve'));
    await user.click(await screen.findByText('Mark 1 of 2 Sleeved'));
    expect(await screen.findByText(/0 sleeved, 1 failed/)).toBeInTheDocument();
  });

  test('to-order list exports a properly quoted CSV', async () => {
    const user = userEvent.setup();
    let blobText = '';
    window.URL.createObjectURL = vi.fn((blob) => {
      blob.text().then((t) => (blobText = t));
      return 'blob:x';
    });
    window.URL.revokeObjectURL = vi.fn();
    render(<SleeveInventoryTab />);
    await user.click(await screen.findByText('To Order'));
    expect(await screen.findByText('No matching product')).toBeInTheDocument();
    await user.click(screen.getByText('Export CSV'));
    await waitFor(() => expect(blobText).not.toBe(''));
    // commas and quotes are escaped; leading '=' is neutralised against formula injection
    expect(blobText).toContain('"Std, ""Premium"""');
    expect(blobText).toContain(`"'=SKU"`);
    expect(blobText).toContain('"Catan, Seafarers; Azul"');
    expect(blobText).toContain('"No match"');
  });

  test('empty states render for each section', async () => {
    const user = userEvent.setup();
    apiClient.getSleeveProducts.mockResolvedValue([]);
    apiClient.getToSleeveList.mockResolvedValue([]);
    apiClient.getToOrderList.mockResolvedValue([]);
    render(<SleeveInventoryTab />);
    expect(await screen.findByText(/No sleeve products added yet/)).toBeInTheDocument();
    await user.click(screen.getByText('Ready to Sleeve'));
    expect(await screen.findByText(/No games have sleevable requirements/)).toBeInTheDocument();
    await user.click(screen.getByText('To Order'));
    expect(await screen.findByText(/Nothing to order/)).toBeInTheDocument();
  });
});
