/**
 * Testing utilities for frontend tests
 * Provides reusable helpers for rendering components with context providers
 */
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StaffProvider } from '../context/StaffContext';

/**
 * Render a component with all required providers
 * @param {React.ReactElement} ui - Component to render
 * @param {Object} options - Rendering options
 * @param {Object} options.staffContext - Mock staff context values
 * @param {Array<string>} options.initialRoutes - Initial router routes
 * @param {Object} options.queryClient - Custom QueryClient instance
 * @returns {RenderResult} Testing library render result
 */
export const renderWithProviders = (ui, options = {}) => {
  const {
    staffContext = {},
    initialRoutes = ['/'],
    queryClient,
    ...renderOptions
  } = options;

  // Create default mock staff context
  const mockStaffContext = {
    library: [],
    selectedCategory: 'all',
    categoryCounts: {},
    showToast: vi.fn(),
    setShowToast: vi.fn(),
    toastMessage: '',
    setToastMessage: vi.fn(),
    toastType: 'success',
    setToastType: vi.fn(),
    isModalOpen: false,
    setIsModalOpen: vi.fn(),
    modalMode: 'add',
    setModalMode: vi.fn(),
    selectedGame: null,
    setSelectedGame: vi.fn(),
    csvImportText: '',
    setCsvImportText: vi.fn(),
    csvCategorizeText: '',
    setCsvCategorizeText: vi.fn(),
    loadLibrary: vi.fn(),
    ...staffContext,
  };

  // Create a new QueryClient with disabled retries for tests
  const testQueryClient = queryClient || new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        cacheTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });

  // Wrapper component with all providers
  const Wrapper = ({ children }) => (
    <QueryClientProvider client={testQueryClient}>
      <StaffProvider value={mockStaffContext}>
        <MemoryRouter initialEntries={initialRoutes}>
          {children}
        </MemoryRouter>
      </StaffProvider>
    </QueryClientProvider>
  );

  return {
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
    mockStaffContext,
  };
};

/**
 * Create a mock game object with default values
 * @param {Object} overrides - Properties to override
 * @returns {Object} Mock game object
 */
export const createMockGame = (overrides = {}) => ({
  id: 1,
  title: 'Test Game',
  bgg_id: 123456,
  year: 2020,
  players_min: 2,
  players_max: 4,
  playtime_min: 30,
  playtime_max: 60,
  mana_meeple_category: 'GATEWAY_STRATEGY',
  complexity: 2.5,
  average_rating: 7.5,
  status: 'OWNED',
  designers: ['Test Designer'],
  mechanics: ['Hand Management', 'Set Collection'],
  publishers: ['Test Publisher'],
  description: 'A test game description',
  thumbnail_url: 'https://example.com/thumb.jpg',
  image: 'https://example.com/image.jpg',
  nz_designer: false,
  is_cooperative: false,
  min_age: 10,
  ...overrides,
});

/**
 * Create an array of mock games
 * @param {number} count - Number of games to create
 * @param {Object} baseOverrides - Base properties for all games
 * @returns {Array<Object>} Array of mock games
 */
export const createMockGames = (count, baseOverrides = {}) => {
  return Array.from({ length: count }, (_, index) =>
    createMockGame({
      id: index + 1,
      bgg_id: 100000 + index,
      title: `Test Game ${index + 1}`,
      ...baseOverrides,
    })
  );
};

/**
 * Wait for async updates to complete
 * Useful for waiting for state updates after async operations
 */
export const waitForAsync = () => new Promise(resolve => setTimeout(resolve, 0));

/**
 * Create a mock fetch response
 * @param {*} data - Response data
 * @param {number} status - HTTP status code
 * @returns {Promise} Mock response promise
 */
export const createMockResponse = (data, status = 200) => {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  });
};

/**
 * Create a mock rejected fetch response
 * @param {string} message - Error message
 * @param {number} status - HTTP status code
 * @returns {Promise} Rejected promise
 */
export const createMockError = (message, status = 500) => {
  const error = new Error(message);
  error.status = status;
  return Promise.reject(error);
};
