import App from './App';

// Mock the API client
jest.mock('./api/client', () => ({
  getPublicGames: jest.fn().mockResolvedValue({
    items: [],
    total: 0,
    page: 1,
    page_size: 24
  }),
  getCategoryCounts: jest.fn().mockResolvedValue({
    all: 0,
    COOP_ADVENTURE: 0,
    GATEWAY_STRATEGY: 0,
    CORE_STRATEGY: 0,
    KIDS_FAMILIES: 0,
    PARTY_ICEBREAKERS: 0,
  }),
  getGame: jest.fn().mockResolvedValue(null),
  getGames: jest.fn().mockResolvedValue([]),
  bulkImportCsv: jest.fn().mockResolvedValue({}),
  bulkCategorizeCsv: jest.fn().mockResolvedValue({}),
  addGame: jest.fn().mockResolvedValue({}),
  updateGame: jest.fn().mockResolvedValue({}),
  deleteGame: jest.fn().mockResolvedValue({}),
  validateAdminToken: jest.fn().mockResolvedValue(true),
}));

describe('App', () => {
  it('imports without errors', () => {
    // Basic smoke test - App module should import successfully
    expect(App).toBeDefined();
    expect(typeof App).toBe('function');
  });
});
