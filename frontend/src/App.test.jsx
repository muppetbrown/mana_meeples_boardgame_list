import { vi } from 'vitest';
import App from './App';

// Mock the API client
vi.mock('./api/client', () => ({
  getPublicGames: vi.fn().mockResolvedValue({
    items: [],
    total: 0,
    page: 1,
    page_size: 24
  }),
  getCategoryCounts: vi.fn().mockResolvedValue({
    all: 0,
    COOP_ADVENTURE: 0,
    GATEWAY_STRATEGY: 0,
    CORE_STRATEGY: 0,
    KIDS_FAMILIES: 0,
    PARTY_ICEBREAKERS: 0,
  }),
  getGame: vi.fn().mockResolvedValue(null),
  getGames: vi.fn().mockResolvedValue([]),
  bulkImportCsv: vi.fn().mockResolvedValue({}),
  bulkCategorizeCsv: vi.fn().mockResolvedValue({}),
  addGame: vi.fn().mockResolvedValue({}),
  updateGame: vi.fn().mockResolvedValue({}),
  deleteGame: vi.fn().mockResolvedValue({}),
  validateAdminToken: vi.fn().mockResolvedValue(true),
}));

describe('App', () => {
  it('imports without errors', () => {
    // Basic smoke test - App module should import successfully
    expect(App).toBeDefined();
    expect(typeof App).toBe('function');
  });
});
