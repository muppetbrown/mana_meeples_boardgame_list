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
    await user.type(screen.getByPlaceholderText('Item ID / SKU'), 'SKU-9');
    await user.clear(screen.getByPlaceholderText('In Stock (sleeves)'));
    await user.type(screen.getByPlaceholderText('In Stock (sleeves)'), '120');
    await user.clear(screen.getByPlaceholderText('Ordered (packs)'));
    await user.type(screen.getByPlaceholderText('Ordered (packs)'), '3');
    await user.click(screen.getByRole('button', { name: 'Add Product' }));
    await waitFor(() =>
      expect(apiClient.createSleeveProduct).toHaveBeenCalledWith(
        expect.objectContaining({
          distributor: 'Dist', item_id: 'SKU-9', name: 'New', width_mm: 60, height_mm: 90,
          sleeves_per_pack: 50, price: 3.5, in_stock: 120, ordered: 3,
        })
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

  describe('stock filter and size groups', () => {
    const prod = (id, name, w, h, inStock, ordered = 0) => ({
      id, distributor: 'D', item_id: `S${id}`, name, width_mm: w, height_mm: h,
      sleeves_per_pack: 100, price: 4, in_stock: inStock, ordered, ordered_sleeves: ordered * 100,
    });
    const products = [
      prod(1, 'Euro Pack A', 59, 92, 200),
      prod(2, 'Mini US Pack', 41, 63, 0, 2),
      prod(3, 'American Pack', 57, 88, 50),
      prod(4, 'Weird Size', 100, 100, 10),
    ];
    const headings = () => screen.getAllByRole('heading', { level: 3 }).map((h) => h.textContent.replace(/\s*\d.*$/, '').trim());

    beforeEach(() => {
      apiClient.getSleeveProducts.mockResolvedValue(products);
    });

    test('groups products under named size groups by default, Other last', async () => {
      render(<SleeveInventoryTab />);
      await screen.findByText('Euro Pack A');
      expect(headings()).toEqual(['Mini American', 'Standard American', 'Standard European', 'Other sizes']);
      const euro = screen.getByRole('region', { name: 'Standard European sleeves' });
      expect(within(euro).getByText('Euro Pack A')).toBeInTheDocument();
      expect(within(euro).getByText(/1 product · 200 sleeves in stock/)).toBeInTheDocument();
    });

    test('group headers pluralise product counts', async () => {
      apiClient.getSleeveProducts.mockResolvedValue([
        prod(1, 'Euro A', 59, 92, 100),
        prod(2, 'Euro B', 59, 92, 50),
      ]);
      render(<SleeveInventoryTab />);
      await screen.findByText('Euro A');
      expect(screen.getByText(/2 products · 150 sleeves in stock/)).toBeInTheDocument();
    });

    test('to-order list can be shown flat without group headings', async () => {
      const user = userEvent.setup();
      render(<SleeveInventoryTab />);
      await user.click(await screen.findByText('To Order'));
      expect((await screen.findAllByRole('region', { name: /order list$/})).length).toBeGreaterThan(0);
      await user.click(screen.getByLabelText('Group by size'));
      expect(screen.queryByRole('region', { name: /order list$/ })).not.toBeInTheDocument();
      expect(screen.getByText('No matching product')).toBeInTheDocument();
    });

    test('group by size can be switched off for a flat table', async () => {
      const user = userEvent.setup();
      render(<SleeveInventoryTab />);
      await screen.findByText('Euro Pack A');
      await user.click(screen.getByLabelText('Group by size'));
      expect(screen.queryByRole('region', { name: /sleeves$/ })).not.toBeInTheDocument();
      expect(screen.getAllByRole('row')).toHaveLength(5); // header + 4 products
    });

    test('"In stock" hides out-of-stock products and updates the summary', async () => {
      const user = userEvent.setup();
      render(<SleeveInventoryTab />);
      await screen.findByText('Euro Pack A');
      await user.selectOptions(screen.getByLabelText('Stock'), 'in_stock');
      expect(screen.queryByText('Mini US Pack')).not.toBeInTheDocument();
      expect(screen.getByText('Euro Pack A')).toBeInTheDocument();
      expect(screen.getByText(/of 4/)).toBeInTheDocument();
    });

    test('out of stock and on order filters', async () => {
      const user = userEvent.setup();
      render(<SleeveInventoryTab />);
      await screen.findByText('Euro Pack A');
      await user.selectOptions(screen.getByLabelText('Stock'), 'out_of_stock');
      expect(screen.getByText('Mini US Pack')).toBeInTheDocument();
      expect(screen.queryByText('Euro Pack A')).not.toBeInTheDocument();
      await user.selectOptions(screen.getByLabelText('Stock'), 'on_order');
      expect(screen.getByText('Mini US Pack')).toBeInTheDocument();
      expect(screen.queryByText('American Pack')).not.toBeInTheDocument();
    });

    test('size group filter shows one group; name keywords beat size', async () => {
      const user = userEvent.setup();
      render(<SleeveInventoryTab />);
      await screen.findByText('Euro Pack A');
      await user.selectOptions(screen.getByLabelText('Size group'), 'mini_american');
      expect(screen.getByText('Mini US Pack')).toBeInTheDocument();
      expect(screen.queryByText('Euro Pack A')).not.toBeInTheDocument();
    });

    test('combined filters with no matches show an empty state and Reset filters restores the list', async () => {
      const user = userEvent.setup();
      render(<SleeveInventoryTab />);
      await screen.findByText('Euro Pack A');
      await user.selectOptions(screen.getByLabelText('Stock'), 'out_of_stock');
      await user.selectOptions(screen.getByLabelText('Size group'), 'standard_european');
      expect(screen.getByText('No products match these filters.')).toBeInTheDocument();
      await user.click(screen.getByText('Reset filters'));
      expect(screen.getByText('Euro Pack A')).toBeInTheDocument();
      expect(screen.getByText('Weird Size')).toBeInTheDocument();
    });

    test('stock filter is only offered on the inventory section', async () => {
      const user = userEvent.setup();
      render(<SleeveInventoryTab />);
      await screen.findByText('Euro Pack A');
      await user.click(screen.getByText('To Order'));
      expect(screen.queryByLabelText('Stock')).not.toBeInTheDocument();
    });

    test('to-order list is grouped with subtotals and filterable by size group', async () => {
      const user = userEvent.setup();
      apiClient.getToOrderList.mockResolvedValue([
        { width_mm: 59, height_mm: 92, total_needed: 300, deficit: 100, product: { product_name: 'Euro', distributor: 'D', item_id: 'E', packs_to_buy: 1, price_per_pack: 4, total_cost: 4 }, game_names: ['A'] },
        { width_mm: 41, height_mm: 63, total_needed: 50, deficit: 50, product: { product_name: 'Mini', distributor: 'D', item_id: 'M', packs_to_buy: 1, price_per_pack: 3, total_cost: 3 }, game_names: ['B'] },
        { width_mm: 41, height_mm: 63, total_needed: 20, deficit: 20, product: null, game_names: ['C'] },
      ]);
      render(<SleeveInventoryTab />);
      await user.click(await screen.findByText('To Order'));
      const mini = await screen.findByRole('region', { name: 'Mini American order list' });
      expect(within(mini).getByText(/2 sizes · deficit 70 · \$3\.00/)).toBeInTheDocument();
      expect(screen.getByRole('region', { name: 'Standard European order list' })).toBeInTheDocument();

      await user.selectOptions(screen.getByLabelText('Size group'), 'standard_european');
      expect(screen.queryByRole('region', { name: 'Mini American order list' })).not.toBeInTheDocument();

      await user.selectOptions(screen.getByLabelText('Size group'), 'tarot');
      expect(screen.getByText(/Nothing to order in this size group/)).toBeInTheDocument();
    });

    test('ready-to-sleeve can be filtered by size group and shows a group badge', async () => {
      const user = userEvent.setup();
      apiClient.getToSleeveList.mockResolvedValue([
        { game_id: 1, game_title: 'Euro Game', all_ready: true, ready_count: 1, total_count: 1,
          sleeves: [{ sleeve_id: 1, ready: true, card_name: null, width_mm: 59, height_mm: 92, quantity: 10, product_name: 'P', product_stock: 50 }] },
        { game_id: 2, game_title: 'Mini Game', all_ready: true, ready_count: 1, total_count: 1,
          sleeves: [{ sleeve_id: 2, ready: true, card_name: null, width_mm: 41, height_mm: 63, quantity: 10, product_name: 'P', product_stock: 50 }] },
      ]);
      render(<SleeveInventoryTab />);
      await user.click(await screen.findByText('Ready to Sleeve'));
      expect(await screen.findByText('Euro Game')).toBeInTheDocument();
      expect(screen.getByText('Standard European')).toBeInTheDocument();
      await user.selectOptions(screen.getByLabelText('Size group'), 'mini_american');
      expect(screen.queryByText('Euro Game')).not.toBeInTheDocument();
      expect(screen.getByText('Mini Game')).toBeInTheDocument();
      await user.selectOptions(screen.getByLabelText('Size group'), 'tarot');
      expect(screen.getByText(/No games ready to sleeve in this size group/)).toBeInTheDocument();
    });

    test('order CSV includes a size group column', async () => {
      const user = userEvent.setup();
      let blobText = '';
      window.URL.createObjectURL = vi.fn((blob) => {
        blob.text().then((t) => (blobText = t));
        return 'blob:x';
      });
      window.URL.revokeObjectURL = vi.fn();
      render(<SleeveInventoryTab />);
      await user.click(await screen.findByText('To Order'));
      await user.click(await screen.findByText('Export CSV'));
      await waitFor(() => expect(blobText).not.toBe(''));
      expect(blobText.split('\n')[0]).toContain('"Size group"');
      expect(blobText).toContain('"Standard Card Game"'); // 63x88 fixture
    });
  });
});
