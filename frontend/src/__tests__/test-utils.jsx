// frontend/src/__tests__/test-utils.jsx
/**
 * Test utilities for React Query integration
 * Phase 2 Performance: Provides QueryClientProvider wrapper for tests
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

/**
 * Creates a new QueryClient for each test with default options
 * Configured for testing: no retries, no caching, console logs off
 */
export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false, // Don't retry failed queries in tests
        cacheTime: 0, // Don't cache in tests (use gcTime in v5)
        gcTime: 0, // Don't keep unused data in tests
        staleTime: 0, // Always consider data stale in tests
      },
      mutations: {
        retry: false, // Don't retry failed mutations in tests
      },
    },
    logger: {
      log: console.log,
      warn: console.warn,
      error: () => {}, // Silence errors in tests
    },
  });
}

/**
 * Wrapper component that provides QueryClient to components under test
 * Usage:
 *   render(<MyComponent />, { wrapper: createQueryWrapper() })
 */
export function createQueryWrapper() {
  const queryClient = createTestQueryClient();

  return function QueryWrapper({ children }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };
}

/**
 * Custom render function with QueryClient provider
 * Usage:
 *   renderWithQuery(<MyComponent />)
 */
export function renderWithQuery(ui, options = {}) {
  const { render } = require('@testing-library/react');
  const queryClient = createTestQueryClient();

  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>,
    options
  );
}
